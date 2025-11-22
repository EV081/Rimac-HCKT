import json
import boto3
import uuid
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from googleapiclient.discovery import build
from utils import get_google_creds 

def json_serial(obj):
    if isinstance(obj, (datetime)):
        return obj.isoformat()
    raise TypeError (f"Type {type(obj)} not serializable")

def create_medical_appointment(cita):
    
    doctor_email = cita.get('doctor_email')
    patient_email = cita.get('patient_email')
    patient_name = cita.get('patient_name', 'Paciente')
    reason = cita.get('reason', 'Consulta General')
    
    start_iso = cita.get('start_iso') 
    end_iso = cita.get('end_iso')     
    
    if not doctor_email or not patient_email:
        # Lanzamos excepción para detener el flujo inmediatamente
        raise ValueError("Faltan correos electrónicos del doctor o paciente")

    # 2. Autenticación
    creds = get_google_creds()
    service = build('calendar', 'v3', credentials=creds)

    # 3. Crear el cuerpo del evento
    event_body = {
        'summary': f'Consulta: {patient_name} - Dr/a. Solicitado',
        'description': f'Motivo de consulta: {reason}.\n\nLink de videollamada adjunto.',
        'start': {
            'dateTime': start_iso,
            'timeZone': 'America/Lima', 
        },
        'end': {
            'dateTime': end_iso,
            'timeZone': 'America/Lima',
        },
        'attendees': [
            {'email': doctor_email, 'displayName': 'Doctor'},
            {'email': patient_email, 'displayName': 'Paciente'}
        ],
        'conferenceData': {
            'createRequest': {
                'requestId': f"meet-{uuid.uuid4()}", 
                'conferenceSolutionKey': {'type': "hangoutsMeet"}
            }
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 15},
            ],
        },
    }

    # 4. Enviar a Google
    response = service.events().insert(
        calendarId='primary', 
        body=event_body, 
        sendUpdates='all', 
        conferenceDataVersion=1
    ).execute()

    return {
        "meet_link": response.get('hangoutLink'),
        "event_link": response.get('htmlLink'),
        "event_id": response.get('id')
    }

# CASO 2: Recordatorio de Pastillas
def create_recurring_event(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        patient_email = body.get('patient_email')
        pill_name = body.get('pill_name')
        start_iso = body.get('start_time') 
        # CORRECCIÓN: Validar end_time o calcularlo si no viene
        end_iso = body.get('end_time') 
        days = body.get('days_count', 7)

        if not start_iso or not end_iso:
             return {"statusCode": 400, "body": json.dumps({"error": "Faltan fechas de inicio o fin"})}

        creds = get_google_creds()
        service = build('calendar', 'v3', credentials=creds)

        recurrence_rule = [f'RRULE:FREQ=DAILY;COUNT={days}']

        event_body = {
            'summary': f'💊 Tomar: {pill_name}',
            'description': 'Recordatorio médico automatizado.',
            'start': {'dateTime': start_iso, 'timeZone': 'America/Lima'},
            'end': {'dateTime': end_iso, 'timeZone': 'America/Lima'},
            'recurrence': recurrence_rule,
            'attendees': [{'email': patient_email}],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 0}, # Al momento
                    {'method': 'popup', 'minutes': 10}, 
                ],
            },
        }

        response = service.events().insert(
            calendarId='primary', 
            body=event_body, 
            sendUpdates='all'
        ).execute()

        return {
            "statusCode": 200, 
            "body": json.dumps({"message": "Tratamiento agendado", "link": response.get('htmlLink')})
        }

    except Exception as e:
        print(f"Error: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

def create_cita(event, context):
    try:
        print(event)
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})

        patient_email = body['patient_email']
        patient_name = body.get('patient_name', 'Paciente')
        doctor_email = body['doctor_email']
        doctor_name= body.get('doctor_name', 'Doctor')
        razon_cita = body['razon_cita']
        hora_inicio_peru= body['hora_inicio_peru']
        hora_fin_peru= body['hora_fin_peru']
        
        nombre_tabla = os.environ["TABLE_NAME"]

        fmt = "%Y-%m-%d %H:%M"
        # Definir zona horaria
        lima_tz = ZoneInfo("America/Lima")
        
        dt_inicio_pe = datetime.strptime(hora_inicio_peru, fmt).replace(tzinfo=lima_tz)
        dt_fin_pe    = datetime.strptime(hora_fin_peru, fmt).replace(tzinfo=lima_tz)

        # Convertir a UTC para guardar en DB (buena práctica)
        dt_inicio_utc = dt_inicio_pe.astimezone(ZoneInfo("UTC"))
        dt_fin_utc    = dt_fin_pe.astimezone(ZoneInfo("UTC"))
        
        uuidv4 = str(uuid.uuid4())
        
        datos_para_calendar = {
            'patient_email': patient_email,
            'patient_name': patient_name,
            'doctor_email': doctor_email,
            'doctor_name': doctor_name,
            'reason': razon_cita,
            'start_iso': dt_inicio_pe.isoformat(), 
            'end_iso': dt_fin_pe.isoformat()
        }

        response_calendar = create_medical_appointment(datos_para_calendar)
        
        # 2. Preparar objeto para DynamoDB
        cita_db = {
            'tenant_id': f"{patient_email}#{doctor_email}",
            'uuid': uuidv4,
            'patient_email': patient_email,
            'patient_name': patient_name,
            'doctor_email': doctor_email,
            'doctor_name': doctor_name,
            'hora_inicio_utc': dt_inicio_utc.isoformat(),
            'hora_fin_utc': dt_fin_utc.isoformat(),
            'razon_cita': razon_cita,
            'meet_link': response_calendar.get('meet_link'), 
            'event_id': response_calendar.get('event_id')
        }

        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(nombre_tabla)
        
        # Guardar en DB
        table.put_item(Item=cita_db)
        
        print(f"Cita creada: {cita_db}")
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Cita creada exitosamente',
                'cita': cita_db
            }, default=json_serial) # default ayuda si hay objetos datetime sueltos
        }

    except KeyError as e:
        return {
            "statusCode": 400, 
            "body": json.dumps({"error": f"Falta campo requerido: {str(e)}"})
        }
    except ValueError as e:
        return {
            "statusCode": 400, 
            "body": json.dumps({"error": str(e)})
        }
    except Exception as e:
        print(f"Error no controlado: {e}")
        return {
            "statusCode": 500, 
            "body": json.dumps({"error": str(e)})
        }
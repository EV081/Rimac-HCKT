import json
import boto3
import uuid
import os
import math
import pytz # Requiere Layer en Lambda
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta # Requiere Layer en Lambda
from zoneinfo import ZoneInfo # Nativo en Python 3.9+
from googleapiclient.discovery import build # Requiere Layer
from utils import get_google_creds 

dynamodb = boto3.resource('dynamodb')

def json_serial(obj):
    """Helper para serializar objetos datetime a string ISO"""
    if isinstance(obj, (datetime)):
        return obj.isoformat()
    raise TypeError (f"Type {type(obj)} not serializable")

def create_medical_appointment_event(cita):
    """Crea un evento único en G-Calendar con Meet (Cita Médica)"""
    
    doctor_email = cita.get('doctor_email')
    patient_email = cita.get('patient_email')
    patient_name = cita.get('patient_name', 'Paciente')
    reason = cita.get('reason', 'Consulta General')
    start_iso = cita.get('start_iso') 
    end_iso = cita.get('end_iso')     
    
    if not doctor_email or not patient_email:
        raise ValueError("Faltan correos electrónicos del doctor o paciente")

    # Autenticación (Tu cuenta actúa como secretaria)
    creds = get_google_creds()
    service = build('calendar', 'v3', credentials=creds)

    event_body = {
        'summary': f'Consulta: {patient_name} - Dr/a. Solicitado',
        'description': f'Motivo de consulta: {reason}.\n\nAgendado por secretaría.',
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
        # Configuración para generar link de Google Meet
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

    response = service.events().insert(
        calendarId='primary',  # 'primary' es TU calendario (Secretario)
        body=event_body, 
        sendUpdates='all',     # Envía correos a Doctor y Paciente
        conferenceDataVersion=1
    ).execute()

    return {
        "meet_link": response.get('hangoutLink'),
        "event_link": response.get('htmlLink'),
        "event_id": response.get('id')
    }

def create_cita(event, context):
    try:
        # 1. Parseo seguro del body
        body = event.get('body', {})
        if isinstance(body, str):
            body = json.loads(body)

        # 2. Extracción de datos
        patient_email = body.get('patient_email')
        patient_name = body.get('patient_name', 'Paciente')
        doctor_email = body.get('doctor_email')
        doctor_name = body.get('doctor_name', 'Doctor')
        razon_cita = body.get('razon_cita')
        hora_inicio_peru = body.get('hora_inicio_peru')
        hora_fin_peru = body.get('hora_fin_peru')
        
        nombre_tabla = os.environ.get("TABLE_NAME")
        if not nombre_tabla:
            raise ValueError("Variable de entorno TABLE_NAME no configurada")

        # 3. Manejo de Fechas (Lima -> UTC)
        fmt = "%Y-%m-%d %H:%M"
        lima_tz = ZoneInfo("America/Lima")
        
        dt_inicio_pe = datetime.strptime(hora_inicio_peru, fmt).replace(tzinfo=lima_tz)
        dt_fin_pe    = datetime.strptime(hora_fin_peru, fmt).replace(tzinfo=lima_tz)

        dt_inicio_utc = dt_inicio_pe.astimezone(ZoneInfo("UTC"))
        dt_fin_utc    = dt_fin_pe.astimezone(ZoneInfo("UTC"))
        
        # 4. Crear evento en Google Calendar
        datos_para_calendar = {
            'patient_email': patient_email,
            'patient_name': patient_name,
            'doctor_email': doctor_email,
            'reason': razon_cita,
            'start_iso': dt_inicio_pe.isoformat(), 
            'end_iso': dt_fin_pe.isoformat()
        }

        response_calendar = create_medical_appointment_event(datos_para_calendar)
        
        # 5. Guardar en DynamoDB
        uuidv4 = str(uuid.uuid4())
        cita_db = {
            'tenant_id': f"{patient_email}#{doctor_email}", # Partition Key
            'uuid': uuidv4,                                  # Sort Key
            'patient_email': patient_email,
            'patient_name': patient_name,
            'doctor_email': doctor_email,
            'doctor_name': doctor_name,
            'hora_inicio_utc': dt_inicio_utc.isoformat(),
            'hora_fin_utc': dt_fin_utc.isoformat(),
            'razon_cita': razon_cita,
            'meet_link': response_calendar.get('meet_link'), 
            'event_id': response_calendar.get('event_id'),
            'created_at': datetime.now().isoformat()
        }

        table = dynamodb.Table(nombre_tabla)
        table.put_item(Item=cita_db)
        
        print(f"Cita creada: {cita_db}")
        
        return {
            'statusCode': 200,
            'headers': { "Access-Control-Allow-Origin": "*" },
            'body': json.dumps({
                'message': 'Cita creada exitosamente',
                'cita': cita_db
            }, default=json_serial)
        }

    except KeyError as e:
        return {"statusCode": 400, "body": json.dumps({"error": f"Falta campo: {str(e)}"}, default=str)}
    except ValueError as e:
        return {"statusCode": 400, "body": json.dumps({"error": str(e)}, default=str)}
    except Exception as e:
        print(f"Error critico: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)}, default=str)}

def create_recurring_event(event, context):
    try:
        # 1. OBTENCIÓN Y SANITIZACIÓN DEL BODY
        raw_body = event.get('body', '{}')
        print(f"RAW BODY RECIBIDO: {repr(raw_body)}") 

        body = {}
        if isinstance(raw_body, str):
            try:
                clean_body = raw_body.replace('\xa0', ' ').strip()
                body = json.loads(clean_body)
            except json.JSONDecodeError as e:
                return {
                    "statusCode": 400, 
                    "body": json.dumps({"error": "JSON inválido", "detalle": str(e)})
                }
        else:
            body = raw_body

        patient_email = body.get('patient_email')
        pill_name = body.get('pill_name')
        medicion_duracion = body.get('medicion_duracion') 
        duracion = int(body.get('duracion', 1))
        indicacion = body.get('indicacion') 
        medicion_frecuencia = body.get('medicion_frecuencia') 
        
        raw_frecuencia = body.get('frecuencia')
        frecuencia = int(raw_frecuencia) if raw_frecuencia else 1
        if frecuencia < 1: frecuencia = 1
        
        indicaciones_consumo = body.get('indicaciones_consumo', '')

        # 2. CONFIGURACIÓN DE TIEMPO BASE (Lima)
        lima_tz = pytz.timezone('America/Lima')
        lima_now = datetime.now(lima_tz).replace(second=0, microsecond=0)

        creds = get_google_creds() 
        service = build('calendar', 'v3', credentials=creds)
        created_links = [] 

        # ==============================================================================
        # CASO 1: HAY INDICACIÓN (COMIDAS) -> SIEMPRE RRULE NATIVA
        # ==============================================================================
        if indicacion in ['Desayuno', 'Almuerzo', 'Cena']:
            print("ESTRATEGIA: RRULE NATIVA (Comidas)")
            
            meal_times = {
                'Desayuno': {'hour': 8, 'minute': 0},
                'Almuerzo': {'hour': 13, 'minute': 0},
                'Cena':     {'hour': 20, 'minute': 0}
            }
            target = meal_times[indicacion]
            start_dt = lima_now.replace(hour=target['hour'], minute=target['minute'], second=0)
            end_dt = start_dt + timedelta(minutes=30)
            
            description = f"Recordatorio médico: {pill_name}.\n{indicaciones_consumo}\nTomar después del {indicacion}."
            
            recurrence_rule = []
            if medicion_duracion == 'Dias':
                recurrence_rule = [f'RRULE:FREQ=DAILY;COUNT={duracion}']
            else:
                until_str = (lima_now + relativedelta(months=+duracion)).astimezone(pytz.utc).strftime('%Y%m%dT%H%M%SZ')
                recurrence_rule = [f'RRULE:FREQ=DAILY;UNTIL={until_str}']

            event_body = {
                'summary': f'💊 Tomar: {pill_name}',
                'description': description,
                'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'America/Lima'},
                'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'America/Lima'},
                'recurrence': recurrence_rule,
                'attendees': [{'email': patient_email}],
                'reminders': {'useDefault': False, 'overrides': [{'method': 'popup', 'minutes': 0}]}
            }
            response = service.events().insert(calendarId='primary', body=event_body, sendUpdates='all').execute()
            created_links.append(response.get('htmlLink'))

        else:
            
            if medicion_frecuencia == 'Dias':
                print("ESTRATEGIA: RRULE NATIVA (Por Días)")
                
                start_dt = lima_now
                end_dt = start_dt + timedelta(minutes=15)
                description = f"Recordatorio médico: {pill_name}.\n{indicaciones_consumo}\nTomar cada {frecuencia} Dias."
                
                until_str = ""
                if medicion_duracion == 'Dias':
                    until_str = (lima_now + timedelta(days=duracion)).astimezone(pytz.utc).strftime('%Y%m%dT%H%M%SZ')
                else:
                    until_str = (lima_now + relativedelta(months=+duracion)).astimezone(pytz.utc).strftime('%Y%m%dT%H%M%SZ')
                
                recurrence_rule = [f'RRULE:FREQ=DAILY;INTERVAL={frecuencia};UNTIL={until_str}']

                event_body = {
                    'summary': f'💊 Tomar: {pill_name}',
                    'description': description,
                    'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'America/Lima'},
                    'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'America/Lima'},
                    'recurrence': recurrence_rule,
                    'attendees': [{'email': patient_email}],
                    'reminders': {'useDefault': False, 'overrides': [{'method': 'popup', 'minutes': 0}]}
                }
                response = service.events().insert(calendarId='primary', body=event_body, sendUpdates='all').execute()
                created_links.append(response.get('htmlLink'))
            
            # 2.B: FRECUENCIA ES HORAS (Ej: Cada 8 horas) -> USAR BUCLE FOR (Para evitar error 400)
            else:

                total_horas = 0
                if medicion_duracion == 'Dias':
                    total_horas = duracion * 24
                else: # Meses
                    total_horas = (duracion * 30) * 24
                    
                count = math.ceil(total_horas / frecuencia)
                if count < 1: count = 1
                if count > 100: count = 100 # Seguridad

                current_start_dt = lima_now
                
                for i in range(count):
                    current_end_dt = current_start_dt + timedelta(minutes=15)
                    iter_desc = f"Recordatorio médico: {pill_name}.\n{indicaciones_consumo}\nToma {i+1} de {count}."
                    
                    event_body = {
                        'summary': f'💊 Tomar: {pill_name} ({i+1}/{count})',
                        'description': iter_desc,
                        'start': {'dateTime': current_start_dt.isoformat(), 'timeZone': 'America/Lima'},
                        'end': {'dateTime': current_end_dt.isoformat(), 'timeZone': 'America/Lima'},
                        'attendees': [{'email': patient_email}],
                        'reminders': {'useDefault': False, 'overrides': [{'method': 'popup', 'minutes': 0}]}
                    }
                    
                    try:
                        response = service.events().insert(calendarId='primary', body=event_body, sendUpdates='all').execute()
                        created_links.append(response.get('htmlLink'))
                    except Exception as e_inner:
                        print(f"Error en evento {i}: {e_inner}")
                    
                    current_start_dt = current_start_dt + timedelta(hours=frecuencia)

        return {
            "statusCode": 200, 
            "headers": { "Access-Control-Allow-Origin": "*" },
            "body": json.dumps({
                "message": "Tratamiento agendado exitosamente", 
                "total_eventos_creados": len(created_links),
                "links": created_links
            })
        }

    except Exception as e:
        print(f"Error CRITICO creando evento: {repr(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}



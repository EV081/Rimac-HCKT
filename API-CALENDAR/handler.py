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
    """Endpoint para Recordatorios de Pastillas (Eventos Recurrentes)"""
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

        # Variables para armar el payload
        start_payload = {}
        end_payload = {}
        recurrence_rule = []
        
        description = f"Recordatorio médico: {pill_name}.\n{indicaciones_consumo}"

        # ==============================================================================
        # ESTRATEGIA A: POR COMIDAS (Usamos Hora Local y TimeZone explícito)
        # ==============================================================================
        if indicacion in ['Desayuno', 'Almuerzo', 'Cena']:
            meal_times = {
                'Desayuno': {'hour': 8, 'minute': 0},
                'Almuerzo': {'hour': 13, 'minute': 0},
                'Cena':     {'hour': 20, 'minute': 0}
            }
            target = meal_times[indicacion]
            start_dt = lima_now.replace(hour=target['hour'], minute=target['minute'], second=0)
            end_dt = start_dt + timedelta(minutes=30)
            
            # Payload con TimeZone explícito (Requerido para reglas diarias locales)
            start_payload = {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'America/Lima'
            }
            end_payload = {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'America/Lima'
            }
            
            description += f"\nTomar después del {indicacion}."
            
            if medicion_duracion == 'Dias':
                recurrence_rule = [f'RRULE:FREQ=DAILY;COUNT={duracion}']
            else:
                treatment_end_date = lima_now + relativedelta(months=+duracion)
                until_utc = treatment_end_date.astimezone(pytz.utc)
                until_str = until_utc.strftime('%Y%m%dT%H%M%SZ')
                recurrence_rule = [f'RRULE:FREQ=DAILY;UNTIL={until_str}']

        # ==============================================================================
        # ESTRATEGIA B: POR FRECUENCIA (Forzamos UTC y SIN campo TimeZone)
        # ==============================================================================
        else:
            # Convertimos "Ahora" a UTC puro
            start_utc = lima_now.astimezone(pytz.utc)
            end_utc = start_utc + timedelta(minutes=15)
            
            # CORRECCIÓN CRÍTICA:
            # 1. Usamos formato 'Z' explícito.
            # 2. NO enviamos la clave 'timeZone' en el payload. Google infiere UTC por la 'Z'.
            # Esto evita el conflicto "Invalid recurrence rule" en reglas horarias.
            start_payload = {'dateTime': start_utc.strftime('%Y-%m-%dT%H:%M:%SZ')}
            end_payload = {'dateTime': end_utc.strftime('%Y-%m-%dT%H:%M:%SZ')}
            
            freq_map = {'Horas': 'HOURLY', 'Dias': 'DAILY'}
            rrule_freq = freq_map.get(medicion_frecuencia, 'DAILY')
            
            description += f"\nTomar cada {frecuencia} {medicion_frecuencia}."
            
            # Usamos COUNT (Matemática) para evitar errores de fecha UNTIL
            count = 1
            if medicion_duracion == 'Dias':
                total_horas = duracion * 24
                if medicion_frecuencia == 'Horas':
                    count = math.ceil(total_horas / frecuencia)
                else: # Dias
                    count = math.ceil(duracion / frecuencia)
            else:
                # Si es meses, asumimos 30 días promedio para calcular count aproximado
                # o usamos UNTIL si prefieres, pero COUNT es más seguro para HOURLY
                dias_aprox = duracion * 30
                total_horas = dias_aprox * 24
                count = math.ceil(total_horas / frecuencia)
            
            if count < 1: count = 1
            recurrence_rule = [f'RRULE:FREQ={rrule_freq};INTERVAL={frecuencia};COUNT={int(count)}']

        print(f"DEBUG RRULE: {recurrence_rule}")
        print(f"DEBUG START PAYLOAD: {start_payload}")

        # 3. LLAMADA A GOOGLE CALENDAR
        creds = get_google_creds() 
        service = build('calendar', 'v3', credentials=creds)

        event_body = {
            'summary': f'💊 Tomar: {pill_name}',
            'description': description,
            'start': start_payload,
            'end': end_payload,
            'recurrence': recurrence_rule,
            'attendees': [{'email': patient_email}],
            'reminders': {
                'useDefault': False,
                'overrides': [{'method': 'popup', 'minutes': 0}],
            },
        }

        print(f"DEBUG Event Body Completo: {event_body}")

        response = service.events().insert(
            calendarId='primary',
            body=event_body, 
            sendUpdates='all'
        ).execute()

        return {
            "statusCode": 200, 
            "headers": { "Access-Control-Allow-Origin": "*" },
            "body": json.dumps({
                "message": "Tratamiento agendado exitosamente", 
                "link": response.get('htmlLink'),
                "rule": recurrence_rule
            })
        }

    except Exception as e:
        print(f"Error CRITICO creando evento: {repr(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}



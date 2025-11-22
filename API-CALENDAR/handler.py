import json
import boto3
import uuid
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from googleapiclient.discovery import build
from utils import get_google_creds # Asumimos que tienes el utils.py del paso anterior

def create_medical_appointment(cita):
    try:
        doctor_email = cita.get('doctor_email')
        patient_email = cita.get('patient_email')
        patient_name = cita.get('patient_name', 'Paciente')
        reason = cita.get('reason', 'Consulta General')
        
        start_iso = cita.get('start_iso') # '2025-11-22T15:00:00'
        end_iso = cita.get('end_iso')     # '2025-11-22T15:30:00'
        
        # Validar datos mínimos
        if not doctor_email or not patient_email:
             return {"statusCode": 400, "body": json.dumps({"error": "Faltan correos"})}

        # 2. Autenticación (Tu cuenta sistema)
        creds = get_google_creds()
        service = build('calendar', 'v3', credentials=creds)

        # 3. Crear el cuerpo del evento
        # Nota: Tu cuenta es la organizadora, ellos son los asistentes.
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
            # AQUÍ ESTÁ LA CLAVE: Invitas a AMBOS
            'attendees': [
                {'email': doctor_email, 'displayName': 'Doctor'},
                {'email': patient_email, 'displayName': 'Paciente'}
            ],
            # Generar Link de Meet automáticamente
            'conferenceData': {
                'createRequest': {
                    'requestId': f"meet-{uuid.uuid4()}", 
                    'conferenceSolutionKey': {'type': "hangoutsMeet"}
                }
            },
            # Recordatorios para ambos
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60}, # 1 día antes
                    {'method': 'popup', 'minutes': 15},      # 15 min antes
                ],
            },
        }

        # 4. Enviar a Google
        response = service.events().insert(
            calendarId='primary', 
            body=event_body, 
            sendUpdates='all', # IMPORTANTE: Esto envía los emails de invitación a los dos
            conferenceDataVersion=1
        ).execute()

        return {
        "meet_link": response.get('hangoutLink'),
        "event_link": response.get('htmlLink'),
        "event_id": response.get('id')
        }
    
    except Exception as e:
        print(f"Error: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

# CASO 2: Recordatorio de Pastillas (Recurrente)
def create_recurring_event(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        patient_email = body.get('patient_email')
        pill_name = body.get('pill_name')
        start_iso = body.get('start_time') # Ej: '2025-11-22T08:00:00' (Primera dosis)
        days = body.get('days_count', 7)   # Por cuántos días
        
        # Calculamos el fin de la primera dosis (30 mins despues)
        # Necesitamos parsing básico de fechas aquí o pedir el end_time
        # Para simplificar, asumimos que el usuario manda el end_time de la PRIMERA dosis
        end_iso = body.get('end_time') 

        creds = get_google_creds()
        service = build('calendar', 'v3', credentials=creds)

        # RRULE: Magia de Google Calendar para repetir eventos
        # FREQ=DAILY;COUNT=7 -> Repetir diariamente 7 veces
        recurrence_rule = [f'RRULE:FREQ=DAILY;COUNT={days}']

        event_body = {
            'summary': f'💊 Tomar: {pill_name}',
            'description': 'Recordatorio médico automatizado.',
            'start': {'dateTime': start_iso, 'timeZone': 'America/Lima'},
            'end': {'dateTime': end_iso, 'timeZone': 'America/Lima'},
            'recurrence': recurrence_rule,
            'attendees': [
                {'email': patient_email}
            ],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 10}, # Notificación en el celular
                    {'method': 'email', 'minutes': 60},
                ],
            },
        }

        response = service.events().insert(
            calendarId='primary', 
            body=event_body, 
            sendUpdates='all'
        ).execute()

        return {"statusCode": 200, "body": json.dumps({"message": "Tratamiento agendado", "link": response.get('htmlLink')})}

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

def create_cita(event, context):
    try:
        print(event) # Log json en CloudWatch
        body = json.loads(event['body'])

        patient_email = body['patient_email']
        patient_name = body.get('patient_name', 'Paciente')
        doctor_email = body['doctor_email']
        doctor_name= body.get('doctor_name', 'Doctor')
        razon_cita = body['razon_cita']
        hora_inicio_peru= body['hora_inicio_peru']
        hora_fin_peru= body['hora_fin_peru']
        nombre_tabla = os.environ["TABLE_NAME"]

        fmt = "%Y-%m-%d %H:%M"
        dt_inicio_pe = datetime.strptime(hora_inicio_peru, fmt).replace(tzinfo=ZoneInfo("America/Lima"))
        dt_fin_pe    = datetime.strptime(hora_fin_peru, fmt).replace(tzinfo=ZoneInfo("America/Lima"))

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

        #Creamos evento calendar
        try:
            response_calendar = create_medical_appointment(datos_para_calendar)
        except Exception as e:
            print(f"Error creando evento en Calendar: {e}")
            return {"statusCode": 500, "body": json.dumps({"error": "Error creando evento en Calendar: " + str(e)})}
        cita_db = {
            'tenant_id': f"{patient_email}#{doctor_email}",
            'uuid': uuidv4,
            'patient_email': patient_email,
            'patient_name': patient_name,
            'doctor_email': doctor_email,
            'doctor_name': doctor_name,
            'hora_inicio_utc': dt_inicio_utc.isoformat(), # Guardamos UTC
            'hora_fin_utc': dt_fin_utc.isoformat(),       # Guardamos UTC
            'razon_cita': razon_cita,
            'meet_link': response_calendar.get('meet_link'), # Guardamos el link generado
            'event_id': response_calendar.get('event_id')
        }

        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(nombre_tabla)
        response = table.put_item(Item=cita_db)
        # Salida (json)
        print(cita_db) # Log json en CloudWatch
        return {
            'statusCode': 200,
            'cita': cita_db,
            'response': response
        }
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
    
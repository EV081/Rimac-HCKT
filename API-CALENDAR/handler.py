import json
import os
from googleapiclient.discovery import build
from utils import get_google_creds # Asumimos que tienes el utils.py del paso anterior

def create_medical_appointment(event, context):
    try:
        # 1. Recibir datos
        body = json.loads(event.get('body', '{}'))
        
        doctor_email = body.get('doctor_email')
        patient_email = body.get('patient_email')
        patient_name = body.get('patient_name', 'Paciente')
        reason = body.get('reason', 'Consulta General')
        
        start_iso = body.get('start_time') # '2025-11-22T15:00:00'
        end_iso = body.get('end_time')     # '2025-11-22T15:30:00'
        
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
                    'requestId': f"meet-{start_iso}", 
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
            "statusCode": 200, 
            "body": json.dumps({
                "message": "Cita agendada exitosamente",
                "meet_link": response.get('hangoutLink'), # Link de la video llamada
                "event_link": response.get('htmlLink')
            })
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
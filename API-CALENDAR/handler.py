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

def create_prescription_schedule(event, context):
    """
    Crea eventos recurrentes para todos los medicamentos de una receta.
    
    Body esperado (schema de recetas):
    {
        "receta_id": "rec-001",
        "paciente": "Juan Pérez",
        "patient_email": "juan.perez@email.com",
        "institucion": "Hospital General",
        "recetas": [
            {
                "producto": "Paracetamol",
                "dosis": "500 mg",
                "frecuencia": 8,
                "medicion_frecuencia": "horas",
                "duracion": 5,
                "duracion_frecuencia": "dias"
            },
            ...
        ],
        "start_date": "2024-01-15" (opcional)
    }
    """
    try:
        body = event.get('body', {})
        if isinstance(body, str):
            body = json.loads(body)
        
        # Validar campos requeridos
        patient_email = body.get('patient_email')
        if not patient_email:
            raise ValueError("El campo 'patient_email' es requerido")
        
        recetas = body.get('recetas', [])
        if not recetas:
            raise ValueError("Debe incluir al menos un medicamento en 'recetas'")
        
        paciente = body.get('paciente', 'Paciente')
        receta_id = body.get('receta_id', str(uuid.uuid4()))
        start_date = body.get('start_date')  # Formato: "YYYY-MM-DD"
        
        # Procesar cada medicamento
        results = []
        errors = []
        
        tz = pytz.timezone('America/Lima')
        base_time = datetime.now(tz).replace(second=0, microsecond=0)
        
        if start_date:
            try:
                base_time = datetime.strptime(start_date, '%Y-%m-%d')
                base_time = tz.localize(base_time.replace(hour=8, minute=0))
            except ValueError:
                raise ValueError("start_date debe tener formato 'YYYY-MM-DD'")
        
        # Horarios sugeridos para distribuir medicamentos
        suggested_times = [
            base_time.replace(hour=8, minute=0),   # 8:00 AM
            base_time.replace(hour=14, minute=0),  # 2:00 PM
            base_time.replace(hour=20, minute=0),  # 8:00 PM
        ]
        
        for idx, medicamento in enumerate(recetas):
            try:
                # Asignar hora de inicio escalonada
                start_time = suggested_times[idx % len(suggested_times)]
                
                # Crear evento individual para este medicamento
                medicamento_body = {
                    'patient_email': patient_email,
                    'producto': medicamento['producto'],
                    'dosis': medicamento.get('dosis'),
                    'frecuencia': medicamento['frecuencia'],
                    'medicion_frecuencia': medicamento['medicion_frecuencia'],
                    'duracion': medicamento['duracion'],
                    'duracion_frecuencia': medicamento['duracion_frecuencia'],
                    'start_time': start_time.strftime('%Y-%m-%d %H:%M')
                }
                
                # Llamar a la función de evento individual
                result = create_single_medication_event(medicamento_body)
                results.append(result)
                
            except Exception as e:
                error_msg = f"Error al agendar {medicamento.get('producto', 'medicamento')}: {str(e)}"
                print(error_msg)
                errors.append(error_msg)
        
        # Preparar respuesta
        response_body = {
            "message": f"Receta procesada: {len(results)} medicamentos agendados",
            "receta_id": receta_id,
            "paciente": paciente,
            "patient_email": patient_email,
            "medicamentos_agendados": results,
            "total_exitosos": len(results),
            "total_errores": len(errors)
        }
        
        if errors:
            response_body["errores"] = errors
        
        status_code = 200 if results else 400
        
        return {
            "statusCode": status_code,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps(response_body, ensure_ascii=False)
        }
        
    except Exception as e:
        print(f"Error al procesar receta: {e}")
        import traceback
        traceback.print_exc()
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)})
        }


def create_single_medication_event(medicamento_data):
    """
    Función auxiliar para crear un evento de medicamento individual.
    Retorna información del evento creado.
    """
    creds = get_google_creds()
    service = build('calendar', 'v3', credentials=creds)
    
    producto = medicamento_data['producto']
    dosis = medicamento_data.get('dosis')
    frecuencia = int(medicamento_data['frecuencia'])
    medicion_frecuencia = medicamento_data['medicion_frecuencia'].lower()
    duracion = int(medicamento_data['duracion'])
    duracion_frecuencia = medicamento_data['duracion_frecuencia'].lower()
    patient_email = medicamento_data['patient_email']
    
    # Parsear hora de inicio
    tz = pytz.timezone('America/Lima')
    start_time_str = medicamento_data.get('start_time')
    if start_time_str:
        start_dt = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M')
        start_dt = tz.localize(start_dt)
    else:
        start_dt = datetime.now(tz).replace(second=0, microsecond=0)
    
    end_dt = start_dt + timedelta(minutes=15)
    
    # Construir descripción
    description_parts = [f"💊 Medicamento: {producto}"]
    if dosis:
        description_parts.append(f"📊 Dosis: {dosis}")
    description_parts.append(f"⏰ Frecuencia: Cada {frecuencia} {medicion_frecuencia}")
    description_parts.append(f"📅 Duración: {duracion} {duracion_frecuencia}")
    description_parts.append("\n⚕️ Recordatorio automático de tratamiento médico")
    
    description = "\n".join(description_parts)
    
    # Calcular RRULE
    freq_map = {'horas': 'HOURLY', 'dias': 'DAILY', 'meses': 'MONTHLY'}
    rrule_freq = freq_map[medicion_frecuencia]
    
    count = calculate_event_count(
        frecuencia, medicion_frecuencia,
        duracion, duracion_frecuencia
    )
    
    if frecuencia == 1:
        recurrence_rule = [f'RRULE:FREQ={rrule_freq};COUNT={count}']
    else:
        recurrence_rule = [f'RRULE:FREQ={rrule_freq};INTERVAL={frecuencia};COUNT={count}']
    
    # Crear evento
    event_body = {
        'summary': f'💊 {producto}' + (f' - {dosis}' if dosis else ''),
        'description': description,
        'start': {
            'dateTime': start_dt.isoformat(),
            'timeZone': 'America/Lima'
        },
        'end': {
            'dateTime': end_dt.isoformat(),
            'timeZone': 'America/Lima'
        },
        'recurrence': recurrence_rule,
        'attendees': [{'email': patient_email}],
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': 0},
                {'method': 'email', 'minutes': 30}
            ],
        },
        'colorId': '10'
    }
    
    response = service.events().insert(
        calendarId='primary',
        body=event_body,
        sendUpdates='all'
    ).execute()
    
    return {
        "producto": producto,
        "dosis": dosis,
        "event_id": response.get('id'),
        "event_link": response.get('htmlLink'),
        "total_recordatorios": count,
        "start_time": start_dt.strftime('%Y-%m-%d %H:%M')
    }


def create_recurring_event(event, context):
    """
    Crea eventos recurrentes en Google Calendar para recordatorios de medicamentos.
    
    Body esperado:
    {
        "patient_email": "paciente@email.com",
        "producto": "Paracetamol",
        "dosis": "500 mg",
        "frecuencia": 8,
        "medicion_frecuencia": "horas",  # "horas", "dias", "meses"
        "duracion": 5,
        "duracion_frecuencia": "dias",   # "horas", "dias", "meses"
        "start_time": "2024-01-15 08:00" (opcional, default: ahora)
    }
    """
    try:
        # 1. Parseo del body
        body = event.get('body', {})
        if isinstance(body, str):
            body = json.loads(body)
            
        # Validación de campos requeridos
        patient_email = body.get('patient_email')
        if not patient_email:
            raise ValueError("El campo 'patient_email' es requerido")
            
        producto = body.get('producto')
        if not producto:
            raise ValueError("El campo 'producto' es requerido")
        
        dosis = body.get('dosis')  # Puede ser None
        frecuencia = int(body.get('frecuencia', 1))
        medicion_frecuencia = body.get('medicion_frecuencia', 'dias').lower()
        duracion = int(body.get('duracion', 1))
        duracion_frecuencia = body.get('duracion_frecuencia', 'dias').lower()
        
        # Validar valores de enum
        valid_mediciones = ['horas', 'dias', 'meses']
        if medicion_frecuencia not in valid_mediciones:
            raise ValueError(f"medicion_frecuencia debe ser uno de: {valid_mediciones}")
        if duracion_frecuencia not in valid_mediciones:
            raise ValueError(f"duracion_frecuencia debe ser uno de: {valid_mediciones}")
        
        # 2. Configuración de zona horaria y tiempo de inicio
        tz = pytz.timezone('America/Lima')
        
        # Permitir especificar hora de inicio o usar ahora
        start_time_str = body.get('start_time')
        if start_time_str:
            try:
                start_dt = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M')
                start_dt = tz.localize(start_dt)
            except ValueError:
                raise ValueError("start_time debe tener formato 'YYYY-MM-DD HH:MM'")
        else:
            start_dt = datetime.now(tz).replace(second=0, microsecond=0)
        
        # Duración del evento: 15 minutos
        end_dt = start_dt + timedelta(minutes=15)
        
        # 3. Construir descripción
        description_parts = [f"💊 Medicamento: {producto}"]
        if dosis:
            description_parts.append(f"📊 Dosis: {dosis}")
        description_parts.append(f"⏰ Frecuencia: Cada {frecuencia} {medicion_frecuencia}")
        description_parts.append(f"📅 Duración del tratamiento: {duracion} {duracion_frecuencia}")
        description_parts.append("\n⚕️ Recordatorio automático de tratamiento médico")
        
        description = "\n".join(description_parts)
        
        # 4. Calcular regla de recurrencia (RRULE)
        recurrence_rule = []
        
        # Mapeo de unidades a frecuencias de Google Calendar
        freq_map = {
            'horas': 'HOURLY',
            'dias': 'DAILY',
            'meses': 'MONTHLY'
        }
        
        rrule_freq = freq_map[medicion_frecuencia]
        
        # Calcular el número total de ocurrencias (COUNT)
        count = calculate_event_count(
            frecuencia, medicion_frecuencia,
            duracion, duracion_frecuencia
        )
        
        # Construir RRULE
        if frecuencia == 1:
            # Si la frecuencia es 1, no necesitamos INTERVAL
            recurrence_rule = [f'RRULE:FREQ={rrule_freq};COUNT={count}']
        else:
            # Si la frecuencia es mayor a 1, usamos INTERVAL
            recurrence_rule = [f'RRULE:FREQ={rrule_freq};INTERVAL={frecuencia};COUNT={count}']
        
        print(f"DEBUG - Producto: {producto}")
        print(f"DEBUG - Frecuencia: cada {frecuencia} {medicion_frecuencia}")
        print(f"DEBUG - Duración: {duracion} {duracion_frecuencia}")
        print(f"DEBUG - COUNT calculado: {count}")
        print(f"DEBUG - RRULE: {recurrence_rule}")
        
        # 5. Crear evento en Google Calendar
        creds = get_google_creds()
        service = build('calendar', 'v3', credentials=creds)
        
        event_body = {
            'summary': f'💊 {producto}' + (f' - {dosis}' if dosis else ''),
            'description': description,
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'America/Lima'
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'America/Lima'
            },
            'recurrence': recurrence_rule,
            'attendees': [{'email': patient_email}],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 0},  # Notificación al momento
                    {'method': 'email', 'minutes': 30}  # Email 30 min antes
                ],
            },
            'colorId': '10'  # Color verde para medicamentos
        }
        
        response = service.events().insert(
            calendarId='primary',
            body=event_body,
            sendUpdates='all'
        ).execute()
        
        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "message": "Tratamiento agendado exitosamente",
                "event_id": response.get('id'),
                "event_link": response.get('htmlLink'),
                "producto": producto,
                "dosis": dosis,
                "total_recordatorios": count,
                "recurrence_rule": recurrence_rule[0],
                "start_date": start_dt.strftime('%Y-%m-%d %H:%M')
            })
        }
        
    except ValueError as e:
        print(f"Error de validación: {e}")
        return {
            "statusCode": 400,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)})
        }
    except Exception as e:
        print(f"Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": f"Error interno: {str(e)}"})
        }


def calculate_event_count(frecuencia, medicion_frecuencia, duracion, duracion_frecuencia):
    """
    Calcula el número total de eventos (COUNT) para la regla de recurrencia.
    
    Ejemplos:
    - Cada 8 horas durante 5 días = (5 * 24) / 8 = 15 eventos
    - Cada 1 día durante 2 meses = 2 * 30 = 60 eventos
    - Cada 12 horas durante 3 días = (3 * 24) / 12 = 6 eventos
    """
    
    # Convertir todo a horas para facilitar el cálculo
    duracion_en_horas = 0
    
    if duracion_frecuencia == 'horas':
        duracion_en_horas = duracion
    elif duracion_frecuencia == 'dias':
        duracion_en_horas = duracion * 24
    elif duracion_frecuencia == 'meses':
        # Aproximación: 1 mes = 30 días
        duracion_en_horas = duracion * 30 * 24
    
    frecuencia_en_horas = 0
    
    if medicion_frecuencia == 'horas':
        frecuencia_en_horas = frecuencia
    elif medicion_frecuencia == 'dias':
        frecuencia_en_horas = frecuencia * 24
    elif medicion_frecuencia == 'meses':
        frecuencia_en_horas = frecuencia * 30 * 24
    
    # Calcular el número de eventos
    count = math.ceil(duracion_en_horas / frecuencia_en_horas)
    
    # Asegurar al menos 1 evento
    return max(1, count)



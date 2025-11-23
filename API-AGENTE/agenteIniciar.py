import json
import boto3
import os
import base64
from enum import Enum
from google import genai
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

# Configuración AWS
dynamodb = boto3.resource('dynamodb')
TABLE_USUARIOS = os.environ.get('TABLE_USUARIOS', 'Usuarios')
TABLE_SERVICIOS = os.environ.get('TABLE_SERVICIOS', 'Servicios')
TABLE_MEMORIA = os.environ.get('TABLE_MEMORIA_CONTEXTUAL', 'MemoriaContextual')
TABLE_HISTORIAL = os.environ.get('TABLE_HISTORIAL_MEDICO', 'HistorialMedico')

# Configuración Gemini
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)

class ContextoEnum(Enum):
    GENERAL = "General"
    SERVICIOS = "Servicios"
    WEARABLES = "Wearables"

def get_user_email(event):
    """Extrae el email del usuario desde el token"""
    headers = {k.lower(): v for k, v in (event.get('headers') or {}).items()}
    auth_header = headers.get('authorization')
    
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        payload = decode_jwt_payload(token)
        if payload:
            return payload.get('email') or payload.get('username')
    return None

def build_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": True,
            "Content-Type": "application/json"
        },
        "body": json.dumps(body, ensure_ascii=False)
    }

def decode_jwt_payload(token):
    """Decodifica el payload de un JWT sin verificar firma"""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        payload = parts[1]
        # Ajustar padding base64
        padding = '=' * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload + padding).decode('utf-8')
        return json.loads(decoded)
    except Exception:
        return None

def get_user_data(correo):
    table = dynamodb.Table(TABLE_USUARIOS)
    response = table.get_item(Key={'correo': correo})
    return response.get('Item')

def get_user_from_cognito(event):
    """Obtiene datos del usuario directamente del ID Token (sin llamar a Cognito API)"""
    headers = {k.lower(): v for k, v in (event.get('headers') or {}).items()}
    auth_header = headers.get('authorization')
    
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
        
    token = auth_header.split(" ")[1]
    payload = decode_jwt_payload(token)
    
    if not payload:
        return None
        
    # Si es un ID Token, ya tiene los atributos
    if payload.get('token_use') == 'id':
        return {
            'correo': payload.get('email'),
            'nombre': payload.get('name', 'Usuario'),
            'rol': payload.get('custom:rol', 'USER'),
            'sexo': payload.get('gender', '')
        }
        
    # Si es un Access Token, no tiene atributos estándar (email, name) usualmente,
    # pero en este caso el cliente está enviando ID Token según los logs.
    return None

def get_recent_memory(correo):
    table = dynamodb.Table(TABLE_MEMORIA)
    try:
        response = table.query(
            KeyConditionExpression=Key('correo').eq(correo),
            ScanIndexForward=False, # Descending order to get latest
            Limit=5
        )
        return response.get('Items', [])
    except ClientError:
        return []

def get_services_context():
    table = dynamodb.Table(TABLE_SERVICIOS)
    # Scan es costoso en producción, pero ok para demo/poc
    response = table.scan(Limit=20) 
    return response.get('Items', [])

def get_medical_history(correo):
    table = dynamodb.Table(TABLE_HISTORIAL)
    try:
        response = table.query(
            KeyConditionExpression=Key('correo').eq(correo),
            ScanIndexForward=False, # Latest first
            Limit=3
        )
        return response.get('Items', [])
    except ClientError:
        return []

def iniciarAgente(event, context):
    """
    Lambda para interactuar con el Agente de Salud.
    Método: POST
    Headers: Authorization: Bearer <token>
    Body: {
        "mensaje": "Hola, me duele la cabeza",
        "contexto": "General" | "Servicios" | "Wearables"
    }
    """
    if not client:
        return build_response(500, {"error": "Gemini API Key no configurada"})

    try:
        # 1. Autenticación
        print(f"DEBUG: Headers received: {event.get('headers')}")
        correo = get_user_email(event)
        print(f"DEBUG: Extracted email: {correo}")
        
        if not correo:
            return build_response(401, {"error": "No autorizado. Token faltante o inválido."})

        body = json.loads(event.get('body') or '{}')
        mensaje = body.get('mensaje')
        contexto_str = body.get('contexto', 'General')
        
        if not mensaje:
            return build_response(400, {"error": "El campo 'mensaje' es requerido"})

        # Validar contexto
        try:
            contexto_enum = ContextoEnum(contexto_str)
        except ValueError:
            return build_response(400, {
                "error": f"Contexto inválido. Valores permitidos: {[e.value for e in ContextoEnum]}"
            })

        # 2. Obtener Datos del Usuario
        print(f"DEBUG: Querying user data for: {correo}")
        usuario = get_user_data(correo)
        print(f"DEBUG: User data found in DynamoDB: {usuario}")
        
        # Si no está en DynamoDB, intentar obtener de Cognito directamente
        if not usuario:
            print("DEBUG: User not found in DynamoDB, trying Cognito...")
            usuario = get_user_from_cognito(event)
            print(f"DEBUG: User data found in Cognito: {usuario}")

        if not usuario:
            return build_response(404, {"error": f"Usuario no encontrado para el correo: {correo}"})
            
        nombre_usuario = usuario.get('nombre', 'Usuario')
        
        # 3. Obtener Memoria Reciente
        memoria_items = get_recent_memory(correo)
        memoria_texto = "\n".join([f"- {m.get('resumen_conversacion', '')}" for m in memoria_items])
        
        # 4. Obtener Contexto Específico
        contexto_extra = ""
        if contexto_enum == ContextoEnum.SERVICIOS:
            servicios = get_services_context()
            servicios_txt = "\n".join([f"- {s.get('nombre')}: {s.get('descripcion', '')}" for s in servicios])
            contexto_extra = f"INFORMACIÓN DE SERVICIOS DISPONIBLES:\n{servicios_txt}\n"
            
        elif contexto_enum == ContextoEnum.WEARABLES:
            historial = get_medical_history(correo)
            historial_txt = ""
            for h in historial:
                fecha = h.get('fecha', '')
                sensores = h.get('sensores', {})
                wearables = h.get('wearables', {})
                historial_txt += f"Fecha: {fecha}, Sensores: {sensores}, Wearables: {wearables}\n"
            contexto_extra = f"HISTORIAL MÉDICO RECIENTE (WEARABLES):\n{historial_txt}\n"

        # 5. Construir Prompt
        system_instruction = f"""
        Eres un asistente virtual especializado en salud y bienestar para la organización {os.environ.get('ORG_NAME', 'Rimac')}.
        Tu usuario se llama {nombre_usuario}.
        
        NO eres un médico. NO debes dar diagnósticos médicos definitivos ni recetar medicamentos.
        Tu función es orientar, sugerir hábitos saludables, y recomendar servicios disponibles si aplica.
        
        CONTEXTO ACTUAL: {contexto_enum.value}
        {contexto_extra}
        
        MEMORIA DE CONVERSACIONES PREVIAS:
        {memoria_texto}
        
        Instrucciones:
        1. Responde de manera empática y profesional.
        2. Usa la información de contexto si es relevante para la pregunta.
        3. Si detectas una emergencia, sugiere contactar a servicios de urgencia inmediatamente.
        4. Si el usuario pide actualizar su historial o memoria, confirma que lo has entendido (aunque la acción técnica sea separada).
        """
        
        # 6. Llamar a Gemini
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=f"{system_instruction}\n\nUsuario: {mensaje}\nAsistente:"
        )
        
        respuesta_agente = response.text
        
        return build_response(200, {
            "mensaje": respuesta_agente,
            "contexto_usado": contexto_enum.value
        })

    except Exception as e:
        print(f"Error: {str(e)}")
        return build_response(500, {"error": str(e)})

import json
import boto3
import os
import time
import base64
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')
TABLE_HISTORIAL = os.environ.get('TABLE_HISTORIAL_MEDICO', 'HistorialMedico')
table = dynamodb.Table(TABLE_HISTORIAL)

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

def get_user_email(event):
    """Extrae el email del usuario desde el token en headers"""
    headers = {k.lower(): v for k, v in (event.get('headers') or {}).items()}
    auth_header = headers.get('authorization')
    
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header.split(" ")[1]
    payload = decode_jwt_payload(token)
    
    if payload:
        return payload.get('email') or payload.get('username')
    return None

def actualizarHistorial(event, context):
    """
    Lambda para crear o actualizar historial médico (wearables/sensores).
    Método: POST
    Headers: Authorization: Bearer <token>
    Body: {
        "fecha": "YYYY-MM-DD",  # Opcional, default hoy
        "sensores": { "pasos": 5000, ... },
        "wearables": { "ritmo_cardiaco": 70, ... }
    }
    """
    try:
        # Autenticación
        correo = get_user_email(event)
        if not correo:
            return build_response(401, {"error": "No autorizado. Token faltante o inválido."})

        body = json.loads(event.get('body') or '{}')
        
        # Fecha actual si no viene
        fecha = body.get('fecha', time.strftime("%Y-%m-%d"))
        
        # Preparar item
        item = {
            'correo': correo,
            'fecha': fecha,
            'sensores': body.get('sensores', {}),
            'wearables': body.get('wearables', {})
        }
        
        # Guardar en DynamoDB
        table.put_item(Item=item)
        
        return build_response(200, {
            "message": "Historial actualizado exitosamente",
            "fecha": fecha,
            "data": item
        })

    except Exception as e:
        print(f"Error: {str(e)}")
        return build_response(500, {"error": str(e)})

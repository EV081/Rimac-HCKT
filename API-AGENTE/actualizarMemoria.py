import json
import boto3
import os
import uuid
import time
import base64
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')
TABLE_MEMORIA = os.environ.get('TABLE_MEMORIA_CONTEXTUAL', 'MemoriaContextual')
table = dynamodb.Table(TABLE_MEMORIA)

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
    """Extrae el email del usuario desde el token"""
    headers = {k.lower(): v for k, v in (event.get('headers') or {}).items()}
    auth_header = headers.get('authorization')
    
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        payload = decode_jwt_payload(token)
        if payload:
            return payload.get('email') or payload.get('username')
    return None

def actualizarMemoria(event, context):
    """
    Lambda para crear o actualizar memoria contextual.
    Método: POST
    Headers: Authorization: Bearer <token>
    Body: {
        "context_id": "opcional-si-es-update",
        "resumen_conversacion": "...",
        "intencion_detectada": "...",
        "datos_extraidos": {...}
    }
    """
    try:
        # Autenticación
        correo = get_user_email(event)
        if not correo:
            return build_response(401, {"error": "No autorizado. Token faltante o inválido."})

        body = json.loads(event.get('body') or '{}')
        
        # Si no viene context_id, generamos uno nuevo (Create)
        context_id = body.get('context_id')
        if not context_id:
            context_id = f"ctx-{uuid.uuid4().hex[:8]}"
            
        # Fecha actual si no viene
        fecha = body.get('fecha', time.strftime("%Y-%m-%d"))
        
        item = {
            'correo': correo,
            'context_id': context_id,
            'fecha': fecha,
            'resumen_conversacion': body.get('resumen_conversacion', ''),
            'intencion_detectada': body.get('intencion_detectada', ''),
            'datos_extraidos': body.get('datos_extraidos', {})
        }
        
        # Guardar en DynamoDB
        table.put_item(Item=item)
        
        return build_response(200, {
            "message": "Memoria actualizada exitosamente",
            "context_id": context_id,
            "data": item
        })

    except Exception as e:
        print(f"Error: {str(e)}")
        return build_response(500, {"error": str(e)})

import json
import boto3
import os
import base64
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')
TABLE_USUARIOS = os.environ.get('TABLE_USUARIOS')
table = dynamodb.Table(TABLE_USUARIOS)

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

def activar_modo_familiar(event, context):
    """
    Lambda para activar modo familiar: cambia el rol de USER a TUTOR
    Método: PUT
    Headers: Authorization: Bearer <token>
    Body: {} (vacío, el correo se obtiene del token)
    """
    try:
        # Obtener correo del token
        correo = get_user_email(event)
        
        if not correo:
            return build_response(401, {
                "error": "No autorizado. Token faltante o inválido."
            })
        
        # Verificar que el usuario existe
        try:
            response = table.get_item(Key={'correo': correo})
        except ClientError as e:
            return build_response(500, {
                "error": f"Error al consultar DynamoDB: {str(e)}"
            })
        
        if 'Item' not in response:
            return build_response(404, {
                "error": f"Usuario con correo '{correo}' no encontrado"
            })
        
        usuario = response['Item']
        rol_actual = usuario.get('rol')
        
        # Validar que el rol actual sea USER
        if rol_actual != 'USER':
            return build_response(400, {
                "error": f"Solo usuarios con rol 'USER' pueden activar modo familiar. Rol actual: '{rol_actual}'"
            })
        
        # Actualizar rol a TUTOR
        try:
            table.update_item(
                Key={'correo': correo},
                UpdateExpression='SET rol = :nuevo_rol',
                ExpressionAttributeValues={':nuevo_rol': 'TUTOR'},
                ReturnValues='ALL_NEW'
            )
        except ClientError as e:
            return build_response(500, {
                "error": f"Error al actualizar usuario: {str(e)}"
            })
        
        return build_response(200, {
            "message": "Modo familiar activado exitosamente",
            "correo": correo,
            "rol_anterior": rol_actual,
            "rol_nuevo": "TUTOR"
        })
        
    except json.JSONDecodeError:
        return build_response(400, {
            "error": "Body inválido, debe ser JSON válido"
        })
    except Exception as e:
        return build_response(500, {
            "error": f"Error interno: {str(e)}"
        })
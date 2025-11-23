import json
import boto3
import os
import base64
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')
TABLE_USUARIOS = os.environ.get('TABLE_USUARIOS')
TABLE_DEPENDIENTES = os.environ.get('TABLE_DEPENDIENTES')

users_table = dynamodb.Table(TABLE_USUARIOS)
dependientes_table = dynamodb.Table(TABLE_DEPENDIENTES)

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

def listar_dependientes(event, context):
    """
    Lambda para listar los dependientes de un tutor
    Método: GET
    Headers: Authorization: Bearer <token>
    """
    try:
        # Obtener correo del tutor desde el token
        correo_tutor = get_user_email(event)
        
        if not correo_tutor:
            return build_response(401, {
                "error": "No autorizado. Token faltante o inválido."
            })
        
        # Verificar que el usuario existe y tiene rol TUTOR
        try:
            response = users_table.get_item(Key={'correo': correo_tutor})
        except ClientError as e:
            return build_response(500, {
                "error": f"Error al consultar usuario: {str(e)}"
            })
        
        if 'Item' not in response:
            return build_response(404, {
                "error": f"Usuario con correo '{correo_tutor}' no encontrado"
            })
        
        tutor = response['Item']
        if tutor.get('rol') != 'TUTOR':
            return build_response(403, {
                "error": f"El usuario no tiene rol TUTOR. Solo los tutores pueden listar dependientes.",
                "rol_actual": tutor.get('rol')
            })
        
        # Consultar dependientes del tutor
        try:
            response = dependientes_table.query(
                KeyConditionExpression='correo_tutor = :correo',
                ExpressionAttributeValues={
                    ':correo': correo_tutor
                }
            )
        except ClientError as e:
            return build_response(500, {
                "error": f"Error al consultar dependientes: {str(e)}"
            })
        
        dependientes = response.get('Items', [])
        
        return build_response(200, {
            "message": "Dependientes obtenidos exitosamente",
            "correo_tutor": correo_tutor,
            "total": len(dependientes),
            "dependientes": dependientes
        })
        
    except json.JSONDecodeError:
        return build_response(400, {
            "error": "Body inválido, debe ser JSON válido"
        })
    except Exception as e:
        return build_response(500, {
            "error": f"Error interno: {str(e)}"
        })

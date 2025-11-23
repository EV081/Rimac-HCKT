import json
import boto3
import os
import uuid
import base64
from datetime import datetime
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

def validar_fecha(fecha_str):
    """Valida formato de fecha YYYY-MM-DD"""
    try:
        datetime.strptime(fecha_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def agregar_dependiente(event, context):
    """
    Lambda para agregar dependientes a un tutor
    Método: POST
    Headers: Authorization: Bearer <token>
    Body: {
        "nombre": "Juan Pérez",
        "cumpleanos": "2015-05-20",
        "parentesco": "HIJO",
        "sexo": "M"
    }
    """
    try:
        # Obtener correo del tutor desde el token
        correo_tutor = get_user_email(event)
        
        if not correo_tutor:
            return build_response(401, {
                "error": "No autorizado. Token faltante o inválido."
            })
        
        # Parsear body
        body = json.loads(event.get('body', '{}'))
        
        nombre = body.get('nombre')
        cumpleanos = body.get('cumpleanos')
        parentesco = body.get('parentesco')
        sexo = body.get('sexo')
        
        # Validaciones de campos requeridos
        campos_requeridos = {
            'nombre': nombre,
            'cumpleanos': cumpleanos,
            'parentesco': parentesco,
            'sexo': sexo
        }
        
        campos_faltantes = [k for k, v in campos_requeridos.items() if not v]
        if campos_faltantes:
            return build_response(400, {
                "error": f"Campos requeridos faltantes: {', '.join(campos_faltantes)}"
            })
        
        # Validar formato de fecha
        if not validar_fecha(cumpleanos):
            return build_response(400, {
                "error": "El campo 'cumpleanos' debe tener formato YYYY-MM-DD"
            })
        
        # Validar parentesco
        if parentesco not in ['HIJO', 'ADULTO_MAYOR']:
            return build_response(400, {
                "error": "El campo 'parentesco' debe ser 'HIJO' o 'ADULTO_MAYOR'"
            })
        
        # Validar sexo
        if sexo not in ['M', 'F']:
            return build_response(400, {
                "error": "El campo 'sexo' debe ser 'M' o 'F'"
            })
        
        # Verificar que el tutor existe y tiene rol TUTOR
        try:
            response = users_table.get_item(Key={'correo': correo_tutor})
        except ClientError as e:
            return build_response(500, {
                "error": f"Error al consultar tutor: {str(e)}"
            })
        
        if 'Item' not in response:
            return build_response(404, {
                "error": f"Tutor con correo '{correo_tutor}' no encontrado"
            })
        
        tutor = response['Item']
        if tutor.get('rol') != 'TUTOR':
            return build_response(400, {
                "error": f"El usuario '{correo_tutor}' no tiene rol TUTOR. Debe activar modo familiar primero."
            })
        
        # Generar dependiente_id único
        dependiente_id = str(uuid.uuid4())
        
        # Crear registro de dependiente
        dependiente = {
            'correo_tutor': correo_tutor,
            'dependiente_id': dependiente_id,
            'nombre': nombre,
            'cumpleanos': cumpleanos,
            'parentesco': parentesco,
            'sexo': sexo
        }
        
        # Guardar en DynamoDB
        try:
            dependientes_table.put_item(Item=dependiente)
        except ClientError as e:
            return build_response(500, {
                "error": f"Error al guardar dependiente: {str(e)}"
            })
        
        return build_response(201, {
            "message": "Dependiente agregado exitosamente",
            "dependiente": dependiente
        })
        
    except json.JSONDecodeError:
        return build_response(400, {
            "error": "Body inválido, debe ser JSON válido"
        })
    except Exception as e:
        return build_response(500, {
            "error": f"Error interno: {str(e)}"
        })

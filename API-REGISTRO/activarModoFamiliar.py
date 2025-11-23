import json
import boto3
import os
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

def activar_modo_familiar(event, context):
    """
    Lambda para activar modo familiar: cambia el rol de USER a TUTOR
    Método: PUT
    Body: { "correo": "usuario@example.com" }
    """
    try:
        # Parsear body
        body = json.loads(event.get('body', '{}'))
        correo = body.get('correo')
        
        if not correo:
            return build_response(400, {
                "error": "El campo 'correo' es requerido"
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

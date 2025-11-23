import json
import boto3
import os
import time
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

def actualizarHistorial(event, context):
    """
    Lambda para crear o actualizar historial médico (wearables/sensores).
    Método: POST
    Body: {
        "correo": "usuario@example.com",
        "fecha": "YYYY-MM-DD",  # Opcional, default hoy
        "sensores": { "pasos": 5000, ... },
        "wearables": { "ritmo_cardiaco": 70, ... }
    }
    """
    try:
        body = json.loads(event.get('body', '{}'))
        correo = body.get('correo')
        
        if not correo:
            return build_response(400, {"error": "El campo 'correo' es requerido"})
            
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

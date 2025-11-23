import json
import boto3
import os
import uuid
import time
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

def actualizarMemoria(event, context):
    """
    Lambda para crear o actualizar memoria contextual.
    Método: POST
    Body: {
        "correo": "usuario@example.com",
        "context_id": "opcional-si-es-update",
        "resumen_conversacion": "...",
        "intencion_detectada": "...",
        "datos_extraidos": {...}
    }
    """
    try:
        body = json.loads(event.get('body', '{}'))
        correo = body.get('correo')
        
        if not correo:
            return build_response(400, {"error": "El campo 'correo' es requerido"})
            
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

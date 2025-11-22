import boto3
import os
import base64
import json
from botocore.exceptions import ClientError
from textract import analizar_receta_medica

s3_client = boto3.client('s3')


def lambda_handler(event, context):
    """
    Sube una imagen de receta médica a S3 y la analiza con Textract.
    
    Espera en event['body']:
    {
        "nombre_paciente": "JulianaHealth",
        "nombre_archivo": "receta_2023.png",
        "imagen_base64": "<BASE64_DE_LA_IMAGEN>"
    }
    
    El bucket S3 se toma de la variable de entorno S3_BUCKET.
    La ruta en S3 será: {nombre_paciente}/{nombre_archivo}
    """
    try:
        # Parsear el body si viene como string
        body = event.get('body', {})
        if isinstance(body, str):
            body = json.loads(body)
        
        # Obtener parámetros
        nombre_paciente = body.get('nombre_paciente')
        nombre_archivo = body.get('nombre_archivo')
        imagen_base64 = body.get('imagen_base64')
        
        # Validaciones
        if not nombre_paciente:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Falta 'nombre_paciente'"})
            }
        
        if not nombre_archivo:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Falta 'nombre_archivo'"})
            }
        
        if not imagen_base64:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Falta 'imagen_base64'"})
            }
        
        # Obtener bucket de variable de entorno
        bucket = os.environ.get('S3_BUCKET')
        if not bucket:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Variable de entorno S3_BUCKET no configurada"})
            }
        
        # Construir la ruta en S3: nombre_paciente/nombre_archivo
        s3_key = f"{nombre_paciente}/{nombre_archivo}"
        
        # Decodificar imagen base64
        try:
            imagen_bytes = base64.b64decode(imagen_base64)
        except Exception as e:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": f"Imagen base64 inválida: {str(e)}"})
            }
        
        # Subir a S3
        try:
            s3_client.put_object(
                Bucket=bucket,
                Key=s3_key,
                Body=imagen_bytes,
                ContentType='image/png'
            )
        except ClientError as e:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": f"Error al subir a S3: {str(e)}"})
            }
        
        # Analizar la receta con Textract usando la función importada
        # Le pasamos el bucket y key que acabamos de crear
        analisis = analizar_receta_medica(bucket, s3_key)
        
        # Preparar respuesta
        resultado = {
            "mensaje": "Receta subida y analizada exitosamente",
            "s3": {
                "bucket": bucket,
                "key": s3_key,
                "tamaño_bytes": len(imagen_bytes)
            },
            "analisis": analisis
        }
        
        return {
            "statusCode": 200,
            "body": json.dumps(resultado, ensure_ascii=False)
        }
        
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Error inesperado: {str(e)}"})
        }

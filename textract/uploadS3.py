import boto3
import os
import base64
import json
from datetime import datetime
from botocore.exceptions import ClientError
from textract import analizar_receta_medica

s3_client = boto3.client('s3')


def sanitizar_nombre(nombre):
    """
    Sanitiza el nombre para usar en S3.
    Reemplaza espacios por guiones bajos y elimina caracteres especiales.
    """
    # Reemplazar espacios por guiones bajos
    nombre = nombre.replace(' ', '_')
    # Eliminar caracteres que pueden causar problemas
    caracteres_permitidos = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.'
    nombre_limpio = ''.join(c for c in nombre if c in caracteres_permitidos)
    return nombre_limpio


def lambda_handler(event, context):
    """
    Sube una imagen de receta médica a S3 y la analiza con Textract.
    
    Espera en event['body']:
    {
        "nombre_paciente": "Elmer Villegas",
        "nombre_archivo": "receta.png",  # Opcional, se genera automáticamente si no se provee
        "imagen_base64": "<BASE64_DE_LA_IMAGEN>"
    }
    
    El bucket S3 se toma de la variable de entorno S3_BUCKET.
    La ruta en S3 será: {nombre_paciente_sanitizado}/{nombre_archivo}_YYYYMMDD_HHMMSS.png
    """
    try:
        # Parsear el body si viene como string
        body = event.get('body', {})
        if isinstance(body, str):
            body = json.loads(body)
        
        # Obtener parámetros
        nombre_paciente = body.get('nombre_paciente')
        nombre_archivo = body.get('nombre_archivo', 'receta')
        imagen_base64 = body.get('imagen_base64')
        
        # Validaciones
        if not nombre_paciente:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Falta 'nombre_paciente'"})
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
        
        # Sanitizar nombre del paciente (quitar espacios y caracteres especiales)
        nombre_paciente_limpio = sanitizar_nombre(nombre_paciente)
        
        # Obtener fecha y hora actual
        fecha_hora = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        # Quitar extensión del nombre de archivo si existe
        nombre_base = nombre_archivo.rsplit('.', 1)[0]
        nombre_base_limpio = sanitizar_nombre(nombre_base)
        
        # Construir nombre de archivo con fecha: nombre_YYYYMMDD_HHMMSS.png
        nombre_archivo_final = f"{nombre_base_limpio}_{fecha_hora}.png"
        
        # Construir la ruta en S3: nombre_paciente/nombre_archivo_fecha.png
        s3_key = f"{nombre_paciente_limpio}/{nombre_archivo_final}"
        
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
                "nombre_original_paciente": nombre_paciente,
                "nombre_sanitizado_paciente": nombre_paciente_limpio,
                "tamaño_bytes": len(imagen_bytes),
                "fecha_subida": fecha_hora
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

import json
import boto3

textract_client = boto3.client("textract")


def extraer_medicinas_del_texto(lineas):
    """
    Procesa las líneas de texto para extraer medicinas e indicaciones.
    Detecta patrones comunes en recetas médicas.
    """
    medicinas = []
    medicina_actual = None
    
    # Palabras clave que indican inicio de medicina
    palabras_medicina = ['mg', 'miligramos', 'gramos', 'tableta', 'cápsula', 'ml', 'comprimido']
    
    for i, linea in enumerate(lineas):
        linea_lower = linea.lower()
        
        # Detectar si es una medicina (contiene dosis o unidades)
        es_medicina = any(palabra in linea_lower for palabra in palabras_medicina)
        
        if es_medicina and not linea_lower.startswith(('dr.', 'paciente', 'otras indicaciones')):
            # Nueva medicina encontrada
            if medicina_actual:
                medicinas.append(medicina_actual)
            
            medicina_actual = {
                "nombre": linea.strip(),
                "indicaciones": []
            }
        elif medicina_actual and linea.strip():
            # Es una indicación de la medicina actual
            if not linea_lower.startswith(('dr.', 'paciente', 'firma', 'correo')):
                medicina_actual["indicaciones"].append(linea.strip())
    
    # Agregar la última medicina
    if medicina_actual:
        medicinas.append(medicina_actual)
    
    return medicinas


def extraer_doctor_paciente(lineas):
    """
    Extrae información del doctor y paciente del texto.
    """
    doctor = ""
    paciente = ""
    
    for i, linea in enumerate(lineas):
        linea_lower = linea.lower()
        
        # Buscar doctor
        if linea_lower.startswith('dr.') or linea_lower.startswith('dr '):
            doctor = linea.strip()
        
        # Buscar paciente
        if 'paciente' in linea_lower:
            # El nombre del paciente suele estar en la misma línea o la siguiente
            if ':' in linea:
                paciente = linea.split(':', 1)[1].strip()
            elif i + 1 < len(lineas):
                paciente = lineas[i + 1].strip()
    
    return doctor, paciente


def analizar_receta_medica(bucket, key):
    """
    Función reutilizable para analizar recetas médicas.
    Extrae: doctor, paciente, y TODAS las medicinas con sus indicaciones.
    
    Args:
        bucket (str): Nombre del bucket S3
        key (str): Ruta del archivo en S3 (ej: "paciente/receta.png")
    
    Returns:
        dict: Información extraída de la receta
    """
    try:
        # Obtener TODO el texto de la receta usando detect_document_text
        response_text = textract_client.detect_document_text(
            Document={"S3Object": {"Bucket": bucket, "Name": key}}
        )
        
        # Extraer todas las líneas de texto
        lineas = []
        for block in response_text.get("Blocks", []):
            if block.get("BlockType") == "LINE":
                lineas.append(block.get("Text", ""))
        
        # Extraer doctor y paciente del texto
        doctor, paciente = extraer_doctor_paciente(lineas)
        
        # Extraer medicinas del texto completo
        medicinas = extraer_medicinas_del_texto(lineas)
        
        # Buscar "Otras indicaciones"
        otras_indicaciones = ""
        for i, linea in enumerate(lineas):
            if "otras indicaciones" in linea.lower():
                # Tomar las siguientes líneas como otras indicaciones
                if i + 1 < len(lineas):
                    otras_indicaciones = lineas[i + 1]
                break
        
        return {
            "doctor": doctor,
            "paciente": paciente,
            "medicinas": medicinas,
            "otras_indicaciones": otras_indicaciones,
            "texto_completo": lineas,
            "total_medicinas": len(medicinas)
        }
        
    except Exception as e:
        import traceback
        return {
            "error": f"Error al analizar con Textract: {str(e)}",
            "traceback": traceback.format_exc()
        }


def lambda_handler(event, context):
    """
    Lambda handler para analizar recetas médicas.
    
    event:
    {
      "bucket": "mi-bucket",
      "key": "paciente/receta.png"
    }
    """
    try:
        body = event.get('body', {})
        if isinstance(body, str):
            body = json.loads(body)
        
        bucket = body.get("bucket")
        key = body.get("key")
        
        if not bucket or not key:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Se requieren 'bucket' y 'key'"})
            }
        
        resultado = analizar_receta_medica(bucket, key)
        
        return {
            "statusCode": 200,
            "body": json.dumps(resultado, ensure_ascii=False)
        }
        
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}, ensure_ascii=False)
        }

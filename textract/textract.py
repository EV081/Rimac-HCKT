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
        # Obtener TODO el texto de la receta
        response_text = textract_client.detect_document_text(
            Document={"S3Object": {"Bucket": bucket, "Name": key}}
        )
        
        # Extraer todas las líneas de texto
        lineas = []
        for block in response_text.get("Blocks", []):
            if block.get("BlockType") == "LINE":
                lineas.append(block.get("Text", ""))
        
        # Usar queries para información específica
        queries = [
            {"Text": "¿Quién es el doctor que recetó?", "Alias": "Doctor", "Pages": ["1"]},
            {"Text": "¿Cuál es el nombre del doctor?", "Alias": "NombreDoctor", "Pages": ["1"]},
            {"Text": "¿Quién es el paciente?", "Alias": "Paciente", "Pages": ["1"]},
            {"Text": "¿Cuál es el nombre del paciente?", "Alias": "NombrePaciente", "Pages": ["1"]},
        ]
        
        response_queries = textract_client.analyze_document(
            Document={"S3Object": {"Bucket": bucket, "Name": key}},
            FeatureTypes=["QUERIES"],
            QueriesConfig={"Queries": queries}
        )
        
        # Extraer respuestas de queries
        blocks = {b["Id"]: b for b in response_queries.get("Blocks", [])}
        resultados = {}
        
        for block in blocks.values():
            if block.get("BlockType") == "QUERY":
                alias = (block.get("Query", {}) or {}).get("Alias")
                if not alias:
                    continue
                
                related_ids = []
                for rel in block.get("Relationships", []):
                    if rel.get("Type") == "ANSWER":
                        related_ids.extend(rel.get("Ids", []))
                
                best_text = ""
                best_conf = -1.0
                for rid in related_ids:
                    ans = blocks.get(rid, {})
                    if ans.get("BlockType") != "QUERY_RESULT":
                        continue
                    text = ans.get("Text") or ""
                    conf = ans.get("Confidence", 0.0)
                    if conf > best_conf and text.strip():
                        best_text, best_conf = text.strip(), conf
                
                resultados[alias] = {"texto": best_text, "confianza": best_conf}
        
        # Consolidar información
        doctor = resultados.get("Doctor", {}).get("texto") or resultados.get("NombreDoctor", {}).get("texto", "")
        paciente = resultados.get("Paciente", {}).get("texto") or resultados.get("NombrePaciente", {}).get("texto", "")
        
        # Extraer medicinas del texto completo
        medicinas = extraer_medicinas_del_texto(lineas)
        
        # Buscar "Otras indicaciones"
        otras_indicaciones = ""
        for i, linea in enumerate(lineas):
            if "otras indicaciones" in linea.lower():
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
        return {"error": f"Error al analizar con Textract: {str(e)}"}


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

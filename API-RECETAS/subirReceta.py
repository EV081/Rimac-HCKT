import os
import json
import base64
import boto3
import re
import time
import uuid
from io import BytesIO
import cgi

# ===============================
# 0. Configuración y Clientes AWS
# ===============================
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
TABLE_RECETAS = os.environ.get('TABLE_RECETAS', 'Recetas')
S3_BUCKET = os.environ.get('S3_BUCKET_RECETAS')
table_recetas = dynamodb.Table(TABLE_RECETAS)

# ===============================
# 1. Inicializar cliente Gemini (no fallar en import-time)
# ===============================
try:
    from google import genai
    from google.genai import types
    _IMPORT_ERROR = None
except Exception as e:
    genai = None
    types = None
    _IMPORT_ERROR = str(e)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = None
_INIT_ERROR = None
if genai is not None and GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        _INIT_ERROR = str(e)
else:
    if genai is None:
        _INIT_ERROR = f"Dependencia faltante: {_IMPORT_ERROR}"
    elif not GEMINI_API_KEY:
        _INIT_ERROR = "GEMINI_API_KEY no configurada en el entorno"

# ===============================
# 2. Helpers
# ===============================
def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body, ensure_ascii=False)
    }

def decode_jwt_payload(token):
    """Decodifica el payload de un JWT sin verificar firma (confiamos en Cognito/APIGW o validación previa)"""
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

def get_user_email(event, fs=None):
    """Intenta obtener el email del usuario desde el token en headers o body"""
    token = None
    
    # 1. Buscar en Header Authorization
    headers = {k.lower(): v for k, v in (event.get('headers') or {}).items()}
    auth_header = headers.get('authorization')
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    
    # 2. Si no está en header, buscar en multipart body (si se pasó fs)
    if not token and fs and 'token' in fs:
        token = fs['token'].value
        
    if not token:
        return None
        
    payload = decode_jwt_payload(token)
    if payload:
        return payload.get('email') or payload.get('username')
    return None

# ===============================
# 3. Lambda Handler
# ===============================
def lambda_handler(event, context):
    try:
        # Validaciones tempranas
        if client is None:
            return _response(500, {
                "message": "Dependencia o inicialización faltante",
                "detail": _INIT_ERROR
            })

        # ===============================
        # 3a. Procesar Multipart
        # ===============================
        headers_raw = event.get('headers') or {}
        headers = {k.lower(): v for k, v in headers_raw.items()}
        content_type = headers.get('content-type')
        if not content_type:
            return _response(400, {"message": "Content-Type header faltante"})
        
        if event.get('isBase64Encoded'):
            body_bytes = base64.b64decode(event.get('body') or "")
        else:
            body = event.get('body') or ""
            if isinstance(body, str):
                body_bytes = body.encode('utf-8')
            else:
                body_bytes = body
        
        env = {'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': content_type}
        fs = cgi.FieldStorage(fp=BytesIO(body_bytes), environ=env, keep_blank_values=True)
        
        if 'file' not in fs:
            return _response(400, {"message": "No se encontró archivo 'file' en la request"})
        
        file_item = fs['file']
        image_bytes = file_item.file.read()
        
        # ===============================
        # 3b. Autenticación
        # ===============================
        user_email = get_user_email(event, fs)
        if not user_email:
            return _response(401, {"message": "No autorizado. Token faltante o inválido."})

        # ===============================
        # 3c. Generar ID temprano (ANTES de S3)
        # ===============================
        receta_id = f"rec-{uuid.uuid4().hex[:8]}"
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")

        # ===============================
        # 3d. Análisis con Gemini
        # ===============================
        prompt = """
        Eres un analizador especializado en recetas médicas.
        A partir de la imagen dada, extrae SOLO la información necesaria y devuélvela
        exclusivamente como un JSON válido.

        Estructura obligatoria:
        {
          "paciente": "Nombre del paciente o null si no está",
          "institucion": "Hospital, clínica, médico o encabezado visible (o null)",
          "recetas": [
            {
              "producto": "Nombre del medicamento",
              "dosis": "Dosis exacta si aparece",
              "frecuencia_valor": 1, // Valor entero (ej. 8) o null
              "frecuencia_unidad": "hora", // 'hora', 'dia', 'mes' o null
              "duracion": "Duración del tratamiento o null (string)"
            }
          ]
        }

        Reglas:
        - No agregues explicaciones.
        - No agregues texto fuera del JSON.
        - Si algo no se lee, pon null.
        - frecuencia_valor debe ser INT.
        """

        response = client.models.generate_content(
            model="gemini-3-pro",
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                prompt
            ]
        )

        # Extracción robusta de JSON
        raw_text = ""
        if hasattr(response, 'text') and response.text:
            raw_text = response.text
        else:
            raw_text = str(response)

        def _extract_json_candidate(text):
            if not text: return None
            t = text.strip()
            t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
            t = re.sub(r"\s*```$", "", t, flags=re.IGNORECASE)
            start = t.find('{')
            end = t.rfind('}')
            if start != -1 and end != -1 and end > start:
                return t[start:end+1].strip()
            return t

        candidate = _extract_json_candidate(raw_text)
        
        try:
            data = json.loads(candidate)
        except Exception:
            return _response(500, {
                "message": "Error al parsear respuesta de Gemini",
                "raw": raw_text
            })

        # ===============================
        # 3e. Subir imagen a S3 (private) + URL firmada
        # ===============================
        url_receta_firmada = None
        s3_key = f"recetas/{user_email}/{receta_id}.jpg"

        if S3_BUCKET:
            try:
                # Subida privada (sin ACL)
                s3.put_object(
                    Bucket=S3_BUCKET,
                    Key=s3_key,
                    Body=image_bytes,
                    ContentType='image/jpeg'
                )

                # Crear URL firmada (24 horas)
                url_receta_firmada = s3.generate_presigned_url(
                    ClientMethod='get_object',
                    Params={'Bucket': S3_BUCKET, 'Key': s3_key},
                    ExpiresIn=86400  # 24h
                )

                print(f"✅ Imagen subida y URL firmada generada: {url_receta_firmada}")

            except Exception as s3_error:
                print(f"❌ Error al subir a S3 o generar URL firmada: {s3_error}")
        else:
            print("⚠️ S3_BUCKET no configurado, saltando subida de imagen")

        # ===============================
        # 3f. Guardar en DynamoDB
        # ===============================
        item = {
            'correo': user_email,
            'receta_id': receta_id,
            'fecha_subida': timestamp,
            'paciente': data.get('paciente'),
            'institucion': data.get('institucion'),
            'recetas': data.get('recetas', [])
        }

        # Guardar URL firmada si existe
        if url_receta_firmada:
            item['url_firmada'] = url_receta_firmada

        try:
            table_recetas.put_item(Item=item)
            print(f"✅ Receta guardada en DynamoDB: {receta_id}")
        except Exception as e:
            return _response(500, {"message": f"Error al guardar en BD: {str(e)}"})


        # ===============================
        # 3g. Respuesta Final
        # ===============================
        return _response(200, {
            "message": "Receta procesada y guardada exitosamente",
            "receta_id": receta_id,
            "url_firmada": url_receta_firmada,
            "data": data
        })

    except Exception as e:
        import traceback
        print(f"❌ Error general: {str(e)}")
        traceback.print_exc()
        return _response(500, {"message": str(e)})

# Wrapper para Serverless
def subirReceta(event, context):
    return lambda_handler(event, context)
import os
import json
import base64
import boto3

# Intentar importar google-genai sin romper la importación del módulo
try:
    from google import genai
    from google.genai import types
    _IMPORT_ERROR = None
except Exception as e:
    genai = None
    types = None
    _IMPORT_ERROR = str(e)

from io import BytesIO
import cgi

# ===============================
# 1. Inicializar cliente Gemini (no fallar en import-time)
# ===============================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = None
_INIT_ERROR = None
if genai is not None and GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        _INIT_ERROR = str(e)
else:
    # No crear client; registramos motivo para usarlo después
    if genai is None:
        _INIT_ERROR = f"Dependencia faltante: { _IMPORT_ERROR }"
    elif not GEMINI_API_KEY:
        _INIT_ERROR = "GEMINI_API_KEY no configurada en el entorno"

# ===============================
# 2. Lambda Handler
# ===============================
def lambda_handler(event, context):
    try:
        # Validaciones tempranas de dependencias/clave
        if client is None:
            return _response(500, {
                "message": "Dependencia o inicialización faltante",
                "detail": _INIT_ERROR
            })

        # ===============================
        # 2a. Extraer imagen del multipart/form-data
        # ===============================
        headers_raw = event.get('headers') or {}
        # Normalizar headers a minúsculas para búsqueda case-insensitive
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
        filename = file_item.filename

        # ===============================
        # 2b. Prompt de extracción estructurada
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
              "frecuencia": "Frecuencia (ej. 1 cada 8 horas) o null",
              "duracion": "Duración del tratamiento o null"
            }
          ]
        }

        Reglas:
        - No agregues explicaciones.
        - No agregues texto fuera del JSON.
        - No inventes datos si no son legibles.
        - Si algo no se lee, pon null.
        """

        # ===============================
        # 2c. Llamada a Gemini
        # ===============================
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type="image/jpeg"  # Cambia a image/png si tu imagen es PNG
                ),
                prompt
            ]
        )

        # ===============================
        # 2d. Validar JSON (con extracción robusta del texto)
        # ===============================
        raw_text = None
        if hasattr(response, 'text') and response.text:
            raw_text = response.text
        else:
            # Intentos alternativos de extracción
            try:
                # algunos SDKs usan output/outputs o candidates
                if hasattr(response, 'output') and response.output:
                    raw_text = getattr(response.output[0], 'content', None) or str(response.output[0])
                elif hasattr(response, 'outputs') and response.outputs:
                    raw_text = getattr(response.outputs[0], 'content', None) or str(response.outputs[0])
                elif hasattr(response, 'candidates') and response.candidates:
                    raw_text = getattr(response.candidates[0], 'content', None) or str(response.candidates[0])
                else:
                    raw_text = str(response)
            except Exception:
                raw_text = str(response)

        try:
            data = json.loads(raw_text)
        except Exception:
            return _response(500, {"message": "Error al parsear respuesta de Gemini", "raw": raw_text})

        return _response(200, data)

    except Exception as e:
        return _response(500, {"message": str(e)})


# ===============================
# 3. Función auxiliar de respuesta
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

# ------------------------------------------------------------------
# Wrapper para Serverless (serverless.yml apunta a handler.analizarReceta)
# ------------------------------------------------------------------
def analizarReceta(event, context):
    # pequeño wrapper para que serverless encuentre la función esperada
    return lambda_handler(event, context)

import os
import json
import base64
import boto3
from google import genai
from google.genai import types
from io import BytesIO
import cgi

# ===============================
# 1. Inicializar cliente Gemini
# ===============================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY no configurada en el entorno")

client = genai.Client(api_key=GEMINI_API_KEY)

# ===============================
# 2. Lambda Handler
# ===============================
def lambda_handler(event, context):
    try:
        # ===============================
        # 2a. Extraer imagen del multipart/form-data
        # ===============================
        content_type = event['headers'].get('content-type') or event['headers'].get('Content-Type')
        if not content_type:
            return _response(400, {"message": "Content-Type header faltante"})
        
        # Parsear body como multipart
        body_bytes = base64.b64decode(event['body']) if event.get('isBase64Encoded') else event['body'].encode()
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
        # 2d. Validar JSON
        # ===============================
        try:
            data = json.loads(response.text)
        except Exception:
            return _response(500, {"message": "Error al parsear respuesta de Gemini", "raw": response.text})

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

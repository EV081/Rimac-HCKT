import os
import json
import base64
import boto3
import time
import uuid
import re
from io import BytesIO
import cgi

# ===============================
# AWS CLIENTS & CONFIG
# ===============================
dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")
lambda_client = boto3.client("lambda", region_name="us-east-1")

TABLE_RECETAS = os.environ.get("TABLE_RECETAS", "Recetas")
S3_BUCKET = os.environ.get("S3_BUCKET_RECETAS")
CALENDAR_LAMBDA_NAME = os.environ.get("CALENDAR_LAMBDA_NAME", "api-calendar-dev-scheduleTreatment")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

table_recetas = dynamodb.Table(TABLE_RECETAS)

# ===============================
# GEMINI INIT
# ===============================
try:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)
    _GEMINI_ERROR = None
except Exception as e:
    client = None
    types = None
    _GEMINI_ERROR = str(e)

# ===============================
# HELPERS
# ===============================
def _response(code, body):
    return {
        "statusCode": code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body, ensure_ascii=False)
    }


def decode_jwt_payload(token: str):
    """Decodifica JWT sin verificar firma."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        payload = parts[1]
        padding = "=" * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload + padding).decode("utf-8")

        return json.loads(decoded)
    except Exception:
        return None


def get_user_email(event, formdata):
    """Extrae email desde Authorization o multipart."""
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    token = None

    # Header
    if "authorization" in headers:
        auth = headers["authorization"]
        if auth.startswith("Bearer "):
            token = auth.split(" ")[1]

    # Multipart
    if not token and formdata and "token" in formdata:
        token = formdata["token"].value

    if not token:
        return None

    payload = decode_jwt_payload(token)
    if not payload:
        return None

    return payload.get("email") or payload.get("username")


def extract_json_from_text(text: str):
    """Extrae solo el JSON del texto generado por Gemini."""
    if not text:
        return None

    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```$", "", text, flags=re.IGNORECASE)

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:
        return text[start:end + 1]

    return text


def schedule_calendar(meds, user_email, auth_header):
    """Invoca lambda de calendario por cada medicamento."""
    results = []

    for med in meds:
        try:
            pill_name = f"{med.get('producto', 'Medicamento')} {med.get('dosis', '')}".strip()

            freq_val = med.get("frecuencia_valor")
            freq_unit = (med.get("frecuencia_unidad") or "").lower()

            payload = {
                "patient_email": user_email,
                "pill_name": pill_name,
                "indicaciones_consumo": "Según receta médica",
                "medicion_duracion": "Dias",
                "duracion": int(med.get("duracion", 30))
            }

            # Frecuencia
            if freq_val and freq_unit:
                payload["frecuencia"] = int(freq_val)
                payload["indicacion"] = None

                if "hora" in freq_unit:
                    payload["medicion_frecuencia"] = "Horas"
                elif "mes" in freq_unit:
                    payload["medicion_frecuencia"] = "Meses"
                else:
                    payload["medicion_frecuencia"] = "Dias"
            else:
                payload.update({
                    "indicacion": None,
                    "medicion_frecuencia": "Dias",
                    "frecuencia": 1
                })

            lambda_client.invoke(
                FunctionName=CALENDAR_LAMBDA_NAME,
                InvocationType="Event",
                Payload=json.dumps({
                    "body": json.dumps(payload),
                    "headers": { "Authorization": auth_header }
                })
            )

            results.append({
                "medicamento": pill_name,
                "status": "programado"
            })

        except Exception as e:
            results.append({
                "medicamento": med.get("producto", "desconocido"),
                "status": "error",
                "error": str(e)
            })

    return results


# ===============================
# MAIN HANDLER
# ===============================
def lambda_handler(event, context):
    try:
        if not client:
            return _response(500, {
                "message": "Gemini no inicializado",
                "detail": _GEMINI_ERROR
            })

        # ===============================
        # MULTIPART
        # ===============================
        headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
        content_type = headers.get("content-type")

        if not content_type:
            return _response(400, {"message": "Content-Type faltante"})

        body_bytes = base64.b64decode(event["body"]) if event.get("isBase64Encoded") else (event["body"] or "").encode()

        env = { "REQUEST_METHOD": "POST", "CONTENT_TYPE": content_type }
        formdata = cgi.FieldStorage(fp=BytesIO(body_bytes), environ=env, keep_blank_values=True)

        if "file" not in formdata:
            return _response(400, {"message": "No se envió archivo 'file'"})

        image_bytes = formdata["file"].file.read()

        # ===============================
        # AUTENTICACIÓN
        # ===============================
        user_email = get_user_email(event, formdata)
        if not user_email:
            return _response(401, {"message": "Token inválido"})

        auth_header = headers.get("authorization") or headers.get("Authorization") or ""

        # ===============================
        # ANALISIS GEMINI
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
              "frecuencia_valor": 1,
              "frecuencia_unidad": "hora",
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


        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[ types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"), prompt ]
        )

        text = resp.text if hasattr(resp, "text") else str(resp)
        json_raw = extract_json_from_text(text)

        try:
            data = json.loads(json_raw)
        except Exception:
            return _response(500, { "message": "JSON inválido de Gemini", "raw": text })

        # ===============================
        # GUARDAR EN S3
        # ===============================
        receta_id = f"rec-{uuid.uuid4().hex[:8]}"
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")

        signed_url = None
        if S3_BUCKET:
            key = f"recetas/{user_email}/{receta_id}.jpg"
            s3.put_object(Bucket=S3_BUCKET, Key=key, Body=image_bytes, ContentType="image/jpeg")

            signed_url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": S3_BUCKET, "Key": key},
                ExpiresIn=86400
            )

        # ===============================
        # GUARDAR EN DYNAMODB
        # ===============================
        item = {
            "correo": user_email,
            "receta_id": receta_id,
            "fecha_subida": timestamp,
            "paciente": data.get("paciente"),
            "institucion": data.get("institucion"),
            "recetas": data.get("recetas", [])
        }

        if signed_url:
            item["url_firmada"] = signed_url

        table_recetas.put_item(Item=item)

        # ===============================
        # CALENDARIO
        # ===============================
        calendar_results = schedule_calendar(
            meds=data.get("recetas", []),
            user_email=user_email,
            auth_header=auth_header
        )

        # ===============================
        # RESPUESTA
        # ===============================
        return _response(200, {
            "message": "Receta procesada exitosamente",
            "receta_id": receta_id,
            "url_firmada": signed_url,
            "data": data,
            "calendar_notifications": calendar_results
        })

    except Exception as e:
        return _response(500, {"message": str(e)})


def subirReceta(event, context):
    return lambda_handler(event, context)

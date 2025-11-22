# Instrucciones de Deploy y Uso

## 1. Deploy del Sistema

```bash
cd textract
serverless deploy
```

Si tienes problemas de memoria durante el deploy, aumenta el heap de Node.js:
```bash
export NODE_OPTIONS="--max-old-space-size=4096"
serverless deploy
```

## 2. Obtener la URL del API

Después del deploy exitoso, verás algo como:

```
✔ Service deployed to stack textract-dev (20s)

endpoints:
  POST - https://abc123xyz.execute-api.us-east-1.amazonaws.com/dev/textract
  POST - https://abc123xyz.execute-api.us-east-1.amazonaws.com/dev/uploadS3
```

Copia la URL del endpoint `uploadS3`.

## 3. Probar con Python

Edita `test_upload.py` y reemplaza `TU-API-ID` con tu URL real:

```python
API_URL = "https://abc123xyz.execute-api.us-east-1.amazonaws.com/dev/uploadS3"
```

Luego ejecuta:
```bash
python3 test_upload.py
```

## 4. Probar con cURL

```bash
# Convertir tu imagen a base64
IMAGEN_BASE64=$(base64 -w 0 tu_receta.png)

# Hacer el request
curl -X POST "https://abc123xyz.execute-api.us-east-1.amazonaws.com/dev/uploadS3" \
  -H "Content-Type: application/json" \
  -d "{
    \"nombre_paciente\": \"Juan_Lopez\",
    \"nombre_archivo\": \"imagen_2.png\",
    \"imagen_base64\": \"$IMAGEN_BASE64\"
  }"
```

## 5. Ejemplo de Respuesta

```json
{
  "mensaje": "Receta subida y analizada exitosamente",
  "s3": {
    "bucket": "textract-bucket-123456789",
    "key": "Juan_Lopez/imagen_2.png",
    "tamaño_bytes": 45678
  },
  "analisis": {
    "doctor": "Dr. Nombre Apellido",
    "paciente": "Juan Lopez",
    "medicinas": [
      {
        "nombre": "Paracetamol 500 miligramos",
        "indicaciones": [
          "1 tableta. Vía oral. 2 veces al día. Por 30 días."
        ]
      },
      {
        "nombre": "Paracetamol 500 miligramos",
        "indicaciones": [
          "1 tableta. Vía oral. 2 veces al día. Por 30 días."
        ]
      }
    ],
    "otras_indicaciones": "Tomar 2 tabletas solo en caso de mucho dolor.",
    "total_medicinas": 2,
    "texto_completo": ["...", "..."]
  }
}
```

## 6. Verificar en S3

Puedes verificar que la imagen se subió correctamente:

```bash
aws s3 ls s3://textract-bucket-123456789/Juan_Lopez/
```

O descargar la imagen:

```bash
aws s3 cp s3://textract-bucket-123456789/Juan_Lopez/imagen_2.png ./descargada.png
```

## Solución de Problemas

### Error: Cross-account pass role
Ya está solucionado en el `serverless.yml` actualizado. El sistema ahora crea sus propios roles IAM.

### Error: Out of memory durante deploy
Ejecuta:
```bash
export NODE_OPTIONS="--max-old-space-size=4096"
serverless deploy
```

### Error: Bucket already exists
Si el bucket ya existe, puedes:
1. Cambiar el nombre en `serverless.yml`
2. O eliminar la sección `resources` si el bucket ya está creado

### Error: Textract no encuentra la imagen
Verifica que:
1. La imagen se subió correctamente a S3
2. El bucket y key son correctos
3. Los permisos IAM incluyen `textract:DetectDocumentText` y `textract:AnalyzeDocument`

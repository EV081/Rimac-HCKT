# Sistema de Análisis de Recetas Médicas

## Descripción
Este sistema permite subir imágenes de recetas médicas a S3 y analizarlas automáticamente con AWS Textract para extraer información clave.

## Funcionalidad

La función `uploadS3.lambda_handler` realiza:

1. **Recibe una imagen en base64** de una receta médica
2. **Sube la imagen a S3** en la ruta: `{nombre_paciente}/{nombre_archivo}.png`
3. **Analiza la receta con Textract** para extraer:
   - Nombre del doctor que recetó
   - Nombre del paciente
   - Medicinas recetadas
   - Indicaciones de las medicinas

## Configuración

### Variable de Entorno
- `S3_BUCKET`: Nombre del bucket S3 donde se guardarán las recetas (configurado en serverless.yml)

## Uso

### Request
```json
{
  "nombre_paciente": "JulianaHealth",
  "nombre_archivo": "receta_09ago2023.png",
  "imagen_base64": "<TU_IMAGEN_EN_BASE64>"
}
```

### Response Exitoso
```json
{
  "mensaje": "Receta subida y analizada exitosamente",
  "s3": {
    "bucket": "textract-bucket-123456789",
    "key": "JulianaHealth/receta_09ago2023.png",
    "tamaño_bytes": 45678
  },
  "analisis": {
    "doctor": "Dr. Nombre Apellido",
    "paciente": "Juliana Health",
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
    "texto_completo": ["Dr. Nombre Apellido", "Paciente Juliana Health", "..."]
  }
}
```

**Nota:** El sistema detecta automáticamente TODAS las medicinas e indicaciones presentes en la receta, sin importar cuántas sean.

## Estructura en S3

Las recetas se organizan por paciente:
```
textract-bucket-123456789/
├── JulianaHealth/
│   ├── receta_09ago2023.png
│   └── receta_15sep2023.png
├── PacienteEjemplo/
│   └── receta_01ene2024.png
```

## Despliegue

```bash
cd textract
serverless deploy
```

Después del deploy, obtendrás una URL como:
```
POST - https://abc123xyz.execute-api.us-east-1.amazonaws.com/dev/uploadS3
```

## Ejemplos de Uso

### 1. Python

```python
import base64
import requests

# Convertir imagen a base64
with open('receta.png', 'rb') as f:
    imagen_base64 = base64.b64encode(f.read()).decode('utf-8')

# Hacer request
response = requests.post(
    'https://TU-API-ID.execute-api.us-east-1.amazonaws.com/dev/uploadS3',
    json={
        "nombre_paciente": "Juan_Lopez",
        "nombre_archivo": "imagen_2.png",
        "imagen_base64": imagen_base64
    }
)

print(response.json())
```

Ver archivo completo: `test_upload.py`

### 2. cURL

```bash
# Convertir imagen a base64
IMAGEN_BASE64=$(base64 -w 0 receta.png)

# Hacer request
curl -X POST "https://TU-API-ID.execute-api.us-east-1.amazonaws.com/dev/uploadS3" \
  -H "Content-Type: application/json" \
  -d "{
    \"nombre_paciente\": \"Juan_Lopez\",
    \"nombre_archivo\": \"imagen_2.png\",
    \"imagen_base64\": \"$IMAGEN_BASE64\"
  }"
```

Ver archivo completo: `ejemplo_curl.sh`

### 3. JavaScript/Node.js

```javascript
const fs = require('fs');

// Convertir imagen a base64
const imagenBase64 = fs.readFileSync('receta.png').toString('base64');

// Hacer request con fetch
fetch('https://TU-API-ID.execute-api.us-east-1.amazonaws.com/dev/uploadS3', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    nombre_paciente: 'Juan_Lopez',
    nombre_archivo: 'imagen_2.png',
    imagen_base64: imagenBase64
  })
})
.then(res => res.json())
.then(data => console.log(data));
```

Ver archivo completo: `ejemplo_nodejs.js`

### 4. Postman

1. Método: `POST`
2. URL: `https://TU-API-ID.execute-api.us-east-1.amazonaws.com/dev/uploadS3`
3. Headers: `Content-Type: application/json`
4. Body (raw JSON):
```json
{
  "nombre_paciente": "Juan_Lopez",
  "nombre_archivo": "imagen_2.png",
  "imagen_base64": "<PEGA_AQUI_TU_BASE64>"
}
```

## Resultado en S3

La imagen se guardará en:
```
textract-bucket-123456789/Juan_Lopez/imagen_2.png
```

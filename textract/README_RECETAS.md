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

## Endpoint

POST: `https://tu-api-gateway.amazonaws.com/dev/uploadS3`

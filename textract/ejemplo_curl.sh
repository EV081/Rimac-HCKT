#!/bin/bash

# Ejemplo de uso con cURL
# Reemplaza TU-API-ID con tu API Gateway ID después del deploy

API_URL="https://TU-API-ID.execute-api.us-east-1.amazonaws.com/dev/uploadS3"

# Convertir imagen a base64
IMAGEN_BASE64=$(base64 -w 0 mi_receta.png)

# Hacer el request
curl -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d "{
    \"nombre_paciente\": \"Juan_Lopez\",
    \"nombre_archivo\": \"imagen_2.png\",
    \"imagen_base64\": \"$IMAGEN_BASE64\"
  }"

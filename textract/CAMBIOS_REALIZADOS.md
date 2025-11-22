# Cambios Realizados

## ✅ Problemas Solucionados

### 1. Error de Textract: InvalidParameterException
**Problema:** El error ocurría porque se intentaba usar queries con AnalyzeDocument, lo cual puede fallar con ciertos parámetros.

**Solución:**
- Simplificado el análisis usando solo `detect_document_text` (más robusto)
- Eliminadas las queries complejas que causaban el error
- Implementada extracción de doctor/paciente mediante búsqueda de patrones en el texto

### 2. Espacios en nombres de archivos S3
**Problema:** "Elmer Villegas" con espacios causaba problemas en S3 y Textract.

**Solución:**
- Función `sanitizar_nombre()` que convierte espacios a guiones bajos
- Elimina caracteres especiales que pueden causar problemas
- Ejemplo: "Elmer Villegas" → "Elmer_Villegas"

### 3. Fecha automática en nombres de archivo
**Problema:** No había forma de distinguir múltiples recetas del mismo paciente.

**Solución:**
- Agregada fecha y hora automática al nombre del archivo
- Formato: `{nombre}_{YYYYMMDD_HHMMSS}.png`
- Ejemplo: `receta_20231109_143025.png`

## 📋 Nuevas Características

### Nombre de archivo con fecha automática
```python
# Request
{
  "nombre_paciente": "Elmer Villegas",
  "nombre_archivo": "receta.png",
  "imagen_base64": "..."
}

# Resultado en S3
textract-bucket-123456789/Elmer_Villegas/receta_20231109_143025.png
```

### Sanitización de nombres
- Espacios → guiones bajos
- Caracteres especiales eliminados
- Solo se permiten: letras, números, guiones, puntos

### Información adicional en respuesta
```json
{
  "s3": {
    "bucket": "textract-bucket-123456789",
    "key": "Elmer_Villegas/receta_20231109_143025.png",
    "nombre_original_paciente": "Elmer Villegas",
    "nombre_sanitizado_paciente": "Elmer_Villegas",
    "tamaño_bytes": 145611,
    "fecha_subida": "20231109_143025"
  }
}
```

## 🔧 Cambios Técnicos

### uploadS3.py
- ✅ Agregada función `sanitizar_nombre()`
- ✅ Agregado timestamp automático
- ✅ Mejorado manejo de nombres de archivo
- ✅ Más información en la respuesta

### textract.py
- ✅ Eliminadas queries complejas que causaban errores
- ✅ Simplificado a solo `detect_document_text`
- ✅ Agregada función `extraer_doctor_paciente()`
- ✅ Mejor manejo de errores con traceback

## 🚀 Cómo Usar

### Request Mínimo
```json
{
  "nombre_paciente": "Elmer Villegas",
  "imagen_base64": "<BASE64>"
}
```

El sistema automáticamente:
- Sanitiza el nombre: "Elmer Villegas" → "Elmer_Villegas"
- Genera nombre de archivo: "receta_20231109_143025.png"
- Sube a: `textract-bucket-123456789/Elmer_Villegas/receta_20231109_143025.png`
- Analiza con Textract
- Retorna toda la información extraída

### Request Completo
```json
{
  "nombre_paciente": "Elmer Villegas",
  "nombre_archivo": "consulta_enero.png",
  "imagen_base64": "<BASE64>"
}
```

Resultado: `textract-bucket-123456789/Elmer_Villegas/consulta_enero_20231109_143025.png`

## 📝 Próximos Pasos

1. Hacer deploy con los cambios:
```bash
cd textract
serverless deploy
```

2. Probar con tu receta:
```bash
python3 test_upload.py
```

3. Verificar que ya no hay errores de Textract

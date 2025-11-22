# Arquitectura del Sistema de Recetas Médicas

## Flujo de Datos

```
1. Cliente envía request a uploadS3
   ↓
   {
     "nombre_paciente": "JulianaHealth",
     "nombre_archivo": "receta.png",
     "imagen_base64": "..."
   }

2. uploadS3.py recibe el request
   ↓
   - Valida parámetros
   - Obtiene S3_BUCKET de variable de entorno
   - Construye ruta: {nombre_paciente}/{nombre_archivo}
   ↓
   
3. Sube imagen a S3
   ↓
   S3: textract-bucket-123456789/JulianaHealth/receta.png
   
4. Llama a textract.analizar_receta_medica(bucket, key)
   ↓
   - Pasa el bucket y key que acaba de crear
   - textract.py procesa la imagen desde S3
   
5. textract.py analiza la receta
   ↓
   - detect_document_text: Extrae TODO el texto
   - analyze_document: Usa queries para doctor/paciente
   - extraer_medicinas_del_texto: Procesa y estructura medicinas
   
6. Retorna resultado completo
   ↓
   {
     "mensaje": "Receta subida y analizada exitosamente",
     "s3": {
       "bucket": "textract-bucket-123456789",
       "key": "JulianaHealth/receta.png",
       "tamaño_bytes": 45678
     },
     "analisis": {
       "doctor": "Dr. Nombre Apellido",
       "paciente": "Juliana Health",
       "medicinas": [
         {
           "nombre": "Paracetamol 500 miligramos",
           "indicaciones": ["1 tableta. Vía oral. 2 veces al día. Por 30 días."]
         }
       ],
       "otras_indicaciones": "Tomar 2 tabletas solo en caso de mucho dolor.",
       "total_medicinas": 2
     }
   }
```

## Archivos y Responsabilidades

### uploadS3.py
- **Responsabilidad**: Punto de entrada, manejo de S3
- **Funciones**:
  - Recibe imagen en base64
  - Valida parámetros
  - Sube imagen a S3 en ruta `{nombre_paciente}/{nombre_archivo}`
  - Llama a `textract.analizar_receta_medica(bucket, key)`
  - Retorna respuesta completa

### textract.py
- **Responsabilidad**: Análisis de recetas con AWS Textract
- **Funciones**:
  - `analizar_receta_medica(bucket, key)`: Función principal reutilizable
  - `extraer_medicinas_del_texto(lineas)`: Procesa texto y extrae medicinas
  - `lambda_handler(event, context)`: Handler alternativo si se llama directamente

### Variables de Entorno
- `S3_BUCKET`: Bucket donde se guardan las recetas (configurado en serverless.yml)

## Ventajas de esta Arquitectura

1. **Separación de responsabilidades**: uploadS3 maneja S3, textract maneja análisis
2. **Reutilizable**: La función `analizar_receta_medica()` puede usarse desde cualquier lugar
3. **Sin duplicación**: El código de análisis está solo en textract.py
4. **Parámetros claros**: uploadS3 crea el archivo y pasa bucket/key a textract
5. **Flexible**: textract.py también puede llamarse directamente como Lambda independiente

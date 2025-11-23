# Sistema de Recetas Médicas

Sistema de gestión de recetas médicas con generación de datos de prueba y población de base de datos.

## Estructura del Proyecto

```
├── API-CALENDAR/          # API de calendario
├── DataGenerator/         # Generador de datos de prueba
│   ├── example-data/      # Datos JSON generados
│   │   ├── usuarios.json
│   │   ├── servicios.json
│   │   └── recetas.json
│   ├── schemas-validation/ # Esquemas de validación
│   │   ├── usuarios.json
│   │   ├── servicios.json
│   │   └── recetas.json
│   ├── DataGenerator.py   # Script generador de datos
│   └── DataPoblator.py    # Script para poblar DynamoDB
└── README.md
```

## DataGenerator

### Características

- Genera datos de prueba para usuarios, servicios y recetas médicas
- Valida datos contra esquemas JSON
- Soporta configuración mediante variables de entorno

### Uso

#### Generar datos de ejemplo

```bash
cd DataGenerator
python3 DataGenerator.py
```

#### Variables de entorno (opcional)

```bash
export AUTHORITY_USUARIO_NOMBRE="Admin Principal"
export AUTHORITY_USUARIO_CORREO="admin@hospital.com"
export AUTHORITY_USUARIO_CONTRASENA="admin123"
export USUARIOS_TOTAL=50
export RECETAS_TOTAL=20
```

### Medicamentos Disponibles

El generador incluye 20 medicamentos diferentes con sus respectivas dosis, frecuencias y duraciones:
- Trevissage, Paracetamol, Ibuprofeno, Amoxicilina
- nasalub, Lagrifilm, agua Thermal, Labello (sin dosis)
- Omeprazol, Loratadina, Aspirina, Metformina
- Atorvastatina, Losartán, Cetirizina, Azitromicina
- Diclofenaco, Ranitidina, Clonazepam, Vitamina D3

### Esquemas de Datos

#### Usuarios
- `correo`: Email del usuario (clave primaria)
- `contrasena`: Contraseña hasheada
- `nombre`: Nombre completo
- `rol`: estudiante | personal_administrativo | autoridad

#### Servicios (Actividades de Bienestar)
- `nombre`: Actividad recomendada (clave primaria)
- `descripcion`: Condición que activa la recomendación

Ejemplos:
- "Tomar un descanso de 10 minutos" → "Se detectaron altos niveles de estrés o se bajó un 10% el nivel de sueño"
- "Realizar ejercicios de respiración" → "La frecuencia cardíaca supera los 100 bpm en reposo"
- "Hidratarse con un vaso de agua" → "Han pasado más de 2 horas sin registrar ingesta de líquidos"

#### Recetas
- `receta_id`: ID único de la receta
- `paciente`: Nombre del paciente
- `institucion`: Institución médica
- `recetas`: Array de medicamentos
  - `producto`: Nombre del medicamento (requerido)
  - `dosis`: Dosis del medicamento (opcional, puede ser null)
  - `frecuencia`: Número que indica cada cuánto tomar (requerido, tipo integer)
  - `medicion_frecuencia`: Unidad de medición de frecuencia (requerido, valores: "dias", "horas", "meses")
  - `duracion`: Duración del tratamiento (requerido, tipo integer)
  - `duracion_frecuencia`: Unidad de medición de duración (requerido, valores: "dias", "horas", "meses")

Ejemplo:
```json
{
  "producto": "Paracetamol",
  "dosis": "500 mg",
  "frecuencia": 8,
  "medicion_frecuencia": "horas",
  "duracion": 5,
  "duracion_frecuencia": "dias"
}
```
Significa: Tomar cada 8 horas durante 5 días

## DataPoblator

Script para poblar tablas DynamoDB con los datos generados.

### Requisitos

```bash
pip install boto3 python-dotenv
```

### Variables de entorno requeridas

```bash
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=123456789012
export TABLE_USUARIOS=recetas-usuarios-dev
export TABLE_SERVICIOS=recetas-servicios-dev
export TABLE_RECETAS=recetas-recetas-dev
```

### Uso

```bash
cd DataGenerator
python3 DataPoblator.py
```

El script:
1. Verifica credenciales AWS
2. Crea recursos (tablas DynamoDB y bucket S3) si no existen
3. Limpia datos existentes en las tablas
4. Puebla las tablas con los datos generados

## API-CALENDAR

Sistema de recordatorios médicos integrado con Google Calendar.

### Características

- Crear citas médicas con Google Meet
- Agendar recordatorios de medicamentos individuales
- Procesar recetas completas con múltiples medicamentos
- Cálculo automático de eventos recurrentes
- Notificaciones por email y popup

### Endpoints

1. `POST /calendar/cita` - Crear cita médica
2. `POST /calendar/tratamiento` - Agendar medicamento individual
3. `POST /calendar/receta` - Procesar receta completa

### Integración con DataGenerator

El endpoint `/calendar/receta` acepta directamente el formato de recetas generado:

```bash
# Generar recetas
cd DataGenerator
python3 DataGenerator.py

# Las recetas en example-data/recetas.json pueden enviarse al API
```

Ver [API-CALENDAR/README.md](API-CALENDAR/README.md) para documentación completa.

## Licencia

MIT

# API Calendar - Sistema de Recordatorios Médicos

API para gestionar citas médicas y recordatorios de tratamientos en Google Calendar.

## Endpoints

### 1. Crear Cita Médica
`POST /calendar/cita`

Crea una cita médica única con Google Meet.

**Body:**
```json
{
  "patient_email": "paciente@email.com",
  "patient_name": "Juan Pérez",
  "doctor_email": "doctor@email.com",
  "doctor_name": "Dra. María García",
  "razon_cita": "Consulta general",
  "hora_inicio_peru": "2024-01-15 10:00",
  "hora_fin_peru": "2024-01-15 10:30"
}
```

**Response:**
```json
{
  "message": "Cita creada exitosamente",
  "cita": {
    "meet_link": "https://meet.google.com/xxx-xxxx-xxx",
    "event_id": "event123",
    "event_link": "https://calendar.google.com/..."
  }
}
```

---

### 2. Crear Recordatorio de Medicamento Individual
`POST /calendar/tratamiento`

Crea recordatorios recurrentes para un medicamento específico.

**Body:**
```json
{
  "patient_email": "paciente@email.com",
  "producto": "Paracetamol",
  "dosis": "500 mg",
  "frecuencia": 8,
  "medicion_frecuencia": "horas",
  "duracion": 5,
  "duracion_frecuencia": "dias",
  "start_time": "2024-01-15 08:00"
}
```

**Campos:**
- `patient_email` (requerido): Email del paciente
- `producto` (requerido): Nombre del medicamento
- `dosis` (opcional): Dosis del medicamento (ej: "500 mg")
- `frecuencia` (requerido): Número que indica cada cuánto tomar
- `medicion_frecuencia` (requerido): "horas", "dias" o "meses"
- `duracion` (requerido): Duración del tratamiento
- `duracion_frecuencia` (requerido): "horas", "dias" o "meses"
- `start_time` (opcional): Hora de inicio en formato "YYYY-MM-DD HH:MM"

**Ejemplos de frecuencia:**
- Cada 8 horas durante 5 días: `frecuencia: 8, medicion_frecuencia: "horas", duracion: 5, duracion_frecuencia: "dias"`
- Una vez al día durante 2 meses: `frecuencia: 1, medicion_frecuencia: "dias", duracion: 2, duracion_frecuencia: "meses"`
- Cada 12 horas durante 7 días: `frecuencia: 12, medicion_frecuencia: "horas", duracion: 7, duracion_frecuencia: "dias"`

**Response:**
```json
{
  "message": "Tratamiento agendado exitosamente",
  "event_id": "event456",
  "event_link": "https://calendar.google.com/...",
  "producto": "Paracetamol",
  "dosis": "500 mg",
  "total_recordatorios": 15,
  "recurrence_rule": "RRULE:FREQ=HOURLY;INTERVAL=8;COUNT=15",
  "start_date": "2024-01-15 08:00"
}
```

---

### 3. Crear Recordatorios para Receta Completa (NUEVO)
`POST /calendar/receta`

Crea recordatorios para todos los medicamentos de una receta médica.

**Body (Schema de Recetas):**
```json
{
  "receta_id": "rec-0c0950ed",
  "paciente": "Valentina Ortiz",
  "patient_email": "valentina.ortiz@email.com",
  "institucion": "Hospital General de México",
  "start_date": "2024-01-15",
  "recetas": [
    {
      "producto": "Diclofenaco",
      "dosis": "75 mg",
      "frecuencia": 12,
      "medicion_frecuencia": "horas",
      "duracion": 5,
      "duracion_frecuencia": "dias"
    },
    {
      "producto": "Vitamina D3",
      "dosis": "1000 UI",
      "frecuencia": 1,
      "medicion_frecuencia": "dias",
      "duracion": 3,
      "duracion_frecuencia": "meses"
    }
  ]
}
```

**Campos:**
- `receta_id` (opcional): ID de la receta
- `paciente` (opcional): Nombre del paciente
- `patient_email` (requerido): Email del paciente
- `institucion` (opcional): Institución médica
- `start_date` (opcional): Fecha de inicio en formato "YYYY-MM-DD"
- `recetas` (requerido): Array de medicamentos con sus detalles

**Response:**
```json
{
  "message": "Receta procesada: 2 medicamentos agendados",
  "receta_id": "rec-0c0950ed",
  "paciente": "Valentina Ortiz",
  "patient_email": "valentina.ortiz@email.com",
  "medicamentos_agendados": [
    {
      "producto": "Diclofenaco",
      "dosis": "75 mg",
      "event_id": "event789",
      "event_link": "https://calendar.google.com/...",
      "total_recordatorios": 10,
      "start_time": "2024-01-15 08:00"
    },
    {
      "producto": "Vitamina D3",
      "dosis": "1000 UI",
      "event_id": "event790",
      "event_link": "https://calendar.google.com/...",
      "total_recordatorios": 90,
      "start_time": "2024-01-15 14:00"
    }
  ],
  "total_exitosos": 2,
  "total_errores": 0
}
```

---

## Cálculo de Recordatorios

El sistema calcula automáticamente cuántos recordatorios se crearán:

### Ejemplos:

1. **Cada 8 horas durante 5 días:**
   - Total horas: 5 días × 24 horas = 120 horas
   - Recordatorios: 120 ÷ 8 = **15 eventos**

2. **Una vez al día durante 2 meses:**
   - Total días: 2 meses × 30 días = 60 días
   - Recordatorios: 60 ÷ 1 = **60 eventos**

3. **Cada 12 horas durante 3 días:**
   - Total horas: 3 días × 24 horas = 72 horas
   - Recordatorios: 72 ÷ 12 = **6 eventos**

---

## Reglas de Recurrencia (RRULE)

El sistema genera reglas RRULE compatibles con Google Calendar:

- `FREQ=HOURLY`: Para medicamentos cada X horas
- `FREQ=DAILY`: Para medicamentos diarios
- `FREQ=MONTHLY`: Para medicamentos mensuales
- `INTERVAL=X`: Intervalo entre eventos
- `COUNT=X`: Número total de eventos

**Ejemplo:**
```
RRULE:FREQ=HOURLY;INTERVAL=8;COUNT=15
```
Significa: Cada 8 horas, 15 veces en total.

---

## Distribución de Horarios

Cuando se agenda una receta completa, los medicamentos se distribuyen en horarios sugeridos:

- **Medicamento 1:** 8:00 AM
- **Medicamento 2:** 2:00 PM
- **Medicamento 3:** 8:00 PM
- **Medicamento 4:** 8:00 AM (ciclo se repite)

Esto evita que todos los recordatorios lleguen al mismo tiempo.

---

## Notificaciones

Cada recordatorio incluye:
- 📱 **Popup:** Notificación al momento exacto
- 📧 **Email:** 30 minutos antes del recordatorio
- 🎨 **Color verde** en el calendario para fácil identificación

---

## Variables de Entorno Requeridas

```bash
GOOGLE_CLIENT_ID=tu_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=tu_client_secret
GOOGLE_REFRESH_TOKEN=tu_refresh_token
TABLE_NAME=nombre_tabla_dynamodb
```

---

## Despliegue

```bash
# Instalar dependencias
npm install -g serverless

# Desplegar
cd API-CALENDAR
serverless deploy
```

---

## Integración con DataGenerator

El endpoint `/calendar/receta` está diseñado para recibir directamente el formato de recetas generado por DataGenerator:

```bash
# Generar datos de ejemplo
cd DataGenerator
python3 DataGenerator.py

# Los datos en example-data/recetas.json pueden enviarse directamente al endpoint
```

---

## Errores Comunes

### Error: "medicion_frecuencia debe ser uno de: ['horas', 'dias', 'meses']"
- Asegúrate de usar minúsculas: "horas" no "Horas"

### Error: "El campo 'patient_email' es requerido"
- Verifica que el body incluya el email del paciente

### Error: "start_time debe tener formato 'YYYY-MM-DD HH:MM'"
- Formato correcto: "2024-01-15 08:00"
- Formato incorrecto: "15/01/2024 8:00"

---

## Licencia

MIT

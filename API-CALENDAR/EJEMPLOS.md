# Ejemplos de Uso - API Calendar

## Caso de Uso Completo: Receta de Valentina Ortiz

### 1. Receta Original (del DataGenerator)

```json
{
  "receta_id": "rec-0c0950ed",
  "paciente": "Valentina Ortiz",
  "institucion": "Hospital General de México",
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

### 2. Request al API

```bash
curl -X POST https://tu-api.execute-api.us-east-1.amazonaws.com/dev/calendar/receta \
  -H "Content-Type: application/json" \
  -d '{
    "receta_id": "rec-0c0950ed",
    "paciente": "Valentina Ortiz",
    "patient_email": "valentina.ortiz@gmail.com",
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
  }'
```

### 3. Eventos Creados en Google Calendar

#### Medicamento 1: Diclofenaco

**Título:** 💊 Diclofenaco - 75 mg

**Descripción:**
```
💊 Medicamento: Diclofenaco
📊 Dosis: 75 mg
⏰ Frecuencia: Cada 12 horas
📅 Duración del tratamiento: 5 dias

⚕️ Recordatorio automático de tratamiento médico
```

**Recurrencia:** `RRULE:FREQ=HOURLY;INTERVAL=12;COUNT=10`

**Calendario de eventos:**
- 2024-01-15 08:00 - Tomar Diclofenaco
- 2024-01-15 20:00 - Tomar Diclofenaco
- 2024-01-16 08:00 - Tomar Diclofenaco
- 2024-01-16 20:00 - Tomar Diclofenaco
- 2024-01-17 08:00 - Tomar Diclofenaco
- 2024-01-17 20:00 - Tomar Diclofenaco
- 2024-01-18 08:00 - Tomar Diclofenaco
- 2024-01-18 20:00 - Tomar Diclofenaco
- 2024-01-19 08:00 - Tomar Diclofenaco
- 2024-01-19 20:00 - Tomar Diclofenaco

**Total:** 10 recordatorios en 5 días

---

#### Medicamento 2: Vitamina D3

**Título:** 💊 Vitamina D3 - 1000 UI

**Descripción:**
```
💊 Medicamento: Vitamina D3
📊 Dosis: 1000 UI
⏰ Frecuencia: Cada 1 dias
📅 Duración del tratamiento: 3 meses

⚕️ Recordatorio automático de tratamiento médico
```

**Recurrencia:** `RRULE:FREQ=DAILY;COUNT=90`

**Calendario de eventos:**
- 2024-01-15 14:00 - Tomar Vitamina D3
- 2024-01-16 14:00 - Tomar Vitamina D3
- 2024-01-17 14:00 - Tomar Vitamina D3
- ... (continúa diariamente)
- 2024-04-14 14:00 - Tomar Vitamina D3

**Total:** 90 recordatorios en 3 meses

---

## Más Ejemplos

### Ejemplo 1: Antibiótico (Amoxicilina)

```json
{
  "patient_email": "juan.perez@email.com",
  "producto": "Amoxicilina",
  "dosis": "875 mg",
  "frecuencia": 12,
  "medicion_frecuencia": "horas",
  "duracion": 7,
  "duracion_frecuencia": "dias"
}
```

**Resultado:**
- Cada 12 horas durante 7 días
- Total: 14 recordatorios
- RRULE: `FREQ=HOURLY;INTERVAL=12;COUNT=14`

---

### Ejemplo 2: Medicamento Crónico (Metformina)

```json
{
  "patient_email": "maria.garcia@email.com",
  "producto": "Metformina",
  "dosis": "850 mg",
  "frecuencia": 12,
  "medicion_frecuencia": "horas",
  "duracion": 3,
  "duracion_frecuencia": "meses"
}
```

**Resultado:**
- Cada 12 horas durante 3 meses
- Total: 180 recordatorios
- RRULE: `FREQ=HOURLY;INTERVAL=12;COUNT=180`

---

### Ejemplo 3: Suplemento Semanal

```json
{
  "patient_email": "carlos.lopez@email.com",
  "producto": "Vitamina B12",
  "dosis": "1000 mcg",
  "frecuencia": 7,
  "medicion_frecuencia": "dias",
  "duracion": 2,
  "duracion_frecuencia": "meses"
}
```

**Resultado:**
- Cada 7 días durante 2 meses
- Total: 9 recordatorios (aproximadamente)
- RRULE: `FREQ=DAILY;INTERVAL=7;COUNT=9`

---

### Ejemplo 4: Gotas Oftálmicas

```json
{
  "patient_email": "ana.martinez@email.com",
  "producto": "Lagrifilm",
  "dosis": null,
  "frecuencia": 3,
  "medicion_frecuencia": "horas",
  "duracion": 1,
  "duracion_frecuencia": "meses"
}
```

**Resultado:**
- Cada 3 horas durante 1 mes
- Total: 240 recordatorios
- RRULE: `FREQ=HOURLY;INTERVAL=3;COUNT=240`

---

## Notificaciones que Recibirá el Paciente

### Email (30 minutos antes)

```
Asunto: Recordatorio: 💊 Diclofenaco - 75 mg

Hola,

Este es un recordatorio de tu medicamento:

💊 Medicamento: Diclofenaco
📊 Dosis: 75 mg
⏰ Hora: 08:00 AM

⚕️ Recordatorio automático de tratamiento médico

---
Ver en Google Calendar: [Link]
```

### Notificación Popup (al momento)

```
💊 Diclofenaco - 75 mg
Ahora - 08:00 AM

Es hora de tomar tu medicamento
```

---

## Visualización en Google Calendar

```
Enero 2024

Lun 15
  08:00 💊 Diclofenaco - 75 mg
  14:00 💊 Vitamina D3 - 1000 UI
  20:00 💊 Diclofenaco - 75 mg

Mar 16
  08:00 💊 Diclofenaco - 75 mg
  14:00 💊 Vitamina D3 - 1000 UI
  20:00 💊 Diclofenaco - 75 mg

Mié 17
  08:00 💊 Diclofenaco - 75 mg
  14:00 💊 Vitamina D3 - 1000 UI
  20:00 💊 Diclofenaco - 75 mg

...
```

---

## Integración con Python

```python
import requests
import json

# Cargar receta del DataGenerator
with open('DataGenerator/example-data/recetas.json', 'r') as f:
    recetas = json.load(f)

# Tomar la primera receta
receta = recetas[0]

# Agregar email del paciente
receta['patient_email'] = 'paciente@email.com'

# Enviar al API
response = requests.post(
    'https://tu-api.execute-api.us-east-1.amazonaws.com/dev/calendar/receta',
    json=receta
)

print(response.json())
```

---

## Casos Especiales

### Medicamento sin dosis

```json
{
  "producto": "nasalub",
  "dosis": null,
  "frecuencia": 2,
  "medicion_frecuencia": "horas",
  "duracion": 1,
  "duracion_frecuencia": "meses"
}
```

El evento se creará sin mostrar la dosis:
- Título: `💊 nasalub`
- Descripción no incluirá la línea de dosis

---

### Múltiples medicamentos al mismo tiempo

Si dos medicamentos tienen la misma frecuencia, el sistema los distribuye en horarios diferentes:

- Medicamento 1: 08:00
- Medicamento 2: 14:00
- Medicamento 3: 20:00
- Medicamento 4: 08:00 (siguiente ciclo)

---

## Troubleshooting

### Problema: Demasiados eventos

Si un medicamento genera más de 500 eventos, considera:
- Reducir la duración
- Aumentar la frecuencia
- Dividir en múltiples recetas

### Problema: Horarios incorrectos

Verifica:
- Zona horaria configurada: `America/Lima`
- Formato de `start_time`: `YYYY-MM-DD HH:MM`
- Que el servidor tenga la hora correcta

### Problema: No llegan notificaciones

Verifica:
- Email del paciente es correcto
- Configuración de notificaciones en Google Calendar
- Permisos del API para enviar invitaciones

---

## Mejores Prácticas

1. **Siempre especifica `start_date`** para control preciso
2. **Usa horarios realistas** (8:00, 14:00, 20:00)
3. **Agrupa medicamentos** con frecuencias similares
4. **Verifica el email** antes de enviar
5. **Prueba con un medicamento** antes de enviar la receta completa

---

## Próximas Funcionalidades

- [ ] Modificar eventos existentes
- [ ] Cancelar tratamientos
- [ ] Marcar dosis como tomadas
- [ ] Estadísticas de adherencia
- [ ] Recordatorios personalizados por paciente
- [ ] Integración con wearables

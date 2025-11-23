import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import random
import os

# Configuración
OUTPUT_DIR = Path(__file__).parent / "example-data"
SCHEMAS_DIR = Path(__file__).parent / "schemas-validation"

# Datos base para generar ejemplos realistas
NOMBRES = [
    "Juan Pérez", "María García", "Carlos López", "Ana Martínez",
    "Luis Rodríguez", "Carmen Fernández", "José González", "Laura Sánchez",
    "Miguel Torres", "Isabel Ramírez", "Pedro Flores", "Sofía Castro",
    "Diego Morales", "Valentina Ortiz", "Andrés Silva", "Camila Rojas",
    "Magali Flores", "Roberto Díaz", "Patricia Ruiz", "Fernando Vega"
]

NOMBRES_DEPENDIENTES = [
    "Pedrito", "Anita", "Carlitos", "Lucía", "Mateo", "Valentina",
    "Sebastián", "Emma", "Santiago", "Mía", "Benjamín", "Isabella",
    "Nicolás", "Sofía", "Martín", "Victoria", "Joaquín", "Camila",
    "Abuela Rosa", "Abuelo José", "Abuela Carmen", "Abuelo Luis",
    "Abuela María", "Abuelo Pedro", "Abuela Ana", "Abuelo Carlos"
]

CORREOS_DOMINIOS = ["utec.edu.pe", "gmail.com", "outlook.com"]

INSTITUCIONES = [
    "Centro Dermatológico \"Dr. Ladislao de la Pascua\"",
    "Hospital General de México",
    "Clínica Santa María",
    "Instituto Nacional de Salud",
    "Hospital Universitario",
    "Centro Médico ABC",
    "Clínica Las Américas"
]

MEDICAMENTOS = [
    {"producto": "Trevissage", "dosis": "20 mg", "frecuencia_valor": 1, "frecuencia_unidad": "dia", "duracion": "2 meses"},
    {"producto": "Paracetamol", "dosis": "500 mg", "frecuencia_valor": 8, "frecuencia_unidad": "horas", "duracion": "5 dias"},
    {"producto": "Ibuprofeno", "dosis": "400 mg", "frecuencia_valor": 12, "frecuencia_unidad": "horas", "duracion": "3 dias"},
    {"producto": "Amoxicilina", "dosis": "875 mg", "frecuencia_valor": 12, "frecuencia_unidad": "horas", "duracion": "7 dias"},
    {"producto": "nasalub", "dosis": None, "frecuencia_valor": 2, "frecuencia_unidad": "horas", "duracion": "1 mes"},
    {"producto": "Lagrifilm", "dosis": None, "frecuencia_valor": 3, "frecuencia_unidad": "horas", "duracion": "1 mes"},
    {"producto": "agua Thermal", "dosis": None, "frecuencia_valor": 2, "frecuencia_unidad": "horas", "duracion": "2 meses"},
    {"producto": "Labello", "dosis": None, "frecuencia_valor": 3, "frecuencia_unidad": "horas", "duracion": "1 mes"},
    {"producto": "Omeprazol", "dosis": "20 mg", "frecuencia_valor": 1, "frecuencia_unidad": "dia", "duracion": "14 dias"},
    {"producto": "Loratadina", "dosis": "10 mg", "frecuencia_valor": 24, "frecuencia_unidad": "horas", "duracion": "10 dias"},
    {"producto": "Aspirina", "dosis": "100 mg", "frecuencia_valor": 1, "frecuencia_unidad": "dia", "duracion": "1 mes"},
    {"producto": "Metformina", "dosis": "850 mg", "frecuencia_valor": 12, "frecuencia_unidad": "horas", "duracion": "3 meses"},
    {"producto": "Atorvastatina", "dosis": "20 mg", "frecuencia_valor": 1, "frecuencia_unidad": "dia", "duracion": "6 meses"},
    {"producto": "Losartán", "dosis": "50 mg", "frecuencia_valor": 1, "frecuencia_unidad": "dia", "duracion": "3 meses"},
    {"producto": "Cetirizina", "dosis": "10 mg", "frecuencia_valor": 1, "frecuencia_unidad": "dia", "duracion": "15 dias"},
    {"producto": "Azitromicina", "dosis": "500 mg", "frecuencia_valor": 1, "frecuencia_unidad": "dia", "duracion": "3 dias"},
    {"producto": "Diclofenaco", "dosis": "75 mg", "frecuencia_valor": 12, "frecuencia_unidad": "horas", "duracion": "5 dias"},
    {"producto": "Ranitidina", "dosis": "150 mg", "frecuencia_valor": 12, "frecuencia_unidad": "horas", "duracion": "30 dias"},
    {"producto": "Clonazepam", "dosis": "0.5 mg", "frecuencia_valor": 1, "frecuencia_unidad": "dia", "duracion": "2 meses"},
    {"producto": "Vitamina D3", "dosis": "1000 UI", "frecuencia_valor": 1, "frecuencia_unidad": "dia", "duracion": "3 meses"}
]

SERVICIOS_BASE = [
    {"nombre": "Tomar un descanso de 10 minutos", "descripcion": "Se detectaron altos niveles de estrés o se bajó un 10% el nivel de sueño"},
    {"nombre": "Realizar ejercicios de respiración", "descripcion": "La frecuencia cardíaca supera los 100 bpm en reposo"},
    {"nombre": "Hidratarse con un vaso de agua", "descripcion": "Han pasado más de 2 horas sin registrar ingesta de líquidos"},
    {"nombre": "Hacer estiramientos de 5 minutos", "descripcion": "Se detectó más de 2 horas de inactividad continua"},
    {"nombre": "Salir a caminar 15 minutos", "descripcion": "Los niveles de vitamina D están bajos o no hay exposición solar"},
    {"nombre": "Meditar durante 10 minutos", "descripcion": "Los niveles de ansiedad superan el umbral normal"},
    {"nombre": "Tomar un snack saludable", "descripcion": "Los niveles de glucosa están por debajo del rango óptimo"},
    {"nombre": "Descansar la vista (regla 20-20-20)", "descripcion": "Más de 1 hora frente a pantallas sin descanso"},
    {"nombre": "Escuchar música relajante", "descripcion": "Se detectaron patrones de estrés o tensión muscular"},
    {"nombre": "Realizar ejercicio cardiovascular", "descripcion": "No se ha registrado actividad física en las últimas 24 horas"},
    {"nombre": "Practicar yoga o pilates", "descripcion": "Los niveles de flexibilidad o movilidad han disminuido"},
    {"nombre": "Tomar una siesta de 20 minutos", "descripcion": "El nivel de sueño acumulado es menor a 6 horas"},
    {"nombre": "Socializar con compañeros", "descripcion": "No se han registrado interacciones sociales en 48 horas"},
    {"nombre": "Organizar el espacio de trabajo", "descripcion": "Los niveles de productividad han bajado un 15%"},
    {"nombre": "Leer un libro o artículo", "descripcion": "Se detectó fatiga mental o necesidad de cambio de actividad"},
    {"nombre": "Tomar el medicamento prescrito", "descripcion": "Es hora de la dosis según la receta médica"},
    {"nombre": "Realizar ejercicios de postura", "descripcion": "Se detectó mala postura durante más de 30 minutos"},
    {"nombre": "Consumir frutas o verduras", "descripcion": "No se ha registrado consumo de nutrientes esenciales hoy"},
    {"nombre": "Practicar mindfulness", "descripcion": "Los niveles de concentración están por debajo del 70%"},
    {"nombre": "Desconectar dispositivos electrónicos", "descripcion": "Tiempo de pantalla supera las 8 horas continuas"}
]

AUTHORITY_NAME = os.getenv("AUTHORITY_USUARIO_NOMBRE", "Autoridad UTEC")
AUTHORITY_EMAIL = os.getenv("AUTHORITY_USUARIO_CORREO", "autoridad@utec.edu.pe")
AUTHORITY_PASSWORD = os.getenv("AUTHORITY_USUARIO_CONTRASENA", "autoridad123")

USUARIOS_TOTAL = int(os.getenv("USUARIOS_TOTAL", "30"))

def generar_correo(nombre):
    """Genera un correo electrónico basado en el nombre"""
    nombre_limpio = nombre.lower().replace(" ", ".")
    dominio = random.choice(CORREOS_DOMINIOS)
    return f"{nombre_limpio}@{dominio}"

def generar_usuarios(cantidad=None):
    usuarios = []
    roles_no_autoridad = ["USER", "ADMIN"]
    objetivo = max(1, cantidad or USUARIOS_TOTAL)
    
    autoridad = {
        "correo": AUTHORITY_EMAIL,
        "contrasena": AUTHORITY_PASSWORD,
        "nombre": AUTHORITY_NAME,
        "sexo": random.choice(["M", "F"]),
        "rol": "TUTOR"
    }
    usuarios.append(autoridad)
    correos_usados = {AUTHORITY_EMAIL}
    
    while len(usuarios) < objetivo:
        nombre = random.choice(NOMBRES)
        correo = generar_correo(nombre)
        if correo in correos_usados:
            continue
        usuarios.append({
            "correo": correo,
            "contrasena": f"hash_{uuid.uuid4().hex[:16]}",
            "nombre": nombre,
            "sexo": random.choice(["M", "F"]),
            "rol": random.choice(roles_no_autoridad)
        })
        correos_usados.add(correo)
    
    if not any(u["rol"] == "USER" for u in usuarios):
        while True:
            nombre = random.choice(NOMBRES)
            correo = generar_correo(nombre)
            if correo in correos_usados:
                continue
            usuarios.append({
                "correo": correo,
                "contrasena": f"hash_{uuid.uuid4().hex[:16]}",
                "nombre": nombre,
                "sexo": random.choice(["M", "F"]),
                "rol": "USER"
            })
            correos_usados.add(correo)
            break
    
    return usuarios

def generar_recetas(usuarios):
    """Genera recetas vinculadas a los usuarios"""
    recetas = []
    
    for usuario in usuarios:
        # 70% de probabilidad de tener recetas
        if random.random() > 0.3:
            # Generar entre 1 y 3 recetas por usuario
            num_recetas = random.randint(1, 3)
            
            for _ in range(num_recetas):
                institucion = random.choice(INSTITUCIONES)
                
                # Generar entre 1 y 5 medicamentos por receta
                num_medicamentos = random.randint(1, 5)
                medicamentos_receta = random.sample(MEDICAMENTOS, min(num_medicamentos, len(MEDICAMENTOS)))
                
                # Copiar los medicamentos para no modificar los originales
                medicamentos_formateados = []
                for med in medicamentos_receta:
                    medicamento = {
                        "producto": med["producto"],
                        "dosis": med["dosis"],
                        "frecuencia_valor": med["frecuencia_valor"],
                        "frecuencia_unidad": med["frecuencia_unidad"],
                        "duracion": med["duracion"]
                    }
                    medicamentos_formateados.append(medicamento)
                
                receta = {
                    "correo": usuario["correo"],
                    "receta_id": f"rec-{str(uuid.uuid4())[:8]}",
                    "paciente": usuario["nombre"],
                    "institucion": institucion,
                    "recetas": medicamentos_formateados
                }
                
                recetas.append(receta)
    
    return recetas

def generar_servicios(usuarios=None):
    """Genera datos de ejemplo para servicios (catálogo global)"""
    servicios = []
    
    # Categorías para asignar
    categorias = ["bienestar", "salud", "productividad", "social"]
    
    for s in SERVICIOS_BASE:
        servicio = {
            "nombre": s["nombre"],
            "descripcion": s["descripcion"],
            "categoria": random.choice(categorias)
        }
        servicios.append(servicio)
            
    return servicios

def generar_memoria_contextual(usuarios):
    """Genera datos de memoria contextual (chatbot)"""
    memorias = []
    
    temas = ["nutrición", "ejercicio", "sueño", "estrés", "medicación"]
    intenciones = ["consultar", "registrar", "pedir consejo", "quejarse"]
    
    for usuario in usuarios:
        # Generar entre 0 y 5 interacciones pasadas
        num_interacciones = random.randint(0, 5)
        
        for _ in range(num_interacciones):
            fecha = (datetime.now() - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))).isoformat()
            tema = random.choice(temas)
            
            # Datos extraídos específicos según el tema
            datos_extraidos = {
                "tema_principal": tema,
                "sentimiento": random.choice(["positivo", "negativo", "neutral"]),
                "urgencia": random.choice(["alta", "media", "baja"])
            }
            
            if tema == "nutrición":
                datos_extraidos["preferencia_alimenticia"] = random.choice(["vegetariano", "omnívoro", "keto"])
            elif tema == "sueño":
                datos_extraidos["horas_promedio"] = random.randint(4, 9)
            
            memoria = {
                "correo": usuario["correo"],
                "context_id": f"ctx-{uuid.uuid4().hex[:8]}",
                "fecha": fecha,
                "resumen_conversacion": f"El usuario consultó sobre {tema} y se le recomendó mejorar sus hábitos.",
                "intencion_detectada": random.choice(intenciones),
                "datos_extraidos": datos_extraidos
            }
            memorias.append(memoria)
            
    return memorias

def generar_historial_medico(usuarios):
    """Genera historial médico con datos de sensores/wearables"""
    historiales = []
    
    for usuario in usuarios:
        # Generar historial para los últimos 7 días
        for i in range(7):
            fecha = (datetime.now() - timedelta(days=i)).replace(hour=23, minute=59, second=59).isoformat()
            
            pasos = random.randint(2000, 15000)
            sueno = random.randint(4, 10)
            ritmo = random.randint(60, 100)
            
            registro = {
                "correo": usuario["correo"],
                "fecha": fecha,
                "sensores": {
                    "pasos": pasos,
                    "horas_de_sueno": sueno
                }
            }
            
            # 50% de probabilidad de tener datos de wearables extra
            if random.random() > 0.5:
                registro["wearables"] = {
                    "pasos": pasos + random.randint(-100, 100), # Ligera variación
                    "ritmo_cardiaco": ritmo,
                    "horas_de_sueno": sueno
                }
            
            historiales.append(registro)
            
    return historiales

def generar_usuarios_dependientes(usuarios):
    """Genera usuarios dependientes vinculados a tutores"""
    dependientes = []
    tutores = [u for u in usuarios if u["rol"] == "TUTOR"]
    
    if not tutores:
        print("⚠️  No hay tutores disponibles para generar dependientes")
        return dependientes
    
    for tutor in tutores:
        # Cada tutor tiene entre 1 y 3 dependientes
        num_dependientes = random.randint(1, 3)
        
        for _ in range(num_dependientes):
            parentesco = random.choice(["HIJO", "ADULTO_MAYOR"])
            
            # Generar fecha de cumpleaños según el parentesco
            if parentesco == "HIJO":
                # Niños entre 0 y 17 años
                edad_anos = random.randint(0, 17)
                cumpleanos = (datetime.now() - timedelta(days=edad_anos * 365 + random.randint(0, 364))).strftime("%Y-%m-%d")
            else:
                # Adultos mayores entre 60 y 90 años
                edad_anos = random.randint(60, 90)
                cumpleanos = (datetime.now() - timedelta(days=edad_anos * 365 + random.randint(0, 364))).strftime("%Y-%m-%d")
            
            dependiente = {
                "correo_tutor": tutor["correo"],
                "dependiente_id": f"dep-{uuid.uuid4().hex[:8]}",
                "nombre": random.choice(NOMBRES_DEPENDIENTES),
                "cumpleanos": cumpleanos,
                "parentesco": parentesco,
                "sexo": random.choice(["M", "F"])
            }
            dependientes.append(dependiente)
    
    return dependientes

def generar_reglas():
    """Genera reglas de salud para pediatría y adultos mayores"""
    reglas = [
        # Reglas de vacunas para pediatría
        {
            "nombre": "Vacuna BCG",
            "descripcion": "Vacuna contra tuberculosis, aplicada al nacer",
            "categoria": "vacunas",
            "grupo_edad": "pediatria",
            "unidad": "dias",
            "regla_activa_empieza_dias": 0,
            "regla_activa_termina_dias": 30,
            "frecuencia_meses": 1
        },
        {
            "nombre": "Vacuna Pentavalente",
            "descripcion": "Vacuna pentavalente (DPT, Hib, Hepatitis B)",
            "categoria": "vacunas",
            "grupo_edad": "pediatria",
            "unidad": "meses",
            "regla_activa_empieza_meses": 2,
            "regla_activa_termina_meses": 6,
            "frecuencia_meses": 2
        },
        # Reglas de chequeos pediátricos
        {
            "nombre": "Control de niño sano - Primer año",
            "descripcion": "Controles mensuales durante el primer año de vida",
            "categoria": "chequeos_pediatria",
            "grupo_edad": "pediatria",
            "unidad": "meses",
            "regla_activa_empieza_meses": 0,
            "regla_activa_termina_meses": 12,
            "frecuencia_meses": 1
        },
        {
            "nombre": "Control de niño sano - Segundo año",
            "descripcion": "Controles cada 2 meses durante el segundo año",
            "categoria": "chequeos_pediatria",
            "grupo_edad": "pediatria",
            "unidad": "meses",
            "regla_activa_empieza_meses": 12,
            "regla_activa_termina_meses": 24,
            "frecuencia_meses": 2
        },
        # Reglas de tamizajes pediátricos
        {
            "nombre": "Tamizaje auditivo neonatal",
            "descripcion": "Prueba de audición en recién nacidos",
            "categoria": "tamizajes_pediatria",
            "grupo_edad": "pediatria",
            "unidad": "dias",
            "regla_activa_empieza_dias": 0,
            "regla_activa_termina_dias": 30,
            "frecuencia_meses": 1
        },
        # Reglas de odontología
        {
            "nombre": "Primera visita al dentista",
            "descripcion": "Primera consulta odontológica",
            "categoria": "odontologia",
            "grupo_edad": "pediatria",
            "unidad": "meses",
            "regla_activa_empieza_meses": 6,
            "regla_activa_termina_meses": 12,
            "frecuencia_meses": 6
        },
        # Reglas para adultos mayores - seguimiento de crónicos
        {
            "nombre": "Control de presión arterial",
            "descripcion": "Monitoreo mensual de presión arterial",
            "categoria": "cronicos_seguimiento",
            "grupo_edad": "adulto_mayor",
            "unidad": "meses",
            "regla_activa_empieza_meses": 720,  # 60 años
            "regla_activa_termina_meses": 1200,  # 100 años
            "frecuencia_meses": 1
        },
        {
            "nombre": "Control de glucosa",
            "descripcion": "Monitoreo trimestral de glucosa en sangre",
            "categoria": "cronicos_seguimiento",
            "grupo_edad": "adulto_mayor",
            "unidad": "meses",
            "regla_activa_empieza_meses": 720,
            "regla_activa_termina_meses": 1200,
            "frecuencia_meses": 3
        },
        # Reglas funcionales para adultos mayores
        {
            "nombre": "Evaluación funcional geriátrica",
            "descripcion": "Evaluación semestral de capacidades funcionales",
            "categoria": "funcional_mayor",
            "grupo_edad": "adulto_mayor",
            "unidad": "meses",
            "regla_activa_empieza_meses": 720,
            "regla_activa_termina_meses": 1200,
            "frecuencia_meses": 6
        }
    ]
    
    return reglas

def generar_alerta_dependientes(dependientes, reglas):
    """Genera alertas para dependientes basadas en reglas"""
    alertas = []
    
    # Mapeo de reglas a mensajes de alerta
    reglas_pediatria = [r for r in reglas if r["grupo_edad"] == "pediatria"]
    reglas_adulto_mayor = [r for r in reglas if r["grupo_edad"] == "adulto_mayor"]
    
    for dependiente in dependientes:
        # Seleccionar reglas según el parentesco
        if dependiente["parentesco"] == "HIJO":
            reglas_aplicables = reglas_pediatria
        else:  # ADULTO_MAYOR
            reglas_aplicables = reglas_adulto_mayor
        
        # 50% de probabilidad de tener alertas activas
        if random.random() < 0.5 and reglas_aplicables:
            num_alertas = random.randint(1, 2)
            reglas_seleccionadas = random.sample(reglas_aplicables, min(num_alertas, len(reglas_aplicables)))
            
            for regla in reglas_seleccionadas:
                # Generar mensaje según la categoría
                if regla["categoria"] == "vacunas":
                    title = f"Vacuna pendiente: {regla['nombre']}"
                    message = f"Es momento de aplicar {regla['descripcion'].lower()}"
                elif regla["categoria"] == "chequeos_pediatria":
                    title = f"Control médico: {regla['nombre']}"
                    message = f"Se acerca la fecha de {regla['descripcion'].lower()}"
                elif regla["categoria"] == "odontologia":
                    title = f"Cita odontológica: {regla['nombre']}"
                    message = f"Recordatorio: {regla['descripcion'].lower()}"
                elif regla["categoria"] == "cronicos_seguimiento":
                    title = f"Control de salud: {regla['nombre']}"
                    message = f"Es necesario realizar {regla['descripcion'].lower()}"
                elif regla["categoria"] == "funcional_mayor":
                    title = f"Evaluación: {regla['nombre']}"
                    message = f"Corresponde realizar {regla['descripcion'].lower()}"
                else:
                    title = f"Recordatorio: {regla['nombre']}"
                    message = regla["descripcion"]
                
                alerta = {
                    "alerta_id": f"alert-{uuid.uuid4().hex[:8]}",
                    "correo_tutor": dependiente["correo_tutor"],
                    "dependent_id": dependiente["dependiente_id"],
                    "regla_nombre": regla["nombre"],
                    "title": title,
                    "message": message,
                    "estado": random.choice([True, False])  # True = activa, False = atendida
                }
                alertas.append(alerta)
    
    return alertas

def validar_con_esquema(datos, nombre_esquema):
    """Valida que los datos cumplan con el esquema definido"""
    try:
        with open(SCHEMAS_DIR / f"{nombre_esquema}.json", "r", encoding="utf-8") as f:
            esquema = json.load(f)
        
        # Verificar propiedades requeridas
        required = esquema.get("required", [])
        for item in datos:
            for campo in required:
                if campo not in item:
                    print(f"⚠️  Advertencia: Falta campo requerido '{campo}' en {nombre_esquema}")
                    return False
        
        print(f"✅ Datos de {nombre_esquema} validados correctamente")
        return True
    except Exception as e:
        print(f"❌ Error al validar {nombre_esquema}: {e}")
        return False

def guardar_json(datos, nombre_archivo):
    """Guarda los datos en un archivo JSON"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    ruta = OUTPUT_DIR / nombre_archivo
    
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)
    
    print(f"📝 Generado: {ruta} ({len(datos)} registros)")

def main():
    """Función principal que orquesta la generación de datos"""
    print("=" * 60)
    print("🚀 GENERADOR DE DATOS - SISTEMA DE RECETAS")
    print("=" * 60)
    print()
    
    # Generar usuarios
    print("📊 Generando usuarios...")
    usuarios = generar_usuarios()
    validar_con_esquema(usuarios, "usuarios")
    guardar_json(usuarios, "usuarios.json")
    print()
    
    # Generar usuarios dependientes
    print("📊 Generando usuarios dependientes...")
    dependientes = generar_usuarios_dependientes(usuarios)
    validar_con_esquema(dependientes, "usuarios_dependientes")
    guardar_json(dependientes, "usuarios_dependientes.json")
    print()
    
    # Generar reglas
    print("📊 Generando reglas...")
    reglas = generar_reglas()
    validar_con_esquema(reglas, "reglas")
    guardar_json(reglas, "reglas.json")
    print()
    
    # Generar alertas de dependientes (requiere dependientes y reglas)
    print("📊 Generando alertas de dependientes...")
    alertas = generar_alerta_dependientes(dependientes, reglas)
    validar_con_esquema(alertas, "alerta_dependientes")
    guardar_json(alertas, "alerta_dependientes.json")
    print()
    
    # Generar servicios
    print("📊 Generando servicios...")
    servicios = generar_servicios()
    validar_con_esquema(servicios, "servicios")
    guardar_json(servicios, "servicios.json")
    print()
    
    # Generar recetas
    print("📊 Generando recetas...")
    recetas = generar_recetas(usuarios)
    validar_con_esquema(recetas, "recetas")
    guardar_json(recetas, "recetas.json")
    print()

    # Generar memoria contextual
    print("📊 Generando memoria contextual...")
    memorias = generar_memoria_contextual(usuarios)
    validar_con_esquema(memorias, "memoria_contextual")
    guardar_json(memorias, "memoria_contextual.json")
    print()

    # Generar historial medico
    print("📊 Generando historial medico...")
    historiales = generar_historial_medico(usuarios)
    validar_con_esquema(historiales, "historial_medico")
    guardar_json(historiales, "historial_medico.json")
    print()
    
    print("=" * 60)
    print("✨ Generación completada exitosamente")
    print(f"📂 Archivos guardados en: {OUTPUT_DIR}")
    print("=" * 60)

if __name__ == "__main__":
    main()

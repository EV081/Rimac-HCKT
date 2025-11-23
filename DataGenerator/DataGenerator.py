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
    {"producto": "Trevissage", "dosis": "20 mg", "frecuencia": 1, "medicion_frecuencia": "dias", "duracion": 2, "duracion_frecuencia": "meses"},
    {"producto": "Paracetamol", "dosis": "500 mg", "frecuencia": 8, "medicion_frecuencia": "horas", "duracion": 5, "duracion_frecuencia": "dias"},
    {"producto": "Ibuprofeno", "dosis": "400 mg", "frecuencia": 12, "medicion_frecuencia": "horas", "duracion": 3, "duracion_frecuencia": "dias"},
    {"producto": "Amoxicilina", "dosis": "875 mg", "frecuencia": 12, "medicion_frecuencia": "horas", "duracion": 7, "duracion_frecuencia": "dias"},
    {"producto": "nasalub", "dosis": None, "frecuencia": 2, "medicion_frecuencia": "horas", "duracion": 1, "duracion_frecuencia": "meses"},
    {"producto": "Lagrifilm", "dosis": None, "frecuencia": 3, "medicion_frecuencia": "horas", "duracion": 1, "duracion_frecuencia": "meses"},
    {"producto": "agua Thermal", "dosis": None, "frecuencia": 2, "medicion_frecuencia": "horas", "duracion": 2, "duracion_frecuencia": "meses"},
    {"producto": "Labello", "dosis": None, "frecuencia": 3, "medicion_frecuencia": "horas", "duracion": 1, "duracion_frecuencia": "meses"},
    {"producto": "Omeprazol", "dosis": "20 mg", "frecuencia": 1, "medicion_frecuencia": "dias", "duracion": 14, "duracion_frecuencia": "dias"},
    {"producto": "Loratadina", "dosis": "10 mg", "frecuencia": 24, "medicion_frecuencia": "horas", "duracion": 10, "duracion_frecuencia": "dias"},
    {"producto": "Aspirina", "dosis": "100 mg", "frecuencia": 1, "medicion_frecuencia": "dias", "duracion": 1, "duracion_frecuencia": "meses"},
    {"producto": "Metformina", "dosis": "850 mg", "frecuencia": 12, "medicion_frecuencia": "horas", "duracion": 3, "duracion_frecuencia": "meses"},
    {"producto": "Atorvastatina", "dosis": "20 mg", "frecuencia": 1, "medicion_frecuencia": "dias", "duracion": 6, "duracion_frecuencia": "meses"},
    {"producto": "Losartán", "dosis": "50 mg", "frecuencia": 1, "medicion_frecuencia": "dias", "duracion": 3, "duracion_frecuencia": "meses"},
    {"producto": "Cetirizina", "dosis": "10 mg", "frecuencia": 1, "medicion_frecuencia": "dias", "duracion": 15, "duracion_frecuencia": "dias"},
    {"producto": "Azitromicina", "dosis": "500 mg", "frecuencia": 1, "medicion_frecuencia": "dias", "duracion": 3, "duracion_frecuencia": "dias"},
    {"producto": "Diclofenaco", "dosis": "75 mg", "frecuencia": 12, "medicion_frecuencia": "horas", "duracion": 5, "duracion_frecuencia": "dias"},
    {"producto": "Ranitidina", "dosis": "150 mg", "frecuencia": 12, "medicion_frecuencia": "horas", "duracion": 30, "duracion_frecuencia": "dias"},
    {"producto": "Clonazepam", "dosis": "0.5 mg", "frecuencia": 1, "medicion_frecuencia": "dias", "duracion": 2, "duracion_frecuencia": "meses"},
    {"producto": "Vitamina D3", "dosis": "1000 UI", "frecuencia": 1, "medicion_frecuencia": "dias", "duracion": 3, "duracion_frecuencia": "meses"}
]

AUTHORITY_NAME = os.getenv("AUTHORITY_USUARIO_NOMBRE", "Autoridad UTEC")
AUTHORITY_EMAIL = os.getenv("AUTHORITY_USUARIO_CORREO", "autoridad@utec.edu.pe")
AUTHORITY_PASSWORD = os.getenv("AUTHORITY_USUARIO_CONTRASENA", "autoridad123")

USUARIOS_TOTAL = int(os.getenv("USUARIOS_TOTAL", "30"))
RECETAS_TOTAL = int(os.getenv("RECETAS_TOTAL", "10"))


def generar_correo(nombre):
    """Genera un correo electrónico basado en el nombre"""
    nombre_limpio = nombre.lower().replace(" ", ".")
    dominio = random.choice(CORREOS_DOMINIOS)
    return f"{nombre_limpio}@{dominio}"


def generar_usuarios(cantidad=None):
    usuarios = []
    roles_no_autoridad = ["USER", "TUTOR"]
    objetivo = max(1, cantidad or USUARIOS_TOTAL)
    
    autoridad = {
        "correo": AUTHORITY_EMAIL,
        "contrasena": AUTHORITY_PASSWORD,
        "nombre": AUTHORITY_NAME,
        "rol": "ADMIN"
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
            "rol": random.choice(roles_no_autoridad)
        })
        correos_usados.add(correo)
    
    if not any(u["rol"] == "estudiante" for u in usuarios):
        while True:
            nombre = random.choice(NOMBRES)
            correo = generar_correo(nombre)
            if correo in correos_usados:
                continue
            usuarios.append({
                "correo": correo,
                "contrasena": f"hash_{uuid.uuid4().hex[:16]}",
                "nombre": nombre,
                "rol": "estudiante"
            })
            correos_usados.add(correo)
            break
    
    return usuarios


def generar_recetas(cantidad=None):
    """Genera datos de ejemplo para recetas médicas"""
    recetas = []
    cantidad = max(1, cantidad or RECETAS_TOTAL)
    
    for i in range(cantidad):
        paciente = random.choice(NOMBRES)
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
                "frecuencia": med["frecuencia"],
                "medicion_frecuencia": med["medicion_frecuencia"],
                "duracion": med["duracion"],
                "duracion_frecuencia": med["duracion_frecuencia"]
            }
            medicamentos_formateados.append(medicamento)
        
        receta = {
            "receta_id": f"rec-{str(uuid.uuid4())[:8]}",
            "paciente": paciente,
            "institucion": institucion,
            "recetas": medicamentos_formateados
        }
        
        recetas.append(receta)
    
    return recetas


def generar_servicios():
    """Genera datos de ejemplo para servicios (actividades de bienestar)"""
    servicios = [
        {
            "nombre": "Tomar un descanso de 10 minutos",
            "descripcion": "Se detectaron altos niveles de estrés o se bajó un 10% el nivel de sueño"
        },
        {
            "nombre": "Realizar ejercicios de respiración",
            "descripcion": "La frecuencia cardíaca supera los 100 bpm en reposo"
        },
        {
            "nombre": "Hidratarse con un vaso de agua",
            "descripcion": "Han pasado más de 2 horas sin registrar ingesta de líquidos"
        },
        {
            "nombre": "Hacer estiramientos de 5 minutos",
            "descripcion": "Se detectó más de 2 horas de inactividad continua"
        },
        {
            "nombre": "Salir a caminar 15 minutos",
            "descripcion": "Los niveles de vitamina D están bajos o no hay exposición solar"
        },
        {
            "nombre": "Meditar durante 10 minutos",
            "descripcion": "Los niveles de ansiedad superan el umbral normal"
        },
        {
            "nombre": "Tomar un snack saludable",
            "descripcion": "Los niveles de glucosa están por debajo del rango óptimo"
        },
        {
            "nombre": "Descansar la vista (regla 20-20-20)",
            "descripcion": "Más de 1 hora frente a pantallas sin descanso"
        },
        {
            "nombre": "Escuchar música relajante",
            "descripcion": "Se detectaron patrones de estrés o tensión muscular"
        },
        {
            "nombre": "Realizar ejercicio cardiovascular",
            "descripcion": "No se ha registrado actividad física en las últimas 24 horas"
        },
        {
            "nombre": "Practicar yoga o pilates",
            "descripcion": "Los niveles de flexibilidad o movilidad han disminuido"
        },
        {
            "nombre": "Tomar una siesta de 20 minutos",
            "descripcion": "El nivel de sueño acumulado es menor a 6 horas"
        },
        {
            "nombre": "Socializar con compañeros",
            "descripcion": "No se han registrado interacciones sociales en 48 horas"
        },
        {
            "nombre": "Organizar el espacio de trabajo",
            "descripcion": "Los niveles de productividad han bajado un 15%"
        },
        {
            "nombre": "Leer un libro o artículo",
            "descripcion": "Se detectó fatiga mental o necesidad de cambio de actividad"
        },
        {
            "nombre": "Tomar el medicamento prescrito",
            "descripcion": "Es hora de la dosis según la receta médica"
        },
        {
            "nombre": "Realizar ejercicios de postura",
            "descripcion": "Se detectó mala postura durante más de 30 minutos"
        },
        {
            "nombre": "Consumir frutas o verduras",
            "descripcion": "No se ha registrado consumo de nutrientes esenciales hoy"
        },
        {
            "nombre": "Practicar mindfulness",
            "descripcion": "Los niveles de concentración están por debajo del 70%"
        },
        {
            "nombre": "Desconectar dispositivos electrónicos",
            "descripcion": "Tiempo de pantalla supera las 8 horas continuas"
        }
    ]
    
    return servicios


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
    
    # Generar servicios
    print("📊 Generando servicios...")
    servicios = generar_servicios()
    validar_con_esquema(servicios, "servicios")
    guardar_json(servicios, "servicios.json")
    print()
    
    # Generar recetas
    print("📊 Generando recetas...")
    recetas = generar_recetas()
    validar_con_esquema(recetas, "recetas")
    guardar_json(recetas, "recetas.json")
    print()
    
    print("=" * 60)
    print("✨ Generación completada exitosamente")
    print(f"📂 Archivos guardados en: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()

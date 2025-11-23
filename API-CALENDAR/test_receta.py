#!/usr/bin/env python3
"""
Script de prueba para el endpoint de recetas.
Envía una receta de ejemplo al API de Calendar.
"""

import json
import requests
import sys

# URL del endpoint (cambiar después del deploy)
API_URL = "https://tu-api-id.execute-api.us-east-1.amazonaws.com/dev/calendar/receta"

# Ejemplo de receta (del DataGenerator)
receta_ejemplo = {
    "receta_id": "rec-0c0950ed",
    "paciente": "Valentina Ortiz",
    "patient_email": "valentina.ortiz@gmail.com",  # Cambiar por email real
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

def test_receta_endpoint():
    """Prueba el endpoint de recetas"""
    print("=" * 60)
    print("🧪 PRUEBA DE ENDPOINT: /calendar/receta")
    print("=" * 60)
    print()
    
    print("📋 Datos de la receta:")
    print(json.dumps(receta_ejemplo, indent=2, ensure_ascii=False))
    print()
    
    print("📤 Enviando solicitud...")
    try:
        response = requests.post(
            API_URL,
            json=receta_ejemplo,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"📊 Status Code: {response.status_code}")
        print()
        
        if response.status_code == 200:
            print("✅ ÉXITO - Receta agendada correctamente")
            print()
            result = response.json()
            print("📝 Respuesta:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            # Mostrar resumen
            print()
            print("=" * 60)
            print("📊 RESUMEN")
            print("=" * 60)
            print(f"Paciente: {result.get('paciente')}")
            print(f"Email: {result.get('patient_email')}")
            print(f"Medicamentos agendados: {result.get('total_exitosos')}")
            print()
            
            for med in result.get('medicamentos_agendados', []):
                print(f"💊 {med['producto']} - {med.get('dosis', 'Sin dosis')}")
                print(f"   📅 {med['total_recordatorios']} recordatorios")
                print(f"   🔗 {med['event_link']}")
                print()
        else:
            print("❌ ERROR")
            print(response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión: {e}")
        print()
        print("💡 Asegúrate de:")
        print("   1. Haber desplegado el API con 'serverless deploy'")
        print("   2. Actualizar la variable API_URL con tu endpoint real")
        print("   3. Tener conexión a internet")
        return False
    
    return response.status_code == 200


def test_medicamento_individual():
    """Prueba el endpoint de medicamento individual"""
    url = API_URL.replace('/receta', '/tratamiento')
    
    print()
    print("=" * 60)
    print("🧪 PRUEBA DE ENDPOINT: /calendar/tratamiento")
    print("=" * 60)
    print()
    
    medicamento = {
        "patient_email": "valentina.ortiz@gmail.com",  # Cambiar por email real
        "producto": "Paracetamol",
        "dosis": "500 mg",
        "frecuencia": 8,
        "medicion_frecuencia": "horas",
        "duracion": 5,
        "duracion_frecuencia": "dias",
        "start_time": "2024-01-15 08:00"
    }
    
    print("📋 Datos del medicamento:")
    print(json.dumps(medicamento, indent=2, ensure_ascii=False))
    print()
    
    print("📤 Enviando solicitud...")
    try:
        response = requests.post(
            url,
            json=medicamento,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"📊 Status Code: {response.status_code}")
        print()
        
        if response.status_code == 200:
            print("✅ ÉXITO - Medicamento agendado correctamente")
            print()
            result = response.json()
            print("📝 Respuesta:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("❌ ERROR")
            print(response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión: {e}")
        return False
    
    return response.status_code == 200


if __name__ == "__main__":
    print()
    print("🏥 SISTEMA DE RECORDATORIOS MÉDICOS")
    print("   Prueba de integración con Google Calendar")
    print()
    
    # Verificar que se actualizó la URL
    if "tu-api-id" in API_URL:
        print("⚠️  ADVERTENCIA: Debes actualizar la variable API_URL")
        print("   con tu endpoint real después de hacer 'serverless deploy'")
        print()
        sys.exit(1)
    
    # Ejecutar pruebas
    test1 = test_medicamento_individual()
    test2 = test_receta_endpoint()
    
    print()
    print("=" * 60)
    print("🏁 RESULTADO FINAL")
    print("=" * 60)
    print(f"Medicamento individual: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"Receta completa: {'✅ PASS' if test2 else '❌ FAIL'}")
    print()
    
    sys.exit(0 if (test1 and test2) else 1)

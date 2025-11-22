#!/usr/bin/env python3
"""
Script de ejemplo para probar la función de upload y análisis de recetas.
"""

import base64
import json
import requests

# URL del endpoint (reemplaza con tu URL después del deploy)
API_URL = "https://TU-API-ID.execute-api.us-east-1.amazonaws.com/dev/uploadS3"

def convertir_imagen_a_base64(ruta_imagen):
    """Convierte una imagen local a base64"""
    with open(ruta_imagen, 'rb') as imagen_file:
        return base64.b64encode(imagen_file.read()).decode('utf-8')

def subir_receta(nombre_paciente, nombre_archivo, ruta_imagen):
    """
    Sube una receta médica al sistema.
    
    Args:
        nombre_paciente: Nombre del paciente (ej: "Juan_Lopez")
        nombre_archivo: Nombre del archivo (ej: "imagen_2.png")
        ruta_imagen: Ruta local de la imagen (ej: "./receta.png")
    """
    # Convertir imagen a base64
    imagen_base64 = convertir_imagen_a_base64(ruta_imagen)
    
    # Preparar el payload
    payload = {
        "nombre_paciente": nombre_paciente,
        "nombre_archivo": nombre_archivo,
        "imagen_base64": imagen_base64
    }
    
    # Hacer el request
    print(f"Subiendo receta de {nombre_paciente}...")
    response = requests.post(API_URL, json=payload)
    
    # Mostrar resultado
    if response.status_code == 200:
        resultado = response.json()
        print("\n✅ Receta subida y analizada exitosamente!\n")
        print(f"📁 Ubicación en S3: {resultado['s3']['bucket']}/{resultado['s3']['key']}")
        print(f"📊 Tamaño: {resultado['s3']['tamaño_bytes']} bytes\n")
        
        analisis = resultado['analisis']
        print(f"👨‍⚕️ Doctor: {analisis['doctor']}")
        print(f"👤 Paciente: {analisis['paciente']}")
        print(f"💊 Total de medicinas: {analisis['total_medicinas']}\n")
        
        print("📋 Medicinas e indicaciones:")
        for i, medicina in enumerate(analisis['medicinas'], 1):
            print(f"\n  {i}. {medicina['nombre']}")
            for indicacion in medicina['indicaciones']:
                print(f"     • {indicacion}")
        
        if analisis.get('otras_indicaciones'):
            print(f"\n📝 Otras indicaciones: {analisis['otras_indicaciones']}")
        
        return resultado
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(response.text)
        return None

# Ejemplo de uso
if __name__ == "__main__":
    # Ejemplo 1: Subir receta de Juan Lopez
    subir_receta(
        nombre_paciente="Juan_Lopez",
        nombre_archivo="imagen_2.png",
        ruta_imagen="./mi_receta.png"  # Cambia esto por tu imagen
    )
    
    # Ejemplo 2: Subir otra receta
    # subir_receta(
    #     nombre_paciente="Maria_Garcia",
    #     nombre_archivo="receta_enero_2024.png",
    #     ruta_imagen="./otra_receta.png"
    # )

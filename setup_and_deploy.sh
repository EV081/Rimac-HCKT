#!/bin/bash

# Aumentar memoria de Node.js para Serverless Framework
export NODE_OPTIONS="--max-old-space-size=8192"

# Colores para los logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"; }
log_success() { echo -e "${GREEN}[$(date +'%H:%M:%S')] ✅ $1${NC}"; }
log_error() { echo -e "${RED}[$(date +'%H:%M:%S')] ❌ $1${NC}"; }
log_warning() { echo -e "${YELLOW}[$(date +'%H:%M:%S')] ⚠️  $1${NC}"; }
log_info() { echo -e "${CYAN}[$(date +'%H:%M:%S')] ℹ️  $1${NC}"; }

# Banner
echo ""
echo "═════════════════════════════════════════════════════════════"
echo "         🏥 RIMAC HCKT - DEPLOY MANAGER 🏥           "
echo "═════════════════════════════════════════════════════════════"
echo ""

# Verificar archivo .env
if [ ! -f .env ]; then
    log_error "No se encontró el archivo .env"
    log_info "Copia .env.example a .env y configúralo:"
    log_info "  cp .env.example .env"
    exit 1
fi

log_success "Archivo .env encontrado"

# Función para verificar y configurar variables de entorno
configure_env() {
    log "🔧 Verificando configuración de variables de entorno..."
    
    # Cargar .env
    source .env
    
    # Verificar AWS_ACCOUNT_ID
    if [ -z "$AWS_ACCOUNT_ID" ]; then
        log_warning "AWS_ACCOUNT_ID no configurado"
        log_info "Obteniendo AWS Account ID..."
        AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
        
        if [ -z "$AWS_ACCOUNT_ID" ]; then
            log_error "No se pudo obtener AWS Account ID. Configura tus credenciales AWS."
            exit 1
        fi
        
        # Actualizar .env
        echo "AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID" >> .env
        log_success "AWS_ACCOUNT_ID configurado: $AWS_ACCOUNT_ID"
    else
        log_success "AWS_ACCOUNT_ID: $AWS_ACCOUNT_ID"
    fi
    
    # Configurar nombre del bucket S3 basado en AWS_ACCOUNT_ID
    EXPECTED_BUCKET="recetas-medicas-data-${AWS_ACCOUNT_ID}"
    
    if [ -z "$S3_BUCKET_RECETAS" ] || [ "$S3_BUCKET_RECETAS" != "$EXPECTED_BUCKET" ]; then
        log_warning "Actualizando S3_BUCKET_RECETAS en .env..."
        
        # Remover línea antigua si existe
        sed -i.bak '/^S3_BUCKET_RECETAS=/d' .env
        
        # Agregar nueva línea
        echo "S3_BUCKET_RECETAS=$EXPECTED_BUCKET" >> .env
        
        log_success "S3_BUCKET_RECETAS configurado: $EXPECTED_BUCKET"
    else
        log_success "S3_BUCKET_RECETAS: $S3_BUCKET_RECETAS"
    fi
    
    # Verificar otras variables críticas
    local missing_vars=()
    
    [ -z "$GEMINI_API_KEY" ] && missing_vars+=("GEMINI_API_KEY")
    [ -z "$TABLE_RECETAS" ] && missing_vars+=("TABLE_RECETAS")
    [ -z "$TABLE_SERVICIOS" ] && missing_vars+=("TABLE_SERVICIOS")
    [ -z "$TABLE_USUARIOS" ] && missing_vars+=("TABLE_USUARIOS")
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_error "Variables faltantes en .env:"
        for var in "${missing_vars[@]}"; do
            log_error "  - $var"
        done
        log_info "Por favor configura estas variables en .env"
        exit 1
    fi
    
    log_success "Todas las variables de entorno están configuradas correctamente"
}

# Función para configurar la base de datos
setup_database() {
    log ""
    log "═══════════════════════════════════════════════════════"
    log "🗄️  CONFIGURACIÓN DE BASE DE DATOS (DYNAMODB)"
    log "═══════════════════════════════════════════════════════"
    
    cd DataGenerator || exit 1
    
    # Instalar dependencias
    log "📦 Instalando dependencias de DataGenerator..."
    if [ -f requirements.txt ]; then
        pip install -r requirements.txt --quiet
    else
        log_error "requirements.txt no encontrado en DataGenerator"
        cd ..
        exit 1
    fi
    
    # Crear tablas si no existen
    log "🏗️  Creando tablas DynamoDB si no existen..."
    python3 create_tables.py
    
    if [ $? -ne 0 ]; then
        log_error "Error al crear tablas"
        cd ..
        exit 1
    fi
    
    log_success "Tablas verificadas/creadas correctamente"
    
    # Verificar si las tablas tienen datos
    log "🔍 Verificando estado de las tablas..."
    HAS_DATA=$(python3 -c "
import boto3
import os
from dotenv import load_dotenv
load_dotenv()
dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', 'us-east-1'))
tables = [os.getenv('TABLE_RECETAS', 'Recetas'), os.getenv('TABLE_SERVICIOS', 'Servicios'), os.getenv('TABLE_USUARIOS', 'Usuarios')]
has_data = False
for t_name in tables:
    try:
        table = dynamodb.Table(t_name)
        response = table.scan(Limit=1)
        if 'Items' in response and len(response['Items']) > 0:
            has_data = True
            break
    except:
        pass
print('YES' if has_data else 'NO')
")
    
    RUN_POPULATOR=false
    
    if [ "$HAS_DATA" = "YES" ]; then
        log_warning "⚠️  Se detectaron datos en las tablas."
        read -p "¿Deseas limpiar los datos y volver a poblar? (s/n): " respuesta
        if [ "$respuesta" = "s" ] || [ "$respuesta" = "S" ]; then
            RUN_POPULATOR=true
        else
            log_info "⏭️  Manteniendo datos existentes."
        fi
    else
        log_info "ℹ️  Las tablas parecen estar vacías."
        read -p "¿Deseas poblar las tablas con datos de ejemplo? (s/n): " respuesta
        if [ "$respuesta" = "s" ] || [ "$respuesta" = "S" ]; then
            RUN_POPULATOR=true
        fi
    fi
    
    # Ejecutar poblador si es necesario
    if [ "$RUN_POPULATOR" = true ]; then
        log "🚀 Ejecutando DataPoblator..."
        python3 DataPoblator.py
        
        if [ $? -eq 0 ]; then
            log_success "Datos poblados correctamente"
        else
            log_error "Error al poblar datos"
        fi
    fi
    
    cd ..
}

# Menú de opciones
echo ""
echo "═══════════════════════════════════════════════════════"
echo "  📋 OPCIONES"
echo "═══════════════════════════════════════════════════════"
echo "  1) 🏗️  Configurar Base de Datos (Crear tablas + Poblar)"
echo "  2) 🚀 Desplegar Servicios (Serverless)"
echo "  3) 🗑️  Eliminar todo"
echo "═══════════════════════════════════════════════════════"
echo ""
read -p "Selecciona una opción (1-3): " opcion

# Configurar variables de entorno primero
configure_env

case $opcion in
    1)
        setup_database
        ;;
    2)
        log_info "Iniciando despliegue con Serverless..."
        
        # Verificar Docker
        if ! command -v docker &> /dev/null; then
            log_error "Docker no está instalado. Se requiere para empaquetar dependencias Python."
            exit 1
        fi
        
        if ! docker ps &> /dev/null; then
            log_error "Docker no está corriendo. Inícialo con: sudo systemctl start docker"
            exit 1
        fi
        
        log_success "Docker está disponible"
        
        # Verificar e instalar dependencias de Node.js
        if [ ! -d "node_modules" ] || [ ! -f "package.json" ]; then
            log_warning "Instalando dependencias de Serverless..."
            npm install --save-dev serverless-python-requirements
        fi
        
        # Limpiar carpetas .serverless y cachés en todas las APIs
        log_info "Limpiando archivos temporales y cachés..."
        for api_dir in API-*/; do
            if [ -d "${api_dir}.serverless" ]; then
                rm -rf "${api_dir}.serverless"
                log_info "   Limpiado: ${api_dir}.serverless"
            fi
            if [ -d "${api_dir}__pycache__" ]; then
                rm -rf "${api_dir}__pycache__"
            fi
            # Limpiar archivos .pyc
            find "${api_dir}" -name "*.pyc" -delete 2>/dev/null || true
        done
        
        # Limpiar caché global de serverless-python-requirements
        if [ -d ".serverless" ]; then
            rm -rf ".serverless"
            log_info "   Limpiado: .serverless global"
        fi
        
        if [ -f serverless-compose.yml ]; then
            log_info "Desplegando con Serverless Compose..."
            serverless deploy
        else
            log_warning "No se encontró serverless-compose.yml, intentando despliegue individual..."
            serverless deploy
        fi
        ;;
    3)
        log_warning "⚠️  Esta acción eliminará los recursos desplegados."
        read -p "¿Estás seguro? (s/n): " confirmar
        if [ "$confirmar" = "s" ] || [ "$confirmar" = "S" ]; then
            serverless remove
        fi
        ;;
    *)
        log_error "Opción inválida"
        exit 1
        ;;
esac

echo ""
log_success "✨ Operación completada"
echo ""
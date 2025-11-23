"""
Handler principal para iniciar conversación con el agente
"""
import json
import traceback
from services.agente_service import AgenteService
from utils.exceptions import UsuarioNoEncontradoError, ContextoInvalidoError
from utils.validators import validar_request_agente
from utils.formatters import formatear_respuesta_exitosa, formatear_respuesta_error

# Instancia global del servicio (reutilizada entre invocaciones Lambda)
agente_service = None

def get_agente_service():
    """Lazy loading del servicio para reutilizar conexiones"""
    global agente_service
    if agente_service is None:
        agente_service = AgenteService()
    return agente_service


def handler(event, context):
    """
    Handler Lambda para procesar consultas del agente
    
    Espera un body JSON con:
    {
        "correo": "usuario@example.com",
        "contexto": "General|Servicios|Estadisticas|Recetas",
        "mensaje": "¿Cómo estoy con mis medicamentos?",
        "historial": [...]  // Opcional
    }
    
    Returns:
        Response JSON con la respuesta del agente
    """
    try:
        # 1. Parsear body
        body = json.loads(event.get('body', '{}'))
        
        # 2. Validar request
        errores_validacion = validar_request_agente(body)
        if errores_validacion:
            return formatear_respuesta_error(
                400,
                'Errores de validación',
                errores_validacion
            )
        
        # 3. Extraer parámetros
        correo = body['correo']
        contexto = body['contexto']
        mensaje = body['mensaje']
        historial = body.get('historial', None)
        guardar_memoria = body.get('guardar_memoria', True)
        
        # 4. Procesar consulta
        service = get_agente_service()
        resultado = service.procesar_consulta(
            correo=correo,
            contexto=contexto,
            mensaje_usuario=mensaje,
            historial_conversacion=historial
        )
        
        # 5. Guardar en memoria si se requiere
        if guardar_memoria:
            service.guardar_memoria_conversacion(
                correo=correo,
                mensaje_usuario=mensaje,
                respuesta_agente=resultado['respuesta']
            )
        
        # 6. Retornar respuesta exitosa
        return formatear_respuesta_exitosa(resultado)
    
    except UsuarioNoEncontradoError as e:
        return formatear_respuesta_error(404, 'Usuario no encontrado', str(e))
    
    except ContextoInvalidoError as e:
        return formatear_respuesta_error(400, 'Contexto inválido', str(e))
    
    except json.JSONDecodeError:
        return formatear_respuesta_error(400, 'JSON inválido', 'El body debe ser JSON válido')
    
    except Exception as e:
        print(f"Error inesperado: {str(e)}")
        print(traceback.format_exc())
        return formatear_respuesta_error(
            500,
            'Error interno del servidor',
            'Ocurrió un error procesando tu solicitud'
        )


def obtener_sugerencias_handler(event, context):
    """
    Handler para obtener sugerencias proactivas basadas en el contexto
    
    Espera query params:
    - correo: Email del usuario
    - contexto: Tipo de contexto
    """
    try:
        # Extraer parámetros de query string
        params = event.get('queryStringParameters', {}) or {}
        
        correo = params.get('correo')
        contexto = params.get('contexto', 'General')
        
        if not correo:
            return formatear_respuesta_error(
                400,
                'Parámetro faltante',
                'Se requiere el parámetro "correo"'
            )
        
        # Obtener sugerencias
        service = get_agente_service()
        sugerencias = service.obtener_sugerencias_contexto(correo, contexto)
        
        return formatear_respuesta_exitosa(sugerencias)
    
    except Exception as e:
        print(f"Error obteniendo sugerencias: {str(e)}")
        return formatear_respuesta_error(
            500,
            'Error interno',
            'No se pudieron obtener las sugerencias'
        )


def health_check_handler(event, context):
    """Handler para health check del servicio"""
    try:
        from contextos.general_contexto import ContextoFactory
        
        return formatear_respuesta_exitosa({
            'status': 'healthy',
            'service': 'API-AGENTE',
            'contextos_disponibles': ContextoFactory.get_contextos_disponibles(),
            'timestamp': context.get('timestamp', 'N/A')
        })
    
    except Exception as e:
        return formatear_respuesta_error(503, 'Service Unavailable', str(e))
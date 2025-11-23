"""
Servicio de autenticación y validación de tokens
"""
import base64
import json
from typing import Optional, Dict

class AuthService:
    """Servicio para autenticación y validación"""
    
    @staticmethod
    def decode_jwt_payload(token: str) -> Optional[Dict]:
        """
        Decodifica el payload de un JWT sin verificar firma
        (Se asume que API Gateway ya validó el token)
        
        Args:
            token: Token JWT
        
        Returns:
            Diccionario con el payload o None si falla
        """
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            payload = parts[1]
            # Ajustar padding base64
            padding = '=' * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload + padding).decode('utf-8')
            return json.loads(decoded)
        except Exception as e:
            print(f"Error decodificando JWT: {str(e)}")
            return None
    
    @staticmethod
    def get_user_email_from_event(event: Dict) -> Optional[str]:
        """
        Extrae el email del usuario desde el evento Lambda
        
        Args:
            event: Evento Lambda de API Gateway
        
        Returns:
            Email del usuario o None si no se encuentra
        """
        try:
            # 1. Buscar en headers
            headers = {k.lower(): v for k, v in (event.get('headers') or {}).items()}
            auth_header = headers.get('authorization')
            
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                payload = AuthService.decode_jwt_payload(token)
                
                if payload:
                    # Intentar obtener email de diferentes campos
                    return (
                        payload.get('email') or 
                        payload.get('username') or 
                        payload.get('cognito:username')
                    )
            
            # 2. Buscar en requestContext (si viene de Cognito authorizer)
            request_context = event.get('requestContext', {})
            authorizer = request_context.get('authorizer', {})
            claims = authorizer.get('claims', {})
            
            if claims:
                return claims.get('email') or claims.get('username')
            
            return None
        
        except Exception as e:
            print(f"Error extrayendo email: {str(e)}")
            return None
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Valida formato básico de email
        
        Args:
            email: String con el email
        
        Returns:
            True si es válido
        """
        import re
        if not email:
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

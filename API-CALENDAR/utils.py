import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

def get_google_creds():
    """
    Reconstruye las credenciales usando las variables de entorno
    y refresca el token si es necesario.
    """
    creds_data = {
        "token": None,
        "refresh_token": os.environ.get("GOOGLE_REFRESH_TOKEN"),
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
        "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
        "scopes": ["https://www.googleapis.com/auth/calendar"]
    }

    creds = Credentials.from_authorized_user_info(creds_data)

    if not creds.valid:
        creds.refresh(Request())
    
    return creds
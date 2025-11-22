import json
import boto3
import os
import time
from datetime import datetime
from botocore.exceptions import ClientError

# Inicialización fuera del handler para reusar conexión (Cold Start optimization)
cognito = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')

CLIENT_ID = os.environ.get('CLIENT_ID')
USERS_TABLE = os.environ.get('USERS_TABLE')
table = dynamodb.Table(USERS_TABLE)

# Helper para serializar fechas si es necesario
def json_serial(obj):
    if isinstance(obj, (datetime)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

# Helper para construir respuestas con CORS (OBLIGATORIO)
def build_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": True,
            "Content-Type": "application/json"
        },
        "body": json.dumps(body, default=json_serial)
    }

def register(event, context):
    try:
        body = json.loads(event['body'])
        email = body.get('email')
        password = body.get('password')
        role = body.get('role', 'user')
        name = body.get('name', 'Sin Nombre')

        if not email or not password:
            return build_response(400, {"error": "Faltan campos obligatorios"})

        # 1. Crear usuario en Cognito
        try:
            cognito.sign_up(
                ClientId=CLIENT_ID,
                Username=email,
                Password=password,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    # Solo agrega 'name' si lo configuraste en Cognito como atributo estándar
                    # {'Name': 'name', 'Value': name} 
                ]
            )
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'UsernameExistsException':
                 return build_response(400, {"error": "El usuario ya existe"})
            print(f"Error Cognito: {e}")
            return build_response(400, {"error": str(e)})
        
        # 2. Guardar en DynamoDB
        # Nota: NO guardamos el password en DynamoDB por seguridad
        usuario = {
            'email': email,
            'name': name,
            'role': role,
            'createdAt': time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        }
        
        table.put_item(Item=usuario)
        
        return build_response(200, {
            "message": "Usuario creado exitosamente",
            "usuario": usuario
        })
        
    except Exception as e:
        print(f"Error General Register: {e}")
        return build_response(500, {"error": "Error interno del servidor"})

def confirm_account(event, context):
    try:
        body = json.loads(event['body'])
        email = body.get('email')
        code = body.get('code')

        if not email or not code:
            return build_response(400, {"error": "Email y código son requeridos"})

        # Llamada a Cognito para verificar el código
        try:
            cognito.confirm_sign_up(
                ClientId=CLIENT_ID,
                Username=email,
                ConfirmationCode=code
            )
        except ClientError as e:
            # Errores comunes: Código expirado (CodeMismatchException, ExpiredCodeException)
            return build_response(400, {"error": str(e)})

        # Si todo sale bien:
        return build_response(200, {
            "message": "Cuenta confirmada exitosamente. Ya puedes iniciar sesión."
        })

    except Exception as e:
        return build_response(500, {"error": str(e)})

def login(event, context):
    try:
        body = json.loads(event['body'])
        email = body.get('email')
        password = body.get('password')

        if not email or not password:
            return build_response(400, {"error": "Email y password requeridos"})

        # 1. Autenticar con Cognito
        auth_resp = cognito.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': password
            }
        )
        
        # 2. Buscar datos extra en DynamoDB
        db_resp = table.get_item(Key={'email': email})
        
        user_role = 'unknown'
        user_name = ''
        
        if 'Item' in db_resp:
            item = db_resp['Item']
            user_role = item.get('role', 'unknown')
            user_name = item.get('name', '')
        
        # 3. Responder
        tokens = auth_resp['AuthenticationResult']
        
        return build_response(200, {
            'message': 'Login exitoso',
            'email': email,
            'name': user_name,
            'role': user_role,
            'access_token': tokens['AccessToken'],
            'id_token': tokens['IdToken'],
            'refresh_token': tokens.get('RefreshToken')
        })
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code in ['NotAuthorizedException', 'UserNotFoundException']:
            return build_response(401, {"error": "Credenciales incorrectas"})
        
        print(f"Error Login: {e}")
        return build_response(400, {"error": str(e)})
    except Exception as e:
        return build_response(500, {"error": str(e)})
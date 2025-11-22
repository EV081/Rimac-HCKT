import json
import boto3
import os
import time
import re
from datetime import datetime
from botocore.exceptions import ClientError

cognito = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')

CLIENT_ID = os.environ.get('CLIENT_ID')
USER_POOL_ID = os.environ.get('USER_POOL_ID') # Necesario para confirmar
USERS_TABLE = os.environ.get('USERS_TABLE')
table = dynamodb.Table(USERS_TABLE)

def build_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": True,
            "Content-Type": "application/json"
        },
        "body": json.dumps(body)
    }

def register(event, context):
    try:
        body = json.loads(event['body'])
        email = body.get('email')
        password = body.get('password')
        role = body.get('role', 'user')
        name = body.get('name', 'Usuario')

        # 1. Validación básica regex
        email_regex = r"[^@]+@[^@]+\.[^@]+"
        if not email or not re.match(email_regex, email) or not password:
            return build_response(400, {"error": "Email o password inválidos"})

        # 2. Crear usuario en Cognito
        try:
            cognito.sign_up(
                ClientId=CLIENT_ID,
                Username=email,
                Password=password,
                UserAttributes=[{'Name': 'email', 'Value': email}]
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'UsernameExistsException':
                return build_response(400, {"error": "El usuario ya existe"})
            return build_response(400, {"error": str(e)})

        # 3. MAGIA: Auto-Confirmar usuario (Sin código de email)
        try:
            cognito.admin_confirm_sign_up(
                UserPoolId=USER_POOL_ID,
                Username=email
            )
        except ClientError as e:
            return build_response(500, {"error": f"Error al auto-validar: {str(e)}"})

        # 4. Guardar en DynamoDB
        usuario = {
            'email': email,
            'name': name,
            'role': role,
            'createdAt': time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        }
        table.put_item(Item=usuario)

        # 5. Obtener Token inmediatamente (Login automático)
        auth_resp = cognito.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': password
            }
        )
        tokens = auth_resp['AuthenticationResult']

        return build_response(200, {
            "message": "Registro completado. Sesión iniciada.",
            "usuario": usuario,
            "access_token": tokens['AccessToken'],
            "id_token": tokens['IdToken']
        })

    except Exception as e:
        return build_response(500, {"error": str(e)})

def login(event, context):
    # (Usa la misma función de login que te pasé antes, no cambia nada)
    try:
        body = json.loads(event['body'])
        email = body.get('email')
        password = body.get('password')

        auth_resp = cognito.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={'USERNAME': email, 'PASSWORD': password}
        )
        
        # Recuperar rol de DynamoDB
        db_resp = table.get_item(Key={'email': email})
        user_data = db_resp.get('Item', {})
        
        tokens = auth_resp['AuthenticationResult']
        
        return build_response(200, {
            "message": "Login exitoso",
            "email": email,
            "role": user_data.get('role', 'unknown'),
            "access_token": tokens['AccessToken'],
            "id_token": tokens['IdToken']
        })
    except ClientError as e:
        return build_response(401, {"error": "Credenciales inválidas"})
    except Exception as e:
        return build_response(500, {"error": str(e)})
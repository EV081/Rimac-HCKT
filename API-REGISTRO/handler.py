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
TABLE_USUARIOS = os.environ.get('TABLE_USUARIOS')
table = dynamodb.Table(TABLE_USUARIOS)

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
        correo = body.get('correo')
        contrasena = body.get('contrasena')
        nombre = body.get('nombre')
        sexo = body.get('sexo')
        rol = body.get('rol', 'USER')

        # 1. Validación de campos requeridos
        if not correo or not contrasena or not nombre or not sexo:
            return build_response(400, {"error": "Campos requeridos: correo, contrasena, nombre, sexo"})

        # Validación de email
        email_regex = r"[^@]+@[^@]+\.[^@]+"
        if not re.match(email_regex, correo):
            return build_response(400, {"error": "Formato de correo inválido"})

        # Validación de sexo
        if sexo not in ['M', 'F']:
            return build_response(400, {"error": "El campo 'sexo' debe ser 'M' o 'F'"})

        # Validación de rol
        if rol not in ['USER', 'ADMIN']:
            return build_response(400, {"error": "El campo 'rol' debe ser 'USER' o 'ADMIN'"})

        # 2. Crear usuario en Cognito
        try:
            cognito.sign_up(
                ClientId=CLIENT_ID,
                Username=correo,
                Password=contrasena,
                UserAttributes=[{'Name': 'email', 'Value': correo}]
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'UsernameExistsException':
                return build_response(400, {"error": "El usuario ya existe"})
            return build_response(400, {"error": str(e)})

        # 3. Auto-Confirmar usuario (Sin código de email)
        try:
            cognito.admin_confirm_sign_up(
                UserPoolId=USER_POOL_ID,
                Username=correo
            )
        except ClientError as e:
            return build_response(500, {"error": f"Error al auto-validar: {str(e)}"})

        # 4. Guardar en DynamoDB
        usuario = {
            'correo': correo,
            'contrasena': contrasena,
            'nombre': nombre,
            'sexo': sexo,
            'rol': rol
        }
        table.put_item(Item=usuario)

        # 5. Obtener Token inmediatamente (Login automático)
        auth_resp = cognito.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': correo,
                'PASSWORD': contrasena
            }
        )
        tokens = auth_resp['AuthenticationResult']

        return build_response(200, {
            "message": "Registro completado. Sesión iniciada.",
            "usuario": {
                'correo': correo,
                'nombre': nombre,
                'sexo': sexo,
                'rol': rol
            },
            "access_token": tokens['AccessToken'],
            "id_token": tokens['IdToken']
        })

    except Exception as e:
        return build_response(500, {"error": str(e)})

def login(event, context):
    try:
        body = json.loads(event['body'])
        correo = body.get('correo')
        contrasena = body.get('contrasena')

        if not correo or not contrasena:
            return build_response(400, {"error": "Campos requeridos: correo, contrasena"})

        auth_resp = cognito.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={'USERNAME': correo, 'PASSWORD': contrasena}
        )
        
        # Recuperar datos de usuario de DynamoDB
        db_resp = table.get_item(Key={'correo': correo})
        user_data = db_resp.get('Item', {})
        
        tokens = auth_resp['AuthenticationResult']
        
        return build_response(200, {
            "message": "Login exitoso",
            "usuario": {
                "correo": correo,
                "nombre": user_data.get('nombre', ''),
                "sexo": user_data.get('sexo', ''),
                "rol": user_data.get('rol', 'USER')
            },
            "access_token": tokens['AccessToken'],
            "id_token": tokens['IdToken']
        })
    except ClientError as e:
        return build_response(401, {"error": "Credenciales inválidas"})
    except Exception as e:
        return build_response(500, {"error": str(e)})
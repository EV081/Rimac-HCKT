import json
import boto3
import os
from datetime import datetime
from botocore.exceptions import ClientError
import time

cognito = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')

CLIENT_ID = os.environ['CLIENT_ID']
USERS_TABLE = os.environ['USERS_TABLE']
table = dynamodb.Table(USERS_TABLE)

def json_serial(obj):
    if isinstance(obj, (datetime)):
        return obj.isoformat()
    raise TypeError (f"Type {type(obj)} not serializable")

def register(event, context):
    try:
        body = json.loads(event['body'])
        email = body.get('email')
        password = body.get('password')
        role = body.get('role', 'user')
        name=body.get('name','user')

        try:
            cognito.sign_up(
            ClientId=CLIENT_ID,
            Username=email,
            Password=password,
            UserAttributes=[{'Name': 'email', 'Value': email}]
            )
        except ClientError as e:
            print("Error al registrar en Cognito:", e)
            return{
                "statusCode": 400, 
                "body": json.dumps({"error en cognito": str(e)})
            }
        
        # 2. Si Cognito tuvo éxito, guardamos el rol en DynamoDB
        # Usamos el email como PK
        usuario={
            'email': email,
            'name': name,
            'role': role,
            'createdAt': time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        }
        table.put_item(Item=usuario)
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Usuario creado exitosamente",
                "usuario": usuario
            }, default=json_serial)
        }
        
    except ClientError as e:
        print("Error al registrar usuario:", e)
        return {
            "statusCode": 400, 
            "body": json.dumps({"error en registro": str(e)})
        }

def login(event, context):
    try:
        body = json.loads(event['body'])
        email = body.get('email')
        password = body.get('password')

        auth_resp = cognito.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': password
            }
        )
        
        # 2. Buscar el rol del usuario en DynamoDB
        db_resp = table.get_item(Key={'email': email})
        
        user_role = 'unknown'
        if 'Item' in db_resp:
            user_role = db_resp['Item'].get('role', 'unknown')
        
        # 3. Preparar respuesta combinada
        tokens = auth_resp['AuthenticationResult']
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Login exitoso',
                'email': email,
                'role': user_role,  # <--- AQUÍ VA EL ROL RECUPERADO
                'access_token': tokens['AccessToken'],
                'id_token': tokens['IdToken'],
                'refresh_token': tokens.get('RefreshToken')
            }, default=json_serial) # default ayuda si hay objetos datetime sueltos
        }
        
    except ClientError as e:
        return {
            "statusCode": 403, 
            "body": json.dumps({"error en login": str(e)})
        }
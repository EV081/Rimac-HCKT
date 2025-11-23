#!/usr/bin/env python3
import boto3
import os
import uuid
from dotenv import load_dotenv
from botocore.exceptions import ClientError

load_dotenv()

s3 = boto3.client('s3', region_name=os.getenv('AWS_REGION', 'us-east-1'))
bucket_name = os.getenv('S3_BUCKET_RECETAS', 'recetas-medicas-bucket')
region = os.getenv('AWS_REGION', 'us-east-1')

print(f"🪣 Configurando bucket S3: {bucket_name}")

# Intentar crear el bucket
try:
    if region == 'us-east-1':
        s3.create_bucket(Bucket=bucket_name)
    else:
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': region}
        )
    print(f'✅ Bucket {bucket_name} creado exitosamente')
except ClientError as e:
    error_code = e.response['Error']['Code']
    if error_code == 'BucketAlreadyOwnedByYou':
        print(f'✅ Bucket {bucket_name} ya existe y es tuyo')
    elif error_code == 'BucketAlreadyExists':
        # Bucket existe pero no es nuestro, agregar UUID
        new_bucket_name = f'{bucket_name}-{uuid.uuid4().hex[:8]}'
        print(f'⚠️  Bucket {bucket_name} ya existe. Intentando con {new_bucket_name}')
        try:
            if region == 'us-east-1':
                s3.create_bucket(Bucket=new_bucket_name)
            else:
                s3.create_bucket(
                    Bucket=new_bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': region}
                )
            # Actualizar .env con el nuevo nombre
            with open('.env', 'r') as f:
                lines = f.readlines()
            with open('.env', 'w') as f:
                for line in lines:
                    if line.startswith('S3_BUCKET_RECETAS='):
                        f.write(f'S3_BUCKET_RECETAS={new_bucket_name}\n')
                    else:
                        f.write(line)
            bucket_name = new_bucket_name
            print(f'✅ Bucket {new_bucket_name} creado y .env actualizado')
        except Exception as inner_e:
            print(f'❌ Error al crear bucket alternativo: {inner_e}')
            exit(1)
    else:
        print(f'❌ Error al crear bucket: {e}')
        exit(1)

# Deshabilitar Block Public Access y configurar política
try:
    # Deshabilitar Block Public Access
    s3.delete_public_access_block(Bucket=bucket_name)
    
    # Configurar política de bucket para acceso público de lectura
    bucket_policy = {
        'Version': '2012-10-17',
        'Statement': [{
            'Sid': 'PublicReadGetObject',
            'Effect': 'Allow',
            'Principal': '*',
            'Action': 's3:GetObject',
            'Resource': f'arn:aws:s3:::{bucket_name}/*'
        }]
    }
    import json
    s3.put_bucket_policy(
        Bucket=bucket_name,
        Policy=json.dumps(bucket_policy)
    )
    print('✅ Bucket configurado para acceso público de lectura')
except Exception as e:
    print(f'⚠️  Advertencia al configurar acceso público: {e}')

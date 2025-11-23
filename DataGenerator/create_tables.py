import json
import os
import boto3
from dotenv import load_dotenv
from botocore.exceptions import ClientError

# Cargar variables de entorno
load_dotenv()

AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
dynamodb = boto3.client('dynamodb', region_name=AWS_REGION)

# Mapeo de archivos de esquema a variables de entorno de nombres de tabla
SCHEMA_MAPPING = {
    "recetas.json": os.getenv('TABLE_RECETAS', 'Recetas'),
    "servicios.json": os.getenv('TABLE_SERVICIOS', 'Servicios'),
    "usuarios.json": os.getenv('TABLE_USUARIOS', 'Usuarios'),
    "memoria_contextual.json": os.getenv('TABLE_MEMORIA_CONTEXTUAL', 'MemoriaContextual'),
    "historial_medico.json": os.getenv('TABLE_HISTORIAL_MEDICO', 'HistorialMedico')
}

SCHEMAS_DIR = "schemas-validation"

def get_dynamodb_type(json_type):
    if json_type == "string":
        return "S"
    elif json_type == "integer" or json_type == "number":
        return "N"
    elif json_type == "boolean":
        return "BOOL" # Not valid for KeySchema usually
    return "S" # Default

def create_table_from_schema(filename, table_name):
    filepath = os.path.join(SCHEMAS_DIR, filename)
    if not os.path.exists(filepath):
        print(f"❌ Esquema no encontrado: {filepath}")
        return False

    with open(filepath, 'r') as f:
        schema = json.load(f)

    if "x-dynamodb" not in schema or "partition_key" not in schema["x-dynamodb"]:
        print(f"❌ Definición x-dynamodb faltante en {filename}")
        return False

    pk_name = schema["x-dynamodb"]["partition_key"]
    # Buscar el tipo del PK en properties
    pk_type = "S"
    if "properties" in schema and pk_name in schema["properties"]:
        pk_type = get_dynamodb_type(schema["properties"][pk_name].get("type", "string"))

    key_schema = [
        {'AttributeName': pk_name, 'KeyType': 'HASH'}
    ]
    attribute_definitions = [
        {'AttributeName': pk_name, 'AttributeType': pk_type}
    ]

    # Verificar si existe sort key (no definido en los esquemas actuales pero por si acaso)
    if "sort_key" in schema["x-dynamodb"]:
        sk_name = schema["x-dynamodb"]["sort_key"]
        sk_type = "S"
        if "properties" in schema and sk_name in schema["properties"]:
            sk_type = get_dynamodb_type(schema["properties"][sk_name].get("type", "string"))
        
        key_schema.append({'AttributeName': sk_name, 'KeyType': 'RANGE'})
        attribute_definitions.append({'AttributeName': sk_name, 'AttributeType': sk_type})

    try:
        print(f"📊 Verificando tabla: {table_name}")
        dynamodb.describe_table(TableName=table_name)
        print(f"   ✅ La tabla '{table_name}' ya existe")
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"   🔨 Creando tabla '{table_name}'...")
            try:
                dynamodb.create_table(
                    TableName=table_name,
                    KeySchema=key_schema,
                    AttributeDefinitions=attribute_definitions,
                    BillingMode='PAY_PER_REQUEST'
                )
                waiter = dynamodb.get_waiter('table_exists')
                waiter.wait(TableName=table_name)
                print(f"   ✅ Tabla '{table_name}' creada exitosamente")
                return True
            except Exception as create_error:
                print(f"   ❌ Error al crear tabla: {str(create_error)}")
                return False
        else:
            print(f"   ❌ Error al verificar tabla: {str(e)}")
            return False

def main():
    print("🏗️  Creando tablas base desde esquemas...")
    success = True
    for schema_file, table_name in SCHEMA_MAPPING.items():
        if not create_table_from_schema(schema_file, table_name):
            success = False
    
    if success:
        print("✅ Todas las tablas verificadas/creadas")
        exit(0)
    else:
        print("❌ Hubo errores al crear tablas")
        exit(1)

if __name__ == "__main__":
    main()

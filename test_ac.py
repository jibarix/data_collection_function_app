import os
from dotenv import load_dotenv
from azure.data.tables import TableServiceClient

# Load environment variables
load_dotenv(dotenv_path=".env")

# Get connection string
connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

if not connection_string:
    print("ERROR: AZURE_STORAGE_CONNECTION_STRING not found in environment variables or .env file")
    exit(1)

print(f"Connection string found: {'Yes' if connection_string else 'No'}")
print("Raw connection string preview:")
print(connection_string[:10] + "..." if connection_string else "None")  # Print only first 10 chars for security

# Test table connection
try:
    service = TableServiceClient.from_connection_string(conn_str=connection_string)
    print("Successfully connected to Azure Tables API")
    
    # List tables to confirm access
    tables = list(service.list_tables())
    print(f"Found {len(tables)} tables")
    
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {str(e)}")
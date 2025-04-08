import os
from dotenv import load_dotenv
from azure.data.tables import TableServiceClient

# Load environment variables
load_dotenv(dotenv_path=".env")

# Get connection string
connection_string = "insert conection string"

print(f"Connection string found: {'Yes' if connection_string else 'No'}")
print("Raw connection string preview:")
print(connection_string[:100])  # Print first 100 characters only

# Test table connection
try:
    service = TableServiceClient.from_connection_string(conn_str=connection_string)
    print("Successfully connected to Azure Tables API")
    
    # List tables to confirm access
    tables = list(service.list_tables())
    print(f"Found {len(tables)} tables")
    
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {str(e)}")
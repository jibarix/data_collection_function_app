# scraper/azure_blob.py

import os
import io
import pandas as pd
import logging
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError

# Connection strings from environment variables
RAW_DATA_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
FINAL_DATA_CONNECTION_STRING = RAW_DATA_CONNECTION_STRING

# Container names based on the guide
RAW_DATA_CONTAINER = "raw-data"       # Stores raw files downloaded from government sources
FINAL_DATA_CONTAINER = "processed-data"  # Stores processed data (e.g., CSV format)

def get_connection_string():
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient
    
    key_vault_name = os.getenv("KEY_VAULT_NAME", "pr-opendata-kv")
    key_vault_uri = f"https://{key_vault_name}.vault.azure.net/"
    secret_name = "Storage-Connection-String"
    
    try:
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=key_vault_uri, credential=credential)
        return client.get_secret(secret_name).value
    except Exception as e:
        logging.error(f"Error retrieving connection string from Key Vault: {str(e)}")
        # Fall back to environment variable
        return os.getenv("AZURE_STORAGE_CONNECTION_STRING")

def upload_raw_data(content: bytes, blob_name: str):
    """Upload the raw Excel file to the designated raw data container."""
    blob_service_client = BlobServiceClient.from_connection_string(RAW_DATA_CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(RAW_DATA_CONTAINER)
    
    # Create the container if it does not exist
    try:
        container_client.create_container()
    except ResourceExistsError:
        # Container already exists - this is expected
        pass
    except Exception as e:
        # Log other errors but continue
        logging.error(f"Error creating container {RAW_DATA_CONTAINER}: {str(e)}")
    
    blob_client = container_client.get_blob_client(blob_name)
    blob_client.upload_blob(content, overwrite=True)
    logging.info(f"Uploaded raw data to blob: {blob_name}")

def upload_final_data(data_df: pd.DataFrame, table_name: str):
    """Upload the processed data (as CSV) to the final data container (Data Lake)."""
    blob_service_client = BlobServiceClient.from_connection_string(FINAL_DATA_CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(FINAL_DATA_CONTAINER)
    
    # Create the container if needed
    try:
        container_client.create_container()
    except ResourceExistsError:
        # Container already exists - this is expected
        pass
    except Exception as e:
        # Log other errors but continue
        logging.error(f"Error creating container {FINAL_DATA_CONTAINER}: {str(e)}")
    
    csv_buffer = io.StringIO()
    data_df.to_csv(csv_buffer, index=False)
    blob_name = f"{table_name}.csv"
    blob_client = container_client.get_blob_client(blob_name)
    blob_client.upload_blob(csv_buffer.getvalue(), overwrite=True)
    logging.info(f"Uploaded final data to blob: {blob_name}")
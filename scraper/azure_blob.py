# scraper/azure_blob.py

import os
import io
import pandas as pd
import logging
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError

# Container names based on the guide
RAW_DATA_CONTAINER = "raw-data"       # Stores raw files downloaded from government sources
FINAL_DATA_CONTAINER = "processed-data"  # Stores processed data (e.g., CSV format)

def get_connection_string():
    """
    Get the storage connection string, trying Key Vault first and
    falling back to environment variables if necessary.
    """
    try:
        # Try to get the connection string from Key Vault
        if os.getenv("KEY_VAULT_NAME"):
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient
            
            key_vault_name = os.getenv("KEY_VAULT_NAME", "pr-opendata-kv")
            key_vault_uri = f"https://{key_vault_name}.vault.azure.net/"
            secret_name = "Storage-Connection-String"
            
            try:
                credential = DefaultAzureCredential()
                client = SecretClient(vault_url=key_vault_uri, credential=credential)
                connection_string = client.get_secret(secret_name).value
                logging.info("Successfully retrieved connection string from Key Vault")
                return connection_string
            except Exception as e:
                logging.warning(f"Error retrieving connection string from Key Vault: {str(e)}")
                # Will fall back to environment variable
    
        # Fall back to environment variable
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not connection_string:
            raise ValueError("Storage connection string not found in Key Vault or environment variables")
        
        logging.info("Using connection string from environment variables")
        return connection_string
    
    except Exception as e:
        logging.error(f"Failed to get connection string: {str(e)}")
        raise

def upload_raw_data(content: bytes, blob_name: str):
    """Upload the raw Excel file to the designated raw data container."""
    try:
        connection_string = get_connection_string()
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
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
    except Exception as e:
        logging.error(f"Error uploading raw data to blob storage: {str(e)}")
        raise

def upload_final_data(data_df: pd.DataFrame, table_name: str):
    """Upload the processed data (as CSV) to the final data container (Data Lake)."""
    try:
        connection_string = get_connection_string()
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
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
    except Exception as e:
        logging.error(f"Error uploading final data to blob storage: {str(e)}")
        raise
# scraper/azure_blob.py

import os
import io
import pandas as pd
from azure.storage.blob import BlobServiceClient

# Connection strings—replace with secure values.
RAW_DATA_CONNECTION_STRING = os.getenv(
    "AZURE_RAW_DATA_CONNECTION_STRING",
    "DefaultEndpointsProtocol=https;AccountName=propendata;AccountKey=<<RAW_KEY>>;EndpointSuffix=core.windows.net"
)
FINAL_DATA_CONNECTION_STRING = os.getenv(
    "AZURE_FINAL_DATA_CONNECTION_STRING",
    "DefaultEndpointsProtocol=https;AccountName=propendata_dl;AccountKey=<<DL_KEY>>;EndpointSuffix=core.windows.net"
)

# Container names based on the guide.
RAW_DATA_CONTAINER = "raw-data"       # Stores raw files downloaded from government sources.
FINAL_DATA_CONTAINER = "processed-data"  # Stores processed data (e.g., CSV format).

def upload_raw_data(content: bytes, blob_name: str):
    """Upload the raw Excel file to the designated raw data container."""
    blob_service_client = BlobServiceClient.from_connection_string(RAW_DATA_CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(RAW_DATA_CONTAINER)
    
    # Create the container if it does not exist.
    try:
        container_client.create_container()
    except Exception:
        pass
    
    blob_client = container_client.get_blob_client(blob_name)
    blob_client.upload_blob(content, overwrite=True)
    print(f"Uploaded raw data to blob: {blob_name}")

def upload_final_data(data_df: pd.DataFrame, table_name: str):
    """Upload the processed data (as CSV) to the final data container (Data Lake)."""
    blob_service_client = BlobServiceClient.from_connection_string(FINAL_DATA_CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(FINAL_DATA_CONTAINER)
    
    # Create the container if needed.
    try:
        container_client.create_container()
    except Exception:
        pass
    
    csv_buffer = io.StringIO()
    data_df.to_csv(csv_buffer, index=False)
    blob_name = f"{table_name}.csv"
    blob_client = container_client.get_blob_client(blob_name)
    blob_client.upload_blob(csv_buffer.getvalue(), overwrite=True)
    print(f"Uploaded final data to blob: {blob_name}")
# scraper/data_tracker.py
import os
import logging
from datetime import datetime
from azure.data.tables import TableServiceClient, TableClient
from azure.core.exceptions import ResourceExistsError

connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
table_name = "ScraperMetadata"

def _get_table_client():
    service = TableServiceClient.from_connection_string(conn_str=connection_string)
    try:
        service.create_table(table_name)
    except ResourceExistsError:
        # Table already exists - this is expected
        pass
    except Exception as e:
        logging.error(f"Error creating table {table_name}: {str(e)}")
    return service.get_table_client(table_name)

def update_last_run(dataset_name: str, timestamp: str) -> None:
    table_client = _get_table_client()
    entity = {
        "PartitionKey": "scraper",
        "RowKey": dataset_name,
        "timestamp": timestamp
    }
    table_client.upsert_entity(entity, mode="replace")
    logging.info(f"Updated last run for {dataset_name} to {timestamp}")

def get_last_run(dataset_name: str):
    table_client = _get_table_client()
    try:
        entity = table_client.get_entity("scraper", dataset_name)
        return datetime.fromisoformat(entity["timestamp"])
    except Exception as e:
        logging.info(f"No previous run found for {dataset_name}: {str(e)}")
        return None
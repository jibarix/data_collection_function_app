# scraper/data_tracker.py

import json
import os
from datetime import datetime

METADATA_FILE = os.path.join(os.path.dirname(__file__), 'metadata_store.json')

def _load_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def _save_metadata(data):
    with open(METADATA_FILE, 'w') as f:
        json.dump(data, f)

def update_last_run(dataset_name: str, timestamp: str) -> None:
    data = _load_metadata()
    data[dataset_name] = timestamp
    _save_metadata(data)

def get_last_run(dataset_name: str):
    data = _load_metadata()
    timestamp = data.get(dataset_name)
    if timestamp:
        try:
            return datetime.fromisoformat(timestamp)
        except Exception:
            return None
    return None

def smart_update(dataset_name: str, data_df, date_field: str, value_fields: list):
    # Dummy function for smart updating—replace with real logic if needed.
    print(f"Smart updating {dataset_name} with {len(data_df)} records based on {date_field} and {value_fields}.")
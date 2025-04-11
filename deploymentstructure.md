data_collection_function_app/
├── run_locally.py (test only, not to be deployed; ignore)
├── function_app/
│   ├── HttpTriggerScraper/
│   │   ├── __init__.py
│   │   └── function.json
│   ├── host.json
│   └── requirements.txt
└── scraper/
    ├── __init__.py
    ├── base_scraper.py
    ├── data_tracker.py
    ├── config.py
    └── azure_blob.py


List of Azure Resources in Current Structure
	•	Resource Group:
	•	Name: pr-opendata-rg
	•	Azure Storage Account:
	•	Name: propendata
	•	Containers:
	•	$logs – Contains system-generated logs.
	•	archive – Stores backups or historical versions of files (if needed).
	•	config – Holds configuration files for your application (if used).
	•	raw-data – Stores the raw Excel files downloaded from the government sources.
	•	processed-data – Stores the final processed data files.
	•	Azure Functions (Function App):
	•	Name: pr-opendata-collector
	•	Hosts the Python-based scraper/collector that handles downloading, processing, and uploading data.
	•	Azure Key Vault:
	•	Name: pr-opendata-kv
	•	Contains secrets such as Storage-Connection-String, which secures the connection details for your Storage Account.
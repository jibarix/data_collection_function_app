data_collection_function_app/     # Root folder
├── .gitignore                    # Git ignore configuration
├── host.json                     # Azure Functions host configuration
├── HttpTriggerScraper/           # Main Azure Function
│   ├── __init__.py               # Function entry point 
│   └── function.json             # Function binding configuration
├── requirements.txt              # Python dependencies
├── run_locally.py                # Script for local testing
├── scraper/                      # Core scraper package
│   ├── __init__.py               # Package initialization
│   ├── azure_blob.py             # Azure Blob Storage utilities
│   ├── base_scraper.py           # Base scraper classes
│   ├── config.py                 # Scraper configurations
│   └── data_tracker.py           # Metadata tracking with Azure Tables
└── test_ac.py                    # Azure connection testing script


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
	•	function-packages – Stores the zip package for deployment.
	•	Azure Functions (Function App):
	•	Name: pr-opendata-collector
	•	Hosts the Python-based scraper/collector that handles downloading, processing, and uploading data.
		az functionapp create \
		--resource-group pr-opendata-rg \
		--name pr-opendata-collector \
		--storage-account propendata \
		--consumption-plan-location eastus \
		--runtime python \
		--runtime-version 3.11 \
		--functions-version 4 \
		--os-type Linux
	•	Azure Key Vault:
	•	Name: pr-opendata-kv
	•	Contains secrets such as Storage-Connection-String, which secures the connection details for your Storage Account.
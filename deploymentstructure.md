your-repo/
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
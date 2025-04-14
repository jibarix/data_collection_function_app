"""
Test a single scraper to help debug issues.

Usage:
    python test_scraper.py auto_sales

This will test the 'auto_sales' scraper only, but won't upload data to Azure.
"""

import os
import sys
import logging
import argparse
from io import BytesIO
import pandas as pd
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def test_scraper(scraper_name):
    # Load environment variables from .env file
    load_dotenv()

    # Verify connection string is available
    if not os.getenv("AZURE_STORAGE_CONNECTION_STRING"):
        logging.error("AZURE_STORAGE_CONNECTION_STRING not found in environment or .env file")
        sys.exit(1)

    # Import scraper modules
    try:
        from scraper.config import SCRAPER_CONFIGS
        from scraper.base_scraper import MonthlyDataScraper
    except ImportError as e:
        logging.error(f"Failed to import scraper modules: {e}")
        sys.exit(1)

    # Check if requested scraper exists
    if scraper_name not in SCRAPER_CONFIGS:
        logging.error(f"Scraper '{scraper_name}' not found. Available scrapers: {', '.join(SCRAPER_CONFIGS.keys())}")
        sys.exit(1)
    
    config = SCRAPER_CONFIGS[scraper_name]
    logging.info(f"Testing scraper: {scraper_name}")
    logging.info(f"Config: {config}")
    
    # Step 1: Create scraper instance
    try:
        scraper = MonthlyDataScraper(config)
        logging.info("✅ Scraper instance created")
    except Exception as e:
        logging.error(f"Failed to create scraper instance: {e}")
        sys.exit(1)
    
    # Step 2: Download Excel file
    try:
        logging.info(f"Downloading: {config['url']}{config['file_name']}")
        content = scraper.download_excel(config['url'], config['file_name'])
        if content:
            logging.info(f"✅ Successfully downloaded {len(content)} bytes")
            
            # Save a local copy for inspection
            os.makedirs("debug", exist_ok=True)
            with open(f"debug/{config['file_name']}", "wb") as f:
                f.write(content)
            logging.info(f"✅ Saved file to debug/{config['file_name']}")
        else:
            logging.error("Download failed")
            sys.exit(1)
    except Exception as e:
        logging.error(f"Download error: {e}")
        sys.exit(1)
    
    # Step 3: Extract data
    try:
        logging.info(f"Extracting data from sheet '{config['sheet_name']}', range '{config['data_location']}'")
        df = scraper.extract_data(content, config['sheet_name'], config['data_location'])
        if df is not None:
            logging.info(f"✅ Successfully extracted data with shape {df.shape}")
            logging.info("Preview of extracted data:")
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', 120)
            logging.info(df.head())
        else:
            logging.error("Data extraction failed")
            sys.exit(1)
    except Exception as e:
        logging.error(f"Data extraction error: {e}")
        sys.exit(1)
    
    # Step 4: Process data
    try:
        logging.info("Processing data...")
        processed = scraper.process_data(df)
        if processed is not None:
            logging.info(f"✅ Successfully processed data with {len(processed)} rows")
            logging.info("Preview of processed data:")
            logging.info(processed.head())
            
            # Save processed data for inspection
            processed.to_csv(f"debug/processed_{scraper_name}.csv", index=False)
            logging.info(f"✅ Saved processed data to debug/processed_{scraper_name}.csv")
        else:
            logging.error("Data processing failed")
            sys.exit(1)
    except Exception as e:
        logging.error(f"Data processing error: {e}")
        sys.exit(1)
    
    # Step 5: Test Azure Storage connectivity without uploading
    try:
        from azure.storage.blob import BlobServiceClient
        from scraper.azure_blob import get_connection_string
        
        connection_string = get_connection_string()
        BlobServiceClient.from_connection_string(connection_string)
        logging.info("✅ Successfully connected to Azure Blob Storage")
    except Exception as e:
        logging.error(f"Azure Blob Storage connection error: {e}")
        sys.exit(1)
    
    # Step 6: Test Data Tracker connectivity without updating
    try:
        from azure.data.tables import TableServiceClient
        from scraper.data_tracker import _get_table_client
        
        table_client = _get_table_client()
        logging.info("✅ Successfully connected to Azure Table Storage")
    except Exception as e:
        logging.error(f"Azure Table Storage connection error: {e}")
        sys.exit(1)
    
    logging.info("✅ All tests passed successfully!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test a single scraper without uploading data to Azure")
    parser.add_argument("scraper_name", help="Name of the scraper to test (e.g., auto_sales)")
    args = parser.parse_args()
    
    test_scraper(args.scraper_name)
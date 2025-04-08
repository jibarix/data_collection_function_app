# run_locally.py

"""
Run locally with:

    export AZURE_STORAGE_CONNECTION_STRING="your-actual-connection-string"
    python run_locally.py

This script uses `dotenv` to load other environment variables from `.env`, 
but assumes the AZURE_STORAGE_CONNECTION_STRING is already exported to the shell.
"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from scraper.config import SCRAPER_CONFIGS
from scraper.base_scraper import MonthlyDataScraper
from scraper.azure_blob import upload_raw_data

# Set up proper logging configuration
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def run_scrapers():
    for name, config in SCRAPER_CONFIGS.items():
        logging.info(f"Processing scraper: {name}")
        
        if config['type'] == 'monthly':
            scraper = MonthlyDataScraper(config)
        else:
            logging.warning(f"Unsupported scraper type: {config['type']}")
            continue
        
        if scraper.should_update(name):
            content = scraper.download_excel(config['url'], config['file_name'])
            if not content:
                logging.error(f"Failed to download file for {name}")
                continue
            
            # Optionally upload raw data for local testing
            try:
                upload_raw_data(content, config['file_name'])
                logging.info(f"Uploaded raw data for {name}")
            except Exception as e:
                logging.error(f"Failed to upload raw data: {str(e)}")
            
            raw_path = os.path.join("local_raw", config['file_name'])
            os.makedirs("local_raw", exist_ok=True)
            with open(raw_path, "wb") as f:
                f.write(content)
            logging.info(f"Saved raw file locally at {raw_path}")
            
            df = scraper.extract_data(content, config['sheet_name'], config['data_location'])
            if df is None:
                logging.error(f"Extraction failed for {name}")
                continue
            
            processed = scraper.process_data(df)
            processed_path = os.path.join("local_processed", f"processed_{config['table_name']}.csv")
            os.makedirs("local_processed", exist_ok=True)
            processed.to_csv(processed_path, index=False)
            logging.info(f"Processed data saved locally at {processed_path}")
            
            scraper.update_last_run(name)
            logging.info(f"Scraper {name} updated successfully.")
        else:
            logging.info(f"No update needed for {name}")

if __name__ == '__main__':
    run_scrapers()
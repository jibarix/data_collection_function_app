# function_app/HttpTriggerScraper/__init__.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import logging
import azure.functions as func
from scraper.config import SCRAPER_CONFIGS
from scraper.base_scraper import MonthlyDataScraper
from scraper.azure_blob import upload_raw_data, upload_final_data

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("pr-opendata-collector function triggered.")
    
    try:
        # Process each scraper configured in SCRAPER_CONFIGS.
        for name, config in SCRAPER_CONFIGS.items():
            logging.info(f"Processing scraper: {name}")
            scraper = None
            if config['type'] == 'monthly':
                scraper = MonthlyDataScraper(config)
            else:
                logging.warning(f"Unsupported scraper type: {config['type']}")
                continue
            
            if scraper.should_update(name):
                # Step 1: Download the Excel file.
                content = scraper.download_excel(config['url'], config['file_name'])
                if content is None:
                    logging.error(f"Failed to download Excel file for {name}.")
                    continue
                
                # Step 2: Upload the raw file to the "raw-data" container.
                upload_raw_data(content, config['file_name'])
                logging.info(f"Uploaded raw data for {name} to the 'raw-data' container.")
                
                # Step 3: Extract and process the data.
                df = scraper.extract_data(content, config['sheet_name'], config['data_location'])
                if df is None:
                    logging.error(f"Data extraction failed for {name}.")
                    continue
                
                processed = scraper.process_data(df)
                
                # Step 4: Insert (or store) the processed data in the target system.
                scraper.insert_data(processed)
                
                # Step 5: Upload the processed data (as CSV) to the "processed-data" container.
                upload_final_data(processed, config['table_name'])
                logging.info(f"Uploaded processed data for {name} to the 'processed-data' container.")
                
                # Step 6: Update the metadata with the last run timestamp.
                scraper.update_last_run(name)
                logging.info(f"Scraper {name} processed and updated successfully.")
            else:
                logging.info(f"No update needed for {name}.")
        
        return func.HttpResponse("Scraper run complete.", status_code=200)
    except Exception as e:
        logging.exception("Error during scraper execution.")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
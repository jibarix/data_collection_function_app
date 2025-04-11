import os
import sys
import logging

# For local development, adjust sys.path to include the root of the project so that the scraper package is found.
if "WEBSITE_INSTANCE_ID" not in os.environ:
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    logging.info(f"Added '{parent_dir}' to sys.path for local development.")

import azure.functions as func
from scraper.config import SCRAPER_CONFIGS
from scraper.base_scraper import MonthlyDataScraper
from scraper.azure_blob import upload_raw_data


def main(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Function HTTP-triggered entry point for the data collection scraper."""
    logging.info("⚡ Function starting up...")

    try:
        logging.info("✅ main() triggered")
        # Process each scraper configured in SCRAPER_CONFIGS.
        for name, config in SCRAPER_CONFIGS.items():
            logging.info(f"Processing scraper: {name}")
            scraper = None
            if config.get('type') == 'monthly':
                scraper = MonthlyDataScraper(config)
            else:
                logging.warning(f"Unsupported scraper type: {config.get('type')}")
                continue
            
            if scraper and scraper.should_update(name):
                # Step 1: Download the Excel file.
                content = scraper.download_excel(config.get('url'), config.get('file_name'))
                if content is None:
                    logging.error(f"Failed to download Excel file for {name}.")
                    continue
                
                # Step 2: Upload the raw file to the 'raw-data' container.
                upload_raw_data(content, config.get('file_name'))
                logging.info(f"Uploaded raw data for {name} to the 'raw-data' container.")
                
                # Step 3: Extract and process the data.
                df = scraper.extract_data(content, config.get('sheet_name'), config.get('data_location'))
                if df is None:
                    logging.error(f"Data extraction failed for {name}.")
                    continue
                
                processed = scraper.process_data(df)
                
                # Step 4: Insert (or store) the processed data in the target system.
                # This internally calls upload_final_data.
                scraper.insert_data(processed)
                logging.info(f"Uploaded processed data for {name} to the 'processed-data' container.")
                
                # Step 5: Update the metadata with the last run timestamp.
                scraper.update_last_run(name)
                logging.info(f"Scraper {name} processed and updated successfully.")
            else:
                logging.info(f"No update needed for scraper: {name}.")
        
        return func.HttpResponse("Scraper run complete.", status_code=200, mimetype="text/plain")
    except Exception as e:
        logging.exception("Error during scraper execution:")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500, mimetype="text/plain")
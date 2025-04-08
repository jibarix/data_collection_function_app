# function_app/HttpTriggerScraper/__init__.py

import logging
import azure.functions as func
from scraper.config import SCRAPER_CONFIGS
from scraper.base_scraper import MonthlyDataScraper
from scraper.azure_blob import upload_raw_data

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
                # Download the Excel file.
                content = scraper.download_excel(config['url'], config['file_name'])
                if content is None:
                    logging.error(f"Failed to download Excel file for {name}.")
                    continue
                
                # Upload raw file to Azure Storage Account.
                upload_raw_data(content, config['file_name'])
                
                # Extract, process, and upload final data.
                df = scraper.extract_data(content, config['sheet_name'], config['data_location'])
                if df is None:
                    logging.error(f"Data extraction failed for {name}.")
                    continue
                
                processed = scraper.process_data(df)
                scraper.insert_data(processed)
                scraper.update_last_run(name)
                logging.info(f"Scraper {name} processed and updated successfully.")
            else:
                logging.info(f"No update needed for {name}.")
        
        return func.HttpResponse("Scraper run complete.", status_code=200)
    except Exception as e:
        logging.exception("Error during scraper execution.")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
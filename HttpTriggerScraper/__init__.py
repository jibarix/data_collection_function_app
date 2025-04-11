import os
import sys
import logging
import traceback

# For local development, adjust sys.path to include the root of the project
if "WEBSITE_INSTANCE_ID" not in os.environ:
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    logging.info(f"Added '{parent_dir}' to sys.path for local development.")

import azure.functions as func

def main(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Function HTTP-triggered entry point for the data collection scraper."""
    logging.info("⚡ Function starting up...")

    try:
        # Import scraper modules - adding explicit error handling here
        try:
            from scraper.config import SCRAPER_CONFIGS
            from scraper.base_scraper import MonthlyDataScraper
            from scraper.azure_blob import upload_raw_data
            logging.info("✅ Successfully imported scraper modules")
        except ImportError as e:
            error_details = traceback.format_exc()
            logging.error(f"❌ Failed to import scraper modules: {e}\n{error_details}")
            return func.HttpResponse(f"Import error: {str(e)}\n{error_details}", status_code=500)

        # Process each scraper configured in SCRAPER_CONFIGS
        logging.info(f"Found {len(SCRAPER_CONFIGS)} scraper configs to process")
        
        for name, config in SCRAPER_CONFIGS.items():
            try:
                logging.info(f"Processing scraper: {name}")
                scraper = None
                if config.get('type') == 'monthly':
                    scraper = MonthlyDataScraper(config)
                else:
                    logging.warning(f"Unsupported scraper type: {config.get('type')}")
                    continue
                
                # Check if update is needed
                if scraper and scraper.should_update(name):
                    # Step 1: Download the Excel file
                    logging.info(f"Downloading Excel file for {name}...")
                    content = scraper.download_excel(config.get('url'), config.get('file_name'))
                    if content is None:
                        logging.error(f"Failed to download Excel file for {name}.")
                        continue
                    logging.info(f"Successfully downloaded {len(content)} bytes for {name}")
                    
                    # Step 2: Upload the raw file
                    logging.info(f"Uploading raw data for {name}...")
                    try:
                        upload_raw_data(content, config.get('file_name'))
                        logging.info(f"Successfully uploaded raw data for {name}")
                    except Exception as e:
                        logging.error(f"Error uploading raw data: {str(e)}")
                        # Continue processing even if upload fails
                    
                    # Step 3: Extract and process
                    logging.info(f"Extracting and processing data for {name}...")
                    df = scraper.extract_data(content, config.get('sheet_name'), config.get('data_location'))
                    if df is None:
                        logging.error(f"Data extraction failed for {name}.")
                        continue
                    
                    processed = scraper.process_data(df)
                    logging.info(f"Successfully processed data for {name}: {len(processed)} rows")
                    
                    # Step 4: Insert processed data
                    logging.info(f"Uploading processed data for {name}...")
                    scraper.insert_data(processed)
                    
                    # Step 5: Update metadata
                    scraper.update_last_run(name)
                    logging.info(f"Scraper {name} processed and updated successfully.")
                else:
                    logging.info(f"No update needed for scraper: {name}.")
            except Exception as e:
                error_details = traceback.format_exc()
                logging.error(f"Error processing scraper {name}: {str(e)}\n{error_details}")
                # Continue with other scrapers
        
        return func.HttpResponse("Scraper run complete.", status_code=200)
    except Exception as e:
        error_details = traceback.format_exc()
        logging.error(f"Error during scraper execution: {str(e)}\n{error_details}")
        return func.HttpResponse(f"Error: {str(e)}\n{error_details}", status_code=500)
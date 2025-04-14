import os
import sys
import logging
import traceback
import json
import azure.functions as func

def main(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Function HTTP-triggered entry point for the data collection scraper."""
    logging.info("⚡ Function starting up...")
    
    # Return diagnostic information dict to help troubleshoot
    diagnostics = {
        "environment": dict(os.environ),
        "sys_path": sys.path,
        "python_version": sys.version,
        "req_method": req.method,
        "req_url": str(req.url),
        "req_headers": dict(req.headers),
        "req_params": dict(req.params),
    }

    # Redact sensitive information from diagnostics
    if "AZURE_STORAGE_CONNECTION_STRING" in diagnostics["environment"]:
        diagnostics["environment"]["AZURE_STORAGE_CONNECTION_STRING"] = "REDACTED"
    if "AzureWebJobsStorage" in diagnostics["environment"]:
        diagnostics["environment"]["AzureWebJobsStorage"] = "REDACTED"

    # Response dictionary
    response = {
        "status": "initializing",
        "diagnostics": diagnostics,
        "steps_completed": [],
        "errors": []
    }

    # For testing without the full scraper
    query_params = req.params
    if query_params.get("mode") == "diagnostic":
        response["status"] = "diagnostic_complete"
        return func.HttpResponse(
            json.dumps(response, indent=2, default=str), 
            mimetype="application/json",
            status_code=200
        )

    # Step 1: Add scraper root directory to path if needed
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
        
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
            logging.info(f"Added '{parent_dir}' to sys.path")
        
        response["steps_completed"].append("path_configuration")
    except Exception as e:
        error_msg = f"Path configuration error: {str(e)}"
        logging.error(f"❌ {error_msg}\n{traceback.format_exc()}")
        response["errors"].append(error_msg)

    # Step 2: Import scraper modules with detailed error reporting
    try:
        from scraper.config import SCRAPER_CONFIGS
        response["steps_completed"].append("import_config")
        
        from scraper.base_scraper import MonthlyDataScraper
        response["steps_completed"].append("import_base_scraper")
        
        from scraper.azure_blob import upload_raw_data
        response["steps_completed"].append("import_azure_blob")
        
        response["scraper_count"] = len(SCRAPER_CONFIGS)
        logging.info(f"✅ Successfully imported scraper modules, found {len(SCRAPER_CONFIGS)} scrapers")
    except ImportError as e:
        error_msg = f"Import error: {str(e)}"
        stack_trace = traceback.format_exc()
        logging.error(f"❌ {error_msg}\n{stack_trace}")
        response["errors"].append(error_msg)
        response["stack_trace"] = stack_trace
        response["status"] = "import_failed"
        return func.HttpResponse(json.dumps(response, indent=2, default=str), 
                                 mimetype="application/json", 
                                 status_code=500)

    # Check for connection string (redacted in logs)
    try:
        from scraper.azure_blob import get_connection_string
        connection_string = get_connection_string()
        if connection_string:
            response["steps_completed"].append("connection_string_found")
            logging.info("✅ Successfully retrieved storage connection string")
        else:
            error_msg = "Connection string is empty or None"
            logging.error(f"❌ {error_msg}")
            response["errors"].append(error_msg)
    except Exception as e:
        error_msg = f"Connection string error: {str(e)}"
        logging.error(f"❌ {error_msg}\n{traceback.format_exc()}")
        response["errors"].append(error_msg)

    # For testing just one scraper
    test_scraper = query_params.get("scraper")
    if test_scraper and test_scraper in SCRAPER_CONFIGS:
        config = SCRAPER_CONFIGS[test_scraper]
        try:
            response["current_scraper"] = test_scraper
            logging.info(f"Running single scraper test for: {test_scraper}")
            
            # Create scraper instance
            scraper = MonthlyDataScraper(config)
            response["steps_completed"].append("created_scraper_instance")
            
            # Test blob storage access
            from azure.storage.blob import BlobServiceClient
            connection_string = get_connection_string()
            BlobServiceClient.from_connection_string(connection_string)
            response["steps_completed"].append("blob_service_connection_test")
            
            # Try downloading
            content = scraper.download_excel(config['url'], config['file_name'])
            if content:
                response["steps_completed"].append("download_excel")
                logging.info(f"Successfully downloaded {len(content)} bytes")
                
                # Try processing (but don't actually save)
                df = scraper.extract_data(content, config['sheet_name'], config['data_location'])
                if df is not None:
                    response["steps_completed"].append("extract_data")
                    response["dataframe_shape"] = list(df.shape)
                    logging.info(f"Successfully extracted data: {df.shape}")
            
            response["status"] = "single_scraper_test_complete"
            return func.HttpResponse(
                json.dumps(response, indent=2, default=str), 
                mimetype="application/json",
                status_code=200
            )
        except Exception as e:
            error_msg = f"Single scraper test error: {str(e)}"
            logging.error(f"❌ {error_msg}\n{traceback.format_exc()}")
            response["errors"].append(error_msg)
            response["status"] = "single_scraper_test_failed"
            return func.HttpResponse(
                json.dumps(response, indent=2, default=str), 
                mimetype="application/json",
                status_code=500
            )

    # Process all scrapers
    try:
        processed_scrapers = []
        for name, config in SCRAPER_CONFIGS.items():
            try:
                logging.info(f"Processing scraper: {name}")
                if config.get('type') == 'monthly':
                    scraper = MonthlyDataScraper(config)
                    
                    # Check if update is needed
                    if scraper.should_update(name):
                        logging.info(f"Update needed for {name}")
                        
                        # Download Excel file
                        content = scraper.download_excel(config.get('url'), config.get('file_name'))
                        if content is None:
                            logging.error(f"Failed to download Excel file for {name}.")
                            continue
                            
                        # Upload raw data
                        try:
                            upload_raw_data(content, config.get('file_name'))
                        except Exception as e:
                            logging.error(f"Error uploading raw data for {name}: {str(e)}")
                            
                        # Extract and process
                        df = scraper.extract_data(content, config.get('sheet_name'), config.get('data_location'))
                        if df is None:
                            logging.error(f"Data extraction failed for {name}.")
                            continue
                            
                        processed = scraper.process_data(df)
                        scraper.insert_data(processed)
                        scraper.update_last_run(name)
                        processed_scrapers.append(name)
                        logging.info(f"Scraper {name} processed successfully.")
                    else:
                        logging.info(f"No update needed for {name}")
                else:
                    logging.warning(f"Unsupported scraper type: {config.get('type')}")
            except Exception as e:
                error_msg = f"Error processing scraper {name}: {str(e)}"
                logging.error(f"❌ {error_msg}\n{traceback.format_exc()}")
                response["errors"].append(error_msg)
        
        response["processed_scrapers"] = processed_scrapers
        response["status"] = "complete"
    except Exception as e:
        error_msg = f"Error during main scraper execution: {str(e)}"
        logging.error(f"❌ {error_msg}\n{traceback.format_exc()}")
        response["errors"].append(error_msg)
        response["status"] = "failed"

    return func.HttpResponse(
        json.dumps(response, indent=2, default=str), 
        mimetype="application/json",
        status_code=200 if not response["errors"] else 500
    )
# scraper/__init__.py

# Import main modules to simplify imports elsewhere
from scraper.base_scraper import BaseEDBScraper, MonthlyDataScraper
from scraper.config import SCRAPER_CONFIGS, TABLES_TO_CREATE
from scraper.azure_blob import upload_raw_data, upload_final_data
from scraper.data_tracker import update_last_run, get_last_run

# Add logging configuration
import logging
logging.getLogger(__name__).setLevel(logging.INFO)
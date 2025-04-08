# scraper/base_scraper.py

import pandas as pd
import logging
from datetime import datetime
from io import BytesIO
import requests
from scraper import data_tracker

class BaseEDBScraper:
    """Base class for Economic Development Bank scrapers"""
    def __init__(self, config: dict):
        self.config = config

    def create_table(self) -> None:
        """Dummy method: Table creation is managed elsewhere."""
        pass

    def process_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process raw data into a standardized format (to be implemented in subclass)"""
        raise NotImplementedError

    def insert_data(self, data: pd.DataFrame) -> None:
        """Upload processed data to the Data Lake using the azure_blob uploader"""
        from scraper import azure_blob
        # Save the processed data as CSV under the given table_name.
        azure_blob.upload_final_data(data, self.config['table_name'])

    def download_excel(self, url: str, file_name: str) -> bytes:
        """Download Excel file from a specified URL"""
        full_url = url + file_name
        try:
            response = requests.get(full_url)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logging.error(f"Download error: {e}")
            return None

    def extract_data(self, excel_content: bytes, sheet_name: str, data_location: str) -> pd.DataFrame:
        """Extract a range of cells from an Excel file"""
        try:
            df = pd.read_excel(BytesIO(excel_content), sheet_name=sheet_name, header=None)
            start_cell, end_cell = data_location.split(":")
            start_row = int(start_cell[1:]) - 1
            start_col = ord(start_cell[0].upper()) - ord('A')
            end_row = int(end_cell[1:]) - 1
            end_col = ord(end_cell[0].upper()) - ord('A')
            return df.iloc[start_row:end_row + 1, start_col:end_col + 1]
        except Exception as e:
            logging.error(f"Extraction error: {e}")
            return None

    def update_last_run(self, dataset_name: str) -> None:
        """Update the timestamp of the last scraper run using data_tracker"""
        timestamp = datetime.utcnow().isoformat()
        data_tracker.update_last_run(dataset_name, timestamp)

    def get_last_run(self, dataset_name: str):
        """Get the timestamp of the last scraper run using data_tracker"""
        return data_tracker.get_last_run(dataset_name)

    def should_update(self, dataset_name: str, update_frequency_hours: int = 24) -> bool:
        """Determine if an update is needed based on the last run"""
        last_run = self.get_last_run(dataset_name)
        if not last_run:
            return True
        now = datetime.utcnow()
        hours_since_update = (now - last_run).total_seconds() / 3600
        return hours_since_update >= update_frequency_hours

# Example implementation for monthly data.
class MonthlyDataScraper(BaseEDBScraper):
    def process_data(self, df: pd.DataFrame) -> pd.DataFrame:
        # Set fiscal years as column headers.
        df.columns = ['Month'] + [int(year) for year in df.iloc[0, 1:]]
        df = df.iloc[1:].reset_index(drop=True)
        
        # Transform from wide to long format.
        df_melted = pd.melt(df, id_vars=['Month'], var_name='Year', value_name=self.config['value_column'])
        
        # Create dates from month names and fiscal years.
        df_melted['Date'] = df_melted.apply(self._create_date, axis=1)
        df_melted = df_melted.dropna(subset=['Date'])
        df_melted = df_melted.sort_values(by='Date').reset_index(drop=True)
        
        # Convert value types.
        if self.config.get('value_type', 'float') == 'int':
            df_melted[self.config['value_column']] = pd.to_numeric(df_melted[self.config['value_column']], errors='coerce')
            df_melted = df_melted.dropna(subset=[self.config['value_column']])
            df_melted[self.config['value_column']] = df_melted[self.config['value_column']].round().astype(int)
        else:
            df_melted[self.config['value_column']] = pd.to_numeric(df_melted[self.config['value_column']], errors='coerce')
            df_melted = df_melted.dropna(subset=[self.config['value_column']])
        
        return df_melted[['Date', self.config['value_column']]]

    def _create_date(self, row: pd.Series):
        month_mapping = {
            'July': 7, 'August': 8, 'September': 9, 'October': 10,
            'November': 11, 'December': 12, 'January': 1, 'February': 2,
            'March': 3, 'April': 4, 'May': 5, 'June': 6
        }
        month_num = month_mapping.get(row['Month'])
        if not month_num:
            return None
        year = int(row['Year'])
        # For fiscal data, use the previous year for months July-December.
        if month_num >= 7:
            return pd.to_datetime(f'{year - 1}-{month_num}-01')
        else:
            return pd.to_datetime(f'{year}-{month_num}-01')
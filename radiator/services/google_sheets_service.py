"""Google Sheets service for uploading CSV files as new sheets."""

import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GoogleSheetsService:
    """Service for uploading CSV files to Google Sheets as new worksheets."""
    
    def __init__(self, credentials_path: str, document_id: str, sheet_prefix: str = "Report_"):
        """
        Initialize Google Sheets service.
        
        Args:
            credentials_path: Path to service account JSON file
            document_id: Google Sheets document ID
            sheet_prefix: Prefix for new sheet names
        """
        self.credentials_path = credentials_path
        self.document_id = document_id
        self.sheet_prefix = sheet_prefix
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Sheets API."""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            self.service = build('sheets', 'v4', credentials=credentials)
            logger.info("Successfully authenticated with Google Sheets API")
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Sheets API: {e}")
            raise
    
    def _sanitize_sheet_name(self, filename: str) -> str:
        """
        Sanitize filename to create valid Google Sheets sheet name.
        
        Google Sheets sheet names:
        - Max 100 characters
        - Cannot contain: [ ] * ? / \\ :
        - Cannot be empty or only spaces
        """
        # Remove file extension
        name = Path(filename).stem
        
        # Remove invalid characters
        name = re.sub(r'[\[\]*?/\\:]', '_', name)
        
        # Remove multiple underscores
        name = re.sub(r'_+', '_', name)
        
        # Trim underscores from start/end
        name = name.strip('_')
        
        # Ensure not empty
        if not name:
            name = "Sheet"
        
        # Truncate to 100 characters
        if len(name) > 100:
            name = name[:100].rstrip('_')
        
        return name
    
    def _read_csv_file(self, file_path: Path) -> Optional[pd.DataFrame]:
        """
        Read CSV file with multiple encoding attempts.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            DataFrame or None if failed
        """
        encodings = ['utf-8', 'utf-8-sig', 'windows-1251', 'cp1251', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                logger.info(f"Successfully read CSV file {file_path.name} with encoding {encoding}")
                return df
            except UnicodeDecodeError:
                logger.debug(f"Failed to read {file_path.name} with encoding {encoding}")
                continue
            except Exception as e:
                logger.error(f"Error reading CSV file {file_path.name} with encoding {encoding}: {e}")
                continue
        
        logger.error(f"Failed to read CSV file {file_path.name} with any encoding")
        return None
    
    def _prepare_data_for_sheets(self, df: pd.DataFrame) -> List[List[Any]]:
        """
        Prepare DataFrame data for Google Sheets format.
        
        Args:
            df: DataFrame to prepare
            
        Returns:
            List of lists representing sheet data
        """
        # Replace NaN values with empty strings
        df_clean = df.fillna('')
        
        # Convert DataFrame to list of lists
        data = df_clean.values.tolist()
        
        # Add headers as first row
        headers = df_clean.columns.tolist()
        data.insert(0, headers)
        
        return data
    
    def create_sheet(self, sheet_name: str) -> bool:
        """
        Create a new sheet in the Google Sheets document.
        
        Args:
            sheet_name: Name for the new sheet
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get existing sheets to check for duplicates
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.document_id).execute()
            existing_sheets = [sheet['properties']['title'] for sheet in spreadsheet['sheets']]
            
            # If sheet already exists, add timestamp
            if sheet_name in existing_sheets:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                sheet_name = f"{sheet_name}_{timestamp}"
            
            # Create new sheet
            request_body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }]
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.document_id,
                body=request_body
            ).execute()
            
            logger.info(f"Successfully created sheet: {sheet_name}")
            return True
            
        except HttpError as e:
            logger.error(f"Failed to create sheet {sheet_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating sheet {sheet_name}: {e}")
            return False
    
    def upload_csv_to_sheet(self, file_path: Path, sheet_name: Optional[str] = None) -> bool:
        """
        Upload CSV file as a new sheet in Google Sheets.
        
        Args:
            file_path: Path to CSV file
            sheet_name: Optional custom sheet name (defaults to filename)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Read CSV file
            df = self._read_csv_file(file_path)
            if df is None:
                return False
            
            # Prepare sheet name
            if sheet_name is None:
                sheet_name = self._sanitize_sheet_name(file_path.name)
            
            # Create new sheet
            if not self.create_sheet(sheet_name):
                return False
            
            # Prepare data for upload
            data = self._prepare_data_for_sheets(df)
            
            # Upload data to sheet
            range_name = f"{sheet_name}!A1"
            
            body = {
                'values': data
            }
            
            self.service.spreadsheets().values().update(
                spreadsheetId=self.document_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            # Auto-resize columns
            self._auto_resize_columns(sheet_name, len(df.columns))
            
            # Add filter to first row (headers)
            self._add_filter_to_first_row(sheet_name, len(df.columns))
            
            logger.info(f"Successfully uploaded {file_path.name} to sheet {sheet_name}")
            return True
            
        except HttpError as e:
            logger.error(f"Failed to upload CSV {file_path.name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error uploading CSV {file_path.name}: {e}")
            return False
    
    def _auto_resize_columns(self, sheet_name: str, num_columns: int):
        """
        Auto-resize columns in the sheet.
        
        Args:
            sheet_name: Name of the sheet
            num_columns: Number of columns to resize
        """
        try:
            # Create column range (A to last column)
            end_column = chr(ord('A') + num_columns - 1)
            range_name = f"{sheet_name}!A:{end_column}"
            
            request_body = {
                'requests': [{
                    'autoResizeDimensions': {
                        'dimensions': {
                            'sheetId': self._get_sheet_id(sheet_name),
                            'dimension': 'COLUMNS',
                            'startIndex': 0,
                            'endIndex': num_columns
                        }
                    }
                }]
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.document_id,
                body=request_body
            ).execute()
            
            logger.debug(f"Auto-resized columns for sheet {sheet_name}")
            
        except Exception as e:
            logger.warning(f"Failed to auto-resize columns for sheet {sheet_name}: {e}")
    
    def _add_filter_to_first_row(self, sheet_name: str, num_columns: int):
        """
        Add filter to the first row (headers) of the sheet.
        
        Args:
            sheet_name: Name of the sheet
            num_columns: Number of columns to include in filter
        """
        try:
            # Get sheet ID
            sheet_id = self._get_sheet_id(sheet_name)
            if sheet_id is None:
                logger.warning(f"Cannot add filter: sheet {sheet_name} not found")
                return
            
            # Create column range (A to last column)
            end_column = chr(ord('A') + num_columns - 1)
            range_name = f"{sheet_name}!A1:{end_column}1"
            
            request_body = {
                'requests': [{
                    'setBasicFilter': {
                        'filter': {
                            'range': {
                                'sheetId': sheet_id,
                                'startRowIndex': 0,
                                'endRowIndex': 1,
                                'startColumnIndex': 0,
                                'endColumnIndex': num_columns
                            }
                        }
                    }
                }]
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.document_id,
                body=request_body
            ).execute()
            
            logger.debug(f"Added filter to first row for sheet {sheet_name}")
            
        except Exception as e:
            logger.warning(f"Failed to add filter to first row for sheet {sheet_name}: {e}")
    
    def _get_sheet_id(self, sheet_name: str) -> Optional[int]:
        """
        Get sheet ID by sheet name.
        
        Args:
            sheet_name: Name of the sheet
            
        Returns:
            Sheet ID or None if not found
        """
        try:
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.document_id).execute()
            for sheet in spreadsheet['sheets']:
                if sheet['properties']['title'] == sheet_name:
                    return sheet['properties']['sheetId']
            return None
        except Exception as e:
            logger.error(f"Failed to get sheet ID for {sheet_name}: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        Test connection to Google Sheets.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.document_id).execute()
            logger.info(f"Successfully connected to Google Sheets: {spreadsheet['properties']['title']}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Google Sheets: {e}")
            return False

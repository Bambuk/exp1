"""Google Sheets service for uploading CSV files as new sheets."""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GoogleSheetsService:
    """Service for uploading CSV files to Google Sheets as new worksheets."""

    def __init__(
        self, credentials_path: str, document_id: str, sheet_prefix: str = "Report_"
    ):
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
                scopes=["https://www.googleapis.com/auth/spreadsheets"],
            )
            self.service = build("sheets", "v4", credentials=credentials)
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
        name = re.sub(r"[\[\]*?/\\:]", "_", name)

        # Remove multiple underscores
        name = re.sub(r"_+", "_", name)

        # Trim underscores from start/end
        name = name.strip("_")

        # Ensure not empty
        if not name:
            name = "Sheet"

        # Truncate to 100 characters
        if len(name) > 100:
            name = name[:100].rstrip("_")

        return name

    def _read_csv_file(self, file_path: Path) -> Optional[pd.DataFrame]:
        """
        Read CSV file with multiple encoding attempts.

        Args:
            file_path: Path to CSV file

        Returns:
            DataFrame or None if failed
        """
        encodings = ["utf-8", "utf-8-sig", "windows-1251", "cp1251", "iso-8859-1"]

        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                logger.info(
                    f"Successfully read CSV file {file_path.name} with encoding {encoding}"
                )
                return df
            except UnicodeDecodeError:
                logger.debug(
                    f"Failed to read {file_path.name} with encoding {encoding}"
                )
                continue
            except Exception as e:
                logger.error(
                    f"Error reading CSV file {file_path.name} with encoding {encoding}: {e}"
                )
                continue

        logger.error(f"Failed to read CSV file {file_path.name} with any encoding")
        return None

    def _prepare_data_for_sheets(self, df: pd.DataFrame) -> List[List[Any]]:
        """
        Prepare DataFrame data for Google Sheets format.
        Converts task keys in "Ключ задачи" column to hyperlinks.

        Args:
            df: DataFrame to prepare

        Returns:
            List of lists representing sheet data
        """
        # Replace NaN values with empty strings
        df_clean = df.fillna("")

        # Convert DataFrame to list of lists
        data = df_clean.values.tolist()

        # Add headers as first row
        headers = df_clean.columns.tolist()
        data.insert(0, headers)

        # Convert task keys to hyperlinks if "Ключ задачи" column exists
        if "Ключ задачи" in headers:
            task_key_index = headers.index("Ключ задачи")

            for i in range(1, len(data)):  # Skip header row
                task_key = data[i][task_key_index]
                if task_key and isinstance(task_key, str) and task_key.strip():
                    # Create HYPERLINK formula for Google Sheets
                    # Use semicolon as separator for Russian locale
                    url = f"https://tracker.yandex.ru/{task_key}"
                    data[i][task_key_index] = f'=HYPERLINK("{url}";"{task_key}")'

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
            spreadsheet = (
                self.service.spreadsheets()
                .get(spreadsheetId=self.document_id)
                .execute()
            )
            existing_sheets = [
                sheet["properties"]["title"] for sheet in spreadsheet["sheets"]
            ]

            # If sheet already exists, add timestamp
            if sheet_name in existing_sheets:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                sheet_name = f"{sheet_name}_{timestamp}"

            # Create new sheet
            request_body = {
                "requests": [{"addSheet": {"properties": {"title": sheet_name}}}]
            }

            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.document_id, body=request_body
            ).execute()

            logger.info(f"Successfully created sheet: {sheet_name}")
            return True

        except HttpError as e:
            logger.error(f"Failed to create sheet {sheet_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating sheet {sheet_name}: {e}")
            return False

    def upload_csv_to_sheet(
        self, file_path: Path, sheet_name: Optional[str] = None
    ) -> bool:
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

            body = {"values": data}

            self.service.spreadsheets().values().update(
                spreadsheetId=self.document_id,
                range=range_name,
                valueInputOption="USER_ENTERED",  # Use USER_ENTERED to process formulas like HYPERLINK
                body=body,
            ).execute()

            # Auto-resize columns
            self._auto_resize_columns(sheet_name, len(df.columns))

            # Add filter to all data (headers + data rows)
            self._add_filter_to_all_data(sheet_name, len(df.columns), len(df) + 1)

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
            end_column = chr(ord("A") + num_columns - 1)
            range_name = f"{sheet_name}!A:{end_column}"

            request_body = {
                "requests": [
                    {
                        "autoResizeDimensions": {
                            "dimensions": {
                                "sheetId": self._get_sheet_id(sheet_name),
                                "dimension": "COLUMNS",
                                "startIndex": 0,
                                "endIndex": num_columns,
                            }
                        }
                    }
                ]
            }

            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.document_id, body=request_body
            ).execute()

            logger.debug(f"Auto-resized columns for sheet {sheet_name}")

        except Exception as e:
            logger.warning(f"Failed to auto-resize columns for sheet {sheet_name}: {e}")

    def _add_filter_to_all_data(self, sheet_name: str, num_columns: int, num_rows: int):
        """
        Add filter to all data in the sheet (headers + data rows).

        Args:
            sheet_name: Name of the sheet
            num_columns: Number of columns to include in filter
            num_rows: Number of rows to include in filter (including header)
        """
        try:
            # Get sheet ID
            sheet_id = self._get_sheet_id(sheet_name)
            if sheet_id is None:
                logger.warning(f"Cannot add filter: sheet {sheet_name} not found")
                return

            # Create column range (A to last column)
            end_column = chr(ord("A") + num_columns - 1)
            range_name = f"{sheet_name}!A1:{end_column}{num_rows}"

            request_body = {
                "requests": [
                    {
                        "setBasicFilter": {
                            "filter": {
                                "range": {
                                    "sheetId": sheet_id,
                                    "startRowIndex": 0,
                                    "endRowIndex": num_rows,
                                    "startColumnIndex": 0,
                                    "endColumnIndex": num_columns,
                                }
                            }
                        }
                    }
                ]
            }

            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.document_id, body=request_body
            ).execute()

            logger.debug(
                f"Added filter to all data ({num_rows} rows, {num_columns} columns) for sheet {sheet_name}"
            )

        except Exception as e:
            logger.warning(
                f"Failed to add filter to all data for sheet {sheet_name}: {e}"
            )

    def _get_sheet_id(self, sheet_name: str) -> Optional[int]:
        """
        Get sheet ID by sheet name.

        Args:
            sheet_name: Name of the sheet

        Returns:
            Sheet ID or None if not found
        """
        try:
            spreadsheet = (
                self.service.spreadsheets()
                .get(spreadsheetId=self.document_id)
                .execute()
            )
            for sheet in spreadsheet["sheets"]:
                if sheet["properties"]["title"] == sheet_name:
                    return sheet["properties"]["sheetId"]
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
            spreadsheet = (
                self.service.spreadsheets()
                .get(spreadsheetId=self.document_id)
                .execute()
            )
            logger.info(
                f"Successfully connected to Google Sheets: {spreadsheet['properties']['title']}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Google Sheets: {e}")
            return False

    def create_pivot_tables_from_dataframe(
        self, details_data: pd.DataFrame, document_id: str
    ) -> Dict[str, Optional[int]]:
        """
        Create Google Sheets pivot tables from DataFrame data.

        Args:
            details_data: DataFrame with details data
            document_id: Google Sheets document ID

        Returns:
            Dictionary with sheet IDs: {'ttd_pivot': sheet_id, 'ttm_pivot': sheet_id}
        """
        try:
            if details_data is None or details_data.empty:
                logger.warning("No details data provided for pivot tables")
                return {"ttd_pivot": None, "ttm_pivot": None}

            # Get the source sheet ID (first sheet with details data)
            source_sheet_id = self._get_source_sheet_id(document_id)
            if source_sheet_id is None:
                logger.error("Could not find source sheet for pivot tables")
                return {"ttd_pivot": None, "ttm_pivot": None}

            # Create TTD pivot table with unique name
            import time

            timestamp = int(time.time())
            ttd_sheet_id = self._create_google_pivot_table(
                document_id, source_sheet_id, f"TTD Pivot {timestamp}", "ttd"
            )

            # Create TTM pivot table with unique name
            ttm_sheet_id = self._create_google_pivot_table(
                document_id, source_sheet_id, f"TTM Pivot {timestamp}", "ttm"
            )

            return {"ttd_pivot": ttd_sheet_id, "ttm_pivot": ttm_sheet_id}

        except Exception as e:
            logger.error(f"Failed to create pivot tables from DataFrame: {e}")
            return {"ttd_pivot": None, "ttm_pivot": None}

    def _get_source_sheet_id(self, document_id: str) -> Optional[int]:
        """
        Get the ID of the source sheet with details data.

        Args:
            document_id: Google Sheets document ID

        Returns:
            Sheet ID if found, None otherwise
        """
        try:
            spreadsheet = (
                self.service.spreadsheets().get(spreadsheetId=document_id).execute()
            )
            sheets = spreadsheet.get("sheets", [])

            if not sheets:
                logger.warning("No sheets found in document")
                return None

            # Look for a sheet that contains details data (not a pivot table)
            for sheet in sheets:
                sheet_name = sheet["properties"]["title"]
                # Skip pivot tables and look for details sheet
                if (
                    not sheet_name.startswith("TTD Pivot")
                    and not sheet_name.startswith("TTM Pivot")
                    and not sheet_name == "Лист1"
                ):
                    logger.info(
                        f"Found source sheet: {sheet_name} (ID: {sheet['properties']['sheetId']})"
                    )
                    return sheet["properties"]["sheetId"]

            # If no suitable sheet found, return the first one
            logger.warning("No suitable source sheet found, using first sheet")
            return sheets[0]["properties"]["sheetId"]

        except Exception as e:
            logger.error(f"Failed to get source sheet ID: {e}")
            return None

    def _create_google_pivot_table(
        self, document_id: str, source_sheet_id: int, sheet_name: str, pivot_type: str
    ) -> Optional[int]:
        """
        Create a Google Sheets pivot table.

        Args:
            document_id: Google Sheets document ID
            source_sheet_id: Source sheet ID with data
            sheet_name: Name for the new pivot sheet
            pivot_type: Type of pivot ("ttd" or "ttm")

        Returns:
            New sheet ID if successful, None otherwise
        """
        try:
            # Create new sheet for pivot table
            request_body = {
                "requests": [
                    {
                        "addSheet": {
                            "properties": {
                                "title": sheet_name,
                                "gridProperties": {"rowCount": 1000, "columnCount": 20},
                            }
                        }
                    }
                ]
            }

            response = (
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=document_id, body=request_body)
                .execute()
            )

            new_sheet_id = response["replies"][0]["addSheet"]["properties"]["sheetId"]

            # Create pivot table
            pivot_table_request = self._build_pivot_table_request(
                source_sheet_id, new_sheet_id, pivot_type
            )

            if pivot_table_request:
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=document_id, body={"requests": [pivot_table_request]}
                ).execute()

            logger.info(f"Successfully created Google Sheets pivot table: {sheet_name}")
            return new_sheet_id

        except Exception as e:
            logger.error(
                f"Failed to create Google Sheets pivot table {sheet_name}: {e}"
            )
            return None

    def _build_pivot_table_request(
        self, source_sheet_id: int, target_sheet_id: int, pivot_type: str
    ) -> Optional[Dict]:
        """
        Build pivot table request for Google Sheets API.

        Args:
            source_sheet_id: Source sheet ID
            target_sheet_id: Target sheet ID
            pivot_type: Type of pivot ("ttd" or "ttm")

        Returns:
            Pivot table request dictionary
        """
        try:
            # Base pivot table configuration
            pivot_table = {
                "source": {
                    "sheetId": source_sheet_id,
                    "startRowIndex": 0,
                    "startColumnIndex": 0,
                    "endRowIndex": 1000,  # Will be adjusted by Google Sheets
                    "endColumnIndex": 20,  # Will be adjusted by Google Sheets
                },
                "rows": [
                    {
                        "sourceColumnOffset": self._get_column_index("Команда"),
                        "showTotals": False,
                        "sortOrder": "ASCENDING",
                    },
                    {
                        "sourceColumnOffset": self._get_column_index("Квартал"),
                        "showTotals": False,
                        "sortOrder": "ASCENDING",
                    },
                ],
                "values": [],
                "criteria": {},
            }

            if pivot_type == "ttd":
                # TTD pivot table values
                pivot_table["values"] = [
                    {
                        "sourceColumnOffset": self._get_column_index("TTD"),
                        "summarizeFunction": "AVERAGE",
                        "name": "TTD Mean",
                    },
                    {
                        "sourceColumnOffset": self._get_column_index("TTD"),
                        "summarizeFunction": "MAX",
                        "name": "TTD Max",
                    },
                    {
                        "sourceColumnOffset": self._get_column_index("TTD"),
                        "summarizeFunction": "COUNTA",
                        "name": "TTD Count",
                    },
                    {
                        "sourceColumnOffset": self._get_column_index("TTD Pause"),
                        "summarizeFunction": "AVERAGE",
                        "name": "TTD Pause Mean",
                    },
                ]
            elif pivot_type == "ttm":
                # TTM pivot table values
                pivot_table["values"] = [
                    {
                        "sourceColumnOffset": self._get_column_index("TTM"),
                        "summarizeFunction": "AVERAGE",
                        "name": "TTM Mean",
                    },
                    {
                        "sourceColumnOffset": self._get_column_index("TTM"),
                        "summarizeFunction": "MAX",
                        "name": "TTM Max",
                    },
                    {
                        "sourceColumnOffset": self._get_column_index("TTM"),
                        "summarizeFunction": "COUNTA",
                        "name": "TTM Count",
                    },
                    {
                        "sourceColumnOffset": self._get_column_index("Пауза"),
                        "summarizeFunction": "AVERAGE",
                        "name": "TTM Pause Mean",
                    },
                    {
                        "sourceColumnOffset": self._get_column_index("Tail"),
                        "summarizeFunction": "AVERAGE",
                        "name": "Tail Mean",
                    },
                    {
                        "sourceColumnOffset": self._get_column_index("Tail"),
                        "summarizeFunction": "MAX",
                        "name": "Tail Max",
                    },
                ]

            return {
                "updateCells": {
                    "start": {
                        "sheetId": target_sheet_id,
                        "rowIndex": 0,
                        "columnIndex": 0,
                    },
                    "rows": [
                        {
                            "values": [
                                {
                                    "pivotTable": pivot_table,
                                }
                            ]
                        }
                    ],
                    "fields": "pivotTable",
                }
            }

        except Exception as e:
            logger.error(f"Failed to build pivot table request: {e}")
            return None

    def _get_column_index(self, column_name: str) -> int:
        """
        Get column index for a given column name.

        Args:
            column_name: Name of the column

        Returns:
            Column index (0-based)
        """
        # Standard column mapping for details CSV
        column_mapping = {
            "Автор": 0,
            "Команда": 1,
            "Ключ задачи": 2,
            "Название": 3,
            "TTD": 4,
            "TTM": 5,
            "Tail": 6,
            "Пауза": 7,
            "TTD Pause": 8,
            "Discovery backlog (дни)": 9,
            "Готова к разработке (дни)": 10,
            "Квартал": 11,
        }

        return column_mapping.get(column_name, 0)

    def _read_csv_file_from_sheet(self, sheet_id: str) -> Optional[pd.DataFrame]:
        """
        Read CSV data from a Google Sheet.

        Args:
            sheet_id: Google Sheets document ID

        Returns:
            DataFrame with sheet data or None if failed
        """
        try:
            # Get all sheets in the document
            spreadsheet = (
                self.service.spreadsheets().get(spreadsheetId=sheet_id).execute()
            )
            sheets = spreadsheet.get("sheets", [])

            if not sheets:
                logger.warning("No sheets found in document")
                return None

            # Use the first sheet (assuming it contains details data)
            sheet_name = sheets[0]["properties"]["title"]
            range_name = f"{sheet_name}!A:Z"  # Read all columns

            result = (
                self.service.spreadsheets()
                .values()
                .get(spreadsheetId=sheet_id, range=range_name)
                .execute()
            )

            values = result.get("values", [])
            if not values:
                logger.warning("No data found in sheet")
                return None

            # Convert to DataFrame
            headers = values[0]
            data = values[1:]
            df = pd.DataFrame(data, columns=headers)

            # Convert numeric columns
            numeric_columns = [
                "TTD",
                "TTM",
                "Tail",
                "Пауза",
                "TTD Pause",
                "Discovery backlog (дни)",
                "Готова к разработке (дни)",
            ]
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            return df

        except Exception as e:
            logger.error(f"Failed to read data from sheet: {e}")
            return None

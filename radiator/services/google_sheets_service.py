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

from radiator.commands.models.ttm_details_columns import TTMDetailsColumns

logger = logging.getLogger(__name__)

# Column notes mapping based on TTM_DETAILS_REPORT_GUIDE.md
COLUMN_NOTES = {
    "Ключ задачи": "Ключ задачи из трекера (например, CPO-123)",
    "Название": "Название задачи",
    "Автор": "Автор задачи",
    "Команда": "Команда автора (определяется через AuthorTeamMappingService если не указана в задаче)",
    "PM Lead": "PM Lead команды (определяется через TeamLeadMappingService)",
    "TTM": "Количество дней от создания задачи до завершения (для завершенных задач) или до текущей даты (для незавершенных)",
    "TTD": "Количество дней от создания задачи до перехода в статус Готова к разработке",
    "Tail": "Время от начала статуса МП / Внешний тест до первого done-статуса после него (с исключением пауз)",
    "DevLT": "Время от первого валидного МП / В работе до последнего валидного МП / Внешний тест (календарное время, без исключения пауз). Для незавершенных задач в статусе МП / В работе рассчитывается до текущей даты",
    "Пауза": "Общее время пауз в задаче",
    "TTD Pause": "Время пауз до достижения статуса Готова к разработке",
    "Discovery backlog (дни)": "Время, проведенное в статусе Discovery backlog",
    "Готова к разработке (дни)": "Время, проведенное в статусе Готова к разработке",
    "Возвраты с Testing": "Количество возвратов в статус Testing для всех связанных FULLSTACK задач",
    "Возвраты с Внешний тест": "Количество возвратов в статус Внешний тест для всех связанных FULLSTACK задач",
    "Всего возвратов": "Сумма возвратов с Testing и Внешний тест",
    "Квартал": "Квартал завершения задачи (определяется по дате stable_done для завершенных задач)",
    "Квартал TTD": "Квартал перехода в статус Готова к разработке",
    "Создана": "Дата создания задачи",
    "Начало работы": "Дата последнего выхода из статуса Discovery backlog",
    "Завершено": "Дата стабильного завершения (stable_done) для завершенных задач",
    "Разработка": "1 если задача имеет валидный статус МП / В работе (>= 5 минут), иначе 0",
    "Завершена": "1 для завершенных задач (с stable_done), 0 для незавершенных",
}


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
    ) -> Optional[str]:
        """
        Upload CSV file as a new sheet in Google Sheets.

        Args:
            file_path: Path to CSV file
            sheet_name: Optional custom sheet name (defaults to filename)

        Returns:
            Name of the created sheet if successful, None otherwise
        """
        try:
            # Read CSV file
            df = self._read_csv_file(file_path)
            if df is None:
                return None

            # Prepare sheet name
            if sheet_name is None:
                sheet_name = self._sanitize_sheet_name(file_path.name)

            # Create new sheet
            if not self.create_sheet(sheet_name):
                return None

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

            # Apply conditional formatting to highlight cells exceeding thresholds
            sheet_id = self._get_sheet_id(sheet_name)
            if sheet_id is not None:
                self._apply_conditional_formatting_to_details(
                    sheet_id=sheet_id, sheet_name=sheet_name, num_rows=len(df)
                )

                # Freeze first row and resize 'Название' column
                self._freeze_first_row(sheet_id=sheet_id, sheet_name=sheet_name)
                self._resize_name_column(sheet_id=sheet_id, sheet_name=sheet_name)

                # Freeze first row and resize 'Название' column
                self._freeze_first_row(sheet_id=sheet_id, sheet_name=sheet_name)
                self._resize_name_column(sheet_id=sheet_id, sheet_name=sheet_name)

                # Add notes to column headers
                self._add_column_notes_to_details(
                    sheet_id=sheet_id,
                    sheet_name=sheet_name,
                    column_names=list(df.columns),
                )

            logger.info(f"Successfully uploaded {file_path.name} to sheet {sheet_name}")
            return sheet_name

        except HttpError as e:
            logger.error(f"Failed to upload CSV {file_path.name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error uploading CSV {file_path.name}: {e}")
            return None

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

    def _get_sheet_name_by_id(self, sheet_id: int) -> Optional[str]:
        """
        Get sheet name by sheet ID.

        Args:
            sheet_id: ID of the sheet

        Returns:
            Sheet name or None if not found
        """
        try:
            spreadsheet = (
                self.service.spreadsheets()
                .get(spreadsheetId=self.document_id)
                .execute()
            )
            for sheet in spreadsheet["sheets"]:
                if sheet["properties"]["sheetId"] == sheet_id:
                    return sheet["properties"]["title"]
            return None
        except Exception as e:
            logger.error(f"Failed to get sheet name for ID {sheet_id}: {e}")
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
        self,
        details_data: pd.DataFrame,
        document_id: str,
        source_sheet_name: Optional[str] = None,
    ) -> Dict[str, Optional[int]]:
        """
        Create Google Sheets pivot tables from DataFrame data.

        Args:
            details_data: DataFrame with details data
            document_id: Google Sheets document ID
            source_sheet_name: Optional name of the source sheet (if not provided, will search for it)

        Returns:
            Dictionary with sheet IDs: {'ttd_pivot': sheet_id, 'ttm_pivot': sheet_id}
        """
        try:
            if details_data is None or details_data.empty:
                logger.warning("No details data provided for pivot tables")
                return {"ttd_pivot": None, "ttm_pivot": None}

            # Get the source sheet ID
            if source_sheet_name:
                source_sheet_id = self._get_sheet_id(source_sheet_name)
            else:
                source_sheet_id = self._get_source_sheet_id(document_id)

            if source_sheet_id is None:
                logger.error("Could not find source sheet for pivot tables")
                return {"ttd_pivot": None, "ttm_pivot": None}

            # Get source sheet name if not provided
            if source_sheet_name is None:
                source_sheet_name = self._get_sheet_name_by_id(source_sheet_id)

            # Create TTD pivot table with unique name
            import time

            timestamp = int(time.time())
            ttd_sheet_id = self._create_google_pivot_table(
                document_id,
                source_sheet_id,
                f"TTD Pivot {timestamp}",
                "ttd",
                source_sheet_name=source_sheet_name,
            )

            # Create TTM pivot table with unique name
            ttm_sheet_id = self._create_google_pivot_table(
                document_id,
                source_sheet_id,
                f"TTM Pivot {timestamp}",
                "ttm",
                source_sheet_name=source_sheet_name,
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
        self,
        document_id: str,
        source_sheet_id: int,
        sheet_name: str,
        pivot_type: str,
        source_sheet_name: Optional[str] = None,
    ) -> Optional[int]:
        """
        Create a Google Sheets pivot table.

        Args:
            document_id: Google Sheets document ID
            source_sheet_id: Source sheet ID with data
            sheet_name: Name for the new pivot sheet
            pivot_type: Type of pivot ("ttd" or "ttm")
            source_sheet_name: Optional name of the source sheet (for percentile statistics)

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

            # Add percentile statistics
            # Get source sheet name if not provided
            if source_sheet_name is None:
                source_sheet_name = self._get_sheet_name_by_id(source_sheet_id)

            if source_sheet_name:
                self._add_percentile_statistics(
                    sheet_id=new_sheet_id,
                    sheet_name=sheet_name,
                    source_sheet_name=source_sheet_name,
                    pivot_type=pivot_type,
                )
            else:
                logger.warning(
                    f"Could not determine source sheet name for percentile statistics"
                )

            # Apply conditional formatting to highlight threshold values
            # Use large number for rows since pivot tables can have dynamic row count
            self._apply_conditional_formatting_to_pivot(
                sheet_id=new_sheet_id,
                sheet_name=sheet_name,
                pivot_type=pivot_type,
                num_rows=1000,
            )

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
            # startRowIndex: 0 means first row contains headers
            # Google Sheets should recognize column headers from row 0
            # Note: endColumnIndex is exclusive, so we need endColumnIndex = column_count
            pivot_table = {
                "source": {
                    "sheetId": source_sheet_id,
                    "startRowIndex": 0,  # First row contains headers
                    "startColumnIndex": 0,
                    "endRowIndex": 1000,  # Will be adjusted by Google Sheets
                    "endColumnIndex": TTMDetailsColumns.get_column_count(),  # Use single source of truth
                },
                "rows": [
                    {
                        "sourceColumnOffset": self._get_column_index("Разработка"),
                        "showTotals": False,
                        "sortOrder": "ASCENDING",
                    },
                    {
                        "sourceColumnOffset": self._get_column_index("Завершена"),
                        "showTotals": False,
                        "sortOrder": "ASCENDING",
                    },
                    {
                        "sourceColumnOffset": self._get_column_index("PM Lead"),
                        "showTotals": False,
                        "sortOrder": "ASCENDING",
                    },
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
                    {
                        "sourceColumnOffset": self._get_column_index(
                            "Discovery backlog (дни)"
                        ),
                        "summarizeFunction": "AVERAGE",
                        "name": "Discovery backlog Mean",
                    },
                    {
                        "sourceColumnOffset": self._get_column_index(
                            "Готова к разработке (дни)"
                        ),
                        "summarizeFunction": "AVERAGE",
                        "name": "Готова к разработке Mean",
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
                    {
                        "sourceColumnOffset": self._get_column_index("DevLT (дни)"),
                        "summarizeFunction": "AVERAGE",
                        "name": "DevLT Mean",
                    },
                    {
                        "sourceColumnOffset": self._get_column_index("DevLT (дни)"),
                        "summarizeFunction": "MAX",
                        "name": "DevLT Max",
                    },
                    {
                        "sourceColumnOffset": self._get_column_index(
                            "Discovery backlog (дни)"
                        ),
                        "summarizeFunction": "AVERAGE",
                        "name": "Discovery backlog Mean",
                    },
                    {
                        "sourceColumnOffset": self._get_column_index(
                            "Готова к разработке (дни)"
                        ),
                        "summarizeFunction": "AVERAGE",
                        "name": "Готова к разработке Mean",
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

    def _index_to_column_letter(self, index: int) -> str:
        """
        Convert 0-based column index to Google Sheets column letter (A-Z, AA-ZZ, ...).

        Args:
            index: 0-based column index

        Returns:
            Column letter (e.g., "A", "B", "AA", "AB")
        """
        result = ""
        index += 1  # Convert to 1-based
        while index > 0:
            index -= 1
            result = chr(ord("A") + (index % 26)) + result
            index //= 26
        return result

    def _get_column_index(self, column_name: str) -> int:
        """
        Get column index for a given column name.

        Args:
            column_name: Name of the column

        Returns:
            Column index (0-based)
        """
        # Use TTMDetailsColumns as single source of truth
        alias_mapping = {
            "DevLT (дни)": "DevLT",
        }

        # Handle aliases
        if column_name in alias_mapping:
            column_name = alias_mapping[column_name]

        try:
            return TTMDetailsColumns.get_column_index(column_name)
        except ValueError:
            # Fallback to 0 for unknown columns (backward compatibility)
            logger.warning(
                f"Column '{column_name}' not found in TTM Details structure, using index 0"
            )
            return 0

    def _calculate_pivot_table_width(self, pivot_type: str) -> int:
        """
        Calculate the width (number of columns) of a pivot table.

        Args:
            pivot_type: Type of pivot ("ttd" or "ttm")

        Returns:
            Number of columns in the pivot table
        """
        # Base: 5 row groupings (Разработка, Завершена, PM Lead, Команда, Квартал)
        base_groupings = 5

        if pivot_type == "ttd":
            # TTD Pivot: 5 row groupings + 6 value columns
            return base_groupings + 6
        elif pivot_type == "ttm":
            # TTM Pivot: 5 row groupings + 10 value columns
            return base_groupings + 10
        else:
            logger.warning(f"Unknown pivot type: {pivot_type}, defaulting to TTD width")
            return base_groupings + 6

    def _add_percentile_statistics(
        self,
        sheet_id: int,
        sheet_name: str,
        source_sheet_name: str,
        pivot_type: str,
    ) -> bool:
        """
        Add percentile statistics next to pivot table.

        Args:
            sheet_id: ID of the sheet with pivot table
            sheet_name: Name of the sheet with pivot table
            source_sheet_name: Name of the source sheet with data
            pivot_type: Type of pivot ("ttd" or "ttm")

        Returns:
            True if successful, False otherwise
        """
        try:
            # Calculate pivot table width
            pivot_table_width = self._calculate_pivot_table_width(pivot_type)

            # Calculate start column index (end of pivot table + 2 columns)
            start_column_index = pivot_table_width + 2
            start_column_letter = self._index_to_column_letter(start_column_index)
            end_column_letter = self._index_to_column_letter(start_column_index + 2)

            # Get column letters for metrics using TTMDetailsColumns indices
            ttm_column_index = TTMDetailsColumns.get_column_index("TTM")
            tail_column_index = TTMDetailsColumns.get_column_index("Tail")
            devlt_column_index = TTMDetailsColumns.get_column_index("DevLT")
            ttd_column_index = TTMDetailsColumns.get_column_index("TTD")

            ttm_column_letter = self._index_to_column_letter(ttm_column_index)
            tail_column_letter = self._index_to_column_letter(tail_column_index)
            devlt_column_letter = self._index_to_column_letter(devlt_column_index)
            ttd_column_letter = self._index_to_column_letter(ttd_column_index)

            # Prepare data based on pivot type
            if pivot_type == "ttm":
                # TTM Pivot: 6 rows, 3 columns
                data = [
                    ["ТТМ, 50 перц.", "ТТМ, 85 перц. ", "TTM, порог"],
                    [
                        f"=PERCENTILE('{source_sheet_name}'!{ttm_column_letter}:{ttm_column_letter};0,5)",
                        f"=PERCENTILE('{source_sheet_name}'!{ttm_column_letter}:{ttm_column_letter};0,85)",
                        180,
                    ],
                    ["Tail, 50 перц.", "Tail, 85 перц. ", "Tail, порог"],
                    [
                        f"=PERCENTILE('{source_sheet_name}'!{tail_column_letter}:{tail_column_letter};0,5)",
                        f"=PERCENTILE('{source_sheet_name}'!{tail_column_letter}:{tail_column_letter};0,85)",
                        60,
                    ],
                    ["DevLT, 50 perc", "DevLT, 85 perc", "DevLT, порог"],
                    [
                        f"=PERCENTILE('{source_sheet_name}'!{devlt_column_letter}:{devlt_column_letter};0,5)",
                        f"=PERCENTILE('{source_sheet_name}'!{devlt_column_letter}:{devlt_column_letter};0,85)",
                        60,
                    ],
                ]
                range_name = f"{sheet_name}!{start_column_letter}2:{end_column_letter}7"
            elif pivot_type == "ttd":
                # TTD Pivot: 2 rows, 3 columns
                data = [
                    ["ТТD, 50 перц.", "ТТD, 85 перц. ", "TTD, порог"],
                    [
                        f"=PERCENTILE('{source_sheet_name}'!{ttd_column_letter}:{ttd_column_letter};0,5)",
                        f"=PERCENTILE('{source_sheet_name}'!{ttd_column_letter}:{ttd_column_letter};0,85)",
                        60,
                    ],
                ]
                range_name = f"{sheet_name}!{start_column_letter}2:{end_column_letter}3"
            else:
                logger.error(f"Unknown pivot type: {pivot_type}")
                return False

            # Write data to sheet
            body = {"values": data}
            self.service.spreadsheets().values().update(
                spreadsheetId=self.document_id,
                range=range_name,
                valueInputOption="USER_ENTERED",  # Use USER_ENTERED to process formulas
                body=body,
            ).execute()

            logger.info(
                f"Successfully added percentile statistics to {sheet_name} at {range_name}"
            )

            # Apply formatting
            self._apply_percentile_statistics_formatting(
                sheet_id=sheet_id,
                start_column_index=start_column_index,
                pivot_type=pivot_type,
            )

            return True

        except Exception as e:
            logger.error(f"Failed to add percentile statistics to {sheet_name}: {e}")
            return False

    def _apply_percentile_statistics_formatting(
        self, sheet_id: int, start_column_index: int, pivot_type: str
    ) -> bool:
        """
        Apply formatting to percentile statistics (bold headers, orange threshold values).

        Args:
            sheet_id: ID of the sheet with pivot table
            start_column_index: Starting column index for statistics (0-based)
            pivot_type: Type of pivot ("ttd" or "ttm")

        Returns:
            True if successful, False otherwise
        """
        try:
            requests = []

            if pivot_type == "ttm":
                # TTM Pivot: bold headers in rows 2, 4, 6 (0-based: 1, 3, 5)
                # Orange thresholds in column 3 (start_column_index + 2) of rows 3, 5, 7 (0-based: 2, 4, 6)
                header_rows = [1, 3, 5]  # Rows 2, 4, 6 (0-based)
                threshold_rows = [2, 4, 6]  # Rows 3, 5, 7 (0-based)
                threshold_column = start_column_index + 2  # Third column (0-based)

                # Apply bold formatting to header rows (all 3 columns)
                for row_index in header_rows:
                    requests.append(
                        {
                            "repeatCell": {
                                "range": {
                                    "sheetId": sheet_id,
                                    "startRowIndex": row_index,
                                    "endRowIndex": row_index + 1,
                                    "startColumnIndex": start_column_index,
                                    "endColumnIndex": start_column_index + 3,
                                },
                                "cell": {
                                    "userEnteredFormat": {
                                        "textFormat": {"bold": True},
                                    }
                                },
                                "fields": "userEnteredFormat.textFormat.bold",
                            }
                        }
                    )

                # Apply orange background to threshold values
                for row_index in threshold_rows:
                    requests.append(
                        {
                            "repeatCell": {
                                "range": {
                                    "sheetId": sheet_id,
                                    "startRowIndex": row_index,
                                    "endRowIndex": row_index + 1,
                                    "startColumnIndex": threshold_column,
                                    "endColumnIndex": threshold_column + 1,
                                },
                                "cell": {
                                    "userEnteredFormat": {
                                        "backgroundColor": {
                                            "red": 1.0,
                                            "green": 0.647,
                                            "blue": 0.0,
                                        }
                                    }
                                },
                                "fields": "userEnteredFormat.backgroundColor",
                            }
                        }
                    )

            elif pivot_type == "ttd":
                # TTD Pivot: bold header in row 2 (0-based: 1)
                # Orange threshold in column 3 (start_column_index + 2) of row 3 (0-based: 2)
                header_row = 1  # Row 2 (0-based)
                threshold_row = 2  # Row 3 (0-based)
                threshold_column = start_column_index + 2  # Third column (0-based)

                # Apply bold formatting to header row (all 3 columns)
                requests.append(
                    {
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": header_row,
                                "endRowIndex": header_row + 1,
                                "startColumnIndex": start_column_index,
                                "endColumnIndex": start_column_index + 3,
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "textFormat": {"bold": True},
                                }
                            },
                            "fields": "userEnteredFormat.textFormat.bold",
                        }
                    }
                )

                # Apply orange background to threshold value
                requests.append(
                    {
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": threshold_row,
                                "endRowIndex": threshold_row + 1,
                                "startColumnIndex": threshold_column,
                                "endColumnIndex": threshold_column + 1,
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "backgroundColor": {
                                        "red": 1.0,
                                        "green": 0.647,
                                        "blue": 0.0,
                                    }
                                }
                            },
                            "fields": "userEnteredFormat.backgroundColor",
                        }
                    }
                )

            else:
                logger.error(f"Unknown pivot type: {pivot_type}")
                return False

            # Apply formatting via batchUpdate
            if requests:
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.document_id, body={"requests": requests}
                ).execute()

                logger.info(
                    f"Successfully applied formatting to percentile statistics (pivot_type={pivot_type})"
                )

            return True

        except Exception as e:
            logger.error(f"Failed to apply formatting to percentile statistics: {e}")
            return False

    def _apply_conditional_formatting_to_details(
        self, sheet_id: int, sheet_name: str, num_rows: int
    ) -> bool:
        """
        Apply conditional formatting to Details sheet to highlight cells exceeding thresholds.

        Args:
            sheet_id: ID of the sheet
            sheet_name: Name of the sheet
            num_rows: Number of data rows (excluding header)

        Returns:
            True if successful, False otherwise
        """
        try:
            requests = []

            # Define columns and thresholds
            formatting_rules = [
                {
                    "column_index": TTMDetailsColumns.get_column_index("TTM"),
                    "threshold": 180,
                },
                {
                    "column_index": TTMDetailsColumns.get_column_index("Tail"),
                    "threshold": 60,
                },
                {
                    "column_index": TTMDetailsColumns.get_column_index("DevLT"),
                    "threshold": 60,
                },
                {
                    "column_index": TTMDetailsColumns.get_column_index("TTD"),
                    "threshold": 60,
                },
            ]

            # Create conditional formatting rule for each column
            for rule_index, rule_config in enumerate(formatting_rules):
                requests.append(
                    {
                        "addConditionalFormatRule": {
                            "rule": {
                                "ranges": [
                                    {
                                        "sheetId": sheet_id,
                                        "startRowIndex": 1,  # Skip header row
                                        "endRowIndex": num_rows + 1,
                                        "startColumnIndex": rule_config["column_index"],
                                        "endColumnIndex": rule_config["column_index"]
                                        + 1,
                                    }
                                ],
                                "booleanRule": {
                                    "condition": {
                                        "type": "NUMBER_GREATER",
                                        "values": [
                                            {
                                                "userEnteredValue": str(
                                                    rule_config["threshold"]
                                                )
                                            }
                                        ],
                                    },
                                    "format": {
                                        "backgroundColor": {
                                            "red": 1.0,
                                            "green": 0.647,
                                            "blue": 0.0,
                                        }
                                    },
                                },
                            },
                            "index": rule_index,
                        }
                    }
                )

            # Apply conditional formatting via batchUpdate
            if requests:
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.document_id, body={"requests": requests}
                ).execute()

                logger.info(
                    f"Successfully applied conditional formatting to {sheet_name}"
                )

            return True

        except Exception as e:
            logger.error(f"Failed to apply conditional formatting to {sheet_name}: {e}")
            return False

    def _apply_conditional_formatting_to_pivot(
        self, sheet_id: int, sheet_name: str, pivot_type: str, num_rows: int
    ) -> bool:
        """
        Apply conditional formatting to Pivot sheet to highlight cells exceeding thresholds.

        Args:
            sheet_id: ID of the sheet
            sheet_name: Name of the sheet
            pivot_type: Type of pivot ("ttd" or "ttm")
            num_rows: Number of data rows (excluding header)

        Returns:
            True if successful, False otherwise
        """
        try:
            requests = []

            # Define columns and thresholds based on pivot type
            if pivot_type == "ttm":
                # TTM Pivot columns:
                # Column 5: TTM Mean (threshold: > 180)
                # Column 6: TTM Max (threshold: > 180)
                # Column 9: Tail Mean (threshold: > 60)
                # Column 10: Tail Max (threshold: > 60)
                # Column 11: DevLT Mean (threshold: > 60)
                # Column 12: DevLT Max (threshold: > 60)
                formatting_rules = [
                    {"column_index": 5, "threshold": 180},  # TTM Mean
                    {"column_index": 6, "threshold": 180},  # TTM Max
                    {"column_index": 9, "threshold": 60},  # Tail Mean
                    {"column_index": 10, "threshold": 60},  # Tail Max
                    {"column_index": 11, "threshold": 60},  # DevLT Mean
                    {"column_index": 12, "threshold": 60},  # DevLT Max
                ]
            elif pivot_type == "ttd":
                # TTD Pivot columns:
                # Column 5: TTD Mean (threshold: > 60)
                # Column 6: TTD Max (threshold: > 60)
                formatting_rules = [
                    {"column_index": 5, "threshold": 60},  # TTD Mean
                    {"column_index": 6, "threshold": 60},  # TTD Max
                ]
            else:
                logger.error(f"Unknown pivot type: {pivot_type}")
                return False

            # Create conditional formatting rule for each column
            for rule_index, rule_config in enumerate(formatting_rules):
                requests.append(
                    {
                        "addConditionalFormatRule": {
                            "rule": {
                                "ranges": [
                                    {
                                        "sheetId": sheet_id,
                                        "startRowIndex": 1,  # Skip header row
                                        "endRowIndex": num_rows + 1,
                                        "startColumnIndex": rule_config["column_index"],
                                        "endColumnIndex": rule_config["column_index"]
                                        + 1,
                                    }
                                ],
                                "booleanRule": {
                                    "condition": {
                                        "type": "NUMBER_GREATER",
                                        "values": [
                                            {
                                                "userEnteredValue": str(
                                                    rule_config["threshold"]
                                                )
                                            }
                                        ],
                                    },
                                    "format": {
                                        "backgroundColor": {
                                            "red": 1.0,
                                            "green": 0.647,
                                            "blue": 0.0,
                                        }
                                    },
                                },
                            },
                            "index": rule_index,
                        }
                    }
                )

            # Apply conditional formatting via batchUpdate
            if requests:
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.document_id, body={"requests": requests}
                ).execute()

                logger.info(
                    f"Successfully applied conditional formatting to {sheet_name} (pivot_type={pivot_type})"
                )

            return True

        except Exception as e:
            logger.error(f"Failed to apply conditional formatting to {sheet_name}: {e}")
            return False

    def _freeze_first_row(self, sheet_id: int, sheet_name: str) -> bool:
        """
        Freeze the first row (header) in the sheet.

        Args:
            sheet_id: ID of the sheet
            sheet_name: Name of the sheet

        Returns:
            True if successful, False otherwise
        """
        try:
            request_body = {
                "requests": [
                    {
                        "updateSheetProperties": {
                            "properties": {
                                "sheetId": sheet_id,
                                "gridProperties": {"frozenRowCount": 1},
                            },
                            "fields": "gridProperties.frozenRowCount",
                        }
                    }
                ]
            }

            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.document_id, body=request_body
            ).execute()

            logger.info(f"Successfully froze first row in {sheet_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to freeze first row in {sheet_name}: {e}")
            return False

    def _resize_name_column(self, sheet_id: int, sheet_name: str) -> bool:
        """
        Resize 'Название' column to fixed width (500 pixels).

        Args:
            sheet_id: ID of the sheet
            sheet_name: Name of the sheet

        Returns:
            True if successful, False otherwise
        """
        try:
            # Use fixed width of 500 pixels
            name_column_index = TTMDetailsColumns.get_column_index("Название")
            fixed_width = 500

            request_body = {
                "requests": [
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": name_column_index,
                                "endIndex": name_column_index + 1,
                            },
                            "properties": {"pixelSize": fixed_width},
                            "fields": "pixelSize",
                        }
                    }
                ]
            }

            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.document_id, body=request_body
            ).execute()

            logger.info(
                f"Successfully resized 'Название' column to {fixed_width}px in {sheet_name}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to resize 'Название' column in {sheet_name}: {e}")
            return False

    def _add_column_notes_to_details(
        self, sheet_id: int, sheet_name: str, column_names: List[str]
    ) -> bool:
        """
        Add notes to column headers in Details sheet.

        Args:
            sheet_id: ID of the sheet
            sheet_name: Name of the sheet
            column_names: List of column names (headers)

        Returns:
            True if successful, False otherwise
        """
        try:
            requests = []

            for column_index, column_name in enumerate(column_names):
                # Get note for this column if available
                note_text = COLUMN_NOTES.get(column_name)
                if not note_text:
                    continue

                requests.append(
                    {
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": 0,  # Header row (0-based)
                                "endRowIndex": 1,
                                "startColumnIndex": column_index,
                                "endColumnIndex": column_index + 1,
                            },
                            "cell": {"note": note_text},
                            "fields": "note",
                        }
                    }
                )

            # Apply notes via batchUpdate
            if requests:
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.document_id, body={"requests": requests}
                ).execute()

                logger.info(
                    f"Successfully added notes to {len(requests)} column headers in {sheet_name}"
                )

            return True

        except Exception as e:
            logger.error(f"Failed to add column notes to {sheet_name}: {e}")
            return False

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
                "DevLT (дни)",
            ]
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            return df

        except Exception as e:
            logger.error(f"Failed to read data from sheet: {e}")
            return None

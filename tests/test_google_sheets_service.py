"""Unit tests for Google Sheets service."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from radiator.services.google_sheets_service import GoogleSheetsService


class TestGoogleSheetsService:
    """Test cases for GoogleSheetsService."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock GoogleSheetsService instance."""
        with patch(
            "radiator.services.google_sheets_service.service_account.Credentials.from_service_account_file"
        ), patch("radiator.services.google_sheets_service.build"):
            service = GoogleSheetsService(
                credentials_path="test_credentials.json",
                document_id="test_document_id",
                sheet_prefix="Test_",
            )
            service.service = Mock()
            return service

    def test_sanitize_sheet_name_basic(self, mock_service):
        """Test basic sheet name sanitization."""
        result = mock_service._sanitize_sheet_name("test_file.csv")
        assert result == "test_file"

    def test_sanitize_sheet_name_invalid_chars(self, mock_service):
        """Test sheet name sanitization with invalid characters."""
        result = mock_service._sanitize_sheet_name("test[file]*with?invalid/chars.csv")
        assert (
            result == "chars"
        )  # After removing invalid chars and multiple underscores

    def test_sanitize_sheet_name_long(self, mock_service):
        """Test sheet name sanitization with long name."""
        long_name = "a" * 150 + ".csv"
        result = mock_service._sanitize_sheet_name(long_name)
        assert len(result) <= 100
        assert result.endswith("a")

    def test_sanitize_sheet_name_empty(self, mock_service):
        """Test sheet name sanitization with empty name."""
        result = mock_service._sanitize_sheet_name("...csv")
        assert result == ".."  # After removing dots, only dots remain

    def test_prepare_data_for_sheets(self, mock_service):
        """Test data preparation for Google Sheets."""
        df = pd.DataFrame(
            {
                "Name": ["Alice", "Bob", None],
                "Age": [25, 30, 35],
                "City": ["New York", "London", "Paris"],
            }
        )

        result = mock_service._prepare_data_for_sheets(df)

        # Check structure
        assert len(result) == 4  # 1 header + 3 data rows
        assert result[0] == ["Name", "Age", "City"]  # Headers
        assert result[1] == ["Alice", 25, "New York"]  # First row
        assert result[2] == ["Bob", 30, "London"]  # Second row
        assert result[3] == ["", 35, "Paris"]  # Third row with NaN replaced

    def test_prepare_data_for_sheets_with_nan(self, mock_service):
        """Test data preparation with NaN values."""
        df = pd.DataFrame({"A": [1, None, 3], "B": [None, "test", None]})

        result = mock_service._prepare_data_for_sheets(df)

        # Check that NaN values are replaced with empty strings
        assert result[1] == [1, ""]  # First data row
        assert result[2] == ["", "test"]  # Second data row
        assert result[3] == [3, ""]  # Third data row

    @patch("radiator.services.google_sheets_service.pd.read_csv")
    def test_read_csv_file_success(self, mock_read_csv, mock_service):
        """Test successful CSV file reading."""
        mock_df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        mock_read_csv.return_value = mock_df

        result = mock_service._read_csv_file(Path("test.csv"))

        assert result is not None
        assert len(result) == 2
        mock_read_csv.assert_called_once()

    @patch("radiator.services.google_sheets_service.pd.read_csv")
    def test_read_csv_file_encoding_fallback(self, mock_read_csv, mock_service):
        """Test CSV file reading with encoding fallback."""
        # First call fails with UnicodeDecodeError, second succeeds
        mock_read_csv.side_effect = [
            UnicodeDecodeError("utf-8", b"", 0, 1, "invalid start byte"),
            pd.DataFrame({"A": [1, 2]}),
        ]

        result = mock_service._read_csv_file(Path("test.csv"))

        assert result is not None
        assert mock_read_csv.call_count == 2

    def test_get_sheet_id_success(self, mock_service):
        """Test successful sheet ID retrieval."""
        mock_service.service.spreadsheets().get().execute.return_value = {
            "sheets": [
                {"properties": {"title": "Sheet1", "sheetId": 123}},
                {"properties": {"title": "Sheet2", "sheetId": 456}},
            ]
        }

        result = mock_service._get_sheet_id("Sheet1")
        assert result == 123

    def test_get_sheet_id_not_found(self, mock_service):
        """Test sheet ID retrieval when sheet not found."""
        mock_service.service.spreadsheets().get().execute.return_value = {
            "sheets": [{"properties": {"title": "Sheet1", "sheetId": 123}}]
        }

        result = mock_service._get_sheet_id("NonExistentSheet")
        assert result is None

    def test_auto_resize_columns(self, mock_service):
        """Test auto-resize columns functionality."""
        mock_service._get_sheet_id = Mock(return_value=123)
        mock_service.service.spreadsheets().batchUpdate().execute.return_value = {}

        mock_service._auto_resize_columns("TestSheet", 3)

        # Verify batchUpdate was called (it's called twice: once for the method, once for execute)
        assert mock_service.service.spreadsheets().batchUpdate.call_count >= 1

    def test_add_filter_to_all_data(self, mock_service):
        """Test adding filter to all data."""
        mock_service._get_sheet_id = Mock(return_value=123)
        mock_service.service.spreadsheets().batchUpdate().execute.return_value = {}

        mock_service._add_filter_to_all_data("TestSheet", 3, 5)

        # Verify batchUpdate was called (it's called twice: once for the method, once for execute)
        assert mock_service.service.spreadsheets().batchUpdate.call_count >= 1

        # Check the request structure
        call_args = mock_service.service.spreadsheets().batchUpdate.call_args
        request_body = call_args[1]["body"]

        assert "requests" in request_body
        assert len(request_body["requests"]) == 1
        assert "setBasicFilter" in request_body["requests"][0]

        filter_range = request_body["requests"][0]["setBasicFilter"]["filter"]["range"]
        assert filter_range["sheetId"] == 123
        assert filter_range["startRowIndex"] == 0
        assert filter_range["endRowIndex"] == 5
        assert filter_range["startColumnIndex"] == 0
        assert filter_range["endColumnIndex"] == 3

    def test_test_connection_success(self, mock_service):
        """Test successful connection test."""
        mock_service.service.spreadsheets().get().execute.return_value = {
            "properties": {"title": "Test Spreadsheet"}
        }

        result = mock_service.test_connection()
        assert result is True

    def test_test_connection_failure(self, mock_service):
        """Test connection test failure."""
        mock_service.service.spreadsheets().get().execute.side_effect = Exception(
            "Connection failed"
        )

        result = mock_service.test_connection()
        assert result is False

    def test_get_column_index_development(self, mock_service):
        """Test that _get_column_index returns correct index for 'Разработка' column."""
        result = mock_service._get_column_index("Разработка")
        assert result == 20

    def test_build_pivot_table_request_ttd_has_development_first(self, mock_service):
        """Test that TTD pivot table has 'Разработка' as first row grouping."""
        source_sheet_id = 100
        target_sheet_id = 200

        request = mock_service._build_pivot_table_request(
            source_sheet_id, target_sheet_id, "ttd"
        )

        assert request is not None
        pivot_table = request["updateCells"]["rows"][0]["values"][0]["pivotTable"]

        # Check rows structure
        rows = pivot_table["rows"]
        assert len(rows) == 3

        # First row should be "Разработка" (index 20)
        assert rows[0]["sourceColumnOffset"] == 20

        # Second row should be "Команда" (index 3)
        assert rows[1]["sourceColumnOffset"] == 3

        # Third row should be "Квартал" (index 4)
        assert rows[2]["sourceColumnOffset"] == 4

    def test_build_pivot_table_request_ttm_has_development_first(self, mock_service):
        """Test that TTM pivot table has 'Разработка' as first row grouping."""
        source_sheet_id = 100
        target_sheet_id = 200

        request = mock_service._build_pivot_table_request(
            source_sheet_id, target_sheet_id, "ttm"
        )

        assert request is not None
        pivot_table = request["updateCells"]["rows"][0]["values"][0]["pivotTable"]

        # Check rows structure
        rows = pivot_table["rows"]
        assert len(rows) == 3

        # First row should be "Разработка" (index 20)
        assert rows[0]["sourceColumnOffset"] == 20

        # Second row should be "Команда" (index 3)
        assert rows[1]["sourceColumnOffset"] == 3

        # Third row should be "Квартал" (index 4)
        assert rows[2]["sourceColumnOffset"] == 4

    def test_build_pivot_table_request_end_column_index(self, mock_service):
        """Test that endColumnIndex is updated to 21."""
        source_sheet_id = 100
        target_sheet_id = 200

        request = mock_service._build_pivot_table_request(
            source_sheet_id, target_sheet_id, "ttd"
        )

        assert request is not None
        pivot_table = request["updateCells"]["rows"][0]["values"][0]["pivotTable"]

        # Check endColumnIndex
        assert pivot_table["source"]["endColumnIndex"] == 21

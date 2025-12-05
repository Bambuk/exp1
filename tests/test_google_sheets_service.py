"""Unit tests for Google Sheets service."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from radiator.commands.models.ttm_details_columns import TTMDetailsColumns
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
        expected = TTMDetailsColumns.get_column_index("Разработка")
        assert result == expected

    def test_get_column_index_finished(self, mock_service):
        """Test that _get_column_index returns correct index for 'Завершена' column."""
        result = mock_service._get_column_index("Завершена")
        expected = TTMDetailsColumns.get_column_index("Завершена")
        assert result == expected

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
        assert len(rows) == 5, "Expected 5 rows in grouping"

        # First row should be "Разработка"
        assert rows[0]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "Разработка"
        )

        # Second row should be "Завершена"
        assert rows[1]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "Завершена"
        )

        # Third row should be "PM Lead"
        assert rows[2]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "PM Lead"
        )

        # Fourth row should be "Команда"
        assert rows[3]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "Команда"
        )

        # Fifth row should be "Квартал"
        assert rows[4]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "Квартал"
        )

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
        assert len(rows) == 5, "Expected 5 rows in grouping"

        # First row should be "Разработка"
        assert rows[0]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "Разработка"
        )

        # Second row should be "Завершена"
        assert rows[1]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "Завершена"
        )

        # Third row should be "PM Lead"
        assert rows[2]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "PM Lead"
        )

        # Fourth row should be "Команда"
        assert rows[3]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "Команда"
        )

        # Fifth row should be "Квартал"
        assert rows[4]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "Квартал"
        )

    def test_build_pivot_table_request_end_column_index(self, mock_service):
        """Test that endColumnIndex matches TTMDetailsColumns.get_column_count()."""
        source_sheet_id = 100
        target_sheet_id = 200

        request = mock_service._build_pivot_table_request(
            source_sheet_id, target_sheet_id, "ttd"
        )

        assert request is not None
        pivot_table = request["updateCells"]["rows"][0]["values"][0]["pivotTable"]

        # Check endColumnIndex matches single source of truth
        expected_count = TTMDetailsColumns.get_column_count()
        assert (
            pivot_table["source"]["endColumnIndex"] == expected_count
        ), f"endColumnIndex should equal TTMDetailsColumns.get_column_count(). Expected {expected_count}, got {pivot_table['source']['endColumnIndex']}"

    def test_index_to_column_letter_basic(self, mock_service):
        """Test basic column letter conversion (A-Z)."""
        assert mock_service._index_to_column_letter(0) == "A"
        assert mock_service._index_to_column_letter(1) == "B"
        assert mock_service._index_to_column_letter(25) == "Z"

    def test_index_to_column_letter_extended(self, mock_service):
        """Test extended column letter conversion (AA-ZZ)."""
        assert mock_service._index_to_column_letter(26) == "AA"
        assert mock_service._index_to_column_letter(27) == "AB"
        assert mock_service._index_to_column_letter(51) == "AZ"
        assert mock_service._index_to_column_letter(52) == "BA"

    def test_index_to_column_letter_specific(self, mock_service):
        """Test specific column indices used in the codebase."""
        # TTM: индекс 6 → колонка G (A=0, B=1, C=2, D=3, E=4, F=5, G=6)
        assert mock_service._index_to_column_letter(6) == "G"
        # Tail: индекс 8 → колонка I (A=0, ..., H=7, I=8)
        assert mock_service._index_to_column_letter(8) == "I"
        # DevLT: индекс 9 → колонка J
        assert mock_service._index_to_column_letter(9) == "J"
        # TTD: индекс 10 → колонка K
        assert mock_service._index_to_column_letter(10) == "K"
        # TTM Pivot start column: 15 → P (A=0, ..., O=14, P=15)
        assert mock_service._index_to_column_letter(15) == "P"
        # TTD Pivot start column: 11 → L (A=0, ..., K=10, L=11)
        assert mock_service._index_to_column_letter(11) == "L"

    def test_get_sheet_name_by_id_success(self, mock_service):
        """Test successful sheet name retrieval by ID."""
        mock_service.service.spreadsheets().get().execute.return_value = {
            "sheets": [
                {"properties": {"title": "Sheet1", "sheetId": 123}},
                {"properties": {"title": "Sheet2", "sheetId": 456}},
            ]
        }

        result = mock_service._get_sheet_name_by_id(123)
        assert result == "Sheet1"

        result = mock_service._get_sheet_name_by_id(456)
        assert result == "Sheet2"

    def test_get_sheet_name_by_id_not_found(self, mock_service):
        """Test sheet name retrieval when sheet ID not found."""
        mock_service.service.spreadsheets().get().execute.return_value = {
            "sheets": [{"properties": {"title": "Sheet1", "sheetId": 123}}]
        }

        result = mock_service._get_sheet_name_by_id(999)
        assert result is None

    def test_calculate_pivot_table_width_ttd(self, mock_service):
        """Test calculation of TTD pivot table width."""
        width = mock_service._calculate_pivot_table_width("ttd")
        # TTD Pivot: 5 row groupings + 4 value columns = 9 колонок
        assert width == 9

    def test_calculate_pivot_table_width_ttm(self, mock_service):
        """Test calculation of TTM pivot table width."""
        width = mock_service._calculate_pivot_table_width("ttm")
        # TTM Pivot: 5 row groupings + 8 value columns = 13 колонок
        assert width == 13

    def test_add_percentile_statistics_ttm_pivot(self, mock_service):
        """Test adding percentile statistics for TTM Pivot."""
        mock_service._get_sheet_id = Mock(return_value=200)
        mock_service._calculate_pivot_table_width = Mock(return_value=13)
        # Mock _index_to_column_letter for different calls:
        # - 15 for start position (P)
        # - 6 for TTM (G), 8 for Tail (I), 9 for DevLT (J)
        mock_service._index_to_column_letter = Mock(
            side_effect=lambda x: {15: "P", 17: "R", 6: "G", 8: "I", 9: "J"}.get(
                x, chr(ord("A") + x)
            )
        )
        mock_service.service.spreadsheets().values().update().execute.return_value = {}

        mock_service._add_percentile_statistics(
            sheet_id=200,
            sheet_name="TTM Pivot",
            source_sheet_name="Report_20240101",
            pivot_type="ttm",
        )

        # Verify that values().update() was called with actual arguments
        # Note: update() is called twice - once for mock setup, once for actual call
        calls = mock_service.service.spreadsheets().values().update.call_args_list
        # Find the call with actual arguments (not just call())
        call_args = None
        for call in calls:
            if call[1] or call[0]:  # Has keyword args or positional args
                call_args = call
                break
        assert call_args is not None, "values().update() was not called with arguments"

        # Check range
        assert call_args[1]["range"] == "TTM Pivot!P2:R7"
        # Check valueInputOption
        assert call_args[1]["valueInputOption"] == "USER_ENTERED"

        # Check data structure
        body = call_args[1]["body"]
        values = body["values"]
        assert len(values) == 6  # 6 rows

        # Check first row (headers)
        assert values[0] == ["ТТМ, 50 перц.", "ТТМ, 85 перц. ", "TTM, порог"]
        # Check second row (formulas) - TTM is at index 6, which is column G
        assert values[1][0] == "=PERCENTILE('Report_20240101'!G:G;0,5)"
        assert values[1][1] == "=PERCENTILE('Report_20240101'!G:G;0,85)"
        assert values[1][2] == 180

    def test_add_percentile_statistics_ttd_pivot(self, mock_service):
        """Test adding percentile statistics for TTD Pivot."""
        mock_service._get_sheet_id = Mock(return_value=200)
        mock_service._calculate_pivot_table_width = Mock(return_value=9)
        # Mock _index_to_column_letter for different calls:
        # - 11 for start position (L)
        # - 10 for TTD (K)
        mock_service._index_to_column_letter = Mock(
            side_effect=lambda x: {11: "L", 13: "N", 10: "K"}.get(x, chr(ord("A") + x))
        )
        mock_service.service.spreadsheets().values().update().execute.return_value = {}

        mock_service._add_percentile_statistics(
            sheet_id=200,
            sheet_name="TTD Pivot",
            source_sheet_name="Report_20240101",
            pivot_type="ttd",
        )

        # Verify that values().update() was called with actual arguments
        # Note: update() is called twice - once for mock setup, once for actual call
        calls = mock_service.service.spreadsheets().values().update.call_args_list
        # Find the call with actual arguments (not just call())
        call_args = None
        for call in calls:
            if call[1] or call[0]:  # Has keyword args or positional args
                call_args = call
                break
        assert call_args is not None, "values().update() was not called with arguments"

        # Check range
        assert call_args[1]["range"] == "TTD Pivot!L2:N3"
        # Check valueInputOption
        assert call_args[1]["valueInputOption"] == "USER_ENTERED"

        # Check data structure
        body = call_args[1]["body"]
        values = body["values"]
        assert len(values) == 2  # 2 rows

        # Check first row (headers)
        assert values[0] == ["ТТD, 50 перц.", "ТТD, 85 перц. ", "TTD, порог"]
        # Check second row (formulas) - TTD is at index 10, which is column K
        assert values[1][0] == "=PERCENTILE('Report_20240101'!K:K;0,5)"
        assert values[1][1] == "=PERCENTILE('Report_20240101'!K:K;0,85)"
        assert values[1][2] == 60

    def test_add_percentile_statistics_position_calculation(self, mock_service):
        """Test that position calculation is correct (end of pivot table + 2 columns)."""
        mock_service._get_sheet_id = Mock(return_value=200)
        mock_service._index_to_column_letter = Mock(
            side_effect=lambda x: chr(ord("A") + x)
        )
        mock_service.service.spreadsheets().values().update().execute.return_value = {}

        # Test TTM: width 13, start column should be 15 (P)
        mock_service._calculate_pivot_table_width = Mock(return_value=13)
        mock_service._add_percentile_statistics(
            sheet_id=200,
            sheet_name="TTM Pivot",
            source_sheet_name="Report",
            pivot_type="ttm",
        )
        # Verify _index_to_column_letter was called with 15
        mock_service._index_to_column_letter.assert_any_call(15)

        # Reset mock
        mock_service._index_to_column_letter.reset_mock()

        # Test TTD: width 9, start column should be 11 (L)
        mock_service._calculate_pivot_table_width = Mock(return_value=9)
        mock_service._add_percentile_statistics(
            sheet_id=200,
            sheet_name="TTD Pivot",
            source_sheet_name="Report",
            pivot_type="ttd",
        )
        # Verify _index_to_column_letter was called with 11
        mock_service._index_to_column_letter.assert_any_call(11)

    def test_add_percentile_statistics_formulas(self, mock_service):
        """Test that PERCENTILE formulas use correct source sheet name."""
        mock_service._get_sheet_id = Mock(return_value=200)
        mock_service._calculate_pivot_table_width = Mock(return_value=13)
        mock_service._index_to_column_letter = Mock(return_value="P")
        mock_service.service.spreadsheets().values().update().execute.return_value = {}

        source_sheet_name = "Report_20240101_120000"
        mock_service._add_percentile_statistics(
            sheet_id=200,
            sheet_name="TTM Pivot",
            source_sheet_name=source_sheet_name,
            pivot_type="ttm",
        )

        call_args = mock_service.service.spreadsheets().values().update.call_args
        body = call_args[1]["body"]
        values = body["values"]

        # Check that formulas contain source sheet name
        assert f"'{source_sheet_name}'" in values[1][0]  # TTM 50 percentile
        assert f"'{source_sheet_name}'" in values[1][1]  # TTM 85 percentile
        assert f"'{source_sheet_name}'" in values[3][0]  # Tail 50 percentile
        assert f"'{source_sheet_name}'" in values[5][0]  # DevLT 50 percentile

    def test_add_percentile_statistics_sheet_name_escaping(self, mock_service):
        """Test that sheet names with spaces are properly escaped in formulas."""
        mock_service._get_sheet_id = Mock(return_value=200)
        mock_service._calculate_pivot_table_width = Mock(return_value=13)
        mock_service._index_to_column_letter = Mock(return_value="P")
        mock_service.service.spreadsheets().values().update().execute.return_value = {}

        source_sheet_name = "Report With Spaces"
        mock_service._add_percentile_statistics(
            sheet_id=200,
            sheet_name="TTM Pivot",
            source_sheet_name=source_sheet_name,
            pivot_type="ttm",
        )

        call_args = mock_service.service.spreadsheets().values().update.call_args
        body = call_args[1]["body"]
        values = body["values"]

        # Check that formulas contain escaped sheet name
        assert f"'{source_sheet_name}'" in values[1][0]

    def test_add_percentile_statistics_dynamic_positioning(self, mock_service):
        """Test that position changes when pivot table width changes."""
        mock_service._get_sheet_id = Mock(return_value=200)
        mock_service._index_to_column_letter = Mock(
            side_effect=lambda x: chr(ord("A") + x)
        )
        mock_service.service.spreadsheets().values().update().execute.return_value = {}

        # Simulate wider pivot table (e.g., if columns were added)
        mock_service._calculate_pivot_table_width = Mock(return_value=15)
        mock_service._add_percentile_statistics(
            sheet_id=200,
            sheet_name="TTM Pivot",
            source_sheet_name="Report",
            pivot_type="ttm",
        )

        # Verify position shifted: 15 + 2 = 17
        mock_service._index_to_column_letter.assert_any_call(17)

    def test_create_pivot_table_with_percentile_statistics(self, mock_service):
        """Test full cycle of creating pivot table with percentile statistics."""
        # Mock sheet creation
        mock_service.service.spreadsheets().batchUpdate().execute.return_value = {
            "replies": [{"addSheet": {"properties": {"sheetId": 200}}}]
        }
        mock_service._get_sheet_id = Mock(return_value=100)  # Source sheet
        mock_service._calculate_pivot_table_width = Mock(return_value=13)
        mock_service._index_to_column_letter = Mock(return_value="P")
        mock_service.service.spreadsheets().values().update().execute.return_value = {}

        result = mock_service._create_google_pivot_table(
            document_id="test_doc",
            source_sheet_id=100,
            sheet_name="TTM Pivot",
            pivot_type="ttm",
            source_sheet_name="Report_20240101",
        )

        assert result == 200
        # Verify that percentile statistics were added
        mock_service.service.spreadsheets().values().update.assert_called()

    def test_create_pivot_tables_from_dataframe_with_source_sheet_name(
        self, mock_service
    ):
        """Test creating pivot tables with source sheet name provided."""
        mock_service._get_sheet_id = Mock(return_value=100)
        mock_service.service.spreadsheets().batchUpdate().execute.return_value = {
            "replies": [{"addSheet": {"properties": {"sheetId": 200}}}]
        }
        mock_service._calculate_pivot_table_width = Mock(return_value=13)
        mock_service._index_to_column_letter = Mock(return_value="P")
        mock_service.service.spreadsheets().values().update().execute.return_value = {}

        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        result = mock_service.create_pivot_tables_from_dataframe(
            details_data=df,
            document_id="test_doc",
            source_sheet_name="Report_20240101",
        )

        assert result["ttm_pivot"] == 200
        # Verify source_sheet_name was used
        mock_service._get_sheet_id.assert_called_with("Report_20240101")

    def test_create_pivot_tables_from_dataframe_without_source_sheet_name(
        self, mock_service
    ):
        """Test creating pivot tables with automatic source sheet name detection."""
        mock_service._get_source_sheet_id = Mock(return_value=100)
        mock_service._get_sheet_name_by_id = Mock(return_value="Report_20240101")
        mock_service.service.spreadsheets().batchUpdate().execute.return_value = {
            "replies": [{"addSheet": {"properties": {"sheetId": 200}}}]
        }
        mock_service._calculate_pivot_table_width = Mock(return_value=13)
        mock_service._index_to_column_letter = Mock(return_value="P")
        mock_service.service.spreadsheets().values().update().execute.return_value = {}

        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        result = mock_service.create_pivot_tables_from_dataframe(
            details_data=df,
            document_id="test_doc",
            source_sheet_name=None,
        )

        assert result["ttm_pivot"] == 200
        # Verify sheet name was retrieved by ID
        mock_service._get_sheet_name_by_id.assert_called()

    def test_apply_percentile_statistics_formatting_ttm_headers_bold(
        self, mock_service
    ):
        """Test that TTM Pivot headers are formatted with bold text."""
        mock_service.service.spreadsheets().batchUpdate().execute.return_value = {}

        mock_service._apply_percentile_statistics_formatting(
            sheet_id=200, start_column_index=15, pivot_type="ttm"
        )

        # Verify batchUpdate was called with actual arguments
        calls = mock_service.service.spreadsheets().batchUpdate.call_args_list
        call_args = None
        for call in calls:
            if call[1] or call[0]:  # Has keyword args or positional args
                call_args = call
                break
        assert call_args is not None, "batchUpdate() was not called with arguments"
        requests = call_args[1]["body"]["requests"]

        # Find requests for bold formatting (headers in rows 2, 4, 6)
        bold_requests = [
            req
            for req in requests
            if "repeatCell" in req
            and "textFormat" in req["repeatCell"]["cell"]["userEnteredFormat"]
            and req["repeatCell"]["cell"]["userEnteredFormat"]["textFormat"].get(
                "bold", False
            )
        ]

        # Should have 3 bold requests for headers (rows 2, 4, 6)
        assert len(bold_requests) == 3

        # Check that rows 2, 4, 6 are formatted
        bold_rows = [
            req["repeatCell"]["range"]["startRowIndex"] for req in bold_requests
        ]
        assert 1 in bold_rows  # Row 2 (0-based index 1)
        assert 3 in bold_rows  # Row 4 (0-based index 3)
        assert 5 in bold_rows  # Row 6 (0-based index 5)

    def test_apply_percentile_statistics_formatting_ttm_thresholds_orange(
        self, mock_service
    ):
        """Test that TTM Pivot threshold values have orange background."""
        mock_service.service.spreadsheets().batchUpdate().execute.return_value = {}

        mock_service._apply_percentile_statistics_formatting(
            sheet_id=200, start_column_index=15, pivot_type="ttm"
        )

        call_args = mock_service.service.spreadsheets().batchUpdate.call_args
        requests = call_args[1]["body"]["requests"]

        # Find requests for orange background (threshold column in rows 3, 5, 7)
        orange_requests = [
            req
            for req in requests
            if "repeatCell" in req
            and req["repeatCell"]["cell"]["userEnteredFormat"].get("backgroundColor")
        ]

        # Should have 3 orange requests for thresholds (rows 3, 5, 7, column 2)
        assert len(orange_requests) == 3

        # Check orange color (RGB: 255, 165, 0 = 1.0, 0.647, 0.0)
        for req in orange_requests:
            bg_color = req["repeatCell"]["cell"]["userEnteredFormat"]["backgroundColor"]
            assert bg_color["red"] == 1.0
            assert bg_color["green"] == 0.647
            assert bg_color["blue"] == 0.0

        # Check that rows 3, 5, 7 are formatted
        orange_rows = [
            req["repeatCell"]["range"]["startRowIndex"] for req in orange_requests
        ]
        assert 2 in orange_rows  # Row 3 (0-based index 2)
        assert 4 in orange_rows  # Row 5 (0-based index 4)
        assert 6 in orange_rows  # Row 7 (0-based index 6)

        # Check that column 2 (threshold column) is formatted
        for req in orange_requests:
            assert (
                req["repeatCell"]["range"]["startColumnIndex"] == 15 + 2
            )  # start_column_index + 2 (third column)

    def test_apply_percentile_statistics_formatting_ttd_headers_bold(
        self, mock_service
    ):
        """Test that TTD Pivot headers are formatted with bold text."""
        mock_service.service.spreadsheets().batchUpdate().execute.return_value = {}

        mock_service._apply_percentile_statistics_formatting(
            sheet_id=200, start_column_index=11, pivot_type="ttd"
        )

        call_args = mock_service.service.spreadsheets().batchUpdate.call_args
        requests = call_args[1]["body"]["requests"]

        # Find requests for bold formatting (header in row 2)
        bold_requests = [
            req
            for req in requests
            if "repeatCell" in req
            and "textFormat" in req["repeatCell"]["cell"]["userEnteredFormat"]
            and req["repeatCell"]["cell"]["userEnteredFormat"]["textFormat"].get(
                "bold", False
            )
        ]

        # Should have 1 bold request for header (row 2)
        assert len(bold_requests) == 1

        # Check that row 2 is formatted
        assert bold_requests[0]["repeatCell"]["range"]["startRowIndex"] == 1

    def test_apply_percentile_statistics_formatting_ttd_thresholds_orange(
        self, mock_service
    ):
        """Test that TTD Pivot threshold value has orange background."""
        mock_service.service.spreadsheets().batchUpdate().execute.return_value = {}

        mock_service._apply_percentile_statistics_formatting(
            sheet_id=200, start_column_index=11, pivot_type="ttd"
        )

        call_args = mock_service.service.spreadsheets().batchUpdate.call_args
        requests = call_args[1]["body"]["requests"]

        # Find requests for orange background (threshold column in row 3)
        orange_requests = [
            req
            for req in requests
            if "repeatCell" in req
            and req["repeatCell"]["cell"]["userEnteredFormat"].get("backgroundColor")
        ]

        # Should have 1 orange request for threshold (row 3, column 2)
        assert len(orange_requests) == 1

        # Check orange color
        bg_color = orange_requests[0]["repeatCell"]["cell"]["userEnteredFormat"][
            "backgroundColor"
        ]
        assert bg_color["red"] == 1.0
        assert bg_color["green"] == 0.647
        assert bg_color["blue"] == 0.0

        # Check that row 3 is formatted
        assert orange_requests[0]["repeatCell"]["range"]["startRowIndex"] == 2

        # Check that column 2 (threshold column) is formatted
        assert (
            orange_requests[0]["repeatCell"]["range"]["startColumnIndex"] == 11 + 2
        )  # start_column_index + 2

    def test_apply_percentile_statistics_formatting_api_calls(self, mock_service):
        """Test that formatting API calls are structured correctly."""
        mock_service.service.spreadsheets().batchUpdate().execute.return_value = {}

        mock_service._apply_percentile_statistics_formatting(
            sheet_id=200, start_column_index=15, pivot_type="ttm"
        )

        call_args = mock_service.service.spreadsheets().batchUpdate.call_args
        requests = call_args[1]["body"]["requests"]

        # Verify all requests have correct structure
        for req in requests:
            assert "repeatCell" in req
            assert "range" in req["repeatCell"]
            assert "cell" in req["repeatCell"]
            assert "userEnteredFormat" in req["repeatCell"]["cell"]
            assert "fields" in req["repeatCell"]

            # Verify range has sheetId
            assert req["repeatCell"]["range"]["sheetId"] == 200

    def test_add_percentile_statistics_includes_formatting(self, mock_service):
        """Test that formatting is applied when adding percentile statistics."""
        mock_service._get_sheet_id = Mock(return_value=200)
        mock_service._calculate_pivot_table_width = Mock(return_value=13)
        mock_service._index_to_column_letter = Mock(
            side_effect=lambda x: {
                15: "P",
                17: "R",
                6: "G",
                8: "I",
                9: "J",
            }.get(x, chr(ord("A") + x))
        )
        mock_service.service.spreadsheets().values().update().execute.return_value = {}
        mock_service.service.spreadsheets().batchUpdate().execute.return_value = {}

        mock_service._add_percentile_statistics(
            sheet_id=200,
            sheet_name="TTM Pivot",
            source_sheet_name="Report_20240101",
            pivot_type="ttm",
        )

        # Verify that formatting was called
        mock_service.service.spreadsheets().batchUpdate.assert_called()

    def test_apply_conditional_formatting_to_details_ttm(self, mock_service):
        """Test conditional formatting for TTM column (> 180)."""
        mock_service._get_sheet_id = Mock(return_value=100)
        mock_service.service.spreadsheets().batchUpdate().execute.return_value = {}

        mock_service._apply_conditional_formatting_to_details(
            sheet_id=100, sheet_name="Details", num_rows=10
        )

        # Verify batchUpdate was called
        calls = mock_service.service.spreadsheets().batchUpdate.call_args_list
        call_args = None
        for call in calls:
            if call[1] or call[0]:
                call_args = call
                break
        assert call_args is not None, "batchUpdate() was not called with arguments"

        requests = call_args[1]["body"]["requests"]

        # Find TTM rule (column index 6)
        ttm_rules = [
            req
            for req in requests
            if "addConditionalFormatRule" in req
            and req["addConditionalFormatRule"]["rule"]["ranges"][0]["startColumnIndex"]
            == 6
        ]

        assert len(ttm_rules) == 1
        rule = ttm_rules[0]["addConditionalFormatRule"]["rule"]
        assert rule["booleanRule"]["condition"]["type"] == "NUMBER_GREATER"
        assert (
            rule["booleanRule"]["condition"]["values"][0]["userEnteredValue"] == "180"
        )
        bg_color = rule["booleanRule"]["format"]["backgroundColor"]
        assert bg_color["red"] == 1.0
        assert bg_color["green"] == 0.647
        assert bg_color["blue"] == 0.0

    def test_apply_conditional_formatting_to_details_tail(self, mock_service):
        """Test conditional formatting for Tail column (> 60)."""
        mock_service._get_sheet_id = Mock(return_value=100)
        mock_service.service.spreadsheets().batchUpdate().execute.return_value = {}

        mock_service._apply_conditional_formatting_to_details(
            sheet_id=100, sheet_name="Details", num_rows=10
        )

        calls = mock_service.service.spreadsheets().batchUpdate.call_args_list
        call_args = None
        for call in calls:
            if call[1] or call[0]:
                call_args = call
                break
        assert call_args is not None

        requests = call_args[1]["body"]["requests"]

        # Find Tail rule (column index 8)
        tail_rules = [
            req
            for req in requests
            if "addConditionalFormatRule" in req
            and req["addConditionalFormatRule"]["rule"]["ranges"][0]["startColumnIndex"]
            == 8
        ]

        assert len(tail_rules) == 1
        rule = tail_rules[0]["addConditionalFormatRule"]["rule"]
        assert rule["booleanRule"]["condition"]["type"] == "NUMBER_GREATER"
        assert rule["booleanRule"]["condition"]["values"][0]["userEnteredValue"] == "60"

    def test_apply_conditional_formatting_to_details_devlt(self, mock_service):
        """Test conditional formatting for DevLT column (> 60)."""
        mock_service._get_sheet_id = Mock(return_value=100)
        mock_service.service.spreadsheets().batchUpdate().execute.return_value = {}

        mock_service._apply_conditional_formatting_to_details(
            sheet_id=100, sheet_name="Details", num_rows=10
        )

        calls = mock_service.service.spreadsheets().batchUpdate.call_args_list
        call_args = None
        for call in calls:
            if call[1] or call[0]:
                call_args = call
                break
        assert call_args is not None

        requests = call_args[1]["body"]["requests"]

        # Find DevLT rule (column index 9)
        devlt_rules = [
            req
            for req in requests
            if "addConditionalFormatRule" in req
            and req["addConditionalFormatRule"]["rule"]["ranges"][0]["startColumnIndex"]
            == 9
        ]

        assert len(devlt_rules) == 1
        rule = devlt_rules[0]["addConditionalFormatRule"]["rule"]
        assert rule["booleanRule"]["condition"]["type"] == "NUMBER_GREATER"
        assert rule["booleanRule"]["condition"]["values"][0]["userEnteredValue"] == "60"

    def test_apply_conditional_formatting_to_details_ttd(self, mock_service):
        """Test conditional formatting for TTD column (> 60)."""
        mock_service._get_sheet_id = Mock(return_value=100)
        mock_service.service.spreadsheets().batchUpdate().execute.return_value = {}

        mock_service._apply_conditional_formatting_to_details(
            sheet_id=100, sheet_name="Details", num_rows=10
        )

        calls = mock_service.service.spreadsheets().batchUpdate.call_args_list
        call_args = None
        for call in calls:
            if call[1] or call[0]:
                call_args = call
                break
        assert call_args is not None

        requests = call_args[1]["body"]["requests"]

        # Find TTD rule (column index 10)
        ttd_rules = [
            req
            for req in requests
            if "addConditionalFormatRule" in req
            and req["addConditionalFormatRule"]["rule"]["ranges"][0]["startColumnIndex"]
            == 10
        ]

        assert len(ttd_rules) == 1
        rule = ttd_rules[0]["addConditionalFormatRule"]["rule"]
        assert rule["booleanRule"]["condition"]["type"] == "NUMBER_GREATER"
        assert rule["booleanRule"]["condition"]["values"][0]["userEnteredValue"] == "60"

    def test_apply_conditional_formatting_to_details_all_columns(self, mock_service):
        """Test that conditional formatting is applied to all required columns."""
        mock_service._get_sheet_id = Mock(return_value=100)
        mock_service.service.spreadsheets().batchUpdate().execute.return_value = {}

        mock_service._apply_conditional_formatting_to_details(
            sheet_id=100, sheet_name="Details", num_rows=10
        )

        calls = mock_service.service.spreadsheets().batchUpdate.call_args_list
        call_args = None
        for call in calls:
            if call[1] or call[0]:
                call_args = call
                break
        assert call_args is not None

        requests = call_args[1]["body"]["requests"]

        # Should have 4 rules (TTM, Tail, DevLT, TTD)
        conditional_rules = [
            req for req in requests if "addConditionalFormatRule" in req
        ]
        assert len(conditional_rules) == 4

        # Check that all required columns are covered
        column_indices = [
            req["addConditionalFormatRule"]["rule"]["ranges"][0]["startColumnIndex"]
            for req in conditional_rules
        ]
        assert 6 in column_indices  # TTM
        assert 8 in column_indices  # Tail
        assert 9 in column_indices  # DevLT
        assert 10 in column_indices  # TTD

        # Check that formatting excludes header row (startRowIndex = 1)
        for req in conditional_rules:
            range_obj = req["addConditionalFormatRule"]["rule"]["ranges"][0]
            assert range_obj["startRowIndex"] == 1  # Skip header

    @patch("radiator.services.google_sheets_service.pd.read_csv")
    def test_upload_csv_to_sheet_includes_conditional_formatting(
        self, mock_read_csv, mock_service
    ):
        """Test that conditional formatting is applied when uploading CSV."""
        # Mock sheet creation
        mock_service.service.spreadsheets().get().execute.return_value = {"sheets": []}
        mock_service.service.spreadsheets().batchUpdate().execute.return_value = {}
        mock_service.service.spreadsheets().values().update().execute.return_value = {}
        mock_service._get_sheet_id = Mock(return_value=100)

        # Mock CSV reading
        from pathlib import Path

        import pandas as pd

        test_csv = Path("/tmp/test_upload.csv")
        df = pd.DataFrame(
            {
                "Ключ задачи": ["CPO-1", "CPO-2"],
                "TTM": [200, 150],
                "Tail": [70, 50],
                "DevLT": [80, 40],
                "TTD": [90, 30],
            }
        )
        mock_read_csv.return_value = df
        result = mock_service.upload_csv_to_sheet(test_csv, "TestSheet")

        # Verify conditional formatting was called
        calls = mock_service.service.spreadsheets().batchUpdate.call_args_list
        conditional_formatting_calls = [
            call
            for call in calls
            if call[1]
            and "requests" in call[1]["body"]
            and any(
                "addConditionalFormatRule" in req for req in call[1]["body"]["requests"]
            )
        ]
        assert len(conditional_formatting_calls) > 0

    def test_freeze_first_row_in_details(self, mock_service):
        """Test freezing first row in Details sheet."""
        mock_service._get_sheet_id = Mock(return_value=100)
        mock_service.service.spreadsheets().batchUpdate().execute.return_value = {}

        mock_service._freeze_first_row(sheet_id=100, sheet_name="Details")

        # Verify batchUpdate was called
        calls = mock_service.service.spreadsheets().batchUpdate.call_args_list
        call_args = None
        for call in calls:
            if call[1] or call[0]:
                call_args = call
                break
        assert call_args is not None, "batchUpdate() was not called with arguments"

        requests = call_args[1]["body"]["requests"]

        # Find freeze row request
        freeze_requests = [req for req in requests if "updateSheetProperties" in req]

        assert len(freeze_requests) == 1
        freeze_req = freeze_requests[0]["updateSheetProperties"]
        assert freeze_req["properties"]["sheetId"] == 100
        assert freeze_req["properties"]["gridProperties"]["frozenRowCount"] == 1
        assert freeze_req["fields"] == "gridProperties.frozenRowCount"

    def test_resize_name_column(self, mock_service):
        """Test resizing 'Название' column to half width."""
        mock_service._get_sheet_id = Mock(return_value=100)
        mock_service.service.spreadsheets().batchUpdate().execute.return_value = {}

        mock_service._resize_name_column(sheet_id=100, sheet_name="Details")

        # Verify batchUpdate was called
        calls = mock_service.service.spreadsheets().batchUpdate.call_args_list
        call_args = None
        for call in calls:
            if call[1] or call[0]:
                call_args = call
                break
        assert call_args is not None, "batchUpdate() was not called with arguments"

        requests = call_args[1]["body"]["requests"]

        # Find resize column request
        resize_requests = [
            req for req in requests if "updateDimensionProperties" in req
        ]

        assert len(resize_requests) == 1
        resize_req = resize_requests[0]["updateDimensionProperties"]
        assert resize_req["range"]["sheetId"] == 100
        assert resize_req["range"]["dimension"] == "COLUMNS"
        assert resize_req["range"]["startIndex"] == 1  # Column B (Название)
        assert resize_req["range"]["endIndex"] == 2
        assert "pixelSize" in resize_req["properties"]
        assert resize_req["fields"] == "pixelSize"

    @patch("radiator.services.google_sheets_service.pd.read_csv")
    def test_upload_csv_to_sheet_applies_freeze_and_resize(
        self, mock_read_csv, mock_service
    ):
        """Test that freeze and resize are applied when uploading CSV."""
        # Mock sheet creation
        mock_service.service.spreadsheets().get().execute.return_value = {"sheets": []}
        mock_service.service.spreadsheets().batchUpdate().execute.return_value = {}
        mock_service.service.spreadsheets().values().update().execute.return_value = {}
        mock_service._get_sheet_id = Mock(return_value=100)

        # Mock CSV reading
        from pathlib import Path

        import pandas as pd

        test_csv = Path("/tmp/test_upload.csv")
        df = pd.DataFrame(
            {
                "Ключ задачи": ["CPO-1", "CPO-2"],
                "Название": ["Task 1", "Task 2"],
                "TTM": [200, 150],
            }
        )
        mock_read_csv.return_value = df
        result = mock_service.upload_csv_to_sheet(test_csv, "TestSheet")

        # Verify freeze and resize were called
        calls = mock_service.service.spreadsheets().batchUpdate.call_args_list
        freeze_calls = [
            call
            for call in calls
            if call[1]
            and "requests" in call[1]["body"]
            and any(
                "updateSheetProperties" in req
                and req["updateSheetProperties"]["properties"]
                .get("gridProperties", {})
                .get("frozenRowCount")
                == 1
                for req in call[1]["body"]["requests"]
            )
        ]
        resize_calls = [
            call
            for call in calls
            if call[1]
            and "requests" in call[1]["body"]
            and any(
                "updateDimensionProperties" in req
                and req["updateDimensionProperties"]["range"]["startIndex"] == 1
                for req in call[1]["body"]["requests"]
            )
        ]

        assert len(freeze_calls) > 0, "Freeze first row was not called"
        assert len(resize_calls) > 0, "Resize name column was not called"

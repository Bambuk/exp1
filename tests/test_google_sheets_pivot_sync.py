"""System tests for synchronization between CSV structure and pivot tables."""

from unittest.mock import Mock, patch

import pytest

from radiator.commands.models.ttm_details_columns import TTMDetailsColumns
from radiator.services.google_sheets_service import GoogleSheetsService


class TestGoogleSheetsPivotSync:
    """Test cases for synchronization between CSV structure and pivot tables."""

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

    def test_google_sheets_service_uses_column_structure(self, mock_service):
        """Test that Google Sheets Service uses TTMDetailsColumns."""
        # Check that _get_column_index uses TTMDetailsColumns
        test_column = "Команда"
        expected_index = TTMDetailsColumns.get_column_index(test_column)
        actual_index = mock_service._get_column_index(test_column)
        assert (
            actual_index == expected_index
        ), f"_get_column_index should use TTMDetailsColumns. Expected {expected_index}, got {actual_index}"

        # Check that _build_pivot_table_request uses TTMDetailsColumns.get_column_count()
        request = mock_service._build_pivot_table_request(100, 200, "ttd")
        assert request is not None
        pivot_table = request["updateCells"]["rows"][0]["values"][0]["pivotTable"]
        expected_count = TTMDetailsColumns.get_column_count()
        actual_count = pivot_table["source"]["endColumnIndex"]
        assert (
            actual_count == expected_count
        ), f"endColumnIndex should equal TTMDetailsColumns.get_column_count(). Expected {expected_count}, got {actual_count}"

    def test_pivot_table_indices_match_column_structure(self, mock_service):
        """Test that pivot table column indices match TTMDetailsColumns structure."""
        source_sheet_id = 100
        target_sheet_id = 200

        # Test TTD pivot table
        request_ttd = mock_service._build_pivot_table_request(
            source_sheet_id, target_sheet_id, "ttd"
        )
        assert request_ttd is not None
        pivot_table_ttd = request_ttd["updateCells"]["rows"][0]["values"][0][
            "pivotTable"
        ]

        # Check endColumnIndex
        expected_count = TTMDetailsColumns.get_column_count()
        assert (
            pivot_table_ttd["source"]["endColumnIndex"] == expected_count
        ), f"endColumnIndex should equal TTMDetailsColumns.get_column_count(). Expected {expected_count}, got {pivot_table_ttd['source']['endColumnIndex']}"

        # Check row grouping indices
        rows = pivot_table_ttd["rows"]
        assert len(rows) == 5, "Expected 5 rows in grouping"
        assert rows[0]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "Разработка"
        )
        assert rows[1]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "Завершена"
        )
        assert rows[2]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "PM Lead"
        )
        assert rows[3]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "Команда"
        )
        assert rows[4]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "Квартал"
        )

        # Check values indices - TTD pivot table should have TTD and TTD Pause columns
        values = pivot_table_ttd["values"]
        assert len(values) == 4, "TTD pivot should have 4 value columns"

        # Check TTD column indices (first 3 values use TTD)
        expected_ttd_index = TTMDetailsColumns.get_column_index("TTD")
        assert (
            values[0]["sourceColumnOffset"] == expected_ttd_index
        ), f"TTD Mean index mismatch. Expected {expected_ttd_index}, got {values[0]['sourceColumnOffset']}"
        assert (
            values[1]["sourceColumnOffset"] == expected_ttd_index
        ), f"TTD Max index mismatch. Expected {expected_ttd_index}, got {values[1]['sourceColumnOffset']}"
        assert (
            values[2]["sourceColumnOffset"] == expected_ttd_index
        ), f"TTD Count index mismatch. Expected {expected_ttd_index}, got {values[2]['sourceColumnOffset']}"

        # Check TTD Pause column index
        expected_ttd_pause_index = TTMDetailsColumns.get_column_index("TTD Pause")
        assert (
            values[3]["sourceColumnOffset"] == expected_ttd_pause_index
        ), f"TTD Pause Mean index mismatch. Expected {expected_ttd_pause_index}, got {values[3]['sourceColumnOffset']}"

        # Test TTM pivot table
        request_ttm = mock_service._build_pivot_table_request(
            source_sheet_id, target_sheet_id, "ttm"
        )
        assert request_ttm is not None
        pivot_table_ttm = request_ttm["updateCells"]["rows"][0]["values"][0][
            "pivotTable"
        ]

        # Check endColumnIndex
        assert (
            pivot_table_ttm["source"]["endColumnIndex"] == expected_count
        ), f"endColumnIndex should equal TTMDetailsColumns.get_column_count(). Expected {expected_count}, got {pivot_table_ttm['source']['endColumnIndex']}"

        # Check row grouping indices
        rows_ttm = pivot_table_ttm["rows"]
        assert len(rows_ttm) == 5, "Expected 5 rows in grouping"
        assert rows_ttm[0]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "Разработка"
        )
        assert rows_ttm[1]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "Завершена"
        )
        assert rows_ttm[2]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "PM Lead"
        )
        assert rows_ttm[3]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "Команда"
        )
        assert rows_ttm[4]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "Квартал"
        )

    def test_pivot_table_has_pm_lead_before_team(self, mock_service):
        """Test that pivot tables have PM Lead before Команда in row grouping."""
        source_sheet_id = 100
        target_sheet_id = 200

        # Test TTD pivot table
        request_ttd = mock_service._build_pivot_table_request(
            source_sheet_id, target_sheet_id, "ttd"
        )
        assert request_ttd is not None
        pivot_table_ttd = request_ttd["updateCells"]["rows"][0]["values"][0][
            "pivotTable"
        ]

        rows_ttd = pivot_table_ttd["rows"]
        # Check that we have 5 rows (was 4)
        assert len(rows_ttd) == 5, f"Expected 5 rows, got {len(rows_ttd)}"

        # Check order: Разработка → Завершена → PM Lead → Команда → Квартал
        assert rows_ttd[0]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "Разработка"
        )
        assert rows_ttd[1]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "Завершена"
        )
        assert rows_ttd[2]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "PM Lead"
        ), "PM Lead should be at index 2, before Команда"
        assert rows_ttd[3]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "Команда"
        )
        assert rows_ttd[4]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "Квартал"
        )

        # Test TTM pivot table
        request_ttm = mock_service._build_pivot_table_request(
            source_sheet_id, target_sheet_id, "ttm"
        )
        assert request_ttm is not None
        pivot_table_ttm = request_ttm["updateCells"]["rows"][0]["values"][0][
            "pivotTable"
        ]

        rows_ttm = pivot_table_ttm["rows"]
        # Check that we have 5 rows (was 4)
        assert len(rows_ttm) == 5, f"Expected 5 rows, got {len(rows_ttm)}"

        # Check order: Разработка → Завершена → PM Lead → Команда → Квартал
        assert rows_ttm[0]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "Разработка"
        )
        assert rows_ttm[1]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "Завершена"
        )
        assert rows_ttm[2]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "PM Lead"
        ), "PM Lead should be at index 2, before Команда"
        assert rows_ttm[3]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "Команда"
        )
        assert rows_ttm[4]["sourceColumnOffset"] == TTMDetailsColumns.get_column_index(
            "Квартал"
        )

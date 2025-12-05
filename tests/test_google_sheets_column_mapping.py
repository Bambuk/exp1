"""Test for Google Sheets column mapping fixes."""

from unittest.mock import patch

import pytest

from radiator.commands.models.ttm_details_columns import TTMDetailsColumns
from radiator.services.google_sheets_service import GoogleSheetsService


class TestGoogleSheetsColumnMapping:
    """Test cases for Google Sheets column mapping."""

    @patch(
        "radiator.services.google_sheets_service.service_account.Credentials.from_service_account_file"
    )
    @patch("radiator.services.google_sheets_service.build")
    def test_column_mapping_includes_devlt(self, mock_build, mock_credentials):
        """Test that column mapping includes DevLT column."""
        # Mock the authentication
        mock_credentials.return_value = None
        mock_build.return_value = None

        # Create a mock service instance
        service = GoogleSheetsService(
            credentials_path="dummy_path", document_id="dummy_id", sheet_prefix="Test_"
        )

        devlt_index = service._get_column_index("DevLT")
        expected_devlt_index = TTMDetailsColumns.get_column_index("DevLT")
        assert (
            devlt_index == expected_devlt_index
        ), f"DevLT should be at index {expected_devlt_index}, got {devlt_index}"

        # Legacy alias still supported
        devlt_alias_index = service._get_column_index("DevLT (дни)")
        assert (
            devlt_alias_index == devlt_index
        ), "Alias 'DevLT (дни)' should map to DevLT column"

        quarter_index = service._get_column_index("Квартал")
        expected_quarter_index = TTMDetailsColumns.get_column_index("Квартал")
        assert (
            quarter_index == expected_quarter_index
        ), f"Quarter should be at index {expected_quarter_index}, got {quarter_index}"

    @patch(
        "radiator.services.google_sheets_service.service_account.Credentials.from_service_account_file"
    )
    @patch("radiator.services.google_sheets_service.build")
    def test_column_mapping_standard_columns(self, mock_build, mock_credentials):
        """Test that standard columns have correct mapping."""
        # Mock the authentication
        mock_credentials.return_value = None
        mock_build.return_value = None

        service = GoogleSheetsService(
            credentials_path="dummy_path", document_id="dummy_id", sheet_prefix="Test_"
        )

        # Test key columns based on current CSV structure (using TTMDetailsColumns)
        assert service._get_column_index(
            "Ключ задачи"
        ) == TTMDetailsColumns.get_column_index("Ключ задачи")
        assert service._get_column_index(
            "Название"
        ) == TTMDetailsColumns.get_column_index("Название")
        assert service._get_column_index("Автор") == TTMDetailsColumns.get_column_index(
            "Автор"
        )
        assert service._get_column_index(
            "Команда"
        ) == TTMDetailsColumns.get_column_index("Команда")
        assert service._get_column_index(
            "PM Lead"
        ) == TTMDetailsColumns.get_column_index("PM Lead")
        assert service._get_column_index(
            "Квартал"
        ) == TTMDetailsColumns.get_column_index("Квартал")
        assert service._get_column_index("TTM") == TTMDetailsColumns.get_column_index(
            "TTM"
        )
        assert service._get_column_index("Пауза") == TTMDetailsColumns.get_column_index(
            "Пауза"
        )
        assert service._get_column_index("Tail") == TTMDetailsColumns.get_column_index(
            "Tail"
        )
        assert service._get_column_index("DevLT") == TTMDetailsColumns.get_column_index(
            "DevLT"
        )
        assert service._get_column_index("TTD") == TTMDetailsColumns.get_column_index(
            "TTD"
        )

    @patch(
        "radiator.services.google_sheets_service.service_account.Credentials.from_service_account_file"
    )
    @patch("radiator.services.google_sheets_service.build")
    def test_column_mapping_unknown_column(self, mock_build, mock_credentials):
        """Test that unknown columns return 0."""
        # Mock the authentication
        mock_credentials.return_value = None
        mock_build.return_value = None

        service = GoogleSheetsService(
            credentials_path="dummy_path", document_id="dummy_id", sheet_prefix="Test_"
        )

        # Test unknown column
        unknown_index = service._get_column_index("Unknown Column")
        assert (
            unknown_index == 0
        ), f"Unknown column should return 0, got {unknown_index}"

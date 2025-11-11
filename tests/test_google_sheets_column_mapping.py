"""Test for Google Sheets column mapping fixes."""

from unittest.mock import patch

import pytest

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
        assert devlt_index == 8, f"DevLT should be at index 8, got {devlt_index}"

        # Legacy alias still supported
        devlt_alias_index = service._get_column_index("DevLT (дни)")
        assert (
            devlt_alias_index == devlt_index
        ), "Alias 'DevLT (дни)' should map to DevLT column"

        quarter_index = service._get_column_index("Квартал")
        assert quarter_index == 4, f"Quarter should be at index 4, got {quarter_index}"

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

        # Test key columns based on current CSV structure
        assert service._get_column_index("Ключ задачи") == 0
        assert service._get_column_index("Название") == 1
        assert service._get_column_index("Автор") == 2
        assert service._get_column_index("Команда") == 3
        assert service._get_column_index("Квартал") == 4
        assert service._get_column_index("TTM") == 5
        assert service._get_column_index("Пауза") == 6
        assert service._get_column_index("Tail") == 7
        assert service._get_column_index("DevLT") == 8
        assert service._get_column_index("TTD") == 9

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

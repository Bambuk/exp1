"""Tests for task key hyperlinks in Google Sheets."""

from unittest.mock import patch

import pandas as pd
import pytest

from radiator.services.google_sheets_service import GoogleSheetsService


class TestTaskKeyHyperlinks:
    """Test cases for task key hyperlink conversion."""

    @pytest.fixture
    def mock_google_sheets_service(self):
        """Create a mock GoogleSheetsService instance."""
        with patch(
            "radiator.services.google_sheets_service.service_account.Credentials.from_service_account_file"
        ), patch("radiator.services.google_sheets_service.build"):
            service = GoogleSheetsService(
                credentials_path="fake_credentials.json",
                document_id="fake_doc_id",
            )
            return service

    def test_prepare_data_converts_task_keys_to_hyperlinks(
        self, mock_google_sheets_service
    ):
        """Test that task keys are converted to HYPERLINK formulas."""
        # Create DataFrame with task keys
        df = pd.DataFrame(
            {
                "Автор": ["Author1", "Author2"],
                "Команда": ["Team1", "Team2"],
                "Ключ задачи": ["CPO-1709", "CPO-2345"],
                "Название": ["Task 1", "Task 2"],
                "TTD": [10.5, 15.2],
            }
        )

        # Prepare data
        data = mock_google_sheets_service._prepare_data_for_sheets(df)

        # Verify headers
        assert data[0] == ["Автор", "Команда", "Ключ задачи", "Название", "TTD"]

        # Verify task keys are converted to HYPERLINK formulas
        task_key_index = 2  # "Ключ задачи" column index

        expected_hyperlink_1 = (
            '=HYPERLINK("https://tracker.yandex.ru/CPO-1709","CPO-1709")'
        )
        expected_hyperlink_2 = (
            '=HYPERLINK("https://tracker.yandex.ru/CPO-2345","CPO-2345")'
        )

        assert data[1][task_key_index] == expected_hyperlink_1
        assert data[2][task_key_index] == expected_hyperlink_2

    def test_prepare_data_handles_empty_task_keys(self, mock_google_sheets_service):
        """Test that empty task keys are not converted."""
        df = pd.DataFrame(
            {
                "Ключ задачи": ["CPO-1709", "", None, "  "],
                "Название": ["Task 1", "Task 2", "Task 3", "Task 4"],
            }
        )

        data = mock_google_sheets_service._prepare_data_for_sheets(df)

        # First row should have hyperlink
        assert (
            '=HYPERLINK("https://tracker.yandex.ru/CPO-1709","CPO-1709")' == data[1][0]
        )

        # Empty strings should remain empty
        assert data[2][0] == ""
        assert data[3][0] == ""
        assert data[4][0] == "  "  # Whitespace-only string doesn't get converted

    def test_prepare_data_without_task_key_column(self, mock_google_sheets_service):
        """Test that data without task key column is processed normally."""
        df = pd.DataFrame(
            {
                "Автор": ["Author1", "Author2"],
                "TTD": [10.5, 15.2],
                "TTM": [20.3, 25.1],
            }
        )

        data = mock_google_sheets_service._prepare_data_for_sheets(df)

        # Should return normal data without hyperlinks
        assert data[0] == ["Автор", "TTD", "TTM"]
        assert data[1] == ["Author1", 10.5, 20.3]
        assert data[2] == ["Author2", 15.2, 25.1]

    def test_prepare_data_with_special_characters_in_task_key(
        self, mock_google_sheets_service
    ):
        """Test that task keys with special characters are properly escaped."""
        df = pd.DataFrame(
            {
                "Ключ задачи": ["CPO-123", "TEST-456"],
                "Название": ["Task with dash", "Another task"],
            }
        )

        data = mock_google_sheets_service._prepare_data_for_sheets(df)

        # Verify hyperlinks are created correctly
        assert data[1][0] == '=HYPERLINK("https://tracker.yandex.ru/CPO-123","CPO-123")'
        assert (
            data[2][0] == '=HYPERLINK("https://tracker.yandex.ru/TEST-456","TEST-456")'
        )

    def test_prepare_data_preserves_other_columns(self, mock_google_sheets_service):
        """Test that other columns are not affected by hyperlink conversion."""
        df = pd.DataFrame(
            {
                "Автор": ["Author1"],
                "Ключ задачи": ["CPO-1709"],
                "Название": ["Task 1"],
                "TTD": [10.5],
                "TTM": [20.3],
                "Квартал": ["2024-Q1"],
            }
        )

        data = mock_google_sheets_service._prepare_data_for_sheets(df)

        # Verify all columns except task key remain unchanged
        assert data[1][0] == "Author1"  # Автор
        assert (
            '=HYPERLINK("https://tracker.yandex.ru/CPO-1709","CPO-1709")' == data[1][1]
        )  # Ключ задачи
        assert data[1][2] == "Task 1"  # Название
        assert data[1][3] == 10.5  # TTD
        assert data[1][4] == 20.3  # TTM
        assert data[1][5] == "2024-Q1"  # Квартал

    def test_prepare_data_with_multiple_task_keys(self, mock_google_sheets_service):
        """Test conversion of multiple task keys."""
        df = pd.DataFrame(
            {
                "Ключ задачи": [
                    "CPO-1",
                    "CPO-100",
                    "CPO-9999",
                    "PROJ-1",
                ],
                "Название": ["T1", "T2", "T3", "T4"],
            }
        )

        data = mock_google_sheets_service._prepare_data_for_sheets(df)

        # Verify all task keys are converted
        assert data[1][0] == '=HYPERLINK("https://tracker.yandex.ru/CPO-1","CPO-1")'
        assert data[2][0] == '=HYPERLINK("https://tracker.yandex.ru/CPO-100","CPO-100")'
        assert (
            data[3][0] == '=HYPERLINK("https://tracker.yandex.ru/CPO-9999","CPO-9999")'
        )
        assert data[4][0] == '=HYPERLINK("https://tracker.yandex.ru/PROJ-1","PROJ-1")'

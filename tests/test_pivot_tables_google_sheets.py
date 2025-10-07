"""Tests for pivot tables functionality in Google Sheets service."""

from unittest.mock import Mock, patch

import pandas as pd
import pytest

from radiator.services.google_sheets_service import GoogleSheetsService


class TestPivotTablesGoogleSheets:
    """Test cases for pivot tables functionality in GoogleSheetsService."""

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

    @pytest.fixture
    def sample_details_data(self):
        """Create sample details CSV data for testing."""
        return pd.DataFrame(
            [
                {
                    "Автор": "Author1",
                    "Команда": "Team1",
                    "Ключ задачи": "CPO-1",
                    "Название": "Task 1",
                    "TTD": 15.5,
                    "TTM": 25.3,
                    "Tail": 5.2,
                    "Пауза": 3.0,
                    "TTD Pause": 2.3,
                    "Discovery backlog (дни)": 3.0,
                    "Готова к разработке (дни)": 2.0,
                    "Квартал": "2024-Q1",
                },
                {
                    "Автор": "Author1",
                    "Команда": "Team1",
                    "Ключ задачи": "CPO-2",
                    "Название": "Task 2",
                    "TTD": 12.1,
                    "TTM": 22.1,
                    "Tail": 4.8,
                    "Пауза": 2.5,
                    "TTD Pause": 1.8,
                    "Discovery backlog (дни)": 2.5,
                    "Готова к разработке (дни)": 1.5,
                    "Квартал": "2024-Q1",
                },
                {
                    "Автор": "Author2",
                    "Команда": "Team2",
                    "Ключ задачи": "CPO-3",
                    "Название": "Task 3",
                    "TTD": 18.0,
                    "TTM": 28.0,
                    "Tail": 6.0,
                    "Пауза": 4.0,
                    "TTD Pause": 3.0,
                    "Discovery backlog (дни)": 4.0,
                    "Готова к разработке (дни)": 3.0,
                    "Квартал": "2024-Q1",
                },
                {
                    "Автор": "Author1",
                    "Команда": "Team1",
                    "Ключ задачи": "CPO-4",
                    "Название": "Task 4",
                    "TTD": 20.0,
                    "TTM": 30.0,
                    "Tail": 7.0,
                    "Пауза": 5.0,
                    "TTD Pause": 4.0,
                    "Discovery backlog (дни)": 5.0,
                    "Готова к разработке (дни)": 4.0,
                    "Квартал": "2024-Q2",
                },
            ]
        )

    def test_get_group_value_with_team(self, mock_service):
        """Test getting group value when team is available."""
        row = {"Команда": "Team1", "Автор": "Author1"}
        result = mock_service._get_group_value(row)
        assert result == "Team1"

    def test_get_group_value_without_team(self, mock_service):
        """Test getting group value when team is not available."""
        row = {"Команда": "", "Автор": "Author1"}
        result = mock_service._get_group_value(row)
        assert result == "Author1"

    def test_get_group_value_team_none(self, mock_service):
        """Test getting group value when team is None."""
        row = {"Команда": None, "Автор": "Author1"}
        result = mock_service._get_group_value(row)
        assert result == "Author1"

    def test_aggregate_ttd_metrics(self, mock_service, sample_details_data):
        """Test aggregation of TTD metrics."""
        # Group data by team and quarter
        grouped = sample_details_data.groupby(
            [
                sample_details_data.apply(
                    lambda row: mock_service._get_group_value(row), axis=1
                ),
                "Квартал",
            ]
        )

        # Test aggregation for first group
        group_data = list(grouped)[0][1]  # First group data

        ttd_values = group_data["TTD"].dropna()
        ttd_pause_values = group_data["TTD Pause"].dropna()

        expected_mean = ttd_values.mean()
        expected_p85 = ttd_values.quantile(0.85)
        expected_count = len(ttd_values)
        expected_pause_mean = ttd_pause_values.mean()

        assert expected_mean == pytest.approx(13.8, rel=1e-2)  # (15.5 + 12.1) / 2
        assert expected_p85 == pytest.approx(
            14.99, rel=1e-2
        )  # 85th percentile for [12.1, 15.5]
        assert expected_count == 2
        assert expected_pause_mean == pytest.approx(2.05, rel=1e-2)  # (2.3 + 1.8) / 2

    def test_aggregate_ttm_metrics(self, mock_service, sample_details_data):
        """Test aggregation of TTM metrics."""
        # Group data by team and quarter
        grouped = sample_details_data.groupby(
            [
                sample_details_data.apply(
                    lambda row: mock_service._get_group_value(row), axis=1
                ),
                "Квартал",
            ]
        )

        # Test aggregation for first group
        group_data = list(grouped)[0][1]  # First group data

        ttm_values = group_data["TTM"].dropna()
        tail_values = group_data["Tail"].dropna()

        expected_mean = ttm_values.mean()
        expected_p85 = ttm_values.quantile(0.85)
        expected_count = len(ttm_values)
        expected_tail_mean = tail_values.mean()
        expected_tail_p85 = tail_values.quantile(0.85)

        assert expected_mean == pytest.approx(23.7, rel=1e-2)  # (25.3 + 22.1) / 2
        assert expected_p85 == pytest.approx(
            24.82, rel=1e-2
        )  # 85th percentile for [22.1, 25.3]
        assert expected_count == 2
        assert expected_tail_mean == pytest.approx(5.0, rel=1e-2)  # (5.2 + 4.8) / 2
        assert expected_tail_p85 == pytest.approx(
            5.14, rel=1e-2
        )  # 85th percentile for [4.8, 5.2]

    def test_create_pivot_data_ttd(self, mock_service, sample_details_data):
        """Test creation of TTD pivot data."""
        pivot_data = mock_service._create_pivot_data(sample_details_data, "ttd")

        # Check structure
        assert len(pivot_data) > 0
        assert "Команда/Автор" in pivot_data[0]
        assert "Квартал" in pivot_data[0]
        assert "TTD Mean" in pivot_data[0]
        assert "TTD P85" in pivot_data[0]
        assert "TTD Count" in pivot_data[0]
        assert "TTD Pause Mean" in pivot_data[0]

        # Check that we have data for both teams
        team_names = [row["Команда/Автор"] for row in pivot_data]
        assert "Team1" in team_names
        assert "Team2" in team_names

    def test_create_pivot_data_ttm(self, mock_service, sample_details_data):
        """Test creation of TTM pivot data."""
        pivot_data = mock_service._create_pivot_data(sample_details_data, "ttm")

        # Check structure
        assert len(pivot_data) > 0
        assert "Команда/Автор" in pivot_data[0]
        assert "Квартал" in pivot_data[0]
        assert "TTM Mean" in pivot_data[0]
        assert "TTM P85" in pivot_data[0]
        assert "TTM Count" in pivot_data[0]
        assert "Tail Mean" in pivot_data[0]
        assert "Tail P85" in pivot_data[0]

        # Check that we have data for both teams
        team_names = [row["Команда/Автор"] for row in pivot_data]
        assert "Team1" in team_names
        assert "Team2" in team_names

    def test_create_pivot_data_empty_dataframe(self, mock_service):
        """Test creation of pivot data with empty DataFrame."""
        empty_df = pd.DataFrame()
        pivot_data = mock_service._create_pivot_data(empty_df, "ttd")
        assert pivot_data == []

    def test_create_pivot_data_missing_columns(self, mock_service):
        """Test creation of pivot data with missing columns."""
        incomplete_df = pd.DataFrame([{"Автор": "Author1", "Квартал": "2024-Q1"}])
        pivot_data = mock_service._create_pivot_data(incomplete_df, "ttd")
        assert pivot_data == []

    def test_create_pivot_sheet_success(self, mock_service):
        """Test successful creation of pivot sheet."""
        # Mock the service methods
        mock_service.service.spreadsheets().batchUpdate().execute.return_value = {
            "replies": [{"addSheet": {"properties": {"sheetId": 123}}}]
        }

        # Mock the values().update() method
        mock_service.service.spreadsheets().values().update().execute.return_value = {}

        # Mock _auto_resize_columns to avoid _get_sheet_id call
        mock_service._auto_resize_columns = Mock()

        pivot_data = [
            {
                "Команда/Автор": "Team1",
                "Квартал": "2024-Q1",
                "TTD Mean": 13.8,
                "TTD P85": 15.5,
                "TTD Count": 2,
                "TTD Pause Mean": 2.05,
            }
        ]

        result = mock_service._create_pivot_sheet(
            sheet_id="test_sheet_id", data=pivot_data, sheet_name="TTD Pivot"
        )

        assert result == 123
        # Should be called once for batchUpdate
        assert mock_service.service.spreadsheets().batchUpdate().execute.call_count == 1

    def test_create_pivot_sheet_api_error(self, mock_service):
        """Test creation of pivot sheet with API error."""
        # Mock API error
        mock_service.service.spreadsheets().batchUpdate().execute.side_effect = (
            Exception("API Error")
        )

        pivot_data = [{"Команда/Автор": "Team1", "Квартал": "2024-Q1"}]

        result = mock_service._create_pivot_sheet(
            sheet_id="test_sheet_id", data=pivot_data, sheet_name="TTD Pivot"
        )

        assert result is None

    def test_create_pivot_tables_from_details_success(
        self, mock_service, sample_details_data
    ):
        """Test successful creation of pivot tables from details."""
        # Mock the service methods
        mock_service._read_csv_file_from_sheet = Mock(return_value=sample_details_data)
        mock_service._create_pivot_sheet = Mock(side_effect=[123, 456])

        result = mock_service.create_pivot_tables_from_details("test_sheet_id")

        expected = {"ttd_pivot": 123, "ttm_pivot": 456}
        assert result == expected

        # Verify that both pivot sheets were created
        assert mock_service._create_pivot_sheet.call_count == 2

    def test_create_pivot_tables_from_details_no_data(self, mock_service):
        """Test creation of pivot tables with no data."""
        # Mock empty data
        mock_service._read_csv_file_from_sheet = Mock(return_value=pd.DataFrame())

        result = mock_service.create_pivot_tables_from_details("test_sheet_id")

        assert result == {"ttd_pivot": None, "ttm_pivot": None}

    def test_create_pivot_tables_from_details_api_error(
        self, mock_service, sample_details_data
    ):
        """Test creation of pivot tables with API error."""
        # Mock the service methods
        mock_service._read_csv_file_from_sheet = Mock(return_value=sample_details_data)
        mock_service._create_pivot_sheet = Mock(side_effect=Exception("API Error"))

        result = mock_service.create_pivot_tables_from_details("test_sheet_id")

        assert result == {"ttd_pivot": None, "ttm_pivot": None}

    def test_filter_valid_data(self, mock_service, sample_details_data):
        """Test filtering of valid data (non-empty TTD/TTM)."""
        # Add some rows with empty TTD/TTM
        invalid_data = pd.DataFrame(
            [
                {"Автор": "Author1", "TTD": None, "TTM": 25.0, "Квартал": "2024-Q1"},
                {"Автор": "Author2", "TTD": 15.0, "TTM": None, "Квартал": "2024-Q1"},
                {"Автор": "Author3", "TTD": None, "TTM": None, "Квартал": "2024-Q1"},
                {"Автор": "Author4", "TTD": 20.0, "TTM": 30.0, "Квартал": "2024-Q1"},
            ]
        )

        filtered_data = mock_service._filter_valid_data(invalid_data)

        # Should only keep Author4 (has both TTD and TTM)
        assert len(filtered_data) == 1
        assert filtered_data.iloc[0]["Автор"] == "Author4"

    def test_handle_special_characters_in_group_names(self, mock_service):
        """Test handling of special characters in group names."""
        row_with_special_chars = {
            "Команда": "Team/Name*With?Special[Chars]",
            "Автор": "Author1",
        }
        result = mock_service._get_group_value(row_with_special_chars)
        assert result == "Team/Name*With?Special[Chars]"

        # Test that special characters are handled in sheet creation
        pivot_data = [
            {"Команда/Автор": "Team/Name*With?Special[Chars]", "Квартал": "2024-Q1"}
        ]

        # Mock the service
        mock_service.service.spreadsheets().batchUpdate().execute.return_value = {
            "replies": [{"addSheet": {"properties": {"sheetId": 123}}}]
        }

        result = mock_service._create_pivot_sheet(
            sheet_id="test_sheet_id", data=pivot_data, sheet_name="TTD Pivot"
        )

        assert result == 123

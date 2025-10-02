"""Tests for status change report with team mapping from file."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from radiator.commands.generate_status_change_report import (
    GenerateStatusChangeReportCommand,
)


class TestStatusChangeReportTeamMapping:
    """Test cases for status change report with team mapping integration."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def author_team_mapping_file(self):
        """Create temporary author-team mapping file."""
        # Create a temporary directory and put the file there as cpo_authors.txt
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "cpo_authors.txt"
            with open(mapping_file, "w", encoding="utf-8") as f:
                f.write("Александр Тихонов;Корзинка и заказ\n")
                f.write("Александр Черкасов;Каталог\n")
                f.write("Александра Степаненкова;Гео и сервисы\n")
                f.write("Алексей Какурин;Каталог\n")
                f.write("Алексей Красников;Оплаты\n")
                f.write("Алексей Никишанин;\n")  # Empty team

            yield str(mapping_file)

    def test_command_init_with_team_grouping_and_mapping_file(
        self, author_team_mapping_file
    ):
        """Test command initialization with team grouping and mapping file."""
        config_dir = str(Path(author_team_mapping_file).parent)

        # This should work - command should accept config_dir parameter
        cmd = GenerateStatusChangeReportCommand(group_by="team", config_dir=config_dir)

        assert cmd.group_by == "team"
        assert cmd.config_dir == config_dir
        # Should have AuthorTeamMappingService initialized
        assert hasattr(cmd, "author_team_mapping_service")
        assert cmd.author_team_mapping_service is not None

    def test_get_status_changes_by_group_with_team_mapping(
        self, mock_db, author_team_mapping_file
    ):
        """Test get_status_changes_by_group with team mapping from file."""
        config_dir = str(Path(author_team_mapping_file).parent)

        # Mock database query results - return authors, not teams
        mock_results = [
            ("Александр Тихонов", 1, 1),  # author, history_id, task_id
            ("Александр Тихонов", 2, 1),
            ("Александр Черкасов", 3, 2),
            ("Алексей Какурин", 4, 3),
            ("Алексей Красников", 5, 4),  # Author with team "Оплаты"
            ("Алексей Никишанин", 6, 5),  # Author without team
            ("Неизвестный Автор", 7, 6),  # Author not in mapping
        ]

        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = mock_results

        mock_db.query.return_value = mock_query

        cmd = GenerateStatusChangeReportCommand(
            group_by="team", config_dir=config_dir, db=mock_db
        )

        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()

        result = cmd.get_status_changes_by_group(start_date, end_date)

        # Should group by teams, not authors
        assert "Корзинка и заказ" in result
        assert "Каталог" in result
        assert "Оплаты" in result
        assert "Без команды" in result

        # Check that authors are mapped to correct teams
        assert result["Корзинка и заказ"]["changes"] == 2  # Александр Тихонов
        assert result["Каталог"]["changes"] == 2  # Александр Черкасов + Алексей Какурин
        assert result["Оплаты"]["changes"] == 1  # Алексей Красников
        assert (
            result["Без команды"]["changes"] == 2
        )  # Алексей Никишанин + Неизвестный Автор

    def test_get_open_tasks_by_group_with_team_mapping(
        self, mock_db, author_team_mapping_file
    ):
        """Test get_open_tasks_by_group with team mapping from file."""
        config_dir = str(Path(author_team_mapping_file).parent)

        # Mock database query results - return authors, not teams
        mock_open_tasks = [
            ("Александр Тихонов", 1, "В работе", datetime.now()),
            ("Александр Черкасов", 2, "В работе", datetime.now()),
            ("Алексей Какурин", 3, "В работе", datetime.now()),
            (
                "Алексей Красников",
                4,
                "В работе",
                datetime.now(),
            ),  # Author with team "Оплаты"
            ("Алексей Никишанин", 5, "В работе", datetime.now()),  # Author without team
            (
                "Неизвестный Автор",
                6,
                "В работе",
                datetime.now(),
            ),  # Author not in mapping
        ]

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = mock_open_tasks

        mock_db.query.return_value = mock_query

        cmd = GenerateStatusChangeReportCommand(
            group_by="team", config_dir=config_dir, db=mock_db
        )

        result = cmd.get_open_tasks_by_group()

        # Should group by teams, not authors
        assert "Корзинка и заказ" in result
        assert "Каталог" in result
        assert "Оплаты" in result
        assert "Без команды" in result

        # Check that authors are mapped to correct teams
        assert result["Корзинка и заказ"]["discovery"] == 1  # Александр Тихонов
        assert (
            result["Каталог"]["discovery"] == 2
        )  # Александр Черкасов + Алексей Какурин
        assert result["Оплаты"]["discovery"] == 1  # Алексей Красников
        assert (
            result["Без команды"]["discovery"] == 2
        )  # Алексей Никишанин + Неизвестный Автор

    def test_team_grouping_without_mapping_file(self, mock_db):
        """Test team grouping when mapping file doesn't exist."""
        cmd = GenerateStatusChangeReportCommand(
            group_by="team", config_dir="nonexistent_dir", db=mock_db
        )

        # Should still work, but all authors should be mapped to "Без команды"
        mock_results = [
            ("Александр Тихонов", 1, 1),
            ("Александр Черкасов", 2, 2),
        ]

        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = mock_results

        mock_db.query.return_value = mock_query

        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()

        result = cmd.get_status_changes_by_group(start_date, end_date)

        # All authors should be mapped to "Без команды"
        assert "Без команды" in result
        assert result["Без команды"]["changes"] == 2

    def test_team_grouping_with_empty_team_mapping(self, mock_db):
        """Test team grouping when author has empty team in mapping file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Алексей Никишанин;\n")  # Empty team
            temp_file = f.name

        try:
            config_dir = str(Path(temp_file).parent)

            cmd = GenerateStatusChangeReportCommand(
                group_by="team", config_dir=config_dir, db=mock_db
            )

            mock_results = [
                ("Алексей Никишанин", 1, 1),
            ]

            mock_query = Mock()
            mock_query.join.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.all.return_value = mock_results

            mock_db.query.return_value = mock_query

            start_date = datetime.now() - timedelta(days=7)
            end_date = datetime.now()

            result = cmd.get_status_changes_by_group(start_date, end_date)

            # Author with empty team should be mapped to "Без команды"
            assert "Без команды" in result
            assert result["Без команды"]["changes"] == 1
        finally:
            Path(temp_file).unlink(missing_ok=True)

    def test_author_grouping_unchanged(self, mock_db, author_team_mapping_file):
        """Test that author grouping still works as before."""
        config_dir = str(Path(author_team_mapping_file).parent)

        cmd = GenerateStatusChangeReportCommand(
            group_by="author", config_dir=config_dir, db=mock_db
        )

        # Author grouping should not use team mapping
        assert cmd.group_by == "author"
        # Should not have team mapping service for author grouping
        assert (
            not hasattr(cmd, "author_team_mapping_service")
            or cmd.author_team_mapping_service is None
        )

    def test_cli_with_config_dir_argument(self, author_team_mapping_file):
        """Test CLI with --config-dir argument."""
        config_dir = str(Path(author_team_mapping_file).parent)

        # This test will fail initially because CLI doesn't support --config-dir yet
        # But we write it to define the expected behavior
        import sys
        from unittest.mock import patch

        test_args = [
            "generate_status_change_report.py",
            "--group-by",
            "team",
            "--config-dir",
            config_dir,
        ]

        with patch.object(sys, "argv", test_args):
            # This should work after implementation
            # For now, it will fail because --config-dir is not supported
            with pytest.raises(SystemExit):
                # This is expected to fail in red phase
                from radiator.commands.generate_status_change_report import main

                main()

    def test_integration_with_real_mapping_file(self, mock_db):
        """Test integration with real mapping file from fixtures."""
        # Use the test fixture file - copy it to cpo_authors.txt
        test_file = Path(__file__).parent / "fixtures" / "test_cpo_authors.txt"
        config_dir = str(test_file.parent)

        # Copy test file to cpo_authors.txt for the service
        import shutil

        cpo_authors_file = Path(config_dir) / "cpo_authors.txt"
        shutil.copy2(test_file, cpo_authors_file)

        cmd = GenerateStatusChangeReportCommand(
            group_by="team", config_dir=config_dir, db=mock_db
        )

        # Should load real mapping file
        assert cmd.author_team_mapping_service is not None

        # Test that it can get teams
        teams = cmd.author_team_mapping_service.get_all_teams()
        assert len(teams) > 0
        assert "Без команды" in teams
        assert "Team Alpha" in teams

    def test_build_report_data_shows_only_teams_not_authors(
        self, mock_db, author_team_mapping_file
    ):
        """Test that build_report_data shows only teams, not individual authors."""
        config_dir = str(Path(author_team_mapping_file).parent)

        # Mock database query results - return authors, not teams
        mock_results = [
            ("Александр Тихонов", 1, 1),  # author, history_id, task_id
            ("Александр Черкасов", 2, 2),
            ("Алексей Какурин", 3, 3),
        ]

        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = mock_results

        mock_db.query.return_value = mock_query

        cmd = GenerateStatusChangeReportCommand(
            group_by="team", config_dir=config_dir, db=mock_db
        )

        # Mock the methods to return data that includes individual authors
        # This simulates the OLD behavior where individual authors were included
        def mock_get_status_changes_by_group(start_date, end_date):
            return {
                "Корзинка и заказ": {"changes": 1, "tasks": 1},
                "Каталог": {"changes": 2, "tasks": 2},
                "Александр Тихонов": {
                    "changes": 1,
                    "tasks": 1,
                },  # Individual author - should NOT appear in team report
                "Александр Черкасов": {
                    "changes": 2,
                    "tasks": 2,
                },  # Individual author - should NOT appear in team report
            }

        def mock_get_open_tasks_by_group():
            return {
                "Корзинка и заказ": {"discovery": 1, "delivery": 0},
                "Каталог": {"discovery": 2, "delivery": 1},
                "Александр Тихонов": {
                    "discovery": 1,
                    "delivery": 0,
                },  # Individual author - should NOT appear in team report
                "Александр Черкасов": {
                    "discovery": 2,
                    "delivery": 1,
                },  # Individual author - should NOT appear in team report
            }

        # Replace the methods with mocks
        cmd.get_status_changes_by_group = mock_get_status_changes_by_group
        cmd.get_open_tasks_by_group = mock_get_open_tasks_by_group

        # Generate report data
        cmd.generate_report_data()

        # Check that report contains only teams, not individual authors
        report_groups = set(cmd.report_data.keys())

        # Should contain teams
        assert "Корзинка и заказ" in report_groups
        assert "Каталог" in report_groups

        # Should NOT contain individual authors
        assert "Александр Тихонов" not in report_groups
        assert "Александр Черкасов" not in report_groups
        assert "Алексей Какурин" not in report_groups

        # Should only contain teams from the mapping service
        all_teams = set(cmd.author_team_mapping_service.get_all_teams())
        for group in report_groups:
            assert (
                group in all_teams
            ), f"Group '{group}' should be a team from mapping service"

    def test_png_table_generation_has_readable_height(
        self, mock_db, author_team_mapping_file
    ):
        """Test that PNG table generation produces readable height for team reports."""
        config_dir = str(Path(author_team_mapping_file).parent)

        cmd = GenerateStatusChangeReportCommand(
            group_by="team", config_dir=config_dir, db=mock_db
        )

        # Mock the methods to return team data (6 teams for better testing)
        def mock_get_status_changes_by_group(start_date, end_date):
            return {
                "Корзинка и заказ": {"changes": 1, "tasks": 1},
                "Каталог": {"changes": 2, "tasks": 2},
                "Оплаты": {"changes": 1, "tasks": 1},
                "Лояльность": {"changes": 3, "tasks": 2},
                "КПП": {"changes": 2, "tasks": 1},
                "Гео и сервисы": {"changes": 1, "tasks": 1},
            }

        def mock_get_open_tasks_by_group():
            return {
                "Корзинка и заказ": {"discovery": 1, "delivery": 0},
                "Каталог": {"discovery": 2, "delivery": 1},
                "Оплаты": {"discovery": 1, "delivery": 0},
                "Лояльность": {"discovery": 2, "delivery": 1},
                "КПП": {"discovery": 1, "delivery": 1},
                "Гео и сервисы": {"discovery": 1, "delivery": 0},
            }

        # Replace the methods with mocks
        cmd.get_status_changes_by_group = mock_get_status_changes_by_group
        cmd.get_open_tasks_by_group = mock_get_open_tasks_by_group

        # Generate report data
        cmd.generate_report_data()

        # Generate PNG table
        png_path = cmd.generate_table()

        # Check that PNG file was created
        assert Path(png_path).exists()

        # Check that PNG file has reasonable height in pixels (not squashed)
        from PIL import Image

        with Image.open(png_path) as img:
            width, height = img.size

            # Calculate expected metrics based on real data analysis:
            # - Author reports: ~24.7px per row
            # - Team reports should have similar density, not 2.3x less
            # - Padding: 28px top + 28px bottom = 56px
            # - Header: ~25px
            # - Data rows: 6 teams * expected_pixels_per_row

            padding_pixels = 28 * 2  # 56px
            header_pixels = 25
            team_count = 6

            # Expect team rows to have similar density to author rows (~20-25px per row)
            expected_pixels_per_team_row = 20  # Conservative estimate
            expected_min_height = (
                padding_pixels
                + header_pixels
                + (team_count * expected_pixels_per_team_row)
            )

            # Calculate actual pixels per team row
            actual_data_pixels = height - padding_pixels - header_pixels
            actual_pixels_per_team_row = (
                actual_data_pixels / team_count if team_count > 0 else 0
            )

            assert (
                height >= expected_min_height
            ), f"PNG height too small ({height}px), expected at least {expected_min_height}px"
            assert (
                actual_pixels_per_team_row >= 15
            ), f"Pixels per team row too small ({actual_pixels_per_team_row:.1f}px), expected at least 15px per row"

        # Clean up
        Path(png_path).unlink(missing_ok=True)

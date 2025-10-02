"""Tests for AuthorTeamMappingService."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from radiator.commands.services.author_team_mapping_service import (
    AuthorTeamMappingService,
)


class TestAuthorTeamMappingService:
    """Test cases for AuthorTeamMappingService."""

    def test_load_author_team_mapping_success(self):
        """Test successful loading of author-team mapping file."""
        # Create temporary file with test data
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Александр Тихонов;Корзинка и заказ\n")
            f.write("Александр Черкасов;Каталог\n")
            f.write("Александра Степаненкова;Гео и сервисы\n")
            f.write("Алексей Какурин;Каталог\n")
            f.write("Алексей Красников;Оплаты\n")
            temp_file = f.name

        try:
            service = AuthorTeamMappingService(temp_file)
            mapping = service.load_author_team_mapping()

            assert len(mapping) == 5
            assert mapping["Александр Тихонов"] == "Корзинка и заказ"
            assert mapping["Александр Черкасов"] == "Каталог"
            assert mapping["Александра Степаненкова"] == "Гео и сервисы"
            assert mapping["Алексей Какурин"] == "Каталог"
            assert mapping["Алексей Красников"] == "Оплаты"
        finally:
            os.unlink(temp_file)

    def test_load_author_team_mapping_empty_teams(self):
        """Test loading file with empty teams (should become 'Без команды')."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Александр Тихонов;Корзинка и заказ\n")
            f.write("Александр Черкасов;\n")  # Empty team
            f.write("Александра Степаненкова;Гео и сервисы\n")
            f.write("Алексей Какурин;\n")  # Empty team
            temp_file = f.name

        try:
            service = AuthorTeamMappingService(temp_file)
            mapping = service.load_author_team_mapping()

            assert len(mapping) == 4
            assert mapping["Александр Тихонов"] == "Корзинка и заказ"
            assert mapping["Александр Черкасов"] == "Без команды"
            assert mapping["Александра Степаненкова"] == "Гео и сервисы"
            assert mapping["Алексей Какурин"] == "Без команды"
        finally:
            os.unlink(temp_file)

    def test_load_author_team_mapping_invalid_lines(self):
        """Test loading file with invalid lines (should be skipped)."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Александр Тихонов;Корзинка и заказ\n")
            f.write("Invalid line without semicolon\n")  # Invalid line
            f.write("Александра Степаненкова;Гео и сервисы\n")
            f.write("Another invalid line\n")  # Invalid line
            f.write("Алексей Какурин;Каталог\n")
            temp_file = f.name

        try:
            service = AuthorTeamMappingService(temp_file)
            mapping = service.load_author_team_mapping()

            # Should only have 3 valid entries
            assert len(mapping) == 3
            assert mapping["Александр Тихонов"] == "Корзинка и заказ"
            assert mapping["Александра Степаненкова"] == "Гео и сервисы"
            assert mapping["Алексей Какурин"] == "Каталог"
        finally:
            os.unlink(temp_file)

    def test_load_author_team_mapping_nonexistent_file(self):
        """Test loading nonexistent file (should return empty mapping)."""
        service = AuthorTeamMappingService("nonexistent_file.txt")
        mapping = service.load_author_team_mapping()

        assert mapping == {}

    def test_get_team_by_author_existing(self):
        """Test getting team for existing author."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Александр Тихонов;Корзинка и заказ\n")
            f.write("Александр Черкасов;Каталог\n")
            temp_file = f.name

        try:
            service = AuthorTeamMappingService(temp_file)
            assert service.get_team_by_author("Александр Тихонов") == "Корзинка и заказ"
            assert service.get_team_by_author("Александр Черкасов") == "Каталог"
        finally:
            os.unlink(temp_file)

    def test_get_team_by_author_nonexistent(self):
        """Test getting team for nonexistent author (should return 'Без команды')."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Александр Тихонов;Корзинка и заказ\n")
            temp_file = f.name

        try:
            service = AuthorTeamMappingService(temp_file)
            assert service.get_team_by_author("Несуществующий Автор") == "Без команды"
        finally:
            os.unlink(temp_file)

    def test_get_team_by_author_empty_team(self):
        """Test getting team for author with empty team (should return 'Без команды')."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Александр Тихонов;Корзинка и заказ\n")
            f.write("Александр Черкасов;\n")  # Empty team
            temp_file = f.name

        try:
            service = AuthorTeamMappingService(temp_file)
            assert service.get_team_by_author("Александр Тихонов") == "Корзинка и заказ"
            assert service.get_team_by_author("Александр Черкасов") == "Без команды"
        finally:
            os.unlink(temp_file)

    def test_get_all_teams(self):
        """Test getting all unique teams."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Александр Тихонов;Корзинка и заказ\n")
            f.write("Александр Черкасов;Каталог\n")
            f.write("Александра Степаненкова;Гео и сервисы\n")
            f.write("Алексей Какурин;Каталог\n")  # Duplicate team
            f.write("Алексей Красников;Оплаты\n")
            f.write("Алексей Никишанин;\n")  # Empty team -> "Без команды"
            temp_file = f.name

        try:
            service = AuthorTeamMappingService(temp_file)
            teams = service.get_all_teams()

            # Should have 5 unique teams including "Без команды"
            assert len(teams) == 5
            assert "Корзинка и заказ" in teams
            assert "Каталог" in teams
            assert "Гео и сервисы" in teams
            assert "Оплаты" in teams
            assert "Без команды" in teams
        finally:
            os.unlink(temp_file)

    def test_get_all_teams_empty_file(self):
        """Test getting teams from empty file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("")  # Empty file
            temp_file = f.name

        try:
            service = AuthorTeamMappingService(temp_file)
            teams = service.get_all_teams()
            assert teams == []
        finally:
            os.unlink(temp_file)

    def test_file_validation_correct_format(self):
        """Test file validation with correct format."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Александр Тихонов;Корзинка и заказ\n")
            f.write("Александр Черкасов;Каталог\n")
            temp_file = f.name

        try:
            service = AuthorTeamMappingService(temp_file)
            # Should not raise any exception
            mapping = service.load_author_team_mapping()
            assert len(mapping) == 2
        finally:
            os.unlink(temp_file)

    def test_file_validation_mixed_format(self):
        """Test file validation with mixed correct and incorrect lines."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Александр Тихонов;Корзинка и заказ\n")
            f.write("Invalid line\n")  # No semicolon
            f.write("Александр Черкасов;Каталог\n")
            f.write("Another invalid line\n")  # No semicolon
            f.write("Александра Степаненкова;Гео и сервисы\n")
            temp_file = f.name

        try:
            service = AuthorTeamMappingService(temp_file)
            # Should not raise exception, but should skip invalid lines
            mapping = service.load_author_team_mapping()
            assert len(mapping) == 3  # Only valid lines
        finally:
            os.unlink(temp_file)

    def test_real_file_loading(self):
        """Test loading from real test fixture file."""
        # Use the test fixture file
        test_file = Path(__file__).parent / "fixtures" / "test_cpo_authors.txt"
        service = AuthorTeamMappingService(str(test_file))

        mapping = service.load_author_team_mapping()
        teams = service.get_all_teams()

        # Should have loaded some data
        assert len(mapping) > 0
        assert len(teams) > 0

        # Test specific entries
        assert service.get_team_by_author("Александр Тихонов") == "Корзинка и заказ"
        assert service.get_team_by_author("Александр Георгиевич Сизых") == "Без команды"
        assert "Без команды" in teams

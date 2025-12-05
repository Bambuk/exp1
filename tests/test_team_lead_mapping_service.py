"""Tests for TeamLeadMappingService."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from radiator.commands.services.team_lead_mapping_service import TeamLeadMappingService


class TestTeamLeadMappingService:
    """Test cases for TeamLeadMappingService."""

    def test_load_team_lead_mapping_success(self):
        """Test successful loading of team-lead mapping file."""
        # Create temporary file with test data
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Авторизация;Лиза Купчинаус\n")
            f.write("Гео и сервисы;Саша Тихонов\n")
            f.write("Каталог;Марина Волкова\n")
            f.write("Корзинка и заказ;Саша Тихонов\n")
            f.write("Оплаты;Саша Тихонов\n")
            temp_file = f.name

        try:
            service = TeamLeadMappingService(temp_file)
            mapping = service.load_team_lead_mapping()

            assert len(mapping) == 5
            assert mapping["Авторизация"] == "Лиза Купчинаус"
            assert mapping["Гео и сервисы"] == "Саша Тихонов"
            assert mapping["Каталог"] == "Марина Волкова"
            assert mapping["Корзинка и заказ"] == "Саша Тихонов"
            assert mapping["Оплаты"] == "Саша Тихонов"
        finally:
            os.unlink(temp_file)

    def test_load_team_lead_mapping_empty_leads(self):
        """Test loading file with empty leads (should become 'Без команды')."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Авторизация;Лиза Купчинаус\n")
            f.write("Гео и сервисы;\n")  # Empty lead
            f.write("Каталог;Марина Волкова\n")
            f.write("Корзинка и заказ;\n")  # Empty lead
            temp_file = f.name

        try:
            service = TeamLeadMappingService(temp_file)
            mapping = service.load_team_lead_mapping()

            assert len(mapping) == 4
            assert mapping["Авторизация"] == "Лиза Купчинаус"
            assert mapping["Гео и сервисы"] == "Без команды"
            assert mapping["Каталог"] == "Марина Волкова"
            assert mapping["Корзинка и заказ"] == "Без команды"
        finally:
            os.unlink(temp_file)

    def test_load_team_lead_mapping_invalid_lines(self):
        """Test loading file with invalid lines (should be skipped)."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Авторизация;Лиза Купчинаус\n")
            f.write("Invalid line without semicolon\n")  # Invalid line
            f.write("Гео и сервисы;Саша Тихонов\n")
            f.write("Another invalid line\n")  # Invalid line
            f.write("Каталог;Марина Волкова\n")
            temp_file = f.name

        try:
            service = TeamLeadMappingService(temp_file)
            mapping = service.load_team_lead_mapping()

            # Should only have 3 valid entries
            assert len(mapping) == 3
            assert mapping["Авторизация"] == "Лиза Купчинаус"
            assert mapping["Гео и сервисы"] == "Саша Тихонов"
            assert mapping["Каталог"] == "Марина Волкова"
        finally:
            os.unlink(temp_file)

    def test_load_team_lead_mapping_nonexistent_file(self):
        """Test loading nonexistent file (should return empty mapping)."""
        service = TeamLeadMappingService("nonexistent_file.txt")
        mapping = service.load_team_lead_mapping()

        assert mapping == {}

    def test_get_lead_by_team_existing(self):
        """Test getting PM Lead for existing team."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Авторизация;Лиза Купчинаус\n")
            f.write("Гео и сервисы;Саша Тихонов\n")
            f.write("Каталог;Марина Волкова\n")
            temp_file = f.name

        try:
            service = TeamLeadMappingService(temp_file)
            assert service.get_lead_by_team("Авторизация") == "Лиза Купчинаус"
            assert service.get_lead_by_team("Гео и сервисы") == "Саша Тихонов"
            assert service.get_lead_by_team("Каталог") == "Марина Волкова"
        finally:
            os.unlink(temp_file)

    def test_get_lead_by_team_nonexistent(self):
        """Test getting PM Lead for nonexistent team (should return 'Без команды')."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Авторизация;Лиза Купчинаус\n")
            f.write("Гео и сервисы;Саша Тихонов\n")
            temp_file = f.name

        try:
            service = TeamLeadMappingService(temp_file)
            assert service.get_lead_by_team("Несуществующая команда") == "Без команды"
            assert service.get_lead_by_team("") == "Без команды"
        finally:
            os.unlink(temp_file)

    def test_load_team_lead_mapping_empty_lines(self):
        """Test loading file with empty lines (should be skipped)."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Авторизация;Лиза Купчинаус\n")
            f.write("\n")  # Empty line
            f.write("Гео и сервисы;Саша Тихонов\n")
            f.write("   \n")  # Line with only whitespace
            f.write("Каталог;Марина Волкова\n")
            temp_file = f.name

        try:
            service = TeamLeadMappingService(temp_file)
            mapping = service.load_team_lead_mapping()

            # Should only have 3 valid entries (empty lines skipped)
            assert len(mapping) == 3
            assert mapping["Авторизация"] == "Лиза Купчинаус"
            assert mapping["Гео и сервисы"] == "Саша Тихонов"
            assert mapping["Каталог"] == "Марина Волкова"
        finally:
            os.unlink(temp_file)

    def test_load_team_lead_mapping_empty_team_name(self):
        """Test loading file with empty team name (should be skipped)."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Авторизация;Лиза Купчинаус\n")
            f.write(";Саша Тихонов\n")  # Empty team name
            f.write("Гео и сервисы;Саша Тихонов\n")
            temp_file = f.name

        try:
            service = TeamLeadMappingService(temp_file)
            mapping = service.load_team_lead_mapping()

            # Should skip line with empty team name
            assert len(mapping) == 2
            assert mapping["Авторизация"] == "Лиза Купчинаус"
            assert mapping["Гео и сервисы"] == "Саша Тихонов"
        finally:
            os.unlink(temp_file)

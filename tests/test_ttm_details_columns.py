"""Tests for TTMDetailsColumns - single source of truth for column structure."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from radiator.commands.generate_ttm_details_report import TTMDetailsReportGenerator
from radiator.commands.models.ttm_details_columns import TTMDetailsColumns


class TestTTMDetailsColumns:
    """Test cases for TTMDetailsColumns."""

    def test_ttm_details_columns_exists(self):
        """Test that TTMDetailsColumns class exists and has required attributes."""
        # Check that class exists
        assert TTMDetailsColumns is not None

        # Check that COLUMN_NAMES exists
        assert hasattr(TTMDetailsColumns, "COLUMN_NAMES")
        assert isinstance(TTMDetailsColumns.COLUMN_NAMES, list)

        # Check that get_column_index method exists
        assert hasattr(TTMDetailsColumns, "get_column_index")
        assert callable(TTMDetailsColumns.get_column_index)

        # Check that get_column_count method exists
        assert hasattr(TTMDetailsColumns, "get_column_count")
        assert callable(TTMDetailsColumns.get_column_count)

        # Check that get_column_mapping method exists
        assert hasattr(TTMDetailsColumns, "get_column_mapping")
        assert callable(TTMDetailsColumns.get_column_mapping)

        # Check that validate_structure method exists
        assert hasattr(TTMDetailsColumns, "validate_structure")
        assert callable(TTMDetailsColumns.validate_structure)

    def test_ttm_details_columns_matches_generator(self, tmp_path):
        """Test that TTMDetailsColumns.COLUMN_NAMES matches generator output."""
        # Create mock database session
        mock_db = Mock()

        # Create generator
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock _collect_csv_rows to return empty list (we only need headers)
        generator._collect_csv_rows = Mock(return_value=[])

        # Generate CSV to get column structure
        csv_path = tmp_path / "test.csv"
        generator.generate_csv(str(csv_path))

        # Read CSV headers
        import csv

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)

        # Check that TTMDetailsColumns.COLUMN_NAMES matches generator headers
        assert (
            TTMDetailsColumns.COLUMN_NAMES == headers
        ), f"Column structure mismatch. Expected {headers}, got {TTMDetailsColumns.COLUMN_NAMES}"

    def test_column_structure_validation(self):
        """Test column structure validation."""
        # Check that structure is not empty
        assert (
            len(TTMDetailsColumns.COLUMN_NAMES) > 0
        ), "COLUMN_NAMES should not be empty"

        # Check that there are no duplicates
        assert len(TTMDetailsColumns.COLUMN_NAMES) == len(
            set(TTMDetailsColumns.COLUMN_NAMES)
        ), "COLUMN_NAMES should not contain duplicates"

        # Check that validate_structure works correctly
        assert TTMDetailsColumns.validate_structure(
            TTMDetailsColumns.COLUMN_NAMES
        ), "validate_structure should return True for correct structure"

        # Check that validate_structure returns False for incorrect structure
        incorrect_structure = TTMDetailsColumns.COLUMN_NAMES.copy()
        incorrect_structure[0] = "Wrong Column"
        assert not TTMDetailsColumns.validate_structure(
            incorrect_structure
        ), "validate_structure should return False for incorrect structure"

        # Check that validate_structure returns False for different length
        shorter_structure = TTMDetailsColumns.COLUMN_NAMES[:-1]
        assert not TTMDetailsColumns.validate_structure(
            shorter_structure
        ), "validate_structure should return False for different length structure"

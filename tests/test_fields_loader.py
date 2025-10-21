"""Tests for fields loader utility."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from radiator.utils.fields_loader import load_fields_list


class TestFieldsLoader:
    """Test cases for fields loader utility."""

    def test_load_fields_list_default_file(self):
        """Test loading fields from default file."""
        # This test will use the actual fields.txt file
        fields = load_fields_list()

        # Should return a list of strings
        assert isinstance(fields, list)
        assert all(isinstance(field, str) for field in fields)

        # Should contain expected fields
        assert "id" in fields
        assert "key" in fields
        assert "summary" in fields
        assert "customer" in fields

        # Should not contain empty strings
        assert "" not in fields
        assert all(field.strip() for field in fields)

    def test_load_fields_list_custom_file(self):
        """Test loading fields from custom file."""
        # Create temporary file with test data
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("field1\n")
            f.write("field2\n")
            f.write("field3\n")
            f.write("\n")  # Empty line
            f.write("field4\n")
            temp_file = Path(f.name)

        try:
            fields = load_fields_list(temp_file)

            # Should return list without empty strings
            assert fields == ["field1", "field2", "field3", "field4"]
        finally:
            temp_file.unlink()

    def test_load_fields_list_handles_empty_lines(self):
        """Test that empty lines are filtered out."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("field1\n")
            f.write("\n")  # Empty line
            f.write("  \n")  # Whitespace only
            f.write("field2\n")
            f.write("\n")  # Another empty line
            temp_file = Path(f.name)

        try:
            fields = load_fields_list(temp_file)

            # Should only return non-empty fields
            assert fields == ["field1", "field2"]
        finally:
            temp_file.unlink()

    def test_load_fields_list_handles_whitespace(self):
        """Test that whitespace is stripped from fields."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("  field1  \n")
            f.write("field2\n")
            f.write("  field3  \n")
            temp_file = Path(f.name)

        try:
            fields = load_fields_list(temp_file)

            # Should strip whitespace
            assert fields == ["field1", "field2", "field3"]
        finally:
            temp_file.unlink()

    def test_load_fields_list_missing_file(self):
        """Test handling of missing file."""
        non_existent_file = Path("/non/existent/file.txt")

        with pytest.raises(FileNotFoundError):
            load_fields_list(non_existent_file)

    def test_load_fields_list_empty_file(self):
        """Test handling of empty file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            # Write nothing to file
            temp_file = Path(f.name)

        try:
            fields = load_fields_list(temp_file)

            # Should return empty list
            assert fields == []
        finally:
            temp_file.unlink()

    def test_load_fields_list_only_empty_lines(self):
        """Test file with only empty lines."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("\n")
            f.write("  \n")
            f.write("\n")
            temp_file = Path(f.name)

        try:
            fields = load_fields_list(temp_file)

            # Should return empty list
            assert fields == []
        finally:
            temp_file.unlink()

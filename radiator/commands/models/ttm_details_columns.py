"""Single source of truth for TTM Details CSV column structure."""

from typing import Dict, List


def _validate_column_structure(column_names: List[str]) -> None:
    """
    Validate column structure.

    Args:
        column_names: List of column names to validate

    Raises:
        ValueError: If structure is invalid
    """
    if not column_names:
        raise ValueError("COLUMN_NAMES cannot be empty")

    if len(column_names) != len(set(column_names)):
        duplicates = [name for name in column_names if column_names.count(name) > 1]
        raise ValueError(f"COLUMN_NAMES contains duplicates: {set(duplicates)}")


class TTMDetailsColumns:
    """Single source of truth for TTM Details CSV column structure."""

    COLUMN_NAMES: List[str] = [
        "Ключ задачи",
        "Название",
        "Автор",
        "Команда",
        "PM Lead",
        "Квартал",
        "TTM",
        "Пауза",
        "Tail",
        "DevLT",
        "TTD",
        "TTD Pause",
        "Discovery backlog (дни)",
        "Готова к разработке (дни)",
        "Возвраты с Testing",
        "Возвраты с Внешний тест",
        "Всего возвратов",
        "Квартал TTD",
        "Создана",
        "Начало работы",
        "Завершено",
        "Разработка",
        "Завершена",
    ]

    # Validate structure at module import time
    _validate_column_structure(COLUMN_NAMES)

    @classmethod
    def get_column_index(cls, column_name: str) -> int:
        """
        Get 0-based index for column name.

        Args:
            column_name: Name of the column

        Returns:
            Column index (0-based)

        Raises:
            ValueError: If column name is not found
        """
        try:
            return cls.COLUMN_NAMES.index(column_name)
        except ValueError:
            raise ValueError(
                f"Column '{column_name}' not found in TTM Details structure"
            )

    @classmethod
    def get_column_count(cls) -> int:
        """
        Get total number of columns.

        Returns:
            Total number of columns
        """
        return len(cls.COLUMN_NAMES)

    @classmethod
    def get_column_mapping(cls) -> Dict[str, int]:
        """
        Get mapping of column names to indices.

        Returns:
            Dictionary mapping column names to their 0-based indices
        """
        return {name: idx for idx, name in enumerate(cls.COLUMN_NAMES)}

    @classmethod
    def validate_structure(cls, columns: List[str]) -> bool:
        """
        Validate that provided columns match expected structure.

        Args:
            columns: List of column names to validate

        Returns:
            True if columns match expected structure, False otherwise
        """
        return columns == cls.COLUMN_NAMES

#!/usr/bin/env python3
"""
Анализ использования БД в тестах - проверка, какие тесты могут писать в живую БД.
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def analyze_test_files():
    """Анализирует тестовые файлы на предмет использования БД."""
    tests_dir = project_root / "tests"

    issues = defaultdict(list)

    # Паттерны для поиска проблемных использований
    patterns = {
        "SessionLocal_direct": {
            "pattern": r"from radiator\.core\.database import.*SessionLocal",
            "description": "Прямой импорт SessionLocal - может использовать живую БД",
            "severity": "HIGH",
        },
        "SessionLocal_usage": {
            "pattern": r"SessionLocal\(\)",
            "description": "Прямое использование SessionLocal() - может подключиться к живой БД",
            "severity": "HIGH",
        },
        "TrackerSyncCommand_init": {
            "pattern": r"TrackerSyncCommand\(\)",
            "description": "Создание TrackerSyncCommand - в __init__ создается SessionLocal()",
            "severity": "MEDIUM",
        },
        "create_sync_log": {
            "pattern": r"create_sync_log|sync_log\s*=",
            "description": "Создание sync_log - может создать запись в tracker_sync_logs",
            "severity": "MEDIUM",
        },
        "run_method": {
            "pattern": r"\.run\(|sync_cmd\.run",
            "description": "Вызов метода run() - создает sync_log в БД",
            "severity": "HIGH",
        },
    }

    # Проходим по всем тестовым файлам
    for test_file in tests_dir.rglob("test_*.py"):
        if not test_file.is_file():
            continue

        content = test_file.read_text(encoding="utf-8")
        relative_path = test_file.relative_to(project_root)

        # Проверяем каждый паттерн
        for pattern_name, pattern_info in patterns.items():
            matches = re.finditer(pattern_info["pattern"], content)
            for match in matches:
                line_num = content[: match.start()].count("\n") + 1
                line_content = content.split("\n")[line_num - 1].strip()

                # Пропускаем комментарии и docstrings
                if (
                    line_content.startswith("#")
                    or '"""' in line_content
                    or "'''" in line_content
                ):
                    continue

                issues[pattern_name].append(
                    {
                        "file": str(relative_path),
                        "line": line_num,
                        "content": line_content[:100],
                        "description": pattern_info["description"],
                        "severity": pattern_info["severity"],
                    }
                )

    return issues


def check_db_session_usage():
    """Проверяет, используют ли тесты db_session фикстуру правильно."""
    tests_dir = project_root / "tests"

    problems = []

    for test_file in tests_dir.rglob("test_*.py"):
        if not test_file.is_file():
            continue

        content = test_file.read_text(encoding="utf-8")
        relative_path = test_file.relative_to(project_root)

        # Проверяем, есть ли использование SessionLocal() без db_session фикстуры
        if "SessionLocal()" in content:
            # Проверяем, есть ли параметр db_session в функции
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if "SessionLocal()" in line:
                    # Ищем определение функции выше
                    func_def_found = False
                    for j in range(i, max(0, i - 20), -1):
                        if re.match(r"^\s*def test_", lines[j]):
                            func_def = lines[j]
                            # Проверяем, есть ли db_session в параметрах
                            if "db_session" not in func_def:
                                problems.append(
                                    {
                                        "file": str(relative_path),
                                        "line": i + 1,
                                        "issue": "Использует SessionLocal() без db_session фикстуры",
                                        "code": line.strip(),
                                    }
                                )
                            func_def_found = True
                            break

    return problems


def main():
    """Основная функция анализа."""
    print("=" * 80)
    print("🔍 Анализ использования БД в тестах")
    print("=" * 80)

    # Анализ паттернов
    print("\n📊 Анализ паттернов использования БД...")
    issues = analyze_test_files()

    # Группируем по файлам
    files_issues = defaultdict(list)
    for pattern_name, pattern_issues in issues.items():
        for issue in pattern_issues:
            files_issues[issue["file"]].append({"pattern": pattern_name, **issue})

    # Выводим результаты
    if files_issues:
        print(
            f"\n⚠️  Найдено {len(files_issues)} файлов с потенциальными проблемами:\n"
        )

        for file_path, file_issues in sorted(files_issues.items()):
            print(f"📄 {file_path}")

            # Группируем по severity
            high_severity = [i for i in file_issues if i["severity"] == "HIGH"]
            medium_severity = [i for i in file_issues if i["severity"] == "MEDIUM"]

            if high_severity:
                print("   🔴 HIGH SEVERITY:")
                for issue in high_severity:
                    print(f"      • Строка {issue['line']}: {issue['description']}")
                    print(f"        {issue['content']}")

            if medium_severity:
                print("   🟡 MEDIUM SEVERITY:")
                for issue in medium_severity:
                    print(f"      • Строка {issue['line']}: {issue['description']}")
                    print(f"        {issue['content']}")

            print()
    else:
        print("✅ Проблемных паттернов не найдено")

    # Проверка использования db_session
    print("\n📊 Проверка использования db_session фикстуры...")
    problems = check_db_session_usage()

    if problems:
        print(f"\n⚠️  Найдено {len(problems)} проблем:\n")
        for problem in problems:
            print(f"📄 {problem['file']}:{problem['line']}")
            print(f"   {problem['issue']}")
            print(f"   Код: {problem['code']}")
            print()
    else:
        print("✅ Все использования SessionLocal() используют db_session фикстуру")

    # Итоговая статистика
    print("\n" + "=" * 80)
    print("📈 Итоговая статистика:")
    print(f"   Файлов с проблемами: {len(files_issues)}")
    print(
        f"   Всего проблемных мест: {sum(len(issues) for issues in files_issues.values())}"
    )
    print("=" * 80)

    # Рекомендации
    print("\n💡 Рекомендации:")
    print(
        "   1. Все тесты должны использовать фикстуру db_session из conftest_tracker.py"
    )
    print("   2. Не использовать SessionLocal() напрямую в тестах")
    print(
        "   3. TrackerSyncCommand должен получать db_session через параметр или фикстуру"
    )
    print("   4. Проверить, что ENVIRONMENT=test установлен при запуске тестов")
    print()


if __name__ == "__main__":
    main()

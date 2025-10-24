#!/usr/bin/env python3
"""
Скрипт для воспроизведения бага с подсчетом возвратов.

Проблема: build_fullstack_hierarchy_batched добавляет все найденные задачи
ко всем CPO задачам, вместо отслеживания правильной принадлежности.
"""

from radiator.commands.services.data_service import DataService
from radiator.commands.services.testing_returns_service import TestingReturnsService
from radiator.core.database import SessionLocal


def main():
    db = SessionLocal()
    returns_service = TestingReturnsService(db)
    data_service = DataService(db)

    cpo_keys = ["CPO-5770", "CPO-4370"]

    print("\n" + "=" * 80)
    print("ВОСПРОИЗВЕДЕНИЕ БАГА С ПОДСЧЕТОМ ВОЗВРАТОВ")
    print("=" * 80)

    for cpo_key in cpo_keys:
        print(f"\n{'='*80}")
        print(f"Анализ: {cpo_key}")
        print(f"{'='*80}")

        # 1. Прямые FULLSTACK связи
        direct_links = returns_service.get_fullstack_links(cpo_key)
        print(f"\n1. Прямые FULLSTACK связи: {direct_links}")

        # 2. ПРАВИЛЬНЫЙ способ (через get_task_hierarchy для каждой связи)
        correct_tasks = set()
        for epic_key in direct_links:
            hierarchy = returns_service.get_task_hierarchy(epic_key)
            correct_tasks.update(hierarchy)

        print(f"\n2. ПРАВИЛЬНАЯ иерархия (get_task_hierarchy):")
        print(f"   Всего задач: {len(correct_tasks)}")
        print(f"   Задачи: {sorted(correct_tasks)}")

        # Подсчитаем правильные возвраты
        correct_testing = 0
        correct_external = 0
        for task_key in correct_tasks:
            history = data_service.get_task_history_by_key(task_key)
            if history:
                test_ret, ext_ret = returns_service.calculate_testing_returns_for_task(
                    task_key, history
                )
                correct_testing += test_ret
                correct_external += ext_ret

        print(f"\n3. ПРАВИЛЬНЫЕ возвраты:")
        print(f"   Testing: {correct_testing}")
        print(f"   External: {correct_external}")
        print(f"   Всего: {correct_testing + correct_external}")

    # 3. БАГОВАННЫЙ способ (через build_fullstack_hierarchy_batched)
    print(f"\n{'='*80}")
    print("БАГОВАННЫЙ метод (build_fullstack_hierarchy_batched)")
    print(f"{'='*80}")

    buggy_hierarchy = returns_service.build_fullstack_hierarchy_batched(
        cpo_keys, max_depth=6
    )

    for cpo_key in cpo_keys:
        buggy_tasks = set(buggy_hierarchy.get(cpo_key, []))

        print(f"\n{cpo_key}:")
        print(f"   Всего задач: {len(buggy_tasks)}")
        print(f"   Задачи: {sorted(buggy_tasks)}")

        # Подсчитаем багованные возвраты
        buggy_testing = 0
        buggy_external = 0
        for task_key in buggy_tasks:
            history = data_service.get_task_history_by_key(task_key)
            if history:
                test_ret, ext_ret = returns_service.calculate_testing_returns_for_task(
                    task_key, history
                )
                buggy_testing += test_ret
                buggy_external += ext_ret

        print(f"\n   БАГОВАННЫЕ возвраты:")
        print(f"   Testing: {buggy_testing}")
        print(f"   External: {buggy_external}")
        print(f"   Всего: {buggy_testing + buggy_external}")

    # 4. Сравнение и пересечения
    print(f"\n{'='*80}")
    print("АНАЛИЗ ПРОБЛЕМЫ")
    print(f"{'='*80}")

    buggy_5770 = set(buggy_hierarchy.get("CPO-5770", []))
    buggy_4370 = set(buggy_hierarchy.get("CPO-4370", []))

    intersection = buggy_5770 & buggy_4370
    print(f"\nПересечение между CPO-5770 и CPO-4370: {len(intersection)} задач")
    print(f"Это означает, что {len(intersection)} задач считаются дважды!")
    print(f"Задачи в пересечении: {sorted(intersection)}")

    # 5. Прямые связи не должны пересекаться
    direct_5770 = set(returns_service.get_fullstack_links("CPO-5770"))
    direct_4370 = set(returns_service.get_fullstack_links("CPO-4370"))

    print(f"\n{'='*80}")
    print("ВЫВОД")
    print(f"{'='*80}")
    print(f"\nПрямые связи CPO-5770: {direct_5770}")
    print(f"Прямые связи CPO-4370: {direct_4370}")
    print(f"Пересечение прямых связей: {direct_5770 & direct_4370}")
    print(f"\n❌ БАГ: Метод build_fullstack_hierarchy_batched добавляет ВСЕ найденные")
    print(f"   дочерние задачи ко ВСЕМ CPO задачам, независимо от реальной иерархии!")

    db.close()


if __name__ == "__main__":
    main()

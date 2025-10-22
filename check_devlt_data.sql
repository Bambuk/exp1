-- SQL-запрос для проверки задач с валидными DevLT данными
-- Ищет CPO-задачи с "МП / В работе" и "МП / Внешний тест" длительностью > 5 минут
-- И которые перешли в "Готова к разработке" или done статусы в 2025 году

WITH task_statuses AS (
    -- Получаем все статусы для каждой задачи
    SELECT
        t.key,
        t.summary,
        sh.status,
        sh.start_date,
        sh.end_date,
        CASE
            WHEN sh.end_date IS NULL THEN NULL
            ELSE EXTRACT(EPOCH FROM (sh.end_date - sh.start_date)) / 60  -- длительность в минутах
        END as duration_minutes
    FROM tracker_tasks t
    JOIN tracker_task_history sh ON t.id = sh.task_id
    WHERE t.key LIKE 'CPO-%'
        AND sh.status IN ('МП / В работе', 'МП / Внешний тест')
    ORDER BY t.key, sh.start_date
),

tasks_with_2025_progress AS (
    -- Задачи, которые перешли в "Готова к разработке" или done статусы в 2025 году
    SELECT DISTINCT t.key
    FROM tracker_tasks t
    JOIN tracker_task_history sh ON t.id = sh.task_id
    WHERE t.key LIKE 'CPO-%'
        AND (
            (sh.status = 'Готова к разработке' AND sh.start_date >= '2025-01-01' AND sh.start_date < '2026-01-01')
            OR (sh.status IN ('Done', 'Готово', 'Закрыто') AND sh.start_date >= '2025-01-01' AND sh.start_date < '2026-01-01')
        )
),

valid_work_statuses AS (
    -- Находим задачи с валидными "МП / В работе" (с end_date и > 5 минут)
    SELECT DISTINCT key
    FROM task_statuses
    WHERE status = 'МП / В работе'
        AND end_date IS NOT NULL
        AND duration_minutes > 5
),

valid_external_test_statuses AS (
    -- Находим задачи с валидными "МП / Внешний тест" (> 5 минут или открытые)
    SELECT DISTINCT key
    FROM task_statuses
    WHERE status = 'МП / Внешний тест'
        AND (end_date IS NULL OR duration_minutes > 5)
),

tasks_with_both_statuses AS (
    -- Задачи, у которых есть и валидные "МП / В работе", и валидные "МП / Внешний тест"
    SELECT w.key
    FROM valid_work_statuses w
    INNER JOIN valid_external_test_statuses e ON w.key = e.key
),

tasks_with_2025_progress_and_devlt AS (
    -- Задачи с валидными DevLT И прогрессом в 2025 году
    SELECT b.key
    FROM tasks_with_both_statuses b
    INNER JOIN tasks_with_2025_progress p ON b.key = p.key
)

-- Основной запрос: показываем детали для задач с валидными DevLT
SELECT
    t.key,
    t.summary,
    t.status as current_status,
    t.created_at,
    -- Статистика по "МП / В работе"
    (SELECT COUNT(*)
     FROM task_statuses ts
     WHERE ts.key = t.key AND ts.status = 'МП / В работе'
         AND ts.end_date IS NOT NULL AND ts.duration_minutes > 5) as valid_work_count,
    -- Статистика по "МП / Внешний тест"
    (SELECT COUNT(*)
     FROM task_statuses ts
     WHERE ts.key = t.key AND ts.status = 'МП / Внешний тест'
         AND (ts.end_date IS NULL OR ts.duration_minutes > 5)) as valid_external_test_count,
    -- Первое валидное "МП / В работе"
    (SELECT MIN(ts.start_date)
     FROM task_statuses ts
     WHERE ts.key = t.key AND ts.status = 'МП / В работе'
         AND ts.end_date IS NOT NULL AND ts.duration_minutes > 5) as first_valid_work,
    -- Последнее валидное "МП / Внешний тест"
    (SELECT MAX(ts.start_date)
     FROM task_statuses ts
     WHERE ts.key = t.key AND ts.status = 'МП / Внешний тест'
         AND (ts.end_date IS NULL OR ts.duration_minutes > 5)) as last_valid_external_test

FROM tracker_tasks t
INNER JOIN tasks_with_2025_progress_and_devlt twb ON t.key = twb.key
ORDER BY t.key;

-- Дополнительная статистика
SELECT
    'Всего CPO задач' as metric,
    COUNT(*) as value
FROM tracker_tasks
WHERE key LIKE 'CPO-%'

UNION ALL

SELECT
    'Задач с валидными DevLT' as metric,
    COUNT(DISTINCT t.key) as value
FROM tracker_tasks t
WHERE t.key LIKE 'CPO-%'
    AND EXISTS (
        SELECT 1 FROM tracker_task_history sh1
        WHERE sh1.task_id = t.id
            AND sh1.status = 'МП / В работе'
            AND sh1.end_date IS NOT NULL
            AND EXTRACT(EPOCH FROM (sh1.end_date - sh1.start_date)) / 60 > 5
    )
    AND EXISTS (
        SELECT 1 FROM tracker_task_history sh2
        WHERE sh2.task_id = t.id
            AND sh2.status = 'МП / Внешний тест'
            AND (sh2.end_date IS NULL OR EXTRACT(EPOCH FROM (sh2.end_date - sh2.start_date)) / 60 > 5)
    )

UNION ALL

SELECT
    'Задач с валидными DevLT и прогрессом в 2025' as metric,
    COUNT(DISTINCT t.key) as value
FROM tracker_tasks t
WHERE t.key LIKE 'CPO-%'
    AND EXISTS (
        SELECT 1 FROM tracker_task_history sh1
        WHERE sh1.task_id = t.id
            AND sh1.status = 'МП / В работе'
            AND sh1.end_date IS NOT NULL
            AND EXTRACT(EPOCH FROM (sh1.end_date - sh1.start_date)) / 60 > 5
    )
    AND EXISTS (
        SELECT 1 FROM tracker_task_history sh2
        WHERE sh2.task_id = t.id
            AND sh2.status = 'МП / Внешний тест'
            AND (sh2.end_date IS NULL OR EXTRACT(EPOCH FROM (sh2.end_date - sh2.start_date)) / 60 > 5)
    )
    AND EXISTS (
        SELECT 1 FROM tracker_task_history sh3
        WHERE sh3.task_id = t.id
            AND (
                (sh3.status = 'Готова к разработке' AND sh3.start_date >= '2025-01-01' AND sh3.start_date < '2026-01-01')
                OR (sh3.status IN ('Done', 'Готово', 'Закрыто') AND sh3.start_date >= '2025-01-01' AND sh3.start_date < '2026-01-01')
            )
    );

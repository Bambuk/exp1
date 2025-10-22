-- Анализ квартального распределения задач с валидными DevLT
-- Показывает в какие кварталы попадают 270 задач с валидными DevLT

WITH valid_devlt_tasks AS (
    -- Задачи с валидными DevLT данными
    SELECT DISTINCT t.key, t.summary, t.created_at
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
),

devlt_target_dates AS (
    -- Находим дату последнего "МП / Внешний тест" для каждой задачи (для квартальной привязки)
    SELECT
        vdt.key,
        vdt.summary,
        vdt.created_at,
        MAX(sh.start_date) as last_external_test_date
    FROM valid_devlt_tasks vdt
    JOIN tracker_task_history sh ON sh.task_id = (
        SELECT t.id FROM tracker_tasks t WHERE t.key = vdt.key
    )
    WHERE sh.status = 'МП / Внешний тест'
        AND (sh.end_date IS NULL OR EXTRACT(EPOCH FROM (sh.end_date - sh.start_date)) / 60 > 5)
    GROUP BY vdt.key, vdt.summary, vdt.created_at
)

-- Основной анализ: распределение по кварталам
SELECT
    CASE
        WHEN EXTRACT(QUARTER FROM last_external_test_date) = 1 THEN
            EXTRACT(YEAR FROM last_external_test_date) || ' Q1'
        WHEN EXTRACT(QUARTER FROM last_external_test_date) = 2 THEN
            EXTRACT(YEAR FROM last_external_test_date) || ' Q2'
        WHEN EXTRACT(QUARTER FROM last_external_test_date) = 3 THEN
            EXTRACT(YEAR FROM last_external_test_date) || ' Q3'
        WHEN EXTRACT(QUARTER FROM last_external_test_date) = 4 THEN
            EXTRACT(YEAR FROM last_external_test_date) || ' Q4'
    END as quarter,
    COUNT(*) as tasks_count,
    MIN(last_external_test_date) as earliest_date,
    MAX(last_external_test_date) as latest_date
FROM devlt_target_dates
GROUP BY
    EXTRACT(YEAR FROM last_external_test_date),
    EXTRACT(QUARTER FROM last_external_test_date)
ORDER BY
    EXTRACT(YEAR FROM last_external_test_date),
    EXTRACT(QUARTER FROM last_external_test_date);

-- Дополнительная статистика: задачи без DevLT в отчете
SELECT
    'Задач с валидными DevLT' as metric,
    COUNT(*) as count
FROM (
    SELECT DISTINCT t.key
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
) valid_tasks

UNION ALL

SELECT
    'Задач в отчете с DevLT' as metric,
    32 as count  -- Из вашего сообщения

UNION ALL

SELECT
    'Потерянных задач' as metric,
    (SELECT COUNT(*) FROM (
        SELECT DISTINCT t.key
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
    ) valid_tasks) - 32 as count;

-- Примеры задач из каждого квартала (первые 20)
SELECT
    CASE
        WHEN EXTRACT(QUARTER FROM last_external_test_date) = 1 THEN
            EXTRACT(YEAR FROM last_external_test_date) || ' Q1'
        WHEN EXTRACT(QUARTER FROM last_external_test_date) = 2 THEN
            EXTRACT(YEAR FROM last_external_test_date) || ' Q2'
        WHEN EXTRACT(QUARTER FROM last_external_test_date) = 3 THEN
            EXTRACT(YEAR FROM last_external_test_date) || ' Q3'
        WHEN EXTRACT(QUARTER FROM last_external_test_date) = 4 THEN
            EXTRACT(YEAR FROM last_external_test_date) || ' Q4'
    END as quarter,
    key,
    summary,
    last_external_test_date
FROM (
    SELECT
        t.key,
        t.summary,
        MAX(sh.start_date) as last_external_test_date
    FROM tracker_tasks t
    JOIN tracker_task_history sh ON sh.task_id = t.id
    WHERE t.key LIKE 'CPO-%'
        AND sh.status = 'МП / Внешний тест'
        AND (sh.end_date IS NULL OR EXTRACT(EPOCH FROM (sh.end_date - sh.start_date)) / 60 > 5)
        AND EXISTS (
            SELECT 1 FROM tracker_task_history sh1
            WHERE sh1.task_id = t.id
                AND sh1.status = 'МП / В работе'
                AND sh1.end_date IS NOT NULL
                AND EXTRACT(EPOCH FROM (sh1.end_date - sh1.start_date)) / 60 > 5
        )
    GROUP BY t.key, t.summary
) devlt_target_dates
ORDER BY
    EXTRACT(YEAR FROM last_external_test_date),
    EXTRACT(QUARTER FROM last_external_test_date),
    key
LIMIT 20;

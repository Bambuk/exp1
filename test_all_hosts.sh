#!/bin/bash

# Скрипт для тестирования доступности всех хостов, используемых в проекте

echo "=== Тестирование доступности всех хостов проекта ==="
echo ""

# Функция для тестирования хоста
test_host() {
    local host=$1
    local description=$2

    echo -n "Тестируем $host ($description)... "

    if ping -c 1 -W 3 "$host" >/dev/null 2>&1; then
        echo "✅ OK"
        return 0
    else
        echo "❌ FAIL"
        return 1
    fi
}

# Функция для тестирования HTTP запроса
test_http() {
    local url=$1
    local description=$2

    echo -n "Тестируем HTTP $url ($description)... "

    if curl -s --connect-timeout 5 --max-time 10 "$url" >/dev/null 2>&1; then
        echo "✅ OK"
        return 0
    else
        echo "❌ FAIL"
        return 1
    fi
}

echo "🔍 Тестируем хосты Yandex Tracker:"
test_host "api.tracker.yandex.net" "API Tracker"
test_host "tracker.yandex.ru" "Tracker Web Interface"

echo ""
echo "🔍 Тестируем Google APIs:"
test_host "www.googleapis.com" "Google APIs"

echo ""
echo "🔍 Тестируем HTTP запросы:"
test_http "https://api.tracker.yandex.net/v2/" "Tracker API v2"
test_http "https://api.tracker.yandex.net/v3/" "Tracker API v3"
test_http "https://www.googleapis.com/auth/spreadsheets" "Google Sheets API"

echo ""
echo "🔍 Проверяем текущие маршруты:"
echo "Маршруты к Яндексу:"
ip route | grep -E "(87\.250\.|5\.45\.207|77\.88\.8|93\.158\.134|95\.108\.128|178\.154\.128)" || echo "Маршруты не найдены"

echo ""
echo "Маршруты к Google:"
ip route | grep -E "(142\.251\.|142\.250\.|172\.217\.|74\.125\.)" || echo "Маршруты не найдены"

echo ""
echo "=== Тестирование завершено ==="

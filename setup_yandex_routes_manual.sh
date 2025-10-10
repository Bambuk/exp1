#!/bin/bash

# Упрощенный скрипт для настройки маршрутизации к серверам Яндекса
# Этот скрипт показывает команды, которые нужно выполнить с правами root

echo "=== Настройка маршрутизации для обхода VPN при обращении к серверам Яндекса ==="
echo ""

# Получаем основной шлюз (не VPN)
MAIN_GATEWAY=$(ip route | grep "default via" | grep -v "tun0" | awk '{print $3}' | head -1)
MAIN_INTERFACE=$(ip route | grep "default via" | grep -v "tun0" | awk '{print $5}' | head -1)

if [ -z "$MAIN_GATEWAY" ]; then
    echo "Ошибка: Не удалось найти основной шлюз"
    exit 1
fi

echo "Обнаружен основной шлюз: $MAIN_GATEWAY"
echo "Обнаружен основной интерфейс: $MAIN_INTERFACE"
echo ""

# IP-адреса серверов Яндекса и связанных сервисов
YANDEX_IPS=(
    # API Tracker
    "87.250.251.121"  # api.tracker.yandex.net
    "87.250.250.242"  # api.b.tracker.yandex.net (альтернативный)
    "93.158.134.211"  # tracker.yandex.ru

    # Диапазоны IP Яндекса
    "5.45.207.0/24"   # Диапазон IP Яндекса
    "77.88.8.0/24"    # Диапазон IP Яндекса
    "87.250.224.0/19" # Диапазон IP Яндекса
    "93.158.134.0/24" # Диапазон IP Яндекса
    "95.108.128.0/17" # Диапазон IP Яндекса
    "178.154.128.0/17" # Диапазон IP Яндекса

    # Google APIs (для Google Sheets интеграции)
    "142.251.36.202"  # www.googleapis.com
    "142.251.36.234"  # www.googleapis.com
    "142.251.37.10"   # www.googleapis.com
    "142.251.36.170"  # www.googleapis.com
    "142.250.0.0/16"  # Диапазон Google APIs
    "172.217.0.0/16"  # Диапазон Google APIs
    "74.125.0.0/16"   # Диапазон Google APIs
)

echo "Для настройки маршрутизации выполните следующие команды с правами root:"
echo ""

# Удаляем существующие маршруты к Яндексу (если есть)
echo "# Удаление существующих маршрутов к Яндексу (если есть):"
for ip in "${YANDEX_IPS[@]}"; do
    echo "ip route del $ip via $MAIN_GATEWAY dev $MAIN_INTERFACE 2>/dev/null || true"
done

echo ""

# Добавляем новые маршруты
echo "# Добавление маршрутов к серверам Яндекса:"
for ip in "${YANDEX_IPS[@]}"; do
    echo "ip route add $ip via $MAIN_GATEWAY dev $MAIN_INTERFACE"
done

echo ""
echo "=== Альтернативный способ - выполнить все команды одной строкой ==="
echo ""

# Создаем команду для выполнения всех операций
COMMANDS=""
for ip in "${YANDEX_IPS[@]}"; do
    COMMANDS="$COMMANDS ip route del $ip via $MAIN_GATEWAY dev $MAIN_INTERFACE 2>/dev/null || true;"
done

for ip in "${YANDEX_IPS[@]}"; do
    COMMANDS="$COMMANDS ip route add $ip via $MAIN_GATEWAY dev $MAIN_INTERFACE;"
done

echo "sudo bash -c \"$COMMANDS\""

echo ""
echo "=== Проверка после настройки ==="
echo "ip route | grep -E '(87\\.250\\.|5\\.45\\.207|77\\.88\\.8|93\\.158\\.134|95\\.108\\.128|178\\.154\\.128)'"
echo "ping -c 3 api.tracker.yandex.net"

echo ""
echo "=== Для постоянного сохранения маршрутов ==="
echo "1. Добавьте команды в /etc/rc.local"
echo "2. Или создайте systemd service (используйте install_yandex_routes.sh)"

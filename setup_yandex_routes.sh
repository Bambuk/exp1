#!/bin/bash

# Скрипт для настройки маршрутизации к серверам Яндекса в обход VPN
# Запускать с правами root (sudo)

echo "Настройка маршрутизации для обхода VPN при обращении к серверам Яндекса..."

# Получаем основной шлюз (не VPN)
MAIN_GATEWAY=$(ip route | grep "default via" | grep -v "tun0" | awk '{print $3}' | head -1)
MAIN_INTERFACE=$(ip route | grep "default via" | grep -v "tun0" | awk '{print $5}' | head -1)

if [ -z "$MAIN_GATEWAY" ]; then
    echo "Ошибка: Не удалось найти основной шлюз"
    exit 1
fi

echo "Основной шлюз: $MAIN_GATEWAY"
echo "Основной интерфейс: $MAIN_INTERFACE"

# Функция для разрешения DNS
resolve_dns() {
    local hostname="$1"
    local ips=()

    echo "Разрешение DNS для $hostname..." >&2

    # Пробуем dig, если доступен
    if command -v dig >/dev/null 2>&1; then
        ips=($(dig +short "$hostname" | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'))
    # Иначе используем nslookup
    elif command -v nslookup >/dev/null 2>&1; then
        ips=($(nslookup "$hostname" | grep -E '^Address:' | awk '{print $2}' | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'))
    # Fallback на getent
    elif command -v getent >/dev/null 2>&1; then
        ips=($(getent hosts "$hostname" | awk '{print $1}' | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'))
    else
        echo "Ошибка: Не найдены команды для DNS-разрешения (dig, nslookup, getent)" >&2
        return 1
    fi

    if [ ${#ips[@]} -eq 0 ]; then
        echo "Предупреждение: Не удалось разрешить $hostname" >&2
        return 1
    fi

    echo "Найдены IP для $hostname: ${ips[*]}" >&2
    printf '%s\n' "${ips[@]}"
    return 0
}

# Доменные имена для динамического разрешения DNS
YANDEX_HOSTS=(
    "api.tracker.yandex.net"
    "api.b.tracker.yandex.net"
    "tracker.yandex.ru"
)

# Статические IP-диапазоны Яндекса (не изменяются)
YANDEX_IP_RANGES=(
    "5.45.207.0/24"   # Диапазон IP Яндекса
    "77.88.8.0/24"    # Диапазон IP Яндекса
    "87.250.224.0/19" # Диапазон IP Яндекса
    "93.158.134.0/24" # Диапазон IP Яндекса
    "95.108.128.0/17" # Диапазон IP Яндекса
    "178.154.128.0/17" # Диапазон IP Яндекса
)

# Google APIs (для Google Sheets интеграции)
GOOGLE_IP_RANGES=(
    "142.250.0.0/16"  # Диапазон Google APIs
    "172.217.0.0/16"  # Диапазон Google APIs
    "74.125.0.0/16"   # Диапазон Google APIs
)

# Собираем все IP для маршрутизации
ALL_IPS=()

# Разрешаем DNS для хостов Яндекса
echo "Разрешение DNS для хостов Яндекса..."
for host in "${YANDEX_HOSTS[@]}"; do
    resolved_ips=($(resolve_dns "$host"))
    if [ $? -eq 0 ]; then
        ALL_IPS+=("${resolved_ips[@]}")
    else
        echo "Пропускаем $host из-за ошибки DNS-разрешения"
    fi
done

# Добавляем статические IP-диапазоны
ALL_IPS+=("${YANDEX_IP_RANGES[@]}")
ALL_IPS+=("${GOOGLE_IP_RANGES[@]}")

echo "Всего IP/диапазонов для маршрутизации: ${#ALL_IPS[@]}"

# Удаляем существующие маршруты (если есть)
echo "Удаление существующих маршрутов..."
for ip in "${ALL_IPS[@]}"; do
    ip route del "$ip" via "$MAIN_GATEWAY" dev "$MAIN_INTERFACE" 2>/dev/null || true
done

# Добавляем новые маршруты
echo "Добавление маршрутов к серверам Яндекса и Google..."
for ip in "${ALL_IPS[@]}"; do
    echo "Добавляем маршрут для $ip через $MAIN_GATEWAY"
    ip route add "$ip" via "$MAIN_GATEWAY" dev "$MAIN_INTERFACE"
    if [ $? -eq 0 ]; then
        echo "✓ Маршрут для $ip добавлен успешно"
    else
        echo "✗ Ошибка добавления маршрута для $ip"
    fi
done

# Проверяем результат
echo ""
echo "Текущие маршруты к Яндексу и Google:"
ip route | grep -E "(87\.250\.|5\.45\.207|77\.88\.8|93\.158\.134|95\.108\.128|178\.154\.128|142\.250\.|172\.217\.|74\.125\.)"

echo ""
echo "Проверка доступности API Яндекса:"
for host in "${YANDEX_HOSTS[@]}"; do
    echo "Проверка $host:"
    ping -c 2 "$host" 2>/dev/null || echo "  Недоступен"
done

echo ""
echo "Настройка завершена!"
echo "Для постоянного сохранения маршрутов добавьте их в /etc/rc.local или создайте systemd service"

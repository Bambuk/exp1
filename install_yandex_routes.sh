#!/bin/bash

# Скрипт для установки и управления маршрутами к Яндексу
# Запускать с правами root (sudo)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="/etc/systemd/system/yandex-routes.service"
ROUTE_SCRIPT="$SCRIPT_DIR/setup_yandex_routes.sh"

case "$1" in
    "install")
        echo "Установка маршрутов к Яндексу..."

        # Делаем скрипт исполняемым
        chmod +x "$ROUTE_SCRIPT"

        # Копируем service файл
        cp "$SCRIPT_DIR/yandex-routes.service" "$SERVICE_FILE"

        # Перезагружаем systemd
        systemctl daemon-reload

        # Включаем сервис
        systemctl enable yandex-routes.service

        # Запускаем сервис
        systemctl start yandex-routes.service

        echo "✓ Сервис установлен и запущен"
        ;;

    "uninstall")
        echo "Удаление сервиса маршрутов к Яндексу..."

        # Останавливаем сервис
        systemctl stop yandex-routes.service 2>/dev/null || true

        # Отключаем сервис
        systemctl disable yandex-routes.service 2>/dev/null || true

        # Удаляем service файл
        rm -f "$SERVICE_FILE"

        # Перезагружаем systemd
        systemctl daemon-reload

        echo "✓ Сервис удален"
        ;;

    "start")
        echo "Запуск маршрутов к Яндексу..."
        systemctl start yandex-routes.service
        ;;

    "stop")
        echo "Остановка маршрутов к Яндексу..."
        systemctl stop yandex-routes.service
        ;;

    "status")
        echo "Статус сервиса маршрутов к Яндексу:"
        systemctl status yandex-routes.service
        echo ""
        echo "Текущие маршруты к Яндексу:"
        ip route | grep -E "(87\.250\.|5\.45\.207|77\.88\.8|93\.158\.134|95\.108\.128|178\.154\.128)" || echo "Маршруты не найдены"
        ;;

    "test")
        echo "Тестирование доступности API Яндекса:"
        ping -c 3 api.tracker.yandex.net
        echo ""
        echo "Проверка маршрута:"
        traceroute api.tracker.yandex.net
        ;;

    *)
        echo "Использование: $0 {install|uninstall|start|stop|status|test}"
        echo ""
        echo "Команды:"
        echo "  install   - Установить и настроить сервис"
        echo "  uninstall - Удалить сервис"
        echo "  start     - Запустить маршруты"
        echo "  stop      - Остановить маршруты"
        echo "  status    - Показать статус"
        echo "  test      - Протестировать подключение"
        exit 1
        ;;
esac

#!/usr/bin/env python3
"""
Тест получения одной задачи по ID через Tracker API
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import requests

# Загружаем переменные окружения из .env
load_dotenv()

def test_single_task():
    """Тестируем получение одной задачи по ID."""
    print("🔍 Тестируем получение одной задачи по ID...")
    
    # Проверяем переменные окружения
    token = os.getenv('TRACKER_API_TOKEN')
    org_id = os.getenv('TRACKER_ORG_ID')
    
    print(f"Token: {token[:20]}..." if token else "Token: не найден")
    print(f"Org ID: {org_id}")
    
    if not token or not org_id:
        print("❌ Переменные окружения не настроены")
        return False
    
    # Убираем кавычки из токена и org_id если они есть
    token = token.strip('"')
    org_id = org_id.strip('"')
    
    print(f"Token (cleaned): {token[:20]}...")
    print(f"Org ID (cleaned): {org_id}")
    
    # Тестируем прямой запрос к API
    headers = {
        'Authorization': f'OAuth {token}',
        'X-Org-ID': org_id,
        'Content-Type': 'application/json'
    }
    
    # Пробуем получить информацию об организации
    org_url = f"https://api.tracker.yandex.net/v2/organizations/{org_id}"
    print(f"📡 Тестируем запрос к организации: {org_url}")
    
    try:
        response = requests.get(org_url, headers=headers)
        print(f"Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            org_data = response.json()
            print(f"✅ Организация получена: {org_data.get('name', 'N/A')}")
        else:
            print(f"❌ Ошибка при получении организации: {response.text}")
            
    except Exception as e:
        print(f"❌ Ошибка при запросе: {e}")
    
    # Теперь попробуем получить одну задачу
    # Сначала попробуем простой поиск
    search_url = "https://api.tracker.yandex.net/v2/issues"
    params = {
        'query': '',
        'limit': 1
    }
    
    print(f"\n📡 Тестируем поиск задач: {search_url}")
    
    try:
        response = requests.get(search_url, headers=headers, params=params)
        print(f"Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            tasks_data = response.json()
            print(f"✅ Задачи получены: {len(tasks_data)}")
            if tasks_data:
                print(f"Первая задача: {tasks_data[0].get('key', 'N/A')}")
        else:
            print(f"❌ Ошибка при поиске задач: {response.text}")
            
    except Exception as e:
        print(f"❌ Ошибка при запросе: {e}")
    
    return True

if __name__ == "__main__":
    test_single_task()

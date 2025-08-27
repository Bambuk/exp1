# Yandex Tracker API - Примеры запросов

## Поиск задач

### POST /v3/issues/_search
**Описание:** Поиск задач с фильтрацией

**URL:** `POST /v3/issues/_search?perPage=15`

**Заголовки:**
```
Host: api.tracker.yandex.net
Authorization: OAuth <OAuth-токен>
X-Org-ID или X-Cloud-Org-ID: <идентификатор_организации>
```

**Тело запроса:**
```json
{
  "filter": {
    "queue": "TREK",
    "assignee": "<user_login>"
  }
}
```

**Параметры:**
- `perPage=15` - количество задач на страницу
- `filter.queue` - очередь задач
- `filter.assignee` - исполнитель задач

**Примечание:** Требуется OAuth токен и идентификатор организации

## Получение задачи

### GET /v3/issues/{issue_key}
**Описание:** Запрос одной задачи с указанием необходимых полей

**URL:** `GET /v3/issues/JUNE-3?expand=attachments`

**Заголовки:**
```
Host: api.tracker.yandex.net
Authorization: OAuth <OAuth-токен>
X-Org-ID или X-Cloud-Org-ID: <идентификатор_организации>
```

**Параметры запроса:**
- `expand=attachments` - включить вложения в ответ

**Примечание:** Требуется OAuth токен и идентификатор организации

## Создание задачи

### POST /v3/issues/
**Описание:** Создать новую задачу

**URL:** `POST /v3/issues/`

**Заголовки:**
```
Host: api.tracker.yandex.net
Authorization: OAuth <OAuth-токен>
X-Org-ID или X-Cloud-Org-ID: <идентификатор_организации>
```

**Тело запроса:**
```json
{
  "queue": "TREK",
  "summary": "Test Issue",
  "parent": "JUNE-2",
  "type": "bug",
  "assignee": "<user_login>",
  "attachmentIds": [55, 56]
}
```

**Параметры:**
- `queue` - очередь задач
- `summary` - название задачи
- `parent` - родительская задача (опционально)
- `type` - тип задачи (bug, task, etc.)
- `assignee` - исполнитель задачи
- `attachmentIds` - массив ID вложений (опционально)

**Примечание:** Требуется OAuth токен и идентификатор организации

## Изменение задач
### PATCH /v3/issues/{issue_key}
**Описание:** Изменить название, описание, тип и приоритет задачи

**URL:** `PATCH /v3/issues/TEST-1`

**Заголовки:**
```
Host: api.tracker.yandex.net
Authorization: OAuth <OAuth-токен>
X-Org-ID или X-Cloud-Org-ID: <идентификатор_организации>
```

**Тело запроса:**
```json
{
  "summary": "<новое_название_задачи>",
  "description": "<новое_описание_задачи>",
  "type": {
      "id": "1",
      "key": "bug"
  },
  "priority": {
      "id": "2",
      "key": "minor"
  }
}
```

**Параметры:**
- `summary` - новое название задачи
- `description` - новое описание задачи
- `type.id` - ID типа задачи
- `type.key` - ключ типа задачи (bug, task, etc.)
- `priority.id` - ID приоритета
- `priority.key` - ключ приоритета (minor, major, critical, etc.)

**Примечание:** Требуется OAuth токен и идентификатор организации
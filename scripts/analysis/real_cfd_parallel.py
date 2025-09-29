import csv
import json
import os
import time
from datetime import datetime, timedelta

import pandas as pd
import requests

# Конфигурация из переменных окружения
API_TOKEN = os.getenv("TRACKER_API_TOKEN", "")
ORG_ID = os.getenv("TRACKER_ORG_ID", "")
from concurrent.futures import ThreadPoolExecutor, as_completed

# === КОНФИГ ===
TASK_LIST_FILE = "data/input/20250805_team_assesment.txt"
STATUS_ORDER_FILE = "data/config/status_order.txt"
UNKNOWN_STATUS_FILE = "data/output/unknown_statuses.txt"
PREVIOUS_STAGE_FILE = ""
FROM_DATE = datetime.strptime("2024-07-01", "%Y-%m-%d")
DEBUG = False
DEBUG_LIMIT = 15
REVERSE_STATUS_ORDER = True
ONLY_LAST_PER_DAY = True

# Проверяем существование входного файла
if not os.path.exists(TASK_LIST_FILE):
    print(f"Warning: Task list file not found: {TASK_LIST_FILE}")
    print("Please create the file or update the path in the script")

# === ВРЕМЕННАЯ МЕТКА ===
TS = datetime.now().strftime("%Y%m%d_%H%M%S")
DEBUG_DIR = "data/output/debug"
os.makedirs(DEBUG_DIR, exist_ok=True)

# === КОНСТАНТЫ ДЛЯ ТРЕКЕРА ===
HEADERS = {
    "Authorization": f"OAuth {API_TOKEN}",
    "X-Org-ID": ORG_ID,
    "Content-Type": "application/json",
}
BASE_URL = "https://api.tracker.yandex.net/v2/"
ISSUE_URL = f"{BASE_URL}issues"

# === ВЫХОДНЫЕ ФАЙЛЫ ===
CSV_STAGE_FILE = f"data/output/tracker_stage_dates_{TS}.csv"
CSV_LONG_FILE = f"data/output/tracker_stage_long_expanded_{TS}.csv"

# === ЗАГРУЗКА ПОРЯДКА СТАТУСОВ ===
try:
    with open(STATUS_ORDER_FILE, "r", encoding="utf-8") as f:
        RAW_STATUS_ORDER = [line.strip() for line in f if line.strip()]
except FileNotFoundError:
    print(f"Warning: Status order file not found: {STATUS_ORDER_FILE}")
    RAW_STATUS_ORDER = []

# Проверяем существование файла с задачами
try:
    with open(TASK_LIST_FILE, "r", encoding="utf-8") as f:
        TASK_IDS = [
            line.strip() for line in f if line.strip() and not line.startswith("#")
        ]
    print(f"Loaded {len(TASK_IDS)} task IDs from {TASK_LIST_FILE}")
except FileNotFoundError:
    print(f"Error: Task list file not found: {TASK_LIST_FILE}")
    print("Please create the file or update the path in the script")
    TASK_IDS = []

n = len(RAW_STATUS_ORDER)
if REVERSE_STATUS_ORDER:
    DISPLAY_ORDER = [f"{n - i:02d}_{name}" for i, name in enumerate(RAW_STATUS_ORDER)]
else:
    DISPLAY_ORDER = [f"{i+1:02d}_{name}" for i, name in enumerate(RAW_STATUS_ORDER)]

STATUS_ORDER = RAW_STATUS_ORDER
STATUS_INDEX = {name: i for i, name in enumerate(STATUS_ORDER)}


def get_task(task_id):
    url = f"{ISSUE_URL}/{task_id}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 200:
        data = r.json()
        with open(
            os.path.join(DEBUG_DIR, f"{task_id}_issue_{TS}.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data
    else:
        raise RuntimeError(f"get_task {task_id} failed: {r.status_code} - {r.text}")


def get_changelog(task_id):
    url = f"{ISSUE_URL}/{task_id}/changelog"
    all_data = []
    index = 0
    while url:
        r = requests.get(url, headers=HEADERS)
        if r.status_code != 200:
            raise RuntimeError(
                f"get_changelog {task_id} failed: {r.status_code} - {r.text}"
            )
        page_data = r.json()
        all_data.extend(page_data)
        with open(
            os.path.join(DEBUG_DIR, f"{task_id}_changelog_{index}_{TS}.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(page_data, f, ensure_ascii=False, indent=2)
        index += 1
        next_url = None
        for part in r.headers.get("Link", "").split(","):
            if 'rel="next"' in part:
                next_url = part.split(";")[0].strip("<> ")
                break
        url = next_url
        time.sleep(0.1)
    return all_data


def extract_teams_and_forecast(issue, changelog):
    result = {
        "team": str(issue.get("63515d47fe387b7ce7b9fc55--team", "")),
        "prodteam": str(issue.get("63515d47fe387b7ce7b9fc55--prodteam", "")),
        "profitForecast": str(
            issue.get("63515d47fe387b7ce7b9fc55--profitForecast", "")
        ),
    }
    return result


def format_user_list(value):
    """Возвращает строку имён из списка/словаря пользователей Яндекс Трекера."""
    if isinstance(value, list):
        names = []
        for v in value:
            if isinstance(v, dict):
                names.append(
                    v.get("display")
                    or str(
                        v.get("id") or v.get("passportUid") or v.get("cloudUid") or ""
                    )
                )
            else:
                names.append(str(v))
        return ", ".join([n for n in names if n])
    elif isinstance(value, dict):
        return value.get("display") or str(value.get("id") or "")
    else:
        return ""


def extract_status_dates(changelog):
    status_dates = {}
    for entry in changelog:
        date = entry.get("updatedAt", "")[:10]
        for field in entry.get("fields", []):
            if field.get("field", {}).get("id") != "status":
                continue
            status_name = field.get("to", {}).get("display") or field.get("to", {}).get(
                "key"
            )
            if status_name not in STATUS_INDEX:
                return None, status_name
            if status_name not in status_dates:
                status_dates[status_name] = date
    return status_dates, None


def process_task(task_id):
    try:
        issue = get_task(task_id)
        changelog = get_changelog(task_id)
        status_dates, unknown_status = extract_status_dates(changelog)
        if unknown_status:
            return {"error": (task_id, unknown_status)}

        extras = extract_teams_and_forecast(issue, changelog)
        row = {
            "task_id": task_id,
            "summary": issue.get("summary", "")[:30],
            "author": issue.get("createdBy", {}).get("display", ""),
            "assignee": issue.get("assignee", {}).get("display", ""),
            "status": issue.get("status", {}).get("display", ""),
            "businessClient": format_user_list(issue.get("businessClient")),
            "team": extras["team"],
            "prodteam": extras["prodteam"],
            "profitForecast": extras["profitForecast"],
            **{s: status_dates.get(s, "") for s in STATUS_ORDER},
        }
        return {"row": row}
    except Exception as e:
        return {"error": (task_id, str(e))}


def main():
    if os.path.exists(PREVIOUS_STAGE_FILE):
        df = pd.read_csv(PREVIOUS_STAGE_FILE, encoding="utf-8")
        for col in [
            "author",
            "assignee",
            "status",
            "team",
            "prodteam",
            "profitForecast",
            "businessClient",
        ]:
            if col not in df.columns:
                df[col] = ""
        df = df[
            [
                "task_id",
                "summary",
                "author",
                "assignee",
                "status",
                "team",
                "prodteam",
                "profitForecast",
                "businessClient",
            ]
            + STATUS_ORDER
        ]
        rows = df.to_dict(orient="records")
        max_date = pd.to_datetime(
            time.ctime(os.path.getmtime(PREVIOUS_STAGE_FILE))
        ).normalize()
    else:
        with open(TASK_LIST_FILE, "r", encoding="utf-8") as f:
            task_ids = [line.strip() for line in f if line.strip()]
        if DEBUG:
            print(f"🛠 DEBUG MODE: только первые {DEBUG_LIMIT} задач")
            task_ids = task_ids[:DEBUG_LIMIT]

        unknowns = set()
        rows = []

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(process_task, task_id): task_id for task_id in task_ids
            }
            for i, future in enumerate(as_completed(futures), 1):
                task_id = futures[future]
                print(f"{i}/{len(task_ids)}: {task_id}")
                result = future.result()
                if "row" in result:
                    rows.append(result["row"])
                elif "error" in result:
                    tid, err = result["error"]
                    if err:
                        print(f"⚠️ Ошибка {tid}: {err}")
                        unknowns.add(f"{tid}: {err}")

        if unknowns:
            with open(UNKNOWN_STATUS_FILE, "a", encoding="utf-8") as f:
                for line in sorted(unknowns):
                    f.write(line + "\n")
            print(f"❗ Неизвестные статусы сохранены: {UNKNOWN_STATUS_FILE}")

        max_date = pd.Timestamp.today().normalize()

    # === Построение long-формата ===
    long_rows = []
    with open("debug_status_dates_dump.json", "w", encoding="utf-8") as f_debug:
        json.dump(rows, f_debug, ensure_ascii=False, indent=2, default=str)

    for row in rows:
        base = {
            "task_id": row.get("task_id"),
            "summary": row.get("summary", "")[:30],
            "author": row.get("author", ""),
            "assignee": row.get("assignee", ""),
            "team": row.get("team", ""),
            "prodteam": row.get("prodteam"),
        }

        status_dates = {
            s: row[s]
            for s in STATUS_ORDER
            if s in row and pd.notna(row[s]) and str(row[s]).strip()
        }
        sorted_statuses = [
            (s, status_dates[s]) for s in STATUS_ORDER if s in status_dates
        ]
        sorted_statuses.sort(key=lambda x: pd.to_datetime(x[1], errors="coerce"))

        if ONLY_LAST_PER_DAY:
            task_daily = {}
            for i, (stage, start_date) in enumerate(sorted_statuses):
                display_stage = DISPLAY_ORDER[STATUS_INDEX[stage]]
                is_last = i + 1 == len(sorted_statuses)
                end_dt = (
                    pd.to_datetime(sorted_statuses[i + 1][1], errors="coerce")
                    if not is_last
                    else max_date
                )
                start_dt = pd.to_datetime(start_date, errors="coerce")
                if pd.isna(start_dt) or pd.isna(end_dt):
                    continue
                end_adjusted = end_dt if is_last else end_dt - timedelta(days=1)
                for day in pd.date_range(start=start_dt, end=end_adjusted, freq="D"):
                    if day >= FROM_DATE:
                        task_daily[day.date()] = display_stage
            for day, stage in task_daily.items():
                long_rows.append({**base, "stage": stage, "date": day})
        else:
            for i, (stage, start_date) in enumerate(sorted_statuses):
                display_stage = DISPLAY_ORDER[STATUS_INDEX[stage]]
                is_last = i + 1 == len(sorted_statuses)
                end_dt = (
                    pd.to_datetime(sorted_statuses[i + 1][1], errors="coerce")
                    if not is_last
                    else max_date
                )
                start_dt = pd.to_datetime(start_date, errors="coerce")
                if pd.isna(start_dt) or pd.isna(end_dt):
                    continue
                for day in pd.date_range(
                    start=start_dt,
                    end=end_dt,
                    freq="D",
                    inclusive="left" if not is_last else "both",
                ):
                    if day >= FROM_DATE:
                        long_rows.append(
                            {**base, "stage": display_stage, "date": day.date()}
                        )

    pd.DataFrame(rows).to_csv(CSV_STAGE_FILE, index=False)
    print(f"📦 Стадии сохранены: {CSV_STAGE_FILE}")

    pd.DataFrame(long_rows).to_csv(CSV_LONG_FILE, index=False)
    print(f"✅ Long-формат сохранён: {CSV_LONG_FILE}")


if __name__ == "__main__":
    main()

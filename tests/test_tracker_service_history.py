from datetime import datetime, timedelta, timezone

from radiator.services.tracker_service import tracker_service


def _iso(dt: datetime) -> str:
    # Tracker API returns Z or +00:00; our code replaces Z with +00:00
    return dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def test_extract_status_history_sorted_end_dates_full_mode():
    # Create two changes out of order (second earlier than first in the list)
    t0 = datetime(2025, 10, 14, 10, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2025, 10, 15, 12, 0, 0, tzinfo=timezone.utc)

    changelog = [
        {
            "updatedAt": _iso(t1),
            "fields": [
                {
                    "field": {"id": "status"},
                    "from": {"display": "Готова к разработке"},
                    "to": {"display": "МП / В работе"},
                }
            ],
        },
        {
            "updatedAt": _iso(t0),
            "fields": [
                {
                    "field": {"id": "status"},
                    "from": {"display": "Analysis"},
                    "to": {"display": "Готова к разработке"},
                }
            ],
        },
    ]

    task_data = {
        "status": "МП / В работе",
        "created_at": t0 - timedelta(hours=1),
        "task_updated_at": t1,
    }

    history = tracker_service.extract_status_history_with_initial_status(
        changelog, task_data, task_key="CPO-TEST"
    )

    # Expect chronological order and non-decreasing end dates
    assert len(history) >= 2
    for i in range(len(history) - 1):
        assert history[i]["start_date"] <= history[i + 1]["start_date"]
        assert history[i].get("end_date") is not None
        assert history[i]["end_date"] >= history[i]["start_date"]


def test_extract_status_history_handles_initial_status():
    t0 = datetime(2025, 10, 10, 9, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2025, 10, 11, 9, 0, 0, tzinfo=timezone.utc)

    changelog = [
        {
            "updatedAt": _iso(t1),
            "fields": [
                {
                    "field": {"id": "status"},
                    "from": {"display": "Backlog"},
                    "to": {"display": "Готова к разработке"},
                }
            ],
        },
    ]

    task_data = {"status": "Готова к разработке", "created_at": t0}

    history = tracker_service.extract_status_history_with_initial_status(
        changelog, task_data
    )

    # Should contain initial status and then the change
    assert len(history) >= 2
    assert history[0]["start_date"] == t0
    assert history[0]["end_date"] == t1
    assert history[1]["start_date"] == t1


def test_extract_status_history_open_interval_no_end():
    t0 = datetime(2025, 10, 10, 9, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2025, 10, 11, 9, 0, 0, tzinfo=timezone.utc)

    changelog = [
        {
            "updatedAt": _iso(t0),
            "fields": [
                {
                    "field": {"id": "status"},
                    "from": {"display": "Backlog"},
                    "to": {"display": "Готова к разработке"},
                }
            ],
        },
        {
            "updatedAt": _iso(t1),
            "fields": [
                {
                    "field": {"id": "status"},
                    "from": {"display": "Готова к разработке"},
                    "to": {"display": "МП / В работе"},
                }
            ],
        },
    ]

    task_data = {"status": "МП / В работе", "created_at": t0}

    history = tracker_service.extract_status_history_with_initial_status(
        changelog, task_data
    )

    # Last interval is open (no end)
    assert history[-1]["end_date"] is None
    assert history[-1]["start_date"] == t1

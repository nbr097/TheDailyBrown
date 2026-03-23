from src.scheduler import get_cached_unread, set_cached_outlook_data, _cache

def test_get_cached_unread_returns_empty_by_default():
    _cache["unread_emails"] = []
    assert get_cached_unread() == []

def test_get_cached_unread_returns_stored_data():
    _cache["unread_emails"] = [{"subject": "Test", "from_name": "Foo"}]
    result = get_cached_unread()
    assert len(result) == 1
    assert result[0]["subject"] == "Test"

def test_set_cached_outlook_data_stores_all_fields():
    _cache["calendar"] = [{"subject": "Personal Event", "source": "personal"}]
    set_cached_outlook_data(
        calendar=[{"subject": "Work Meeting", "source": "work"}],
        flagged_emails=[{"subject": "Flag1", "from_name": "Boss"}],
        unread_emails=[{"subject": "Unread1", "from_name": "IT"}],
    )
    assert len(_cache["calendar"]) == 2
    assert any(e["source"] == "personal" for e in _cache["calendar"])
    assert any(e["source"] == "work" for e in _cache["calendar"])
    assert _cache["flagged_emails"] == [{"subject": "Flag1", "from_name": "Boss"}]
    assert _cache["unread_emails"] == [{"subject": "Unread1", "from_name": "IT"}]

def test_set_cached_outlook_data_replaces_old_work_events():
    _cache["calendar"] = [
        {"subject": "Personal", "source": "personal"},
        {"subject": "Old Work", "source": "work"},
    ]
    set_cached_outlook_data(
        calendar=[{"subject": "New Work", "source": "work"}],
        flagged_emails=[],
        unread_emails=[],
    )
    subjects = [e["subject"] for e in _cache["calendar"]]
    assert "Personal" in subjects
    assert "New Work" in subjects
    assert "Old Work" not in subjects

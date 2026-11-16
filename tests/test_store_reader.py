"""The reader for the rugbydata parquet store.

The offline tests cover the argument checking and the URL it builds. The
network tests actually read the store and are skipped unless --network is
passed, so a normal run needs no connection.
"""

import pytest

import rb


def test_rejects_an_unknown_kind():
    with pytest.raises(ValueError) as exc:
        rb.get("nonsense", "team_registry")
    assert "kind must be one of" in str(exc.value)


@pytest.mark.parametrize(
    "kind", ["team", "player", "match", "competition", "venue"]
)
def test_accepts_every_documented_kind(kind, monkeypatch):
    """Each documented kind builds the URL the store expects."""
    seen = {}

    def fake_read_parquet(url, **kwargs):
        seen["url"] = url
        import pandas as pd
        return pd.DataFrame({"ok": [1]})

    monkeypatch.setattr(rb.pd, "read_parquet", fake_read_parquet)
    monkeypatch.setattr(rb.time, "sleep", lambda _: None)

    rb.get(kind, "some_id")
    assert seen["url"] == f"{rb.BASE}{kind}/some_id.parquet"


def test_a_missing_file_is_not_retried(monkeypatch):
    """A 404 means the file is not there, so retrying only wastes requests."""
    from urllib.error import HTTPError

    calls = []

    def fake_read_parquet(url, **kwargs):
        calls.append(url)
        raise HTTPError(url, 404, "Not Found", {}, None)

    monkeypatch.setattr(rb.pd, "read_parquet", fake_read_parquet)
    monkeypatch.setattr(rb.time, "sleep", lambda _: None)

    with pytest.raises(HTTPError):
        rb.get("player", "missing", retries=3)
    assert len(calls) == 1, "a 404 should not be retried"


def test_a_transient_failure_is_retried(monkeypatch):
    """The host throttles sustained access, so transient errors are retried."""
    calls = []

    def fake_read_parquet(url, **kwargs):
        calls.append(url)
        if len(calls) < 3:
            raise TimeoutError("throttled")
        import pandas as pd
        return pd.DataFrame({"ok": [1]})

    monkeypatch.setattr(rb.pd, "read_parquet", fake_read_parquet)
    monkeypatch.setattr(rb.time, "sleep", lambda _: None)

    out = rb.get("player", "slow", retries=5)
    assert len(calls) == 3
    assert len(out) == 1


def test_gives_up_after_the_retry_limit(monkeypatch):
    calls = []

    def fake_read_parquet(url, **kwargs):
        calls.append(url)
        raise TimeoutError("still throttled")

    monkeypatch.setattr(rb.pd, "read_parquet", fake_read_parquet)
    monkeypatch.setattr(rb.time, "sleep", lambda _: None)

    with pytest.raises(TimeoutError):
        rb.get("player", "hopeless", retries=4)
    assert len(calls) == 4


# --- these actually read the store ---------------------------------------

@pytest.mark.network
def test_the_registries_are_reachable():
    teams = rb.get("team", "team_registry")
    assert {"team_id", "team_name"} <= set(teams.columns)
    assert len(teams) > 100


@pytest.mark.network
def test_a_player_file_carries_the_scoring_columns():
    """The columns a fantasy scoring system needs must be present."""
    matches = rb.get("match", "match_registry")
    assert len(matches) > 1000

    needed = {
        "tries", "try_assists", "conversion_goals", "penalty_goals",
        "tackles_made", "turnovers_won", "line_breaks", "metres_carried",
        "offloads", "penalties_conceded", "yellow_cards", "red_cards",
    }
    sample = rb.get("player", "2dff28d0")
    missing = needed - set(sample.columns)
    assert not missing, f"the store no longer carries {sorted(missing)}"

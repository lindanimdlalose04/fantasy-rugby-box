"""Direct reader for the rugbydata parquet store.

Reads the parquet files that back the rugbypy package straight from the raw
store. Requests are retried with exponential backoff, since the host throttles
sustained sequential access; a genuine 404 is raised immediately rather than
retried.

Data source: Bailey, S. rugbypy. https://github.com/seanyboi/rugbypy
Store:       https://github.com/seanyboi/rugbydata (Apache-2.0)

Carried over unchanged from RugbyBox. See docs/lineage.md. RugbyBox is
frozen, so fixes flow one way: into this file, not back.
"""

import time
from urllib.error import HTTPError

import pandas as pd

BASE = "https://raw.githubusercontent.com/seanyboi/rugbydata/main/data/v3/"

VALID_KINDS = {"team", "player", "match", "competition", "venue"}


def get(kind: str, name: str, retries: int = 3, pause: float = 0.2) -> pd.DataFrame:
    """Read one parquet file from the store.

    kind:    one of team, player, member, match, competition, venue
    name:    an entity id, or a registry name such as 'team_registry'
    retries: attempts before giving up on a transient failure
    pause:   delay after a successful read, to stay under the host's rate limit
    """
    if kind not in VALID_KINDS:
        raise ValueError(f"kind must be one of {sorted(VALID_KINDS)}, got {kind!r}")

    url = f"{BASE}{kind}/{name}.parquet"
    last_error = None

    for attempt in range(retries):
        try:
            df = pd.read_parquet(url, engine="pyarrow")
            time.sleep(pause)
            return df
        except HTTPError as exc:
            if exc.code == 404:
                raise                      # the file genuinely is not there
            last_error = exc
        except Exception as exc:
            last_error = exc
        time.sleep(2 ** attempt)           # 1s, 2s, 4s, 8s, 16s

    raise last_error
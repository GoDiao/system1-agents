"""Record real clm-serve responses as fixtures, the way tests/data/served_laya/ was recorded.

    python3 record_fixtures.py http://127.0.0.1:8091

Writes tests/data/clm/<name>.json as {"status", "content_type", "body"} (or "text" for a body that is not JSON),
so the tests replay what a server actually sent rather than what we imagine it sends.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent

CHOICE = {
    "model": "clm-latest",
    "state": {"ticket": "I was charged twice for order 4411."},
    "questions": {
        "pick": {
            "type": "choice",
            "instructions": "Which queue?",
            "criteria": {"billing": "Charges and refunds", "technical": "Software problems"},
        }
    },
}
NOUL = {
    "model": "clm-latest",
    "state": {"ticket": "Please refund the duplicate charge."},
    "questions": {"check": {"type": "noul", "instructions": "Does the customer ask for a refund?"}},
}
BAD = {"model": "clm-latest", "state": {}, "questions": {"pick": {"type": "choice", "criteria": {}}}}


def record(url: str, name: str, body: dict | None, method: str = "POST", path: str = "/v1/systemone") -> None:
    request = urllib.request.Request(
        url.rstrip("/") + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            status, content_type, raw = response.status, response.headers.get("Content-Type", ""), response.read()
    except urllib.error.HTTPError as error:
        status, content_type, raw = error.code, error.headers.get("Content-Type", ""), error.read()
    entry: dict = {"status": status, "content_type": content_type.split(";")[0]}
    try:
        entry["body"] = json.loads(raw)
    except ValueError:
        entry["text"] = raw.decode("utf-8", "replace")
    (OUT / f"{name}.json").write_text(json.dumps(entry, indent=2, sort_keys=True) + "\n")
    print(f"{name}: {status} {entry.get('body', entry.get('text'))!r}"[:160])


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8091"
    OUT.mkdir(parents=True, exist_ok=True)
    record(url, "models", None, method="GET", path="/v1/models")
    record(url, "choice", CHOICE)
    record(url, "noul", NOUL)
    record(url, "bad_question", BAD)


if __name__ == "__main__":
    main()

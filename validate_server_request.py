"""Validate the fixed public-collection request from the existing ECS trigger."""
import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

CN = timezone(timedelta(hours=8))
REQUEST = "requests/server-wine-trigger.json"
SLOTS = {
    "07:10": "易茅时价", "07:30": "易茅时价", "07:50": "易茅时价",
    "10:15": "今日酒价", "10:45": "茅粉鲁智深",
}


def source_for_request(request, now):
    if not isinstance(request, dict) or set(request) != {
        "version", "request_id", "date", "source", "requested_at",
    } or type(request["version"]) is not int or request["version"] != 1:
        raise ValueError("invalid request schema")
    now = now.astimezone(CN)
    date = now.date().isoformat()
    rid = request["request_id"]
    if request["date"] != date or not isinstance(rid, str) or not rid.startswith(date + "T"):
        raise ValueError("request does not identify today")
    timestamp = request["requested_at"]
    if not isinstance(timestamp, str):
        raise ValueError("invalid timestamp")
    requested = datetime.fromisoformat(timestamp)
    if requested.utcoffset() is None:
        raise ValueError("request timestamp requires timezone")
    requested = requested.astimezone(CN)
    if requested.date() != now.date() or requested > now + timedelta(minutes=5):
        raise ValueError("request timestamp is not today")
    slot = rid[len(date) + 1:]
    if re.fullmatch(r"probe-\d{6}", slot):
        expected = "易茅时价"
    else:
        expected = SLOTS.get(slot)
        if expected is None:
            raise ValueError("unrecognized timer slot")
        if slot in {"10:15", "10:45"}:
            slot_start = datetime.fromisoformat(date + "T" + slot).replace(tzinfo=CN)
            if not slot_start <= requested < slot_start + timedelta(minutes=5):
                raise ValueError("request was created outside its timer slot")
    if request["source"] != expected:
        raise ValueError("source is not authorized for this timer slot")
    return expected


def run():
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    sha = os.environ["GITHUB_SHA"]
    if event.get("ref") != "refs/heads/main" or event.get("after") != sha:
        raise ValueError("unexpected ref or head")
    changed = subprocess.check_output(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", sha],
        text=True,
    ).splitlines()
    if changed != [REQUEST]:
        raise ValueError("unexpected commit paths")
    request = json.loads(Path(REQUEST).read_text())
    source = source_for_request(request, datetime.now(CN))
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"source={source}\n")


if __name__ == "__main__":
    run()

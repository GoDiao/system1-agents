# coding: utf-8
"""The MCP frames proxy: the client sees only its own responses; every browser call yields one stamped PNG."""

from __future__ import annotations

import base64
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import TestCase, skipUnless

try:
    from PIL import Image

    HAVE_PIL = True
except ImportError:  # the report extra is not installed
    HAVE_PIL = False

FAKE_SERVER = r"""
import base64, io, json, sys
png = sys.argv[1]
for raw in sys.stdin.buffer:
    message = json.loads(raw)
    if message.get("method") != "tools/call":
        reply = {"jsonrpc": "2.0", "id": message["id"], "result": {"ok": True}}
    elif message["params"]["name"] == "browser_take_screenshot":
        reply = {"jsonrpc": "2.0", "id": message["id"], "result": {"content": [{"type": "image", "data": png, "mimeType": "image/png"}]}}
    else:
        reply = {"jsonrpc": "2.0", "id": message["id"], "result": {"content": [{"type": "text", "text": "done"}]}}
    sys.stdout.write(json.dumps(reply) + "\n")
    sys.stdout.flush()
"""


@skipUnless(HAVE_PIL, "the report extra (pillow) is not installed")
class TestCastProxy(TestCase):
    def test_client_sees_its_replies_and_each_browser_call_leaves_a_frame(self) -> None:
        buffer = io.BytesIO()
        Image.new("RGB", (8, 8), (200, 30, 30)).save(buffer, format="PNG")
        png = base64.b64encode(buffer.getvalue()).decode()
        requests = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "browser_click", "arguments": {}}},
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "browser_snapshot", "arguments": {}},
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            frames = Path(tmp) / "frames"
            proxy = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "evals.replay.cast",
                    "--frames",
                    str(frames),
                    "--",
                    sys.executable,
                    "-c",
                    FAKE_SERVER,
                    png,
                ],
                input="".join(json.dumps(r) + "\n" for r in requests).encode(),
                capture_output=True,
                timeout=30,
                check=False,
            )
            replies = [json.loads(line) for line in proxy.stdout.decode().splitlines() if line.strip()]
            files = sorted(frames.glob("t*.png"))
            calls = [json.loads(line) for line in (frames / "calls.jsonl").read_text().splitlines()]
            self.assertEqual([r["id"] for r in replies], [1, 2, 3], proxy.stderr.decode()[-500:])
            self.assertEqual(
                [f.name.split("-", 1)[1] for f in files], ["0001-browser_click.png", "0002-browser_snapshot.png"]
            )
            self.assertEqual([c["tool"] for c in calls], ["browser_click", "browser_snapshot"])
            for call in calls:
                self.assertLessEqual(call["request_ms"], call["response_ms"])
                self.assertLessEqual(call["response_ms"], call["frame_ms"])
            with Image.open(files[0]) as image:
                self.assertEqual(image.size, (8, 8))

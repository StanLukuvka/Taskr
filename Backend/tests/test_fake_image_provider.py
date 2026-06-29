from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "fake_image_provider.py"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _request_json(url: str, *, method: str = "GET", payload: dict | None = None) -> tuple[int, dict]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req, timeout=1) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def test_fake_image_provider_endpoints_and_port_env() -> None:
    port = _free_port()
    env = os.environ.copy()
    env["PORT"] = str(port)
    process = subprocess.Popen(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        base_url = f"http://127.0.0.1:{port}"
        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                status, body = _request_json(f"{base_url}/credits")
            except Exception:
                time.sleep(0.1)
                continue
            if status == 200:
                break
            time.sleep(0.1)
        else:
            output = process.stdout.read() if process.stdout else ""
            raise AssertionError(f"server did not start on PORT={port}; output={output!r}")

        assert (status, body) == (200, {"balance": 100})
        assert _request_json(f"{base_url}/deduct", method="POST", payload={"amount": 15}) == (200, {"ok": True, "balance": 85})

        status, body = _request_json(f"{base_url}/generate", method="POST", payload={})
        assert status == 200
        assert body["image_url"] == f"http://127.0.0.1:{port}/image/1"
        assert body["balance"] == 75
        assert body["credits_deducted"] == 10

        assert _request_json(f"{base_url}/topup", method="POST", payload={"amount": 25}) == (200, {"ok": True, "balance": 100})
        assert _request_json(f"{base_url}/credits") == (200, {"balance": 100})
        assert _request_json(f"{base_url}/deduct", method="POST", payload={"amount": True}) == (
            400,
            {"ok": False, "error": "amount must be a positive integer"},
        )
        assert _request_json(f"{base_url}/deduct", method="POST", payload={"amount": 101}) == (
            402,
            {"ok": False, "error": "insufficient credits", "balance": 100},
        )
    finally:
        process.terminate()
        process.wait(timeout=5)

"""
One-command unattended test suite.

Runs, against the seed data and the fixed APP_NOW clock:
  1. Rule + API tests (pytest, including authorization and concurrency)
  2. The rules report generator (validated as JSON)
  3. The two-browser Playwright end-to-end meeting sync test, booting the
     FastAPI backend and the Next.js frontend on fresh local processes.
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
E2E_DB = ROOT / "e2e_ninety.db"
APP_NOW = "2026-11-11T15:00:00Z"
BACKEND_PORT = 8000
FRONTEND_PORT = 3000

IS_WINDOWS = os.name == "nt"
PY = sys.executable
servers: list[subprocess.Popen] = []


def run_step(name, cmd, env=None, cwd=None):
    print("\n==================================================")
    print(f"--> RUNNING: {name}")
    print(f"--> COMMAND: {' '.join(str(c) for c in cmd)}")
    print("==================================================")
    current_env = os.environ.copy()
    if env:
        current_env.update(env)
    result = subprocess.run(cmd, env=current_env, cwd=cwd)
    if result.returncode != 0:
        print(f"\n[FAILED] {name} exited with code {result.returncode}")
        teardown_servers()
        sys.exit(result.returncode)
    print(f"[PASSED] {name}")


def tool(name: str) -> str:
    """Resolve a node_modules/.bin tool, honouring Windows shims."""
    shim = FRONTEND / "node_modules" / ".bin" / (name + (".cmd" if IS_WINDOWS else ""))
    return str(shim)


def port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def wait_for_http(url: str, timeout: int = 180):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status < 500:
                    return
        except Exception:
            time.sleep(1)
    raise RuntimeError(f"Timed out waiting for {url}")


def start_server(name, cmd, env=None, cwd=None):
    log_dir = ROOT / "test-artifacts"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"{name}.log"
    log_handle = open(log_path, "w", encoding="utf-8")
    current_env = os.environ.copy()
    if env:
        current_env.update(env)
    print(f"--> Starting {name} (log: {log_path})")
    proc = subprocess.Popen(
        cmd, env=current_env, cwd=cwd,
        stdout=log_handle, stderr=subprocess.STDOUT,
    )
    servers.append(proc)
    return proc


def teardown_servers():
    for proc in reversed(servers):
        if proc.poll() is not None:
            continue
        try:
            if IS_WINDOWS:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            else:
                proc.terminate()
        except Exception:
            pass
    servers.clear()
    for suffix in ("", "-wal", "-shm"):
        path = E2E_DB.with_name(E2E_DB.name + suffix)
        if path.exists():
            path.unlink(missing_ok=True)


def run_e2e():
    if not port_is_free(BACKEND_PORT):
        raise RuntimeError(f"Port {BACKEND_PORT} is already in use; stop that process before running the suite")
    if not port_is_free(FRONTEND_PORT):
        raise RuntimeError(f"Port {FRONTEND_PORT} is already in use; stop that process before running the suite")

    E2E_DB.unlink(missing_ok=True)
    backend_env = {
        "DATABASE_URL": f"sqlite:///./{E2E_DB.name}",
        "APP_NOW": APP_NOW,
        "COMPANY_TIMEZONE": "America/Chicago",
    }

    run_step("Seed e2e database", [PY, "-m", "backend.app.seeder"], {"DATABASE_URL": backend_env["DATABASE_URL"]}, cwd=ROOT)

    start_server(
        "backend",
        [PY, "-m", "uvicorn", "backend.app.main:app",
         "--host", "127.0.0.1", "--port", str(BACKEND_PORT)],
        backend_env, cwd=ROOT,
    )
    wait_for_http(f"http://127.0.0.1:{BACKEND_PORT}/docs")

    # Always build so the e2e run exercises the current frontend sources.
    run_step("Build frontend", [tool("next"), "build"], cwd=FRONTEND)

    start_server(
        "frontend",
        [tool("next"), "start", "-p", str(FRONTEND_PORT)],
        {"BACKEND_URL": f"http://127.0.0.1:{BACKEND_PORT}"},
        cwd=FRONTEND,
    )
    wait_for_http(f"http://127.0.0.1:{FRONTEND_PORT}/")

    run_step(
        "End-to-end two-browser meeting sync (Playwright)",
        [tool("playwright"), "test"],
        {"BASE_URL": f"http://127.0.0.1:{FRONTEND_PORT}"},
        cwd=FRONTEND,
    )


def main():
    try:
        run_step(
            "Backend Rule & API Tests",
            [PY, "-m", "pytest", "backend/tests", "-v"],
            {"DATABASE_URL": "sqlite:///./test_ninety.db", "APP_NOW": APP_NOW},
        )

        run_step(
            "Rules Report Generation & Verification",
            [PY, "backend/rules_report.py", "-o", "rules_report.json"],
            {"APP_NOW": APP_NOW},
        )

        with open(ROOT / "rules_report.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "now" in data, "rules_report.json missing 'now'"
        assert "teams" in data, "rules_report.json missing 'teams'"
        assert set(data["teams"].keys()) == {"team_lead", "team_sales", "team_ops"}, \
            "rules_report.json missing teams"
        print("\n[PASSED] rules_report.json verified successfully!")

        if "--skip-e2e" in sys.argv:
            print("\n[Skipped] End-to-end suite (--skip-e2e)")
        else:
            run_e2e()

        print("\n==================================================")
        print("ALL TESTS AND VERIFICATIONS PASSED UNATTENDED!")
        print("==================================================")
    finally:
        teardown_servers()


if __name__ == "__main__":
    main()

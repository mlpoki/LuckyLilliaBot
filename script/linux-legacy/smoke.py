"""Exercise the complete Linux bundle using a fresh account-data directory."""

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request


def request(url, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=3) as response:
        return response.status, response.read()


def main():
    arch = sys.argv[1]
    output = Path.cwd() / "out"
    root = output / f"LLBot-CLI-linux-{arch}"
    evidence = output / "evidence"
    evidence.mkdir(exist_ok=True)
    environment = os.environ.copy()
    home = output / "test-home"
    home.mkdir()
    environment.update(HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"))
    result = {"arch": arch, "account_login_tested": False, "passed": False}
    processes = []
    try:
        for executable, argument in [("llbot", "--version"), ("bin/llbot/node", "--version"), ("bin/llbot/ffmpeg", "-version"), ("bin/llbot/ffprobe", "-version")]:
            version = subprocess.check_output([root / executable, argument], env=environment, text=True, stderr=subprocess.STDOUT)
            result[executable] = version.splitlines()[0]
        log = (evidence / "startup.log").open("w")
        child = subprocess.Popen([
            "xvfb-run", "-a", "dbus-run-session", "--", str(root / "start.sh"),
            "--qq-args=--no-sandbox",
        ], cwd=root, env=environment, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        processes.append(child)
        deadline = time.monotonic() + 100
        last_error = "startup did not provide ready endpoints"
        while time.monotonic() < deadline:
            if child.poll() is not None:
                raise RuntimeError(f"CLI exited with status {child.returncode}")
            try:
                health_status, _ = request("http://127.0.0.1:13000/health")
                _, raw = request("http://127.0.0.1:13000/", {"type": "call", "data": {"func": "getSelfInfo", "args": []}})
                response = json.loads(raw)
                inner = response.get("data", {})
                if isinstance(inner, str):
                    inner = json.loads(inner)
                info = inner.get("result", {})
                if response.get("type") != "call" or not isinstance(info, dict) or not isinstance(info.get("online"), bool):
                    raise RuntimeError("PMHQ did not return a QQ online-state boolean")
                webui_status, _ = request("http://127.0.0.1:3080/")
                text = (evidence / "startup.log").read_text(errors="replace")
                if "TypeError" in text or "ERR_MODULE_NOT_FOUND" in text:
                    raise RuntimeError("LLBot reported a runtime exception")
                if health_status == 200 and webui_status == 200:
                    time.sleep(8)
                    if child.poll() is not None:
                        raise RuntimeError("CLI stopped after endpoints became ready")
                    result.update(passed=True, pmhq_health=200, webui_http=200, qq_online_state_available=True)
                    break
            except Exception as error:
                last_error = str(error)
            time.sleep(2)
        if not result["passed"]:
            raise RuntimeError(last_error)
    except Exception as error:
        result["error"] = str(error)
        raise
    finally:
        for child in processes:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
        (evidence / "smoke.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2), flush=True)
        if not result["passed"] and (evidence / "startup.log").exists():
            print("\n".join((evidence / "startup.log").read_text(errors="replace").splitlines()[-70:]), flush=True)


if __name__ == "__main__":
    main()

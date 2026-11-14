"""Check the native macOS CLI or Desktop with fresh runtime data."""

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request


def http(url, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=3) as response:
        return response.status, response.read()


def main():
    kind = sys.argv[1]
    output = Path.cwd() / "out"
    root = output / f"LLBot-{kind}-macos-arm64"
    base = root
    evidence = output / "evidence"
    evidence.mkdir()
    home = output / "test-home"
    home.mkdir()
    environment = os.environ.copy()
    environment.update(HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"))
    environment["PATH"] = str(base / "bin/llbot") + ":" + environment["PATH"]
    result = {"kind": kind, "passed": False, "account_login_tested": False}
    child = None
    try:
        for executable in ("node", "ffmpeg", "ffprobe"):
            argument = "--version" if executable == "node" else "-version"
            text = subprocess.check_output([base / "bin/llbot" / executable, argument], text=True, stderr=subprocess.STDOUT)
            result[executable] = text.splitlines()[0]
        subprocess.run([base / "bin/llbot/node", root / "prepare.cjs", "--ci"], env=environment, check=True)
        log = (evidence / "startup.log").open("w")
        command = [str(root / "Start.command")]
        if kind == "CLI":
            command.append("--headless")
        child = subprocess.Popen(command, cwd=root, env=environment, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        deadline = time.monotonic() + 120
        last_error = "endpoints did not become ready"
        while time.monotonic() < deadline:
            if child.poll() is not None:
                raise RuntimeError(f"{kind} exited with {child.returncode}")
            try:
                health, _ = http("http://127.0.0.1:13000/health")
                _, raw = http("http://127.0.0.1:13000/", {"type": "call", "data": {"func": "getSelfInfo", "args": []}})
                response = json.loads(raw)
                inner = response.get("data", {})
                if isinstance(inner, str):
                    inner = json.loads(inner)
                if not isinstance(inner.get("result", {}).get("online"), bool):
                    raise RuntimeError("QQ online-state interface is not ready")
                webui, _ = http("http://127.0.0.1:3080/")
                qr_ready = True
                if kind == "CLI":
                    qr = root / "qrcode.png"
                    qr_ready = qr.exists() and qr.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
                if health == 200 and webui == 200 and qr_ready:
                    time.sleep(8)
                    if child.poll() is not None:
                        raise RuntimeError("Process stopped after endpoints became ready")
                    result.update(passed=True, pmhq_health=200, webui_http=200, qq_online_state_available=True)
                    if kind == "CLI":
                        result["login_qrcode_available"] = True
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
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
        for executable in (base / "bin/qq/QQ.app/Contents/MacOS/QQ", base / "bin/pmhq/pmhq", base / "bin/llbot/node"):
            subprocess.run(["pkill", "-f", str(executable)], check=False)
        (evidence / "smoke.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2), flush=True)
        if not result["passed"] and (evidence / "startup.log").exists():
            print("\n".join((evidence / "startup.log").read_text(errors="replace").splitlines()[-90:]), flush=True)
            for log in base.glob("logs/*.log"):
                shutil_target = evidence / ("desktop-" + log.name)
                shutil_target.write_bytes(log.read_bytes())


if __name__ == "__main__":
    main()

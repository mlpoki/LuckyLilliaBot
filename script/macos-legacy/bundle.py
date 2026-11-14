"""Restore the historical macOS packages with their fixed runtime components."""

import base64
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tarfile


UPSTREAM = "https://github.com/LuckyLilliaDev/LuckyLilliaBot/releases/download/v7.12.15/"
CLI_SHA256 = "540a14ef2afaefa7893f033228e37942073dc80cf8719c638881892d14c5ab88"
DESKTOP_SHA256 = "0f02c1114ceb1f75569cc64b902425df81400e78e1c9250e8998be14fab1e051"
PMHQ_INTEGRITY = "UyN4/EBBx+lgNlsxMFzx61UbOhZoJg/S7tnlqVT6JPzUqRo5KqiI1KDCDBQ9nWg74C8jp9YtJx8EhIQ+7cSDiA=="
MEDIA = {
    "ffmpeg": ("4.1.5", "hYqTiP63mXz7wSQfuqfFwfLOfwwFChUedeCVKkBtl/cliaTM7/ePI9bVzfZ2c+dWu3TqCwLDRWNSJ5pqZl8otA=="),
    "ffprobe": ("5.0.1", "vwNCNjokH8hfkbl6m95zICHwkSzhEvDC3GVBcUp5HX8+4wsX10SP3B+bGur7XUzTIZ4cQpgJmEIAx6TUwRepMg=="),
}


def download(url, path, algorithm, expected):
    subprocess.run(["curl", "-fLsS", "--retry", "3", "--connect-timeout", "20", "--max-time", "300", url, "-o", str(path)], check=True)
    digest = hashlib.file_digest(path.open("rb"), algorithm).digest()
    actual = base64.b64encode(digest).decode() if algorithm == "sha512" else digest.hex()
    if actual != expected:
        raise RuntimeError(f"Checksum mismatch: {path.name}")


def extract(archive, destination):
    with tarfile.open(archive, "r:xz") as package:
        members = [member for member in package.getmembers()
                   if "__MACOSX" not in Path(member.name).parts
                   and not Path(member.name).name.startswith("._")]
        package.extractall(destination, members=members, filter="data")


def patch_readiness(base):
    script = base / "bin/llbot/llbot.js"
    text = script.read_text()
    old = "if (!pmhqSelfInfo.online) {"
    if text.count(old) != 1:
        raise RuntimeError("Cannot identify the historical login readiness guard")
    script.write_text(text.replace(old, "if (!pmhqSelfInfo?.online) {").replace("//# sourceMappingURL=llbot.js.map", ""))
    (base / "bin/llbot/llbot.js.map").unlink()


def main():
    kind = sys.argv[1]
    source = Path.cwd() / "script/macos-legacy"
    output = Path.cwd() / "out"
    output.mkdir()
    downloads = output / "downloads"
    downloads.mkdir()
    cli_archive = downloads / "cli.tar.xz"
    download(UPSTREAM + "LLBot-CLI-macos-arm64.tar.xz", cli_archive, "sha256", CLI_SHA256)
    root = output / f"LLBot-{kind}-macos-arm64"
    root.mkdir()
    if kind == "CLI":
        extract(cli_archive, root)
        base = root
    else:
        cli = downloads / "cli"
        cli.mkdir()
        extract(cli_archive, cli)
        desktop_archive = downloads / "desktop.tar.xz"
        download(UPSTREAM + "LLBot-Desktop-macos-arm64.tar.xz", desktop_archive, "sha256", DESKTOP_SHA256)
        extract(desktop_archive, root)
        base = root / "LuckyLilliaDesktop.app/Contents/MacOS"
        shutil.copytree(cli / "bin", base / "bin", dirs_exist_ok=True, symlinks=True)
    pmhq_url = "https://registry.npmjs.org/pmhq-dist-macos-arm64/-/pmhq-dist-macos-arm64-7.1.1.tgz"
    pmhq_archive = downloads / "pmhq.tgz"
    download(pmhq_url, pmhq_archive, "sha512", PMHQ_INTEGRITY)
    with tarfile.open(pmhq_archive, "r:gz") as package:
        for member, name in [("pmhq-macos-arm64", "pmhq"), ("libpmhq.dylib", "libpmhq.dylib"), ("package.json", "package.json")]:
            (base / "bin/pmhq" / name).write_bytes(package.extractfile("package/" + member).read())
    patch_readiness(base)
    component_record = {
        "llbot_version": "7.12.15",
        "upstream_cli_sha256": CLI_SHA256,
        "upstream_desktop_sha256": DESKTOP_SHA256 if kind == "Desktop" else None,
        "workflow_commit": os.environ.get("GITHUB_SHA", "local"),
        "startup_fix": "Retry when PMHQ has not returned account information yet",
        "pmhq_source": {"url": pmhq_url, "sha512_base64": PMHQ_INTEGRITY},
    }
    for tool, (version, integrity) in MEDIA.items():
        url = f"https://registry.npmjs.org/@{tool}-installer/darwin-arm64/-/darwin-arm64-{version}.tgz"
        archive = downloads / f"{tool}.tgz"
        download(url, archive, "sha512", integrity)
        with tarfile.open(archive, "r:gz") as package:
            target = base / "bin/llbot" / tool
            target.write_bytes(package.extractfile(f"package/{tool}").read())
            target.chmod(0o755)
            notices = root / "licenses" / tool
            notices.mkdir(parents=True)
            for member in package:
                if member.isfile() and Path(member.name).name != tool:
                    (notices / Path(member.name).name).write_bytes(package.extractfile(member).read())
        component_record[tool] = {"url": url, "version": version, "sha512_base64": integrity}
    required = ["bin/llbot/node", "bin/llbot/ffmpeg", "bin/llbot/ffprobe", "bin/pmhq/pmhq", "bin/pmhq/libpmhq.dylib", "bin/qq/QQ.app/Contents/MacOS/QQ"]
    if kind == "CLI":
        required.append("llbot")
    else:
        required.append("LuckyLilliaDesktop")
    for relative in required:
        executable = base / relative
        executable.chmod(executable.stat().st_mode | 0o111)
        architecture = subprocess.check_output(["lipo", "-archs", str(executable)], text=True).strip()
        if "arm64" not in architecture.split():
            raise RuntimeError(f"Missing arm64 architecture: {relative}: {architecture}")
    for relative in ("bin/pmhq/pmhq", "bin/pmhq/libpmhq.dylib", "bin/llbot/llbot.js"):
        component_record[relative + "_sha256"] = hashlib.file_digest((base / relative).open("rb"), "sha256").hexdigest()
    component_record["pmhq_version"] = subprocess.check_output([base / "bin/pmhq/pmhq", "--version"], text=True).strip()
    component_record["node_version"] = subprocess.check_output([base / "bin/llbot/node", "--version"], text=True).strip()
    with (base / "bin/qq/QQ.app/Contents/Info.plist").open("rb") as stream:
        info = plistlib.load(stream)
        component_record["qq_bundle_version"] = info.get("CFBundleShortVersionString")
        component_record["qq_bundle_build"] = info.get("CFBundleVersion")
    component_record["qq_version"] = json.loads((base / "bin/qq/QQ.app/Contents/Resources/app/package.json").read_text())["version"]
    (base / "bin/pmhq/pmhq_config.json").write_text(json.dumps({"qq_path": "", "quick_login_qq": "", "default_host": "127.0.0.1", "default_port": 13000}, indent=2))
    for name in ("Start.command", "prepare.cjs"):
        shutil.copy2(source / name, root / name)
    (root / "Start.command").chmod(0o755)
    (root / "package-kind.txt").write_text(kind)
    (root / "COMPONENTS.json").write_text(json.dumps(component_record, indent=2) + "\n")
    shutil.copy2(source / "README.md", root / "README.md")
    if kind == "Desktop":
        subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(root / "LuckyLilliaDesktop.app")], check=True)
    archive = output / f"LLBot-{kind}-macos-arm64.tar.gz"
    with tarfile.open(archive, "w:gz", compresslevel=5) as package:
        package.add(root, arcname=root.name)
    digest = hashlib.file_digest(archive.open("rb"), "sha256").hexdigest()
    archive.with_suffix(archive.suffix + ".sha256").write_text(f"{digest}  {archive.name}\n")
    print(json.dumps(component_record, indent=2), flush=True)


if __name__ == "__main__":
    main()

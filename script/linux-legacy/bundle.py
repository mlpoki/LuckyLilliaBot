"""Assemble the historical Linux release with pinned platform dependencies."""

import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import zipfile


ARCHIVES = {
    "x64": {
        "deb_arch": "amd64",
        "llbot_sha256": "37fd13134281808291cd7ccd2aba64250280ef3de19b17d2b6a88b08ed16b70a",
        "qq_sha256": "a4252719c1beb8adce0da09ebfc310ce50c79ea548f5cce429505765d0bfba84",
        "pmhq_integrity": "U7KKfmx4JKYBitxAUfonW51R1+gFchXox0R2qib2DIcDm6nQFUyyhGBtx+Qhd1qfmblAS/IM+WPKAyXeUgT53Q==",
        "ffmpeg_version": "4.1.0",
        "ffmpeg_integrity": "Y5BWhGLU/WpQjOArNIgXD3z5mxxdV8c41C+U15nsE5yF8tVcdCGet5zPs5Zy3Ta6bU7haGpIzryutqCGQA/W8A==",
        "ffprobe_integrity": "D3UeqTLYPNs7pBWPLUYGehPdRVqU8eACox4OZy3pZUZatxye2YKlvBwEfaLdL1v2Z4FOAlLUhms0kY8m8kqSRA==",
    },
    "arm64": {
        "deb_arch": "arm64",
        "llbot_sha256": "6e98701e73c734a8957475f04e492d618d705e532d05b7df2118ec36fa1e605b",
        "qq_sha256": "870ed3c0e417e9bb3a021c1d56518bc2fbba82d1c3e1871384f64ab7e21923f7",
        "pmhq_integrity": "axeuxU3y88YqrVVAhj+t+X4+1Hx2CnafTEGvr7YxWr5Ly0Z1TdVVdjfxK5gGPL5abxXYunk7DTV77OfCa48NaQ==",
        "ffmpeg_version": "4.1.4",
        "ffmpeg_integrity": "dljEqAOD0oIM6O6DxBW9US/FkvqvQwgJ2lGHOwHDDwu/pX8+V0YsDL1xqHbj1DMX/+nP9rxw7G7gcUvGspSoKg==",
        "ffprobe_integrity": "X1VvWtlLs6ScP73biVLuHD5ohKJKsMTa0vafCESOen4mOoNeLAYbxOVxDWAdFz9cpZgRiloFj5QD6nDj8E28yQ==",
    },
}


def download(url, path, algorithm, expected):
    subprocess.run([
        "curl", "--fail", "--location", "--silent", "--show-error",
        "--retry", "3", "--connect-timeout", "20", "--max-time", "300",
        url, "--output", str(path),
    ], check=True)
    digest = hashlib.file_digest(path.open("rb"), algorithm).digest()
    actual = base64.b64encode(digest).decode() if algorithm == "sha512" else digest.hex()
    if actual != expected:
        raise RuntimeError(f"Digest mismatch for {url}")


def install_npm_binary(tool, arch, version, integrity, downloads, root):
    url = f"https://registry.npmjs.org/@{tool}-installer/linux-{arch}/-/linux-{arch}-{version}.tgz"
    archive = downloads / f"{tool}.tgz"
    download(url, archive, "sha512", integrity)
    with tarfile.open(archive, "r:gz") as package:
        data = package.extractfile(f"package/{tool}").read()
        destination = root / "bin" / "llbot" / tool
        destination.write_bytes(data)
        destination.chmod(0o755)
        notices = root / "licenses" / tool
        notices.mkdir(parents=True)
        for member in package:
            if member.isfile() and Path(member.name).name != tool:
                (notices / Path(member.name).name).write_bytes(package.extractfile(member).read())
    return {"url": url, "sha512_base64": integrity, "version": version}


def main():
    arch = sys.argv[1]
    lock = ARCHIVES[arch]
    workspace = Path.cwd()
    output = workspace / "out"
    output.mkdir(exist_ok=True)
    downloads = output / "downloads"
    downloads.mkdir(exist_ok=True)
    root = output / f"LLBot-CLI-linux-{arch}"
    root.mkdir()
    upstream_url = f"https://github.com/LuckyLilliaDev/LuckyLilliaBot/releases/download/v7.12.15/LLBot-CLI-linux-{arch}.zip"
    upstream = downloads / "llbot.zip"
    download(upstream_url, upstream, "sha256", lock["llbot_sha256"])
    with zipfile.ZipFile(upstream) as package:
        package.extractall(root)
    main_script = root / "bin/llbot/llbot.js"
    source = main_script.read_text()
    old_guard = "if (!pmhqSelfInfo.online) {"
    if source.count(old_guard) != 1:
        raise RuntimeError("Historical login readiness guard could not be identified uniquely")
    source = source.replace(old_guard, "if (!pmhqSelfInfo?.online) {")
    source = source.replace("//# sourceMappingURL=llbot.js.map", "")
    main_script.write_text(source)
    (root / "bin/llbot/llbot.js.map").unlink()
    for name in ("llbot", "bin/llbot/node", "bin/pmhq/pmhq"):
        (root / name).chmod(0o755)
    pmhq_url = f"https://registry.npmjs.org/pmhq-dist-linux-{arch}/-/pmhq-dist-linux-{arch}-7.3.2.tgz"
    pmhq = downloads / "pmhq.tgz"
    download(pmhq_url, pmhq, "sha512", lock["pmhq_integrity"])
    with tarfile.open(pmhq, "r:gz") as package:
        for source, target in [(f"pmhq-linux-{arch}", "pmhq"), ("libpmhq.so", "libpmhq.so")]:
            data = package.extractfile(f"package/{source}").read()
            if (root / "bin/pmhq" / target).read_bytes() != data:
                raise RuntimeError(f"Historical release PMHQ differs from npm 7.3.2: {target}")
        (root / "bin/pmhq/package.json").write_bytes(package.extractfile("package/package.json").read())
    qq_url = f"https://github.com/zydou/QQ-Linux/releases/download/3.2.23-260108/QQ-3.2.23-260108-{lock['deb_arch']}.deb"
    qq_deb = downloads / "qq.deb"
    download(qq_url, qq_deb, "sha256", lock["qq_sha256"])
    qq_extract = downloads / "qq-extracted"
    subprocess.run(["dpkg-deb", "--extract", str(qq_deb), str(qq_extract)], check=True)
    shutil.copytree(qq_extract / "opt/QQ", root / "QQ", symlinks=True)
    qq_version = json.loads((root / "QQ/resources/app/package.json").read_text())["version"]
    if qq_version != "3.2.23-44343":
        raise RuntimeError(f"Unexpected QQ version {qq_version}")
    media = {}
    for tool in ("ffmpeg", "ffprobe"):
        version = lock["ffmpeg_version"] if tool == "ffmpeg" else "5.2.0"
        media[tool] = install_npm_binary(tool, arch, version, lock[f"{tool}_integrity"], downloads, root)
    for name in ("start.sh", "install-dependencies.sh"):
        shutil.copy2(workspace / "script/linux-legacy" / name, root / name)
        (root / name).chmod(0o755)
    shutil.copy2(workspace / "script/linux-legacy/README.md", root / "README.md")
    components = {
        "llbot": {"version": "7.12.15", "url": upstream_url, "sha256": lock["llbot_sha256"]},
        "qq": {"version": qq_version, "url": qq_url, "sha256": lock["qq_sha256"]},
        "pmhq": {"version": "7.3.2", "url": pmhq_url, "sha512_base64": lock["pmhq_integrity"]},
        "media": media,
        "node_version": subprocess.check_output([root / "bin/llbot/node", "--version"], text=True).strip(),
        "workflow_commit": os.environ.get("GITHUB_SHA", "local"),
        "startup_fix": "Retry when PMHQ getSelfInfo has not returned an object yet",
        "patched_llbot_sha256": hashlib.file_digest(main_script.open("rb"), "sha256").hexdigest(),
    }
    (root / "COMPONENTS.json").write_text(json.dumps(components, indent=2) + "\n")
    for relative in ("llbot", "bin/pmhq/pmhq", "bin/llbot/node", "bin/llbot/ffmpeg", "bin/llbot/ffprobe", "QQ/qq"):
        result = subprocess.run(["file", str(root / relative)], check=True, capture_output=True, text=True)
        expected = "x86-64" if arch == "x64" else "ARM aarch64"
        if expected not in result.stdout:
            raise RuntimeError(result.stdout)
    archive = output / f"LLBot-CLI-linux-{arch}.tar.gz"
    with tarfile.open(archive, "w:gz", compresslevel=5) as package:
        package.add(root, arcname=root.name)
    digest = hashlib.file_digest(archive.open("rb"), "sha256").hexdigest()
    archive.with_suffix(archive.suffix + ".sha256").write_text(f"{digest}  {archive.name}\n")
    print(f"Assembled {archive.name}", flush=True)


if __name__ == "__main__":
    main()

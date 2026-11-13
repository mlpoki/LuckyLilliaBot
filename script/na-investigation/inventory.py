"""Read pinned public release bytes. Never execute package code or native libraries."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

EXPECTED = {
    'LLBot-CLI-win-x64.zip': '3b29f2bdaafbbb1e0e494e42d81da7566aeb16114e9eb42a5d168c59dbcadcb7',
    'LLBot-Desktop-win-x64.zip': '38fde3cc61d76fc9bfcfabcc7b0b362a5c938016d8b57a1665d4173492d3981f',
}
out = Path('evidence')
out.mkdir(exist_ok=True)
packages = Path('packages')
packages.mkdir(exist_ok=True)
release = json.loads(subprocess.check_output([
    'gh', 'api', 'repos/mlpoki/LuckyLilliaBot/releases/tags/v8.3.2',
], text=True, encoding='utf-8'))
(out / 'release.json').write_text(json.dumps(release, indent=2), encoding='utf-8')
report = []
for name, expected in EXPECTED.items():
    asset = next(a for a in release['assets'] if a['name'] == name)
    if asset['digest'] != 'sha256:' + expected:
        raise RuntimeError(f'Source asset changed: {name}')
    subprocess.run(['gh', 'release', 'download', 'v8.3.2', '--repo',
                    'mlpoki/LuckyLilliaBot', '--pattern', name, '--dir', str(packages)], check=True)
    archive = packages / name
    actual = hashlib.sha256(archive.read_bytes()).hexdigest()
    if actual != expected:
        raise RuntimeError(f'Package SHA-256 mismatch: {name}')
    component = name.removesuffix('.zip')
    entries = []
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            if member.is_dir():
                continue
            data = z.read(member)
            path = member.filename.replace('\\', '/')
            if path.startswith('/') or '..' in path.split('/') or ':' in path:
                raise RuntimeError(f'Unsafe archive member: {path}')
            item = {'path': path, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            if path.endswith('.json') and len(data) < 100_000:
                try:
                    item['json'] = json.loads(data)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    pass
            entries.append(item)
            if path.endswith(('.exe', '.dll', '.node')):
                # Preserve launcher/native bytes for subsequent REA read-only analysis.
                if not path.endswith(('node.exe', 'ffmpeg.exe', 'ffprobe.exe')):
                    target = out / 'binaries' / component / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
            if path.endswith(('.js', '.txt', '.json')) and len(data) < 5_000_000:
                target = out / 'text' / component / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            if path.endswith(('.exe', '.dll', '.node')):
                # Literal byte strings are candidates only, not observed requests or call paths.
                urls = sorted(set(m.decode('ascii') for m in re.findall(rb'https?://[A-Za-z0-9_./:?=&%#@+~-]{4,250}', data)))
                item['ascii_url_candidates'] = urls
    report.append({'name': name, 'sha256': actual, 'asset_id': asset['id'], 'files': entries})
(out / 'inventory.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps([{'name': p['name'], 'sha256': p['sha256'], 'files': len(p['files'])} for p in report]))

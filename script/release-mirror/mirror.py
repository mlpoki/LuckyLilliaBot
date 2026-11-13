"""Mirror released bytes and the original Git tag in fork GitHub Actions."""

import base64
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import zipfile


UPSTREAM = 'LuckyLilliaDev/LuckyLilliaBot'
FORK = 'mlpoki/LuckyLilliaBot'
NAMES = {
    'LuckyLillia-CLI-win-x64.zip': 'LLBot-CLI-win-x64.zip',
    'LuckyLillia-Desktop-win-x64.zip': 'LLBot-Desktop-win-x64.zip',
    'LuckyLillia-CLI-linux-x64.zip': 'LLBot-CLI-linux-x64.zip',
    'LuckyLillia-CLI-linux-arm64.zip': 'LLBot-CLI-linux-arm64.zip',
}
MARKER = '<!-- llbot-release-mirror:LuckyLilliaDev/LuckyLilliaBot -->'


class GitHub:
    def __init__(self, token):
        self.token = token

    def request(self, path, method='GET', data=None):
        url = path if path.startswith('https://uploads.github.com/') else 'https://api.github.com' + path
        headers = {
            'Authorization': 'Bearer ' + self.token,
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
        }
        if isinstance(data, bytes):
            headers['Content-Type'] = 'application/zip'
        elif data is not None:
            headers['Content-Type'] = 'application/json'
            data = json.dumps(data).encode()
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 404 and method == 'GET':
                return None
            raise RuntimeError(f'GitHub HTTP {error.code} {method} {url}: {error.read().decode()}') from error

    def download(self, asset, path):
        result = subprocess.run([
            'curl', '--fail', '--location', '--silent', '--show-error',
            '--connect-timeout', '30', '--max-time', '600',
            '--header', 'Authorization: Bearer ' + self.token,
            '--header', 'Accept: application/octet-stream',
            '--output', str(path), asset['url'],
        ])
        if result.returncode:
            raise RuntimeError(f'Asset download failed: {asset["name"]}, curl exit {result.returncode}')


def select_assets(release):
    if not release or release['draft'] or release['prerelease']:
        raise RuntimeError('Upstream has no latest official Release')
    result = []
    for name in NAMES:
        matches = [asset for asset in release['assets'] if asset['name'] == name]
        if len(matches) != 1:
            actual = [asset['name'] for asset in release['assets']]
            raise RuntimeError(f'Required asset {name}: expected one, found {len(matches)}. Actual assets: {actual}')
        result.append(matches[0])
    return result


def snapshot(release):
    return {
        'id': release['id'], 'tag_name': release['tag_name'],
        'name': release['name'], 'body': release.get('body'),
        'assets': [{key: asset.get(key) for key in ('id', 'name', 'size', 'digest', 'url')}
                   for asset in select_assets(release)],
    }


def verify_file(path, asset, expected=None):
    if path.stat().st_size == 0 or path.stat().st_size != asset['size']:
        raise RuntimeError(f'Asset size mismatch: {asset["name"]}')
    with path.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    if asset.get('digest') and asset['digest'] != 'sha256:' + digest:
        raise RuntimeError(f'Asset digest mismatch: {asset["name"]}')
    if expected and digest != expected:
        raise RuntimeError(f'Existing asset content conflict: {asset["name"]}')
    return digest


def git(directory, *args):
    return subprocess.check_output(['git', '-C', str(directory), *args], text=True).strip()


def remote_tag(directory, remote, tag):
    output = git(directory, 'ls-remote', '--tags', remote, 'refs/tags/' + tag)
    return output.split()[0] if output else None


def check_tag(actual, expected):
    if actual != expected:
        raise RuntimeError(f'Tag object conflict or missing tag: existing {actual}, upstream {expected}')


def check_fork_tag(directory, tag, expected):
    actual = remote_tag(directory, 'fork', tag)
    if actual is not None:
        check_tag(actual, expected)


def find_release(api, tag):
    # Listing includes drafts, so interrupted first uploads can resume.
    page = 1
    while True:
        releases = api.request(f'/repos/{FORK}/releases?per_page=100&page={page}')
        if releases is None:
            raise RuntimeError('Cannot list fork Releases')
        for release in releases:
            if release['tag_name'] == tag:
                if MARKER not in (release.get('body') or ''):
                    raise RuntimeError(f'Existing Release {release["id"]} has no mirror source marker')
                return release
        if len(releases) < 100:
            return None
        page += 1


def release_assets(api, release):
    result = []
    page = 1
    while True:
        assets = api.request(f'/repos/{FORK}/releases/{release["id"]}/assets?per_page=100&page={page}')
        if assets is None:
            raise RuntimeError('Release disappeared while reading assets')
        result.extend(assets)
        if len(assets) < 100:
            return result
        page += 1


def verify_existing(api, assets, files, directory):
    present = set()
    for item in files:
        matches = [asset for asset in assets if asset['name'] == item['target_name']]
        if len(matches) > 1:
            raise RuntimeError(f'Duplicate target asset: {item["target_name"]}')
        if matches:
            asset = matches[0]
            if asset['size'] != item['size']:
                raise RuntimeError(f'Existing asset size conflict: {asset["name"]}')
            path = directory / ('verify-' + asset['name'])
            # Verify actual published bytes even when the API supplies a digest.
            api.download(asset, path)
            verify_file(path, asset, item['sha256'])
            present.add(asset['name'])
    return present


def mirror(api, directory, evidence):
    upstream = '/repos/' + UPSTREAM
    release = api.request(upstream + '/releases/latest')  # Exactly once per run.
    locked = snapshot(release)
    evidence['upstream'] = locked
    evidence['upstream_url'] = release['html_url']
    tag = locked['tag_name']
    subprocess.run(['git', 'check-ref-format', 'refs/tags/' + tag], check=True)
    source = directory / 'source.git'
    subprocess.run(['git', 'init', '--bare', str(source)], check=True)
    git(source, 'remote', 'add', 'upstream', f'https://github.com/{UPSTREAM}.git')
    git(source, 'remote', 'add', 'fork', f'https://github.com/{FORK}.git')
    git(source, 'fetch', '--no-tags', 'upstream', f'refs/tags/{tag}:refs/tags/{tag}')
    object_sha = git(source, 'rev-parse', 'refs/tags/' + tag)
    commit = git(source, 'rev-parse', f'refs/tags/{tag}^{{commit}}')
    evidence.update(tag_object=object_sha, commit=commit,
                    tag_type=git(source, 'cat-file', '-t', object_sha))
    check_fork_tag(source, tag, object_sha)
    files = evidence['files'] = []
    for asset in select_assets(release):
        path = directory / NAMES[asset['name']]
        api.download(asset, path)
        digest = verify_file(path, asset)
        with zipfile.ZipFile(path) as archive:
            bad = archive.testzip()
            if bad:
                raise RuntimeError(f'Corrupt ZIP member: {bad}')
        files.append({'source_name': asset['name'], 'target_name': path.name,
                      'source_id': asset['id'], 'size': asset['size'], 'sha256': digest})
    target = find_release(api, tag)
    if target:
        verify_existing(api, release_assets(api, target), files, directory)

    # Revalidate the locked version immediately before any write.
    current = api.request(upstream + f'/releases/{release["id"]}')
    if snapshot(current) != locked:
        raise RuntimeError('Upstream Release inputs changed during download')
    check_tag(remote_tag(source, 'upstream', tag), object_sha)
    check_fork_tag(source, tag, object_sha)
    git(source, 'push', 'fork', f'refs/tags/{tag}:refs/tags/{tag}')
    evidence['tag_synced'] = True
    body = (release.get('body') or '') + '\n\n---\n' + MARKER + '\n'
    body += (f'\nMirrored from {release["html_url"]}\n\n'
             f'- Original tag `{tag}`, commit `{commit}`, tag object `{object_sha}`.\n'
             f'- Synchronized at {evidence["started_at"]}. Windows/Linux only.\n'
             '- Upstream finished packages copied directly, without recompilation.\n'
             '- Package bytes match upstream. Runtime functionality has not been independently verified.\n'
             '- Asset renames only, archive contents and original signatures preserved.\n')
    for original, renamed in NAMES.items():
        body += f'  - `{original}` → `{renamed}`\n'
    if target is None:
        target = api.request(f'/repos/{FORK}/releases', 'POST', {
            'tag_name': tag, 'name': release['name'], 'body': body,
            'draft': True, 'prerelease': False,
        })
    evidence['fork_release_id'] = target['id']
    evidence['fork_release_url'] = target['html_url']
    present = verify_existing(api, release_assets(api, target), files, directory)
    evidence['uploaded'] = []
    for item in files:
        if item['target_name'] in present:
            continue
        url = target['upload_url'].split('{')[0] + '?name=' + urllib.parse.quote(item['target_name'])
        api.request(url, 'POST', (directory / item['target_name']).read_bytes())
        evidence['uploaded'].append(item['target_name'])
    if verify_existing(api, release_assets(api, target), files, directory) != set(NAMES.values()):
        raise RuntimeError('Required published assets are incomplete')
    check_tag(remote_tag(source, 'fork', tag), object_sha)
    target = api.request(f'/repos/{FORK}/releases/{target["id"]}', 'PATCH', {
        'name': release['name'], 'body': body, 'draft': False, 'prerelease': False,
    })
    published = api.request(f'/repos/{FORK}/releases/{target["id"]}')
    if published['draft'] or published['prerelease'] or published['tag_name'] != tag:
        raise RuntimeError('Release publication verification failed')
    if verify_existing(api, release_assets(api, published), files, directory) != set(NAMES.values()):
        raise RuntimeError('Published assets changed')
    check_tag(remote_tag(source, 'fork', tag), object_sha)
    git(source, 'fetch', '--no-tags', 'fork', f'refs/tags/{tag}:refs/verification/published')
    evidence['fork_tag_object'] = git(source, 'rev-parse', 'refs/verification/published')
    evidence['fork_commit'] = git(source, 'rev-parse', 'refs/verification/published^{commit}')
    if evidence['fork_tag_object'] != object_sha or evidence['fork_commit'] != commit:
        raise RuntimeError('Published tag object or source commit mismatch')
    evidence['status'] = 'complete'


def main():
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('GITHUB_REPOSITORY') != FORK:
        raise RuntimeError('This script must run in the authorized fork GitHub Actions')
    directory = Path(os.environ['RUNNER_TEMP']) / 'llbot-mirror'
    directory.mkdir()
    evidence = {
        'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'incomplete', 'workflow_sha': os.environ['WORKFLOW_SHA'],
        'script_commit': git(Path.cwd(), 'rev-parse', 'HEAD'),
        'run_url': f'https://github.com/{FORK}/actions/runs/{os.environ["GITHUB_RUN_ID"]}',
        'run_attempt': os.environ['GITHUB_RUN_ATTEMPT'],
    }
    token = os.environ['GH_TOKEN']
    auth = base64.b64encode(('x-access-token:' + token).encode()).decode()
    os.environ.update(GIT_CONFIG_COUNT='1',
                      GIT_CONFIG_KEY_0='http.https://github.com/.extraheader',
                      GIT_CONFIG_VALUE_0='AUTHORIZATION: basic ' + auth)
    try:
        mirror(GitHub(token), directory, evidence)
    except Exception as error:
        evidence['error'] = str(error)
        raise
    finally:
        (directory / 'evidence.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as summary:
            summary.write('## Release mirror evidence\n\n```json\n' + json.dumps(evidence, indent=2) + '\n```\n')


if __name__ == '__main__':
    main()

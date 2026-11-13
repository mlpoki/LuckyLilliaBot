"""Offline behavioral checks, executed by fork Actions without application code."""

import copy
import hashlib
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import mirror


class FakeGitHub:
    def __init__(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('bin/llbot/original.txt', 'original upstream bytes')
        self.payload = buffer.getvalue()
        self.release = {
            'id': 10, 'tag_name': 'v1.2.3', 'name': 'Original title',
            'body': 'Original notes https://example.org/update',
            'draft': False, 'prerelease': False, 'html_url': 'https://example.org/source',
            'assets': [self.asset(name, index) for index, name in enumerate(mirror.NAMES, 1)],
        }
        self.release['assets'].append(self.asset('macos.zip', 5))
        self.target = None
        self.assets = []
        self.contents = {}
        self.latest_calls = 0
        self.uploads = 0
        self.fail_upload = None
        self.changed_inputs = False

    def asset(self, name, asset_id):
        return {'id': asset_id, 'name': name, 'size': len(self.payload),
                'digest': 'sha256:' + hashlib.sha256(self.payload).hexdigest(),
                'url': 'https://example.org/assets/' + str(asset_id)}

    def request(self, path, method='GET', data=None):
        if path.endswith('/releases/latest'):
            self.latest_calls += 1
            return copy.deepcopy(self.release)
        if path.endswith('/releases/10'):
            value = copy.deepcopy(self.release)
            if self.changed_inputs:
                value['assets'][0]['id'] += 1000
            return value
        if '/assets?per_page=' in path:
            return copy.deepcopy(self.assets)
        if '/releases?per_page=' in path:
            return [copy.deepcopy(self.target)] if self.target else []
        if method == 'POST' and path.startswith('https://uploads.github.com/'):
            if self.fail_upload == self.uploads + 1:
                raise RuntimeError('Injected upload interruption')
            from urllib.parse import parse_qs, urlparse
            name = parse_qs(urlparse(path).query)['name'][0]
            asset = self.asset(name, 100 + self.uploads)
            self.assets.append(asset)
            self.contents[asset['url']] = data
            self.uploads += 1
            return copy.deepcopy(asset)
        if method == 'POST' and path.endswith('/releases'):
            self.target = dict(data, id=20, html_url='https://example.org/fork',
                               upload_url='https://uploads.github.com/repos/fork/releases/20/assets{?name,label}')
            return copy.deepcopy(self.target)
        if path.endswith('/releases/20'):
            if method == 'PATCH':
                self.target.update(data)
            return copy.deepcopy(self.target)
        raise AssertionError((method, path))

    def download(self, asset, path):
        path.write_bytes(self.contents.get(asset['url'], self.payload))


class MirrorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.upstream = self.root / 'upstream'
        self.fork = self.root / 'fork.git'
        subprocess.run(['git', 'init', str(self.upstream)], check=True, capture_output=True)
        self.git = mirror.git
        self.git(self.upstream, 'config', 'user.name', 'Mirror test')
        self.git(self.upstream, 'config', 'user.email', 'mirror@example.org')
        self.git(self.upstream, 'commit', '--allow-empty', '-m', 'Upstream source')
        self.git(self.upstream, 'tag', '-a', 'v1.2.3', '-m', 'Original annotated tag')
        subprocess.run(['git', 'init', '--bare', str(self.fork)], check=True, capture_output=True)
        self.api = FakeGitHub()
        self.counter = 0

    def routed_git(self, directory, *args):
        if args[:2] == ('remote', 'add'):
            location = self.upstream if args[2] == 'upstream' else self.fork
            args = (*args[:3], str(location))
        return self.git(directory, *args)

    def run_mirror(self):
        self.counter += 1
        directory = self.root / str(self.counter)
        directory.mkdir()
        evidence = {'started_at': '2026-11-13T00:00:00Z', 'status': 'incomplete'}
        with patch.object(mirror, 'git', side_effect=self.routed_git):
            mirror.mirror(self.api, directory, evidence)
        return evidence

    def test_first_sync_preserves_annotated_object_and_excludes_macos(self):
        evidence = self.run_mirror()
        self.assertEqual(evidence['status'], 'complete')
        self.assertEqual(evidence['tag_type'], 'tag')
        self.assertEqual(self.git(self.upstream, 'rev-parse', 'v1.2.3'),
                         self.git(self.fork, 'rev-parse', 'v1.2.3'))
        self.assertEqual({a['name'] for a in self.api.assets}, set(mirror.NAMES.values()))
        self.assertEqual(self.api.latest_calls, 1)
        self.assertFalse(self.api.target['draft'])
        self.assertTrue(self.api.target['body'].startswith(self.api.release['body']))

    def test_lightweight_tag(self):
        self.git(self.upstream, 'tag', '-d', 'v1.2.3')
        self.git(self.upstream, 'tag', 'v1.2.3')
        self.assertEqual(self.run_mirror()['tag_type'], 'commit')

    def test_identical_rerun_skips_all_uploads(self):
        self.run_mirror()
        before = copy.deepcopy(self.api.assets)
        self.run_mirror()
        self.assertEqual(self.api.assets, before)
        self.assertEqual(self.api.uploads, 4)
        self.assertEqual(self.api.latest_calls, 2)

    def test_upload_interruption_resumes_draft(self):
        self.api.fail_upload = 2
        with self.assertRaisesRegex(RuntimeError, 'interruption'):
            self.run_mirror()
        self.assertTrue(self.api.target['draft'])
        self.assertEqual(len(self.api.assets), 1)
        self.api.fail_upload = None
        self.run_mirror()
        self.assertEqual(self.api.uploads, 4)
        self.assertFalse(self.api.target['draft'])

    def test_missing_asset_and_duplicate_asset_fail_before_writes(self):
        for duplicate in (False, True):
            with self.subTest(duplicate=duplicate):
                self.api = FakeGitHub()
                if duplicate:
                    self.api.release['assets'].append(self.api.release['assets'][0])
                else:
                    self.api.release['assets'].pop(0)
                with self.assertRaisesRegex(RuntimeError, 'Required asset'):
                    self.run_mirror()
                self.assertIsNone(self.api.target)

    def test_no_official_release(self):
        for release in (None, dict(self.api.release, prerelease=True), dict(self.api.release, draft=True)):
            self.api.release = release
            with self.assertRaisesRegex(RuntimeError, 'no latest official'):
                self.run_mirror()

    def test_missing_tag(self):
        self.git(self.upstream, 'tag', '-d', 'v1.2.3')
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_mirror()
        self.assertIsNone(self.api.target)

    def test_same_commit_different_annotation_conflicts(self):
        self.run_mirror()
        self.git(self.upstream, 'tag', '-f', '-a', 'v1.2.3', '-m', 'Different annotation')
        with self.assertRaisesRegex(RuntimeError, 'Tag object conflict'):
            self.run_mirror()
        self.assertEqual(self.api.uploads, 4)

    def test_changed_release_inputs_fail_before_writes(self):
        self.api.changed_inputs = True
        with self.assertRaisesRegex(RuntimeError, 'inputs changed'):
            self.run_mirror()
        self.assertIsNone(self.api.target)
        result = subprocess.run(['git', '-C', str(self.fork), 'show-ref', '--tags'],
                                capture_output=True)
        self.assertEqual(result.returncode, 1)

    def test_upstream_tag_mutation_fails_before_writes(self):
        original = self.api.download
        def mutate(asset, path):
            original(asset, path)
            self.git(self.upstream, 'tag', '-f', '-a', 'v1.2.3', '-m', 'Mutated while downloading')
        self.api.download = mutate
        with self.assertRaisesRegex(RuntimeError, 'Tag object conflict'):
            self.run_mirror()
        self.assertIsNone(self.api.target)

    def test_existing_asset_different_bytes_conflicts(self):
        self.run_mirror()
        asset = self.api.assets[0]
        self.api.contents[asset['url']] = b'x' * asset['size']
        with self.assertRaisesRegex(RuntimeError, 'digest mismatch|content conflict'):
            self.run_mirror()
        self.assertEqual(self.api.uploads, 4)

    def test_digest_absent_still_checks_bytes(self):
        self.run_mirror()
        self.api.assets[0]['digest'] = None
        self.api.contents[self.api.assets[0]['url']] = b'x' * self.api.assets[0]['size']
        with self.assertRaisesRegex(RuntimeError, 'content conflict'):
            self.run_mirror()

    def test_handwritten_release_is_preserved(self):
        self.run_mirror()
        self.api.target['body'] = 'User release notes'
        with self.assertRaisesRegex(RuntimeError, 'no mirror source marker'):
            self.run_mirror()
        self.assertEqual(self.api.target['body'], 'User release notes')

    def test_missing_asset_on_published_release_is_restored(self):
        self.run_mirror()
        self.api.assets.pop()
        unrelated = self.api.asset('user-file.txt', 900)
        self.api.assets.append(unrelated)
        self.run_mirror()
        self.assertEqual(self.api.uploads, 5)
        self.assertIn(unrelated, self.api.assets)

    def test_upstream_digest_failure_stops_before_writes(self):
        self.api.release['assets'][0]['digest'] = 'sha256:invalid'
        with self.assertRaisesRegex(RuntimeError, 'digest mismatch'):
            self.run_mirror()
        self.assertIsNone(self.api.target)

    def test_zero_byte_download_fails_before_writes(self):
        self.api.payload = b''
        with self.assertRaisesRegex(RuntimeError, 'size mismatch'):
            self.run_mirror()
        self.assertIsNone(self.api.target)

    def test_http_failure_does_not_fall_back(self):
        with patch.object(self.api, 'request', side_effect=RuntimeError('GitHub HTTP 403 rate limit')):
            with self.assertRaisesRegex(RuntimeError, 'HTTP 403'):
                self.run_mirror()
        self.assertIsNone(self.api.target)


if __name__ == '__main__':
    unittest.main()

"""Observable integrity, failure, portability and release-isolation tests."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from fiction_tools import (COVERAGE, digest, finalize, json_bytes, make_snapshot,
                           parse_json, safe_path, verify_snapshot, write_new)
from validate_repo import scan_text, validate_repo, validate_skill
from build_release import build

REPO = Path(__file__).resolve().parents[1]


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='fiction-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.put('canon.md', 'A limit stays in effect.\n')
        self.put('outline.md', 'Preserve a partial record.\n')
        self.put('candidate.md', '# Scene\r\n\r\n记录缺了一位。\r\n')
        self.put('approval.json', {'outline_sha256': self.bind('outline.md')['sha256'],
                                   'decision': 'approved', 'evidence': 'Synthetic test approval only.'})
        self.snapshot = make_snapshot(self.root, ['canon.md', 'outline.md', 'approval.json'])
        self.put('snapshot.json', self.snapshot)
        self.review = {
            'candidate_sha256': self.bind('candidate.md')['sha256'],
            'outline_sha256': self.bind('outline.md')['sha256'],
            'source_snapshot_sha256': self.bind('snapshot.json')['sha256'],
            'conclusion': 'pass', 'round': 0, 'mode': 'single-reviewer',
            'coverage': {k: {'status': 'checked', 'evidence': 'Synthetic fixture; no semantic claim.'} for k in COVERAGE},
            'issues': []}
        self.put('review.json', self.review)
        self.job = {'schema': 1, **{k: self.bind(rel) for k, rel in {
            'candidate': 'candidate.md', 'outline': 'outline.md', 'approval': 'approval.json',
            'source_snapshot': 'snapshot.json', 'review': 'review.json'}.items()}}

    def put(self, rel, value):
        data = json_bytes(value) if isinstance(value, (dict, list)) else value.encode('utf-8')
        (self.root / rel).write_bytes(data)

    def bind(self, rel):
        return {'path': rel, 'sha256': digest((self.root / rel).read_bytes())}

    def with_review(self, value):
        self.put('review.json', value)
        job = copy.deepcopy(self.job)
        job['review'] = self.bind('review.json')
        return job

    def test_snapshot_detects_changed_source(self):
        self.assertEqual(len(verify_snapshot(self.root, self.snapshot)), 3)
        self.put('canon.md', 'Changed limit.\n')
        with self.assertRaisesRegex(ValueError, 'Source changed'):
            verify_snapshot(self.root, self.snapshot)

    def test_snapshot_detects_missing_source(self):
        (self.root / 'canon.md').unlink()
        with self.assertRaises(FileNotFoundError):
            verify_snapshot(self.root, self.snapshot)

    def test_snapshot_rejects_empty_duplicate_invalid_entries(self):
        for value in ({'schema': 1, 'files': []}, {'schema': 1, 'files': self.snapshot['files'] * 2},
                      {'schema': 1, 'files': [{'path': 'canon.md', 'sha256': 'x'}]}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                verify_snapshot(self.root, value)
        with self.assertRaises(ValueError):
            make_snapshot(self.root, ['canon.md', 'canon.md'])

    def test_rejects_path_escape_and_noncanonical_paths(self):
        for rel in ('../outside.md', '/absolute.md', 'a/../canon.md', './canon.md', '.',
                    'a//b.md', 'drive:' + '/file.md', 'a' + '\\' + 'file.md'):
            with self.subTest(path=rel), self.assertRaises(ValueError):
                safe_path(self.root, rel)

    def test_rejects_symlink_input_when_supported(self):
        try:
            (self.root / 'alias.md').symlink_to(self.root / 'canon.md')
        except OSError:
            self.skipTest('OS does not permit creating symlinks for this account')
        with self.assertRaisesRegex(ValueError, 'Symlinks'):
            make_snapshot(self.root, ['alias.md'])

    def test_finalize_exact_bytes_and_refuses_overwrite(self):
        result = finalize(self.root, self.job, 'reviewed.md')
        self.assertEqual(result['sha256'], self.job['candidate']['sha256'])
        self.assertEqual((self.root / 'reviewed.md').read_bytes(), (self.root / 'candidate.md').read_bytes())
        with self.assertRaises(FileExistsError):
            finalize(self.root, self.job, 'reviewed.md')
        self.assertIn('author acceptance', result['meaning'])

    def test_finalize_rejects_candidate_changed_after_review(self):
        self.put('candidate.md', 'A changed ending.\n')
        job = copy.deepcopy(self.job)
        job['candidate'] = self.bind('candidate.md')
        with self.assertRaisesRegex(ValueError, 'current candidate'):
            finalize(self.root, job, 'reviewed.md')
        self.assertFalse((self.root / 'reviewed.md').exists())

    def test_finalize_rejects_source_changed_after_review(self):
        self.put('canon.md', 'New effect.\n')
        with self.assertRaisesRegex(ValueError, 'Source changed'):
            finalize(self.root, self.job, 'reviewed.md')

    def test_finalize_rejects_missing_or_forged_binding(self):
        for key in ('candidate', 'outline', 'approval', 'source_snapshot', 'review'):
            job = copy.deepcopy(self.job)
            job[key]['sha256'] = '0' * 64
            with self.subTest(key=key), self.assertRaises(ValueError):
                finalize(self.root, job, 'reviewed.md')

    def test_finalize_rejects_nonpass_invalid_rounds_and_mode(self):
        for key, value in (('conclusion', 'incomplete'), ('round', 4), ('round', -1),
                           ('round', True), ('round', '0'), ('mode', 'unknown')):
            review = copy.deepcopy(self.review)
            review[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                finalize(self.root, self.with_review(review), 'reviewed.md')

    def test_finalize_rejects_missing_coverage_and_fake_not_applicable(self):
        for key, value in (('coverage', {}), ('coverage', {k: {'status': 'missing', 'evidence': 'x'} for k in COVERAGE}),
                           ('coverage', {k: {'status': 'not-applicable', 'evidence': ''} for k in COVERAGE})):
            review = copy.deepcopy(self.review)
            review[key] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                finalize(self.root, self.with_review(review), 'reviewed.md')

    def test_finalize_rejects_open_required_and_unproved_resolutions(self):
        cases = [
            [{'id': 'Q1', 'severity': 'blocking', 'status': 'open'}],
            [{'id': 'Q1', 'severity': 'required', 'status': 'open'}],
            [{'id': 'Q1', 'severity': 'required', 'status': 'resolved', 'evidence': ''}],
            [{'id': 'Q1', 'severity': 'typo', 'status': 'resolved'}],
            [{'id': 'Q1', 'severity': 'optional', 'status': 'open'}] * 2,
        ]
        for issues in cases:
            review = copy.deepcopy(self.review)
            review['issues'] = issues
            with self.subTest(issues=issues), self.assertRaises(ValueError):
                finalize(self.root, self.with_review(review), 'reviewed.md')

    def test_finalize_accepts_optional_open_and_explained_scope(self):
        review = copy.deepcopy(self.review)
        review['coverage']['narration'] = {'status': 'not-applicable', 'evidence': 'Only factual audit requested; no stable author voice claim.'}
        review['issues'] = [{'id': 'Q1', 'severity': 'optional', 'status': 'open'}]
        review['round'] = 3
        result = finalize(self.root, self.with_review(review), 'reviewed.md')
        self.assertEqual(result['sha256'], self.job['candidate']['sha256'])

    def test_finalize_rejects_pending_approval_even_if_rehashed(self):
        approval = {'decision': 'pending', 'outline_sha256': self.job['outline']['sha256'], 'evidence': 'Waiting.'}
        self.put('approval.json', approval)
        snap = make_snapshot(self.root, ['canon.md', 'outline.md', 'approval.json'])
        self.put('snapshot.json', snap)
        review = copy.deepcopy(self.review)
        review['source_snapshot_sha256'] = self.bind('snapshot.json')['sha256']
        job = self.with_review(review)
        job['source_snapshot'] = self.bind('snapshot.json')
        job['approval'] = self.bind('approval.json')
        with self.assertRaisesRegex(ValueError, 'Approval is absent'):
            finalize(self.root, job, 'reviewed.md')

    def test_finalize_rejects_snapshot_missing_approval(self):
        self.put('snapshot.json', make_snapshot(self.root, ['canon.md', 'outline.md']))
        job = copy.deepcopy(self.job)
        job['source_snapshot'] = self.bind('snapshot.json')
        with self.assertRaisesRegex(ValueError, 'must be included'):
            finalize(self.root, job, 'reviewed.md')

    def test_finalize_rejects_inputs_as_output(self):
        for output in ('candidate.md', 'canon.md', '../escape.md'):
            with self.subTest(output=output), self.assertRaises(ValueError):
                finalize(self.root, self.job, output)

    def test_duplicate_json_keys_and_output_preservation(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
            parse_json('{"x": 1, "x": 2}')
        p = self.root / 'sentinel.md'
        write_new(p, b'keep')
        with self.assertRaises(FileExistsError):
            write_new(p, b'replace')
        self.assertEqual(p.read_bytes(), b'keep')


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='fiction-package-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'source'
        skill = self.root / 'skills' / 'test-skill'
        skill.mkdir(parents=True)
        (skill / 'SKILL.md').write_text('---\nname: test-skill\ndescription: Check a test fixture when explicitly requested.\n---\n\n# Test\n', encoding='utf-8')
        self.manifest = {'schema': 1, 'files': ['skills/test-skill/SKILL.md', 'release-allowlist.json']}
        self.save_manifest()

    def save_manifest(self):
        (self.root / 'release-allowlist.json').write_bytes(json_bytes(self.manifest))

    def test_build_exact_allowlist_and_hashes(self):
        output = self.base / 'release'
        report = self.base / 'hashes.json'
        result = build(self.root, output, report)
        actual = {p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()}
        self.assertEqual(actual, set(self.manifest['files']))
        self.assertEqual(result['file_count'], 2)
        for item in result['files']:
            self.assertEqual(item['sha256'], digest((output / item['path']).read_bytes()))
        self.assertTrue(report.is_file())

    def test_release_refuses_private_extra_file(self):
        (self.root / 'private-draft.md').write_text('Synthetic private material.', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Unlisted files'):
            build(self.root, self.base / 'release')
        self.assertFalse((self.base / 'release').exists())

    def test_release_refuses_existing_or_nested_output(self):
        for output in (self.root, self.root / 'dist'):
            with self.subTest(output=output), self.assertRaises(ValueError):
                build(self.root, output)
        existing = self.base / 'existing'
        existing.mkdir()
        (existing / 'keep.txt').write_text('keep', encoding='utf-8')
        with self.assertRaises(ValueError):
            build(self.root, existing)
        self.assertEqual((existing / 'keep.txt').read_text(), 'keep')

    def test_release_rejects_missing_duplicate_and_escape_allowlist(self):
        original = copy.deepcopy(self.manifest)
        for extra in ('missing.md', '../outside.md', '.env', original['files'][0]):
            self.manifest = copy.deepcopy(original)
            self.manifest['files'].append(extra)
            self.save_manifest()
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                validate_repo(self.root)

    def test_skill_copy_is_self_contained(self):
        with tempfile.TemporaryDirectory(prefix='fiction-installed-') as folder:
            for skill in (REPO / 'skills').iterdir():
                if skill.is_dir():
                    dest = Path(folder) / skill.name
                    shutil.copytree(skill, dest)
                    self.assertTrue(validate_skill(dest))

    def test_broken_or_external_skill_reference_is_rejected(self):
        skill = self.root / 'skills' / 'test-skill'
        p = skill / 'SKILL.md'
        original = p.read_text(encoding='utf-8')
        for link in ('references/missing.md', '../../release-allowlist.json'):
            p.write_text(original + '\n[ref](' + link + ')\n', encoding='utf-8')
            with self.subTest(link=link), self.assertRaises(ValueError):
                validate_skill(skill)

    def test_sensitive_patterns_detect_synthetic_credentials(self):
        samples = ['gh' + 'p_' + 'A' * 30, 'sk' + '-' + 'a' * 30,
                   'person' + '@' + 'example.test', 'Z' + ':' + '\\' + 'private' + '\\' + 'file.md',
                   '-----BEGIN ' + 'PRIVATE KEY-----']
        for sample in samples:
            with self.subTest(sample=sample):
                self.assertTrue(scan_text(sample))
        self.assertEqual(scan_text('Use relative paths and your own private workspace.'), [])

    def test_cold_start_release_without_site_packages(self):
        output = self.base / 'clean-release'
        build(REPO, output)
        elsewhere = self.base / 'empty-working-directory'
        elsewhere.mkdir()
        for script, args in (('validate_repo.py', []), ('fiction_tools.py', ['demo'])):
            result = subprocess.run([sys.executable, '-S', str(output / 'scripts' / script), *args],
                                    cwd=elsewhere, text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(result.stdout.strip())


if __name__ == '__main__':
    unittest.main()

"""File integrity helpers; no model calls or semantic approval decisions."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tempfile

COVERAGE = ('canon', 'continuity', 'motivation', 'dialogue', 'knowledge',
            'narration', 'outline', 'records')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_path(root, relative):
    if not isinstance(relative, str) or not relative or '\\' in relative or ':' in relative:
        raise ValueError('Expected a portable relative path')
    parts = PurePosixPath(relative)
    if parts.is_absolute() or '..' in parts.parts or relative != parts.as_posix() or parts.as_posix() == '.':
        raise ValueError('Path escapes or is not canonical')
    root = Path(root).resolve()
    path = root.joinpath(*parts.parts)
    for segment in (path, *path.parents):
        if segment == root:
            break
        if segment.is_symlink():
            raise ValueError('Symlinks are not allowed')
    if not path.resolve().is_relative_to(root):
        raise ValueError('Path escapes root')
    return path


def parse_json(data):
    def unique(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise ValueError('Duplicate JSON key')
            result[k] = v
        return result
    return json.loads(data, object_pairs_hook=unique)


def read_json(path):
    return parse_json(Path(path).read_bytes())


def write_new(path, data):
    path = Path(path)
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError('Output symlinks are not allowed')
    with path.open('xb') as stream:
        stream.write(data)


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def make_snapshot(root, paths):
    if not paths or len(set(paths)) != len(paths):
        raise ValueError('Snapshot requires unique explicit input files')
    return {'schema': 1, 'files': [
        {'path': rel, 'sha256': digest(safe_path(root, rel).read_bytes())}
        for rel in sorted(paths)]}


def valid_hash(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def verify_snapshot(root, snapshot):
    if not isinstance(snapshot, dict) or snapshot.get('schema') != 1 or not isinstance(snapshot.get('files'), list) or not snapshot['files']:
        raise ValueError('Invalid or empty snapshot')
    seen = set()
    for item in snapshot['files']:
        if not isinstance(item, dict) or set(item) != {'path', 'sha256'} or not valid_hash(item['sha256']):
            raise ValueError('Invalid snapshot entry')
        rel = item['path']
        if rel in seen:
            raise ValueError('Duplicate snapshot path')
        seen.add(rel)
        if digest(safe_path(root, rel).read_bytes()) != item['sha256']:
            raise ValueError('Source changed: ' + rel)
    return seen


def finalize(root, job, output):
    if not isinstance(job, dict) or job.get('schema') != 1:
        raise ValueError('Invalid job schema')
    blobs = {}
    paths = []
    for key in ('candidate', 'outline', 'approval', 'source_snapshot', 'review'):
        entry = job.get(key)
        if not isinstance(entry, dict) or set(entry) != {'path', 'sha256'} or not valid_hash(entry['sha256']):
            raise ValueError('Missing file binding: ' + key)
        paths.append(entry['path'])
        blobs[key] = safe_path(root, entry['path']).read_bytes()
        if not blobs[key].strip() or digest(blobs[key]) != entry['sha256']:
            raise ValueError('Empty or stale file binding: ' + key)
    if len(set(paths)) != len(paths):
        raise ValueError('Job roles must refer to distinct files')
    snapshot = parse_json(blobs['source_snapshot'])
    inputs = verify_snapshot(root, snapshot)
    if not {job['outline']['path'], job['approval']['path']}.issubset(inputs):
        raise ValueError('Outline and approval must be included in source snapshot')
    if {job['candidate']['path'], job['review']['path'], job['source_snapshot']['path']} & inputs:
        raise ValueError('Snapshot must contain inputs, not candidate or review outputs')
    approval = parse_json(blobs['approval'])
    if not isinstance(approval, dict) or approval.get('outline_sha256') != job['outline']['sha256'] or approval.get('decision') != 'approved' or not isinstance(approval.get('evidence'), str) or not approval['evidence'].strip():
        raise ValueError('Approval is absent, unbound or lacks actual evidence')
    review = parse_json(blobs['review'])
    if not isinstance(review, dict):
        raise ValueError('Invalid review')
    for key in ('candidate', 'outline', 'source_snapshot'):
        if review.get(key + '_sha256') != job[key]['sha256']:
            raise ValueError('Review does not bind current ' + key)
    if review.get('conclusion') != 'pass' or type(review.get('round')) is not int or not 0 <= review['round'] <= 3:
        raise ValueError('Review not passed or default retry limit exceeded')
    if review.get('mode') not in ('single-reviewer', 'independent'):
        raise ValueError('Review mode must be disclosed')
    coverage = review.get('coverage')
    if not isinstance(coverage, dict) or set(coverage) != set(COVERAGE):
        raise ValueError('Incomplete coverage')
    for item in coverage.values():
        if not isinstance(item, dict) or item.get('status') not in ('checked', 'not-applicable') or not isinstance(item.get('evidence'), str) or not item['evidence'].strip():
            raise ValueError('Coverage missing status or evidence/reason')
    issues = review.get('issues')
    if not isinstance(issues, list):
        raise ValueError('Issues must be an explicit list')
    ids = set()
    for issue in issues:
        if not isinstance(issue, dict) or not isinstance(issue.get('id'), str) or not issue['id'].strip() or issue['id'] in ids:
            raise ValueError('Missing or duplicate issue ID')
        ids.add(issue['id'])
        if issue.get('severity') not in ('blocking', 'required', 'optional') or issue.get('status') not in ('open', 'resolved'):
            raise ValueError('Invalid issue severity or status')
        if issue['severity'] != 'optional' and issue['status'] != 'resolved':
            raise ValueError('Unresolved blocking/required issue')
        if issue['status'] == 'resolved' and (not isinstance(issue.get('evidence'), str) or not issue['evidence'].strip()):
            raise ValueError('Resolution lacks evidence')
    out = safe_path(root, output)
    if output in paths or output in inputs:
        raise ValueError('Output must be a new file outside all inputs')
    write_new(out, blobs['candidate'])
    if out.read_bytes() != blobs['candidate']:
        raise ValueError('Copy verification failed')
    return {'output': output, 'sha256': digest(blobs['candidate']),
            'meaning': 'reviewed copy only; author acceptance and publication are separate'}


def demo():
    """Mechanical demo with synthetic declarations, never a model review."""
    with tempfile.TemporaryDirectory(prefix='fiction-demo-') as folder:
        root = Path(folder)
        values = {'canon.md': 'Demo: a bell rings once.\n',
                  'outline.md': 'Ring once and stop.\n',
                  'candidate.md': '# Bell\n\nThe bell rang once.\n'}
        for rel, content in values.items():
            (root / rel).write_text(content, encoding='utf-8')
        bind = lambda rel: {'path': rel, 'sha256': digest((root / rel).read_bytes())}
        approval = {'decision': 'approved', 'outline_sha256': bind('outline.md')['sha256'],
                    'evidence': 'Synthetic demonstration approval, not real author consent.'}
        write_new(root / 'approval.json', json_bytes(approval))
        snap = make_snapshot(root, ['canon.md', 'outline.md', 'approval.json'])
        write_new(root / 'snapshot.json', json_bytes(snap))
        review = {'candidate_sha256': bind('candidate.md')['sha256'],
                  'outline_sha256': bind('outline.md')['sha256'],
                  'source_snapshot_sha256': bind('snapshot.json')['sha256'],
                  'round': 0, 'mode': 'single-reviewer', 'conclusion': 'pass',
                  'coverage': {k: {'status': 'checked', 'evidence': 'Synthetic fixture only.'} for k in COVERAGE},
                  'issues': []}
        write_new(root / 'review.json', json_bytes(review))
        job = {'schema': 1, **{k: bind(rel) for k, rel in {
            'candidate': 'candidate.md', 'outline': 'outline.md', 'approval': 'approval.json',
            'source_snapshot': 'snapshot.json', 'review': 'review.json'}.items()}}
        result = finalize(root, job, 'reviewed.md')
        return {'demo': 'mechanical only', 'identical_copy': result['sha256'] == bind('candidate.md')['sha256'], 'temporary_workspace_removed_on_return': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    snap = commands.add_parser('snapshot')
    snap.add_argument('--root', required=True)
    snap.add_argument('--output', required=True)
    snap.add_argument('paths', nargs='+')
    verify = commands.add_parser('verify')
    verify.add_argument('--root', required=True)
    verify.add_argument('--snapshot', required=True)
    final = commands.add_parser('finalize')
    final.add_argument('--root', required=True)
    final.add_argument('--job', required=True)
    final.add_argument('--output', required=True, help='New path relative to root')
    commands.add_parser('demo')
    args = parser.parse_args()
    try:
        if args.command == 'snapshot':
            snapshot = make_snapshot(args.root, args.paths)
            target = Path(args.output).resolve()
            if target in {safe_path(args.root, rel).resolve() for rel in args.paths}:
                raise ValueError('Snapshot output overlaps source')
            write_new(args.output, json_bytes(snapshot))
            result = {'snapshot_files': len(snapshot['files'])}
        elif args.command == 'verify':
            result = {'verified_files': len(verify_snapshot(args.root, read_json(args.snapshot)))}
        elif args.command == 'finalize':
            result = finalize(args.root, read_json(args.job), args.output)
        else:
            result = demo()
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, 'error: ' + str(error) + '\n')


if __name__ == '__main__':
    main()

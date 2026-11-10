"""Validate this repository's deliberately minimal Skill and release contracts."""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import unquote
from fiction_tools import read_json, safe_path

SENSITIVE = {
    'absolute machine path': r'\b[A-Za-z]:[\\/]|/(?:Users|home)/[A-Za-z0-9_.-]+/',
    'email address': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
    'GitHub token': r'\bgh[pousr]_[A-Za-z0-9]{20,}\b|github_pat_[A-Za-z0-9_]{20,}',
    'API secret': r'\bsk-[A-Za-z0-9_-]{20,}\b',
    'private key': r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    'credential assignment': r'(?i)(?:api[_-]?key|access[_-]?token|password)\s*[=:]\s*[\x22\x27]?[A-Za-z0-9_./+-]{12,}',
}


def listed_files(root):
    manifest = read_json(safe_path(root, 'release-allowlist.json'))
    if not isinstance(manifest, dict) or manifest.get('schema') != 1 or not isinstance(manifest.get('files'), list) or not manifest['files']:
        raise ValueError('Invalid allowlist')
    paths = manifest['files']
    if not all(isinstance(x, str) for x in paths) or len(set(paths)) != len(paths):
        raise ValueError('Duplicate or non-string allowlist entry')
    if 'release-allowlist.json' not in paths:
        raise ValueError('Manifest must be explicitly allowed')
    for rel in paths:
        if any(part.startswith('.') for part in Path(rel).parts) and rel != '.gitignore':
            raise ValueError('Hidden release path refused: ' + rel)
        path = safe_path(root, rel)
        if not path.is_file():
            raise ValueError('Missing allowed file: ' + rel)
    return paths


def scan_text(value):
    return [kind for kind, expression in SENSITIVE.items() if re.search(expression, value)]


def validate_skill(path):
    skill = Path(path)
    value = (skill / 'SKILL.md').read_text(encoding='utf-8')
    match = re.match(r'\A---\n(.*?)\n---\n', value, re.S)
    if not match:
        raise ValueError('Invalid frontmatter: ' + skill.name)
    fields = {}
    for line in match[1].splitlines():
        item = re.fullmatch(r'(name|description): ([^\n]+)', line)
        if not item or item[1] in fields:
            raise ValueError('Only unique plain name/description scalars are supported here')
        fields[item[1]] = item[2]
    name = fields.get('name', '')
    description = fields.get('description', '')
    if name != skill.name or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name) or not 1 <= len(name) <= 64:
        raise ValueError('Invalid or mismatched skill name')
    if not 1 <= len(description) <= 1024 or any(c in description for c in '<>') or ': ' in description or description.startswith(('[', '{', '!', '&', '*', '|', '>')):
        raise ValueError('Invalid plain description')
    if '[TODO:' in value:
        raise ValueError('Unfinished scaffold')
    for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', value):
        if '://' not in link:
            target = (skill / unquote(link.split('#')[0])).resolve()
            if not target.is_relative_to(skill.resolve()) or not target.is_file():
                raise ValueError('Skill reference is not self-contained: ' + link)
    return True


def validate_repo(root):
    root = Path(root).resolve()
    paths = listed_files(root)
    allowed = set(paths)
    extras = []
    import os
    for base, dirs, files in os.walk(root, followlinks=False):
        for name in list(dirs):
            p = Path(base) / name
            if p.is_symlink():
                raise ValueError('Symlink directory refused')
            if name in ('.git', '__pycache__'):
                dirs.remove(name)
        for name in files:
            p = Path(base) / name
            rel = p.relative_to(root).as_posix()
            if rel not in allowed:
                extras.append(rel)
    if extras:
        raise ValueError('Unlisted files present: ' + ', '.join(sorted(extras)))
    skills = 0
    for rel in paths:
        path = safe_path(root, rel)
        text = path.read_text(encoding='utf-8')
        hits = scan_text(text)
        if hits:
            raise ValueError('Sensitive pattern in ' + rel + ': ' + ', '.join(hits))
        if rel.endswith('/SKILL.md'):
            validate_skill(path.parent)
            skills += 1
        if path.suffix == '.md':
            for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
                if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', link):
                    continue
                local = unquote(link.split('#')[0])
                if not local:
                    continue
                target = (path.parent / local).resolve()
                if not target.is_relative_to(root) or not target.is_file() or target.relative_to(root).as_posix() not in allowed:
                    raise ValueError('Broken or unlisted link in ' + rel + ': ' + link)
        if path.suffix == '.json':
            read_json(path)
        if path.suffix == '.py':
            compile(text, rel, 'exec')
    if not skills:
        raise ValueError('No skills found')
    return {'allowed_files': len(paths), 'skills': skills, 'links': 'checked',
            'sensitive_pattern_scan': 'no matches; manual review still required'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        print(json.dumps(validate_repo(args.root), ensure_ascii=False))
    except (ValueError, OSError, TypeError, KeyError) as error:
        parser.exit(1, 'error: ' + str(error) + '\n')


if __name__ == '__main__':
    main()

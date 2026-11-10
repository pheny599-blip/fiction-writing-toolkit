"""Build a fresh directory from reviewed, explicit file names; never publish."""
import argparse
from pathlib import Path
import shutil
import tempfile
from fiction_tools import digest, json_bytes, safe_path, write_new
from validate_repo import listed_files, validate_repo


def build(root, output, hash_report=None):
    root = Path(root).resolve()
    output = Path(output).absolute()
    if output.is_symlink() or any(p.is_symlink() for p in output.parents):
        raise ValueError('Output symlink refused')
    if output.exists() or output.resolve().is_relative_to(root) or root.is_relative_to(output.resolve()):
        raise ValueError('Output must be a new directory outside the source root')
    if not output.parent.is_dir():
        raise ValueError('Output parent must exist')
    if hash_report is not None:
        report = Path(hash_report).absolute()
        if report.exists() or report.is_symlink() or any(p.is_symlink() for p in report.parents):
            raise ValueError('Hash report must be a new regular file')
        if report.resolve().is_relative_to(root) or report.resolve().is_relative_to(output):
            raise ValueError('Keep the approval hash report outside source and release trees')
    validate_repo(root)
    paths = listed_files(root)
    stage = Path(tempfile.mkdtemp(prefix='fiction-release-', dir=output.parent))
    try:
        hashes = []
        for rel in paths:
            data = safe_path(root, rel).read_bytes()
            dest = stage / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            write_new(dest, data)
            hashes.append({'path': rel, 'sha256': digest(data), 'bytes': len(data)})
        validate_repo(stage)
        # Reservation prevents overwriting an output created concurrently.
        output.mkdir()
        try:
            for child in stage.iterdir():
                shutil.move(str(child), output / child.name)
        except BaseException:
            shutil.rmtree(output)
            raise
        result = {'schema': 1, 'files': hashes, 'file_count': len(hashes)}
        if hash_report is not None:
            write_new(hash_report, json_bytes(result))
        return result
    finally:
        shutil.rmtree(stage)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--hash-report', type=Path)
    args = parser.parse_args()
    try:
        result = build(args.root, args.output, args.hash_report)
        print('Built ' + str(result['file_count']) + ' allowlisted files; no Git or publishing action performed.')
    except (ValueError, OSError, TypeError, KeyError) as error:
        parser.exit(1, 'error: ' + str(error) + '\n')


if __name__ == '__main__':
    main()

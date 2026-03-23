from __future__ import annotations

from pathlib import Path
import argparse
import os
import zipfile


def iter_files(path: Path):
    if path.is_file():
        yield path, Path(path.name)
        return

    for child in sorted(path.rglob("*")):
        if child.is_file():
            yield child, child.relative_to(path.parent)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--root-name", required=True)
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for raw_path in args.paths:
            path = Path(raw_path).resolve()
            if not path.exists():
                raise FileNotFoundError(path)

            for file_path, rel_path in iter_files(path):
                archive_path = Path(args.root_name) / rel_path
                info = zipfile.ZipInfo.from_file(file_path, arcname=str(archive_path))
                st_mode = os.stat(file_path).st_mode
                info.external_attr = (st_mode & 0xFFFF) << 16
                with file_path.open("rb") as source, archive.open(info, "w") as target:
                    target.write(source.read())

    print(f"Created archive: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

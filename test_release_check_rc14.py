#!/usr/bin/env python3
"""Path discovery contracts for the RC14 release receipt."""
from pathlib import Path
import tempfile

from release_check_rc14 import resolve_v4_root


def catalog_at(root: Path) -> Path:
    path = root / "04_SEARCH" / "325ix_multimodal.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    return path


def main():
    with tempfile.TemporaryDirectory(prefix="ix-rc14-paths-") as temp:
        repo = Path(temp) / "checkout"
        repo.mkdir()

        nested = repo / "google_drive" / "14_MULTIMODAL_MEDIA_AND_GRAPH"
        catalog_at(nested)
        assert resolve_v4_root(repo) == nested.resolve()

        separate = Path(temp) / "synced-v4"
        catalog_at(separate)
        assert resolve_v4_root(repo, separate) == separate.resolve()
        assert resolve_v4_root(repo, separate / "missing") is None

        legacy = Path(temp) / "legacy-checkout"
        legacy.mkdir()
        catalog_at(legacy)
        assert resolve_v4_root(legacy) == legacy.resolve()

        empty = Path(temp) / "empty-checkout"
        empty.mkdir()
        assert resolve_v4_root(empty) is None

    print("PASS: RC14 release check discovers nested, explicit, and legacy V4 catalog paths")


if __name__ == "__main__":
    main()

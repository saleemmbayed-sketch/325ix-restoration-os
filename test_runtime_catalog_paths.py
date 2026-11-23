#!/usr/bin/env python3
"""Runtime path contract for read-only V4 data and legacy catalog fallback."""
from pathlib import Path
import tempfile

from app import resolve_runtime_catalog_paths


def touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'fixture; path resolver does not open or mutate source data')
    return path


def main():
    with tempfile.TemporaryDirectory() as temp:
        temp = Path(temp)
        app_root = temp / 'workbench'
        app_root.mkdir()
        home = temp / 'home'
        v4_root = app_root / '14_MULTIMODAL_MEDIA_AND_GRAPH'
        multimodal = touch(v4_root / '04_SEARCH' / '325ix_multimodal.sqlite3')
        touch(v4_root / '03_MANIFESTS' / 'image_assets.jsonl')

        # A local V4 copy is sufficient; no duplicate legacy database is needed.
        source, mm, assets = resolve_runtime_catalog_paths(app_root, v4_root_arg=v4_root, home=home)
        assert source == multimodal and mm == multimodal and assets == v4_root
        assert not (app_root / 'data').exists()

        # An explicit DB path is also accepted without a --v4-root argument.
        source, mm, assets = resolve_runtime_catalog_paths(
            app_root, multimodal_arg=multimodal, home=home)
        assert source == multimodal and mm == multimodal and assets == v4_root

        # Preserve legacy-only startup behavior in a tree without V4 catalog data.
        legacy_root = temp / 'legacy-workbench'
        legacy = touch(legacy_root / 'data' / '325ix_assemblies.sqlite3')
        source, mm, assets = resolve_runtime_catalog_paths(legacy_root, home=home)
        assert source == legacy and mm is None and assets is None

        # Prefer V4 when both read-only catalog formats are present.
        source, mm, _ = resolve_runtime_catalog_paths(
            app_root, catalog_arg=legacy, v4_root_arg=v4_root, home=home)
        assert source == multimodal and mm == multimodal

        for kwargs in (
            {'catalog_arg': temp / 'missing.sqlite3', 'v4_root_arg': v4_root},
            {'multimodal_arg': temp / 'missing-multimodal.sqlite3', 'catalog_arg': legacy},
            {'v4_root_arg': temp / 'missing-v4-folder'},
        ):
            try:
                resolve_runtime_catalog_paths(app_root, home=home, **kwargs)
            except FileNotFoundError:
                pass
            else:
                raise AssertionError('Missing explicit runtime input was silently accepted: '+repr(kwargs))

    with tempfile.TemporaryDirectory() as temp:
        try:
            resolve_runtime_catalog_paths(Path(temp) / 'empty-workbench', home=Path(temp) / 'home')
        except FileNotFoundError as exc:
            assert '--multimodal-db' in str(exc) and '--catalog' in str(exc)
        else:
            raise AssertionError('Missing catalog inputs should fail with a usage hint')

    print('PASS: V4 folder can be the read-only catalog source; legacy fallback and explicit-path errors are covered')


if __name__ == '__main__':
    main()

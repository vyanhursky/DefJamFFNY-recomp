"""Setup must carry and import lazy fighter adapters without a development tree."""
import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('setup_fighter_assets',ROOT/'scripts/check-setup-assets.py')
assets=importlib.util.module_from_spec(spec);spec.loader.exec_module(assets)


def test_setup_manifest_requires_every_fighter_adapter():
    files={'source/'+path.relative_to(ROOT).as_posix():'' for path in (ROOT/'setup').glob('fighter_*.py')}
    assets.verify_fighter_sources({'files':files})
    del files['source/setup/fighter_film_proof.py']
    with pytest.raises(ValueError,match='fighter_film_proof'):
        assets.verify_fighter_sources({'files':files})


def test_isolated_import_probe_detects_a_missing_transitive_adapter(tmp_path):
    source=tmp_path/'source/setup';source.mkdir(parents=True)
    (source/'fighter_a.py').write_text('import fighter_b\n',encoding='utf-8')
    with pytest.raises(subprocess.CalledProcessError):assets.fighter_import_probe(tmp_path,sys.executable)
    (source/'fighter_b.py').write_text('VALUE=1\n',encoding='utf-8')
    assets.fighter_import_probe(tmp_path,sys.executable)

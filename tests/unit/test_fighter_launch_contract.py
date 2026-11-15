"""Every setting the compiler puts in the fighter manifest has a native reader."""
import re
import sys
import pytest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'setup'))
from fighter_packages import runtime_environment


def native_names():
    """RECOMP_FIGHTER_* names the game reads (literal, or a literal stem plus _SHA256)."""
    text=''.join(path.read_text(encoding='utf-8') for folder in ('src/patches','src/hooks')
                 for path in (ROOT/folder).glob('*.c*'))
    return set(re.findall(r'"(RECOMP_FIGHTER_[A-Z0-9_]+)"',text))


@pytest.mark.parametrize('ui_pack', [None, 'fighter-ui-'+'c'*24])
def test_manifest_settings_from_the_caf_producer_are_all_read_by_the_game(tmp_path, ui_pack):
    report={'binding_mode':'participant-window','caf_fighters':{'example/fighter':{}},
            'caf_sha256':'a'*64,'caf_extras_sha256':'b'*64,'caf_faces_sha256':'c'*64,
            'appearance_files':{'assets/v2ip.viv':'d'*64,'assets/entity.xml':'e'*64,'assets/nis.viv':'f'*64}}
    environment=runtime_environment(tmp_path,report,tmp_path/'screens.viv',ui_pack=tmp_path/ui_pack if ui_pack else None)
    environment.update({'RECOMP_FIGHTER_STATE':'','RECOMP_FIGHTER_IDENTITIES':''})  # fighter_manifest.write adds these
    names=native_names()
    unread={key for key in environment if key not in names and not (key.endswith('_SHA256') and key[:-7] in names)}
    assert not unread,'The game never reads these manifest settings: '+', '.join(sorted(unread))


def test_normal_play_reads_fighter_settings_only_through_the_manifest_lookup():
    """A stale RECOMP_FIGHTER_* in a shell or launch option must not reach a fighter module."""
    for path in sorted((ROOT/'src/patches').glob('fighter_*.c')):
        if path.name=='fighter_config.c':continue
        text=path.read_text(encoding='utf-8')
        assert not re.search(r'getenv\(\s*"RECOMP_FIGHTER_',text),path.name

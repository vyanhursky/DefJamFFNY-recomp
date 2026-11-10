"""The managed-launch consumer must admit the actual CAF producer's settings."""
import re
import sys
import pytest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'setup'))
from fighter_packages import runtime_environment


@pytest.mark.parametrize('ui_pack', [None, 'fighter-ui-'+'c'*24])
def test_managed_launcher_admits_caf_texture_and_finisher_projection(tmp_path, ui_pack):
    report={'binding_mode':'participant-window','caf_fighters':{'example/fighter':{}},
            'caf_sha256':'a'*64,'caf_extras_sha256':'b'*64,'caf_faces_sha256':'c'*64}
    environment=runtime_environment(tmp_path,report,tmp_path/'screens.viv',ui_pack=tmp_path/ui_pack if ui_pack else None)
    source=(ROOT/'src/hooks/pc_mods.cpp').read_text()
    body=re.search(r'static const std::set<std::string> allowed = \{(.*?)\};',source,re.S).group(1)
    admitted=set(re.findall(r'"([A-Z0-9_]+)"',body))
    unsupported={key for key in environment if key.removeprefix('RECOMP_FIGHTER_') not in admitted}
    assert not unsupported,'Managed launcher rejects compiler settings: '+', '.join(sorted(unsupported))

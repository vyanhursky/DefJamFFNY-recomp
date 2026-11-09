"""Component export rejects mutable/ambiguous requests before asset admission."""
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'setup'))

import pytest
from fighter_assets import AssetError
from fighter_pair_export import export_pair


def request(tmp_path,**change):
    path=tmp_path/'model.o';path.write_bytes(b'invented data')
    spec={'path':str(path),'sha256':'0'*64}
    value={'format':'fighter-pair-export-request-1','template_choice':0,'model':spec,'face':spec,
           'subject':{'data':spec,'links':spec},'counterpart':{'data':spec,'links':spec}}
    value.update(change)
    output=tmp_path/'request.json';output.write_text(json.dumps(value),encoding='utf-8')
    return output


@pytest.mark.parametrize('change',[{'template_choice':True},{'template_choice':82},
                                  {'format':'native-bank'},{'command':'execute'}, {'model':{'path':'model.o'}}])
def test_ambiguous_or_unsealed_request_rejected(tmp_path,change):
    with pytest.raises(AssetError):
        export_pair(tmp_path,request(tmp_path,**change),{})


def test_changed_source_fails_before_native_or_original_access(tmp_path):
    with pytest.raises(AssetError,match='input changed'):
        export_pair(tmp_path,request(tmp_path),{})


def test_duplicate_request_members_and_oversized_request_rejected(tmp_path):
    path=request(tmp_path)
    path.write_text('{"format":"one","format":"two"}',encoding='utf-8')
    with pytest.raises(AssetError,match='Duplicate'):
        export_pair(tmp_path,path,{})
    path.write_bytes(b' '*65537)
    with pytest.raises(AssetError,match='exceeds budget'):
        export_pair(tmp_path,path,{})

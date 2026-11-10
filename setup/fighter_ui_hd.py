"""Content-addressed, verified texture-v1 overlays for owned fighter UI PNGs."""
import hashlib
import re
import tempfile
from pathlib import Path

from mods import ordinary_path,check,durable_rename,validate_textures
PREFIX='fighter-ui-hd/'


def compile_hd(portraits):
    images={}
    for portrait in portraits.values():
        for identity,png in getattr(portrait,'hd_images',{}).items():
            check(identity not in images or images[identity]==png,'Conflicting fighter HD UI art for one native texture')
            images[identity]=png
    if not images:return {},{}
    files={PREFIX+'textures/'+key+'.png':value for key,value in sorted(images.items())}
    text='[pack]\nschema = 1\nname = Fighter UI art\npng_mips = opacity\n\n[textures]\n'+''.join(key+' = textures/'+key+'.png\n' for key in sorted(images))
    files[PREFIX+'manifest.ini']=text.encode()
    return files,{name:hashlib.sha256(data).hexdigest() for name,data in files.items()}


def validate_hd_files(report,resources):
    hashes=report.get('portrait_hd_files',{})
    check(type(hashes) is dict and len(hashes)<=4097,'Invalid fighter HD UI file set')
    if not hashes:return set()
    check(PREFIX+'manifest.ini' in hashes,'Fighter HD UI needs its manifest')
    for relative,digest in hashes.items():
        check(relative==PREFIX+'manifest.ini' or re.fullmatch(re.escape(PREFIX)+r'textures/[0-9a-f]{64}\.png',relative),'Invalid fighter HD UI cache path')
        check(relative in resources and hashlib.sha256(resources[relative]).hexdigest()==digest,'Fighter HD UI cache receipt differs')
    return set(hashes)


def stage(cache,report,mods):
    hashes=report.get('portrait_hd_files',{})
    if not hashes:return None
    from fighter_registry import fingerprint
    mods=ordinary_path(mods);mods.mkdir(parents=True,exist_ok=True)
    name='fighter-ui-'+fingerprint(hashes)[:24];destination=ordinary_path(mods/name)
    payload={}
    for relative,digest in hashes.items():
        path=ordinary_path(Path(cache)/relative)
        raw=path.read_bytes()
        check(hashlib.sha256(raw).hexdigest()==digest,'Compiled HD UI changed before activation')
        payload[relative.removeprefix(PREFIX)]=raw
    def verify(folder):
        actual={p.relative_to(folder).as_posix() for p in folder.rglob('*') if ordinary_path(p).is_file()}
        check(actual==set(payload),'Generated HD UI folder has unexpected files')
        check(all((folder/n).read_bytes()==raw for n,raw in payload.items()),'Generated HD UI folder changed')
        validate_textures(folder)
    if destination.exists():verify(destination);return destination
    with tempfile.TemporaryDirectory(prefix='.fighter-ui-stage-',dir=mods) as temporary:
        folder=Path(temporary)/name;folder.mkdir()
        for relative,raw in payload.items():
            path=folder/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        verify(folder);durable_rename(folder,destination)
    verify(destination);return destination

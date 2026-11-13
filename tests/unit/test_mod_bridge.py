"""Native process/argv/OS lock checks without renderer or game data."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import pytest

ROOT=Path(__file__).resolve().parents[2]


def test_helper_status_with_isolated_python(tmp_path):
    # -I reproduces embedded Windows Python omitting the script directory.
    data=tmp_path/'isolated data'
    result=subprocess.run([sys.executable,'-I',str(ROOT/'setup/mods.py'),'status',
                           '--data-dir',str(data),'--runtime','0.10.8'],
                          cwd=tmp_path,capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stdout+result.stderr
    assert (data/'mod-manager/view.ini').is_file()


DRIVER=r'''
#include "pc_mods.h"
#include "pc_ui_actions.h"
#include "fighter_config.h"
#include <iostream>
#include <thread>
#include <chrono>
#include <cstdlib>
extern "C" int pc_settings_save_checked(void) { std::abort(); }
std::string data;
namespace pcui { std::string folder_path(Folder which) { return data; } }
int main(int argc,char **argv) {
 data=argv[1];
 if(std::string(argv[2])=="fighter" || std::string(argv[2])=="fighter-ui") {
   if(!pc_fighters_prepare("")) {std::cerr<<pc_fighters_error()<<std::endl;return 5;}
   std::cout<<defjam_fighter_managed()<<std::endl;
   if(std::string(argv[2])=="fighter-ui") {
     std::cout<<(getenv("RECOMP_TEXTURE_ROOT")?getenv("RECOMP_TEXTURE_ROOT"):"")<<std::endl;
     std::cout<<(getenv("RECOMP_TEXTURE_PACKS")?getenv("RECOMP_TEXTURE_PACKS"):"")<<std::endl;
   }
   for(int i=3;i<argc;i++) {const char *value=defjam_fighter_env(argv[i]);std::cout<<argv[i]<<"="<<(value?value:"")<<std::endl;}
   return 0;
 }
 if(std::string(argv[2])=="hold") {
   if(!pc_mods_game_lock())return 2;
   std::cout<<"locked"<<std::endl;
   std::string input;std::getline(std::cin,input);return 0;
 }
 if(!pcui::mod_start(argv[2],argc>3?argv[3]:""))return 3;
 for(int i=0;i<1000 && pcui::mod_busy();i++) {pcui::mod_poll();std::this_thread::sleep_for(std::chrono::milliseconds(10));}
 std::cout<<pcui::mod_status()<<"\n"<<pcui::mod_view().catalogue<<std::endl;
 return pcui::mod_busy()?4:0;
}
'''

@pytest.fixture(scope='module')
def bridge(tmp_path_factory):
    folder=tmp_path_factory.mktemp('mod bridge with spaces')
    source=folder/'main.cpp';source.write_text(DRIVER)
    # This process/lock fixture has no initialized toolkit or settings registry.
    # Status/recovery must not read or write settings; fail loudly if that changes.
    (folder/'recomp_settings.h').write_text(r'''#pragma once
#include <stddef.h>
#include <stdlib.h>
#define RECOMP_SETTING_TEXT_MAX 1024
enum { RECOMP_SETTING_FROM_ENV = 2 };
struct RecompSetting { int source; };
static inline const char *recomp_settings_get_text(const char *, const char *, char *, size_t, const char *) { abort(); }
static inline RecompSetting *recomp_settings_find(const char *, const char *) { abort(); }
static inline int recomp_settings_set_text(const char *, const char *, const char *) { abort(); }
static inline int recomp_settings_set(const char *, const char *, int) { abort(); }
''')
    compiler=shutil.which('cl') or shutil.which('clang++') or shutil.which('g++')
    if not compiler:pytest.skip('C++ compiler required')
    exe=folder/('bridge.exe' if os.name=='nt' else 'bridge')
    if Path(compiler).stem.lower()=='cl':
        command=[compiler,'/nologo','/std:c++17','/EHsc','/I'+str(folder),'/I'+str(ROOT/'src/hooks'),'/I'+str(ROOT/'src/patches'),
                 '/I'+str(ROOT/'src'),'/DDEFJAM_MOD_SOURCE_DIR="'+str(ROOT)+'"',str(source),str(ROOT/'src/hooks/pc_mods.cpp'),
                 str(ROOT/'src/patches/fighter_config.c'),'/Fe:'+str(exe)]
    else:
        command=[compiler,'-std=c++17','-pthread','-I'+str(folder),'-I'+str(ROOT/'src/hooks'),'-I'+str(ROOT/'src/patches'),
                 '-I'+str(ROOT/'src'),'-DDEFJAM_MOD_SOURCE_DIR="'+str(ROOT)+'"',str(source),str(ROOT/'src/hooks/pc_mods.cpp'),
                 str(ROOT/'src/patches/fighter_config.c'),'-o',str(exe)]  # C++ here; the header has extern "C"
    result=subprocess.run(command,cwd=folder,capture_output=True,text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


def test_async_status_and_space_paths(bridge,tmp_path):
    data=tmp_path/'data with spaces'
    env={**os.environ,'DEFJAM_MOD_PYTHON':sys.executable}
    # Developer override is deliberately unavailable for broken installed Python.
    env.pop('DEFJAM_INSTALL_DIR',None)
    result=subprocess.run([str(bridge),str(data),'status'],env=env,capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'inventory refreshed' in result.stdout
    assert (data/'mod-manager/view.ini').exists()


def test_helper_preserves_verified_payload_after_importing_modules(bridge, tmp_path):
    # Real GUI helpers run from the inspected app payload. Importing a module
    # must not add bytecode that makes the next Repair reject its inventory.
    sys.path.insert(0, str(ROOT / 'setup'))
    try:
        import engine
    finally:
        sys.path.pop(0)
    payload = tmp_path / 'sealed payload'
    source = payload / 'source'
    setup = source / 'setup'
    setup.mkdir(parents=True)
    (setup / 'readonly_dependency.py').write_text('VALUE = 7\n', encoding='utf-8')
    (setup / 'mods.py').write_text('''
import json, sys
from pathlib import Path
import readonly_dependency
root = Path(sys.argv[sys.argv.index('--data-dir') + 1]) / 'mod-manager'
(root / 'helper-proof.json').write_text(json.dumps({
    'no_bytecode': sys.dont_write_bytecode,
    'value': readonly_dependency.VALUE,
    'command': sys.argv[1],
}))
''', encoding='utf-8')
    files = {p.relative_to(payload).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in setup.iterdir()}
    manifest = dict(schema=1, platform=engine.HOST_PLATFORM, version='1.1.1',
                    source_commit='0' * 40, toolkit_commit='1' * 40, files=files)
    (payload / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    engine.verify_payload(payload)
    env = {k: v for k, v in os.environ.items()
           if k not in {'DEFJAM_INSTALL_DIR', 'PYTHONDONTWRITEBYTECODE', 'PYTHONPYCACHEPREFIX'}}
    env['DEFJAM_MOD_PYTHON'] = sys.executable
    data = tmp_path / 'external data'
    result = subprocess.run([str(bridge), str(data), 'status'], cwd=source, env=env,
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    proof = json.loads((data / 'mod-manager/helper-proof.json').read_text(encoding='utf-8'))
    assert proof == dict(no_bytecode=True, value=7, command='status')
    engine.verify_payload(payload)
    assert not list(payload.rglob('__pycache__'))


@pytest.mark.parametrize('activation_ok', [True, False])
def test_catalogue_fighter_install_uses_activation_transaction_not_texture_settings(bridge, tmp_path, activation_ok):
    source = tmp_path / 'helper source'
    (source / 'setup').mkdir(parents=True)
    (source / 'setup/mods.py').write_text(f'''
import sys
from pathlib import Path
root = Path(sys.argv[sys.argv.index('--data-dir') + 1]) / 'mod-manager'
root.mkdir(parents=True, exist_ok=True)
with (root / 'commands.txt').open('a') as record:
    record.write(sys.argv[1] + '\\n')
assert sys.argv[sys.argv.index('--id') + 1] == 'synthetic-fighters'
if sys.argv[1] == 'install':
    (root / 'view.ini').write_text('[installed.synthetic-fighters]\\nfolder=synthetic-fighters\\ncategory=fighters\\nname=Synthetic\\n')
elif sys.argv[1] == 'fighter-enable':
    (root / 'progress.ini').write_text('[progress]\\nmessage=activation {"verified" if activation_ok else "refused"}\\n')
    sys.exit({0 if activation_ok else 1})
else:
    raise AssertionError(sys.argv)
''', encoding='utf-8')
    env = {**os.environ, 'DEFJAM_MOD_PYTHON': sys.executable}
    env.pop('DEFJAM_INSTALL_DIR', None)
    result = subprocess.run([str(bridge), str(tmp_path / 'data'), 'install-enable', 'synthetic-fighters'],
                            cwd=source, env=env, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / 'data/mod-manager/commands.txt').read_text().splitlines() == ['install', 'fighter-enable']
    if not activation_ok:
        assert 'activation refused' in result.stdout
    # All toolkit settings functions abort in this driver: either outcome must
    # avoid the texture/language settings and preserve the helper's decision.


def test_native_game_and_fighter_prepare_share_runtime_lock(bridge, tmp_path):
    sys.path.insert(0, str(ROOT / 'setup'))
    from mods import file_lock
    data = tmp_path / 'shared launch'
    parent = subprocess.Popen([str(bridge), str(data), 'hold'], stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert parent.stdout.readline().strip() == 'locked'
        with file_lock(data / 'mod-manager/runtime.lock', shared=True):
            with pytest.raises(ValueError, match='busy'):
                with file_lock(data / 'mod-manager/runtime.lock'):
                    pytest.fail('Installer acquired running game lock')
    finally:
        parent.communicate('\n', timeout=10)


def test_polling_does_not_block_atomic_progress_updates(bridge,tmp_path):
    # The real download replaces progress.ini once per MiB while the launcher
    # reads it. Brief Windows sharing/scanner locks must not abort the download.
    source=tmp_path/'helper source';(source/'setup').mkdir(parents=True)
    (source/'setup/mods.py').write_text(f'''
import os, sys, tempfile
from pathlib import Path
sys.path.insert(0,{str(ROOT/'setup')!r})
import mods
root=Path(sys.argv[sys.argv.index('--data-dir')+1])/'mod-manager'
sys.stderr=open(root/'helper-error.log','w')
for i in range(500):
    mods.atomic_bytes(root/'progress.ini',('[progress]\\nmessage=Downloading package\\ndone='+str(i)+'\\ntotal=5000\\n').encode())
''')
    env={**os.environ,'DEFJAM_MOD_PYTHON':sys.executable}
    env.pop('DEFJAM_INSTALL_DIR',None)
    result=subprocess.run([str(bridge),str(tmp_path/'data'),'status'],cwd=source,
                          env=env,capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stdout+result.stderr
    error=(tmp_path/'data/mod-manager/helper-error.log').read_text()
    assert 'inventory refreshed' in result.stdout,result.stdout+result.stderr+error


@pytest.mark.skipif(os.name!='nt',reason='Windows readers deny replacing an open file')
def test_progress_replacement_waits_for_a_windows_reader(tmp_path):
    import threading
    sys.path.insert(0,str(ROOT/'setup'))
    try:
        import mods
    finally:
        sys.path.pop(0)
    target=tmp_path/'progress.ini'
    target.write_bytes(b'previous snapshot')
    reader=target.open('rb')
    release=threading.Timer(0.1,reader.close)
    release.start()
    try:
        mods.atomic_bytes(target,b'new snapshot')
    finally:
        release.join()
        reader.close()
    assert target.read_bytes()==b'new snapshot'


def test_runtime_lock_interoperates_with_python_helper(bridge,tmp_path):
    sys.path.insert(0,str(ROOT/'setup'))
    try:
        import mods
    finally:sys.path.pop(0)
    data=tmp_path/'data'
    process=subprocess.Popen([str(bridge),str(data),'hold'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
    try:
        assert process.stdout.readline().strip()=='locked'
        manager=mods.Manager(data,keys=[])
        with pytest.raises(ValueError,match='game is running'):
            with mods.file_lock(manager.root/'runtime.lock'):pass
    finally:
        process.communicate('done\n',timeout=10)
    assert (manager.root/'runtime.lock').stat().st_size == 0
    with mods.file_lock(manager.root/'runtime.lock'):pass
    assert (manager.root/'runtime.lock').stat().st_size == 0


def test_incomplete_transaction_blocks_game_even_without_launcher(bridge,tmp_path):
    root=tmp_path/'mod-manager';root.mkdir();(root/'journal.json').write_text('{}')
    result=subprocess.run([str(bridge),str(tmp_path),'hold'],capture_output=True,text=True,timeout=10)
    assert result.returncode==2


def fighter_data(tmp_path, *, enabled=True, head=False):
    """A data folder whose view lists one fighter pack, as mods.py writes it."""
    root = tmp_path / 'mod-manager'
    root.mkdir()
    (root / 'view.ini').write_text('[installed.synthetic-fighters]\nfolder=synthetic-fighters\ncategory=fighters\n'
                                   f'name=Synthetic\nenabled={int(enabled)}\n')
    if head:
        (root / 'fighter-profiles').mkdir()
        (root / 'fighter-profiles/head.json').write_text('{}')
    return root


def manifest(root, environment, inputs, language=''):
    lines = ['[manifest]', 'schema=1', 'runtime=0.0.0', 'language=' + language, '[environment]']
    lines += [key + '=' + value for key, value in environment.items()]
    lines.append('[inputs]')
    for index, path in enumerate(inputs):
        info = Path(path).stat()
        lines.append(f'{index}={info.st_size}|{info.st_mtime_ns}|{path}')
    (root / 'fighter-manifest.ini').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def prepare_helper(tmp_path, body):
    """A stand-in mods.py: records each command, then runs body for fighter-prepare."""
    source = tmp_path / 'helper source'
    (source / 'setup').mkdir(parents=True)
    (source / 'setup/mods.py').write_text(f"""
import sys
from pathlib import Path
sys.path.insert(0, {str(ROOT / 'tests/unit')!r})
root = Path(sys.argv[sys.argv.index('--data-dir') + 1]) / 'mod-manager'
with (root / 'commands.txt').open('a') as record:
    record.write(sys.argv[1] + '\\n')
assert sys.argv[1] == 'fighter-prepare', sys.argv
{body}
""", encoding='utf-8')
    env = {k: v for k, v in os.environ.items() if not k.startswith('RECOMP_FIGHTER_')}
    env.pop('DEFJAM_INSTALL_DIR', None)
    env['DEFJAM_MOD_PYTHON'] = sys.executable
    return source, env


def commands(root):
    path = root / 'commands.txt'
    return path.read_text().splitlines() if path.exists() else []


def test_no_enabled_fighter_pack_leaves_the_game_inert(bridge, tmp_path):
    root = fighter_data(tmp_path, enabled=False)
    source, env = prepare_helper(tmp_path, 'raise SystemExit(9)')
    result = subprocess.run([str(bridge), str(tmp_path), 'fighter', 'RECOMP_FIGHTER_NAMES'], cwd=source, env=env,
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ['0', 'RECOMP_FIGHTER_NAMES=']
    assert commands(root) == []


def test_fresh_manifest_plays_without_python_and_ignores_inherited_switches(bridge, tmp_path):
    root = fighter_data(tmp_path)
    cache = tmp_path / 'names.bin'
    cache.write_bytes(b'names')
    manifest(root, {'RECOMP_FIGHTER_NAMES': str(cache)}, [cache])
    source, env = prepare_helper(tmp_path, 'raise SystemExit(9)')
    env['RECOMP_FIGHTER_TEST_SAVE_STOP'] = 'sidecar'  # a stale shell or Steam launch option
    result = subprocess.run([str(bridge), str(tmp_path), 'fighter', 'RECOMP_FIGHTER_NAMES', 'RECOMP_FIGHTER_TEST_SAVE_STOP'],
                            cwd=source, env=env, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ['1', 'RECOMP_FIGHTER_NAMES=' + str(cache), 'RECOMP_FIGHTER_TEST_SAVE_STOP=']
    assert commands(root) == []
    assert 'saves stay in save/' in result.stderr


@pytest.mark.parametrize('change', ['size', 'missing', 'runtime', 'none'])
def test_stale_manifest_is_rebuilt_once_before_play(bridge, tmp_path, change):
    root = fighter_data(tmp_path)
    cache = tmp_path / 'names.bin'
    cache.write_bytes(b'names')
    manifest(root, {'RECOMP_FIGHTER_NAMES': 'old'}, [cache])
    if change == 'size':
        cache.write_bytes(b'longer names')
    elif change == 'missing':
        cache.unlink()
    elif change == 'runtime':
        text = (root / 'fighter-manifest.ini').read_text().replace('runtime=0.0.0', 'runtime=1.2.0-beta.2')
        (root / 'fighter-manifest.ini').write_text(text)
    elif change == 'none':
        (root / 'fighter-manifest.ini').unlink()
    fresh = tmp_path / 'fresh.bin'
    fresh.write_bytes(b'fresh')
    source, env = prepare_helper(tmp_path, f"""
from test_mod_bridge import manifest
manifest(root, {{'RECOMP_FIGHTER_NAMES': 'new'}}, [Path({str(fresh)!r})])
""")
    result = subprocess.run([str(bridge), str(tmp_path), 'fighter', 'RECOMP_FIGHTER_NAMES'], cwd=source, env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ['1', 'RECOMP_FIGHTER_NAMES=new']
    assert commands(root) == ['fighter-prepare']


def test_beta_store_moves_back_into_save_even_with_no_pack_enabled(bridge, tmp_path):
    root = fighter_data(tmp_path, enabled=False, head=True)
    source, env = prepare_helper(tmp_path, """
(root.parent / 'fighter-state').mkdir()
(root.parent / 'fighter-state/migrated.json').write_text('{}')
""")
    result = subprocess.run([str(bridge), str(tmp_path), 'fighter'], cwd=source, env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ['0']
    assert commands(root) == ['fighter-prepare']
    # The move is done: the next launch does not start Python again.
    again = subprocess.run([str(bridge), str(tmp_path), 'fighter'], cwd=source, env=env,
                           capture_output=True, text=True, timeout=30)
    assert again.returncode == 0 and commands(root) == ['fighter-prepare']


def test_failed_preparation_refuses_play_with_the_helper_message(bridge, tmp_path):
    root = fighter_data(tmp_path)
    source, env = prepare_helper(tmp_path, """
(root / 'progress.ini').write_text('[progress]\\nmessage=Fighter pack changed or is missing\\n')
raise SystemExit(1)
""")
    result = subprocess.run([str(bridge), str(tmp_path), 'fighter'], cwd=source, env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 5
    assert 'Fighter pack changed or is missing' in result.stderr


@pytest.mark.parametrize('damage', [None, 'traversal', 'missing', 'redirect', 'root', 'budget'])
def test_managed_ui_layer_is_verified_transient_and_last(bridge, tmp_path, damage):
    name='fighter-ui-'+'c'*24
    projected='../'+name if damage=='traversal' else name
    root=fighter_data(tmp_path)
    cache=tmp_path/'names.bin';cache.write_bytes(b'names')
    manifest(root,{'RECOMP_FIGHTER_UI_TEXTURE_PACK':projected},[cache])
    source,env=prepare_helper(tmp_path,'raise SystemExit(9)')
    env.pop('RECOMP_TEXTURE_ROOT',None);env.pop('RECOMP_TEXTURE_PACKS',None)
    folder=tmp_path/name
    if damage!='missing':
        folder.mkdir();(folder/'manifest.ini').write_text('[pack]\nschema=1\n')
    if damage=='redirect':
        outside=tmp_path/'elsewhere';outside.mkdir()
        (folder/'manifest.ini').unlink();folder.rmdir()
        try:folder.symlink_to(outside,target_is_directory=True)
        except OSError:pytest.skip('Creating directory symlinks requires permission')
    if damage=='root':
        other=tmp_path/'other';other.mkdir();env['RECOMP_TEXTURE_ROOT']=str(other)
    env['RECOMP_TEXTURE_PACKS']='x'*1000 if damage=='budget' else 'existing-hd'
    result=subprocess.run([str(bridge),str(tmp_path),'fighter-ui'],cwd=source,env=env,
                          capture_output=True,text=True,timeout=15)
    if damage is None:
        assert result.returncode==0,result.stderr
        lines=result.stdout.splitlines()
        assert Path(lines[1]).resolve()==tmp_path.resolve()
        assert lines[2]=='existing-hd;'+name
        assert 'HD UI texture layer active' in result.stderr
    else:
        assert result.returncode==5,result.stderr
        assert 'HD UI texture layer active' not in result.stderr
    # All settings functions abort in this driver: this must remain a per-launch layer.

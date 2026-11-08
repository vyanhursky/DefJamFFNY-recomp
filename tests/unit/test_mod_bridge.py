"""Native process/argv/OS lock checks without renderer or game data."""
from pathlib import Path
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
#include <iostream>
#include <thread>
#include <chrono>
std::string data;
namespace pcui { std::string folder_path(Folder which) { return data; } }
int main(int argc,char **argv) {
 data=argv[1];
 if(std::string(argv[2])=="fighter") {
   if(!pc_fighters_prepare("")) {std::cerr<<pc_fighters_error()<<std::endl;return 5;}
   std::cout<<pc_fighters_healthy()<<std::endl;
   std::string input;std::getline(std::cin,input);
   std::cout<<pc_fighters_healthy()<<std::endl;
   pc_fighters_finish();return 0;
 }
 if(std::string(argv[2])=="hold") {
   if(!pc_mods_game_lock())return 2;
   std::cout<<"locked"<<std::endl;
   std::string input;std::getline(std::cin,input);return 0;
 }
 if(!pcui::mod_start("status"))return 3;
 for(int i=0;i<1000 && pcui::mod_busy();i++) {pcui::mod_poll();std::this_thread::sleep_for(std::chrono::milliseconds(10));}
 std::cout<<pcui::mod_status()<<"\n"<<pcui::mod_view().catalogue<<std::endl;
 return pcui::mod_busy()?4:0;
}
'''

@pytest.fixture(scope='module')
def bridge(tmp_path_factory):
    folder=tmp_path_factory.mktemp('mod bridge with spaces')
    source=folder/'main.cpp';source.write_text(DRIVER)
    compiler=shutil.which('cl') or shutil.which('clang++') or shutil.which('g++')
    if not compiler:pytest.skip('C++ compiler required')
    exe=folder/('bridge.exe' if os.name=='nt' else 'bridge')
    if Path(compiler).stem.lower()=='cl':
        command=[compiler,'/nologo','/std:c++17','/EHsc','/I'+str(ROOT/'src/hooks'),
                 '/DDEFJAM_MOD_SOURCE_DIR="'+str(ROOT)+'"',str(source),str(ROOT/'src/hooks/pc_mods.cpp'),'/Fe:'+str(exe)]
    else:
        command=[compiler,'-std=c++17','-pthread','-I'+str(ROOT/'src/hooks'),
                 '-DDEFJAM_MOD_SOURCE_DIR="'+str(ROOT)+'"',str(source),str(ROOT/'src/hooks/pc_mods.cpp'),'-o',str(exe)]
    subprocess.run(command,cwd=folder,check=True,capture_output=True)
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


def test_native_game_and_python_supervisor_share_runtime_lock(bridge, tmp_path):
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


def fighter_helper(tmp_path, environment=''):
    source = tmp_path / 'helper source'
    (source / 'setup').mkdir(parents=True)
    (tmp_path / 'mod-manager').mkdir()
    (tmp_path / 'mod-manager/state.json').write_text('{}')
    (source / 'setup/mods.py').write_text(f'''
import sys, time
from pathlib import Path
root=Path(sys.argv[sys.argv.index('--data-dir')+1])/'mod-manager'
pid=sys.argv[sys.argv.index('--parent-pid')+1]
session=root/'fighter-sessions'/('a'*32)
data=session/'fighter-runtime-probe';data.mkdir(parents=True)
journal=session/'journal';journal.mkdir()
(journal/'supervisor.json').write_text('{{}}')
ready=root/('fighter-session-'+pid+'.ini')
ready.write_text('[session]\\nstate=ready\\nparent_pid='+pid+'\\ndata_root='+str(data)+'\\n{environment}')
deadline=time.monotonic()+15
while not (root/('fighter-session-'+pid+'.stop')).exists() and time.monotonic()<deadline:
    time.sleep(.02)
ready.write_text('[session]\\nstate=complete\\n')
''')
    env = {k:v for k,v in os.environ.items() if not k.startswith('RECOMP_FIGHTER_')}
    env.pop('DEFJAM_INSTALL_DIR', None)
    env['DEFJAM_MOD_PYTHON'] = sys.executable
    return source, env


def test_managed_native_bridge_refuses_stale_supervisor_and_acknowledges_exit(bridge, tmp_path):
    import time
    source, env = fighter_helper(tmp_path)
    parent = subprocess.Popen([str(bridge), str(tmp_path), 'fighter'], cwd=source, env=env,
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert parent.stdout.readline().strip() == '1'
        heartbeat = next((tmp_path / 'mod-manager/fighter-sessions').glob('*/journal/supervisor.json'))
        os.utime(heartbeat, (time.time()-30, time.time()-30))
        output, error = parent.communicate('\n', timeout=15)
        assert output.strip() == '0'
        assert parent.returncode == 0
        assert 'managed profile session completed' in error
    finally:
        if parent.poll() is None:
            parent.kill(); parent.wait()


def test_managed_native_bridge_rejects_test_switch_in_ready_projection(bridge, tmp_path):
    source, env = fighter_helper(tmp_path, '[environment]\\nRECOMP_FIGHTER_TEST_SAVE_STOP=intent\\n')
    parent = subprocess.Popen([str(bridge), str(tmp_path), 'fighter'], cwd=source, env=env,
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        _, error = parent.communicate('\n', timeout=10)
        assert parent.returncode == 5
        assert 'unsupported runtime setting' in error
    finally:
        # The fake helper has no parent watcher; let it exit without waiting for
        # its timeout even when startup was refused.
        (tmp_path / f'mod-manager/fighter-session-{parent.pid}.stop').write_text('complete')
        if parent.poll() is None:
            parent.kill(); parent.wait()


def test_managed_native_bridge_accepts_owned_timeline_and_cinematic_proofs(bridge, tmp_path):
    names=('TAGS','TAGS_SHA256','CAMERAS','CAMERAS_SHA256','TIMELINE_BINDINGS','FILM_PROOFS')
    projection='[environment]\\n'+''.join('RECOMP_FIGHTER_'+name+'=sealed-fixture\\n' for name in names)
    source,env=fighter_helper(tmp_path,projection)
    result=subprocess.run([str(bridge),str(tmp_path),'fighter'],cwd=source,env=env,
                          input='\n',capture_output=True,text=True,timeout=15)
    assert result.returncode==0,result.stderr
    assert result.stdout.splitlines()==['1','1']
    assert 'managed profile session completed' in result.stderr

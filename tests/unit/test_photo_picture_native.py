"""Temporary photo looks must preserve the player's options and title gamma."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
DRIVER = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "picture.h"
unsigned char memory[4096];
uint32_t g_esp=64, g_ecx=256;
extern unsigned char g_recomp_gamma[3][256];
static int reads, uploads;
static PictureOptions saved={135,65,1,43,1};
int recomp_settings_get(const char *section,const char *key,int fallback) {
    (void)section; reads++;
    if (!strcmp(key,"brightness")) return saved.brightness;
    if (!strcmp(key,"color_tint")) return saved.color_tint;
    if (!strcmp(key,"vignette")) return saved.vignette;
    if (!strcmp(key,"vignette_strength")) return saved.vignette_strength;
    if (!strcmp(key,"scratches")) return saved.scratches;
    return fallback;
}
void d3d8_gamma_set(const void *ramp) { (void)ramp; uploads++; }
int main(int argc,char **argv) {
    PictureOptions entry, current, edited, nested;
    unsigned char title[768], original[768];
    int i, before_reads, before_uploads;
    assert(argc==2);
    for (i=0;i<768;i++) title[i]=(unsigned char)(i/3);
    picture_apply_settings();
    picture_title_ramp(title);
    memcpy(original,g_recomp_gamma,sizeof original);
    picture_photo_begin(&entry);
    assert(!memcmp(&entry,&saved,sizeof entry));
    edited=entry;
    if (!strcmp(argv[1],"restore")) {
        edited.brightness=175; edited.color_tint=0;
        edited.vignette=0; edited.scratches=0;
        picture_photo_set(&edited);
        assert(memcmp(original,g_recomp_gamma,sizeof original));
        assert(!picture_scratches_on());
        before_reads=reads;
        saved.brightness=50; /* e.g. a settings refresh while Photo Mode owns the look */
        picture_apply_settings();
        assert(reads==before_reads);
        picture_photo_current(&current);
        assert(!memcmp(&current,&edited,sizeof current));
        picture_photo_begin(&nested); /* must not replace the original restore point */
        picture_photo_end();
        picture_photo_current(&current);
        assert(!memcmp(&current,&entry,sizeof current));
        assert(!memcmp(original,g_recomp_gamma,sizeof original));
        assert(picture_scratches_on());
        before_uploads=uploads;
        picture_photo_end();
        picture_photo_set(&edited); /* inactive overrides are ignored */
        assert(uploads==before_uploads);
        picture_photo_current(&current);
        assert(!memcmp(&current,&entry,sizeof current));
        picture_apply_settings();
        picture_photo_current(&current);
        assert(current.brightness==50); /* ordinary settings work again after exit */
    } else {
        edited.brightness=999; edited.color_tint=-20;
        edited.vignette=-1; edited.vignette_strength=-20; edited.scratches=0;
        picture_photo_set(&edited);
        picture_photo_current(&current);
        assert(current.brightness==200 && current.color_tint==0);
        assert(current.vignette==1 && current.vignette_strength==0 && current.scratches==0);
        edited.brightness=-10; edited.color_tint=999; edited.vignette_strength=999;
        picture_photo_set(&edited);
        picture_photo_current(&current);
        assert(current.brightness==50 && current.color_tint==100 && current.vignette_strength==100);
        picture_photo_end();
        picture_photo_current(&current);
        assert(!memcmp(&current,&entry,sizeof current));
        assert(!memcmp(original,g_recomp_gamma,sizeof original));
    }
    puts("photo picture state restored");
    return 0;
}
'''


@pytest.fixture(scope='module')
def picture_tool(tmp_path_factory):
    compiler = shutil.which('cl' if os.name == 'nt' else 'cc')
    if not compiler:
        pytest.skip('native picture fixture needs a C compiler')
    folder = tmp_path_factory.mktemp('photo-picture')
    include = folder / 'recomp/gen'
    include.mkdir(parents=True)
    (include / 'recomp_types.h').write_text(
        '#include <stdint.h>\nextern unsigned char memory[];\n'
        'extern uint32_t g_esp,g_ecx;\n'
        '#define MEM32(a) (*(uint32_t *)(memory+(a)))\n'
        '#define MEM8(a) (*(uint8_t *)(memory+(a)))\n')
    # Source-only CI intentionally omits the toolkit submodule. The fixture
    # supplies only the settings function it implements, never a disk writer.
    (folder / 'recomp_settings.h').write_text(
        'int recomp_settings_get(const char *, const char *, int);\n')
    (folder / 'driver.c').write_text(DRIVER)
    executable = folder / ('picture.exe' if os.name == 'nt' else 'picture')
    includes = [folder, ROOT / 'src/patches']
    sources = [folder / 'driver.c', ROOT / 'src/patches/picture.c']
    if os.name == 'nt':
        command = [compiler, '/nologo', '/O2', '/TC', *['/I'+str(p) for p in includes],
                   *map(str, sources), '/Fe:'+str(executable)]
    else:
        command = [compiler, '-O2', *['-I'+str(p) for p in includes], *map(str, sources),
                   '-o', str(executable), '-lm']
    result = subprocess.run(command, cwd=folder, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return executable


@pytest.mark.parametrize('case', ['restore', 'clamp'])
def test_temporary_picture_state(picture_tool, case):
    result = subprocess.run([str(picture_tool), case], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'photo picture state restored' in result.stdout

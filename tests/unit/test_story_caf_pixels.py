"""Compile and exercise the production host compositor with synthetic pixels.

No game data or generated code. Exhaustive native alpha, clipped rectangles,
all supported scales, mixed partial packs and independent injury clones.
"""
import ctypes
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[2]

class Image(ctypes.Structure):
    _fields_ = [('pixels', ctypes.POINTER(ctypes.c_ubyte)), ('width', ctypes.c_uint),
                ('height', ctypes.c_uint), ('scale', ctypes.c_uint), ('hd', ctypes.c_int)]

@pytest.fixture(scope='module')
def core(tmp_path_factory):
    cc = shutil.which('cc')
    if not cc: pytest.skip('C compiler unavailable')
    path = tmp_path_factory.mktemp('story-caf') / 'core.so'
    subprocess.run([cc, '-shared', '-fPIC', '-std=c11', '-Wall', '-Wextra', '-Werror',
                    str(ROOT/'src/patches/story_caf_pixels.c'), '-o', str(path)], check=True)
    lib = ctypes.CDLL(str(path))
    lib.story_caf_image_copy.argtypes = [ctypes.POINTER(Image), ctypes.POINTER(Image)]
    lib.story_caf_image_layer.argtypes = [ctypes.POINTER(Image), ctypes.POINTER(Image), ctypes.c_int, ctypes.c_int, ctypes.c_int]
    lib.story_caf_image_free.argtypes = [ctypes.POINTER(Image)]
    return lib

def owned(core, w, h, scale, values):
    data = (ctypes.c_ubyte * len(values))(*values)
    source = Image(data, w, h, scale, scale > 1)
    result = Image()
    assert core.story_caf_image_copy(ctypes.byref(result), ctypes.byref(source))
    return result

def read(image):
    return ctypes.string_at(image.pixels, image.width*image.height*image.scale**2*4)

def test_native_blend_all_alpha(core):
    for alpha in range(256):
        d = owned(core,1,1,1,[201,13,99,70])
        s = owned(core,1,1,1,[17,250,61,alpha])
        assert core.story_caf_image_layer(ctypes.byref(d),ctypes.byref(s),0,0,1)
        rgb = [17,250,61] if alpha == 255 else [201,13,99] if not alpha else [
            (a*alpha+b*(255-alpha)+128)>>8 for a,b in zip([17,250,61],[201,13,99])]
        assert read(d) == bytes(rgb+[max(alpha,70)])
        core.story_caf_image_free(ctypes.byref(d)); core.story_caf_image_free(ctypes.byref(s))

@pytest.mark.parametrize('scale',[1,2,3,4])
def test_copy_clip_scale_and_independent_injury(core,scale):
    d = owned(core,2,2,1,[10,20,30,255]*4)
    s = owned(core,2,1,scale,[100,110,120,0]*(2*scale**2))
    assert core.story_caf_image_layer(ctypes.byref(d),ctypes.byref(s),-1,1,0)
    assert d.scale == scale
    expected = b''.join(bytes([100,110,120,0] if y>=scale and x<scale else [10,20,30,255])
                        for y in range(2*scale) for x in range(2*scale))
    assert read(d)==expected
    clone = Image(); assert core.story_caf_image_copy(ctypes.byref(clone),ctypes.byref(d))
    clone.pixels[0]=250; assert d.pixels[0]==10
    before=read(d)
    assert not core.story_caf_image_layer(ctypes.byref(d),ctypes.byref(s),257,0,1)
    assert read(d)==before
    for p in (d,s,clone):core.story_caf_image_free(ctypes.byref(p))

def test_mixed_scale_partial_pack(core):
    d=owned(core,1,1,3,[1,2,3,255]*9)
    s=owned(core,1,1,1,[11,22,33,255])
    assert core.story_caf_image_layer(ctypes.byref(d),ctypes.byref(s),0,0,1)
    assert d.scale==3 and d.hd and read(d)==bytes([11,22,33,255]*9)
    for p in (d,s):core.story_caf_image_free(ctypes.byref(p))

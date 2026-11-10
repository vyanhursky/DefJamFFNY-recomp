import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'setup'))
from fighter_caf_portrait import layout


def test_native_quad_layout_joins_tiled_portrait_without_reordering_images():
    rows={4:{'bounds':(-16384,-16384,-11437,-10821),'logical':(128,256)},
          3:{'bounds':(-11437,-16384,-8192,-10821),'logical':(84,256)},
          2:{'bounds':(-16384,-10821,-11437,-8192),'logical':(128,121)},
          1:{'bounds':(-11437,-10821,-8192,-8192),'logical':(84,121)}}
    w,h,crops=layout(rows)
    assert (w,h)==(212,377)
    assert crops=={4:(0,0,128,256),3:(128,0,212,256),2:(0,256,128,377),1:(128,256,212,377)}


def test_native_layout_refuses_overlap_and_mismatched_raster_sizes():
    with pytest.raises(ValueError,match='overlap'):
        layout({1:{'bounds':(0,0,10,10),'logical':(10,10)},2:{'bounds':(0,0,10,10),'logical':(10,10)}})
    with pytest.raises(ValueError,match='scales'):
        layout({1:{'bounds':(0,0,10,10),'logical':(10,10)},2:{'bounds':(10,0,20,10),'logical':(20,10)}})


def test_portrait_framing_trims_only_alpha_margins_and_heads_square_results():
    from PIL import Image
    from fighter_caf_portrait import frame_png
    image=Image.new('RGBA',(100,200));image.paste((255,0,0,255),(25,20,75,70));image.paste((0,0,255,255),(25,70,75,180))
    selector=frame_png(image,'selector_2p');result=frame_png(image,'result_2p')
    assert selector.size==(50,160) and selector.getpixel((0,159))==(0,0,255,255)
    assert result.size==(50,50) and result.getpixel((25,25))==(255,0,0,255)
    with pytest.raises(ValueError):frame_png(Image.new('RGBA',(64,64)),'selector_2p')

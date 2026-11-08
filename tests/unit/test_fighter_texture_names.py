"""Explicit model/SHPX identities preserve streams and parsed bindings."""
import pytest
from test_fighter_geometry import geometry_fixture
from test_fighter_xsh import texture
from fighter_texture_names import renamed
from fighter_geometry import Geometry
from fighter_elf import Model
from fighter_xsh import Textures
from fighter_assets import AssetError


def test_explicit_texture_names_preserve_every_vertex_payload_and_pixels():
    original=Model(bytes(geometry_fixture(with_skin=True,with_bindings=True)[0]));images=Textures(texture())
    model,data=renamed(original,images,{'TEST':'Z001'})
    assert Geometry(model).texture_shapes==['Z001'] and Textures(data).images[0]['name']=='Z001'
    a,b=Geometry(original),Geometry(model)
    for old,new in zip(a.meshes,b.meshes):
        assert old['vertex_count']==new['vertex_count']
    for name in original.exports:
        if name.startswith('__VB:::'):
            first=a.vertex_buffer(original.export_offset(name));second=b.vertex_buffer(model.export_offset(name))
            assert original.data[original.data_range(first['data'],first['bytes']):][:first['bytes']]==model.data[model.data_range(second['data'],second['bytes']):][:second['bytes']]
    for before,after in zip(images.images,Textures(data).images):
        assert images.data[before['pixels_offset']:before['pixels_offset']+before['pixels_bytes']]==data[after['pixels_offset']:after['pixels_offset']+after['pixels_bytes']]
    assert Geometry(original).texture_shapes==['TEST']
    with pytest.raises(AssetError):renamed(original,images,{'unknown':'Z001'})

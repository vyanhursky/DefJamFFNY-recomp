"""Explicit four-character texture identity edits through parsed fields only."""
import re
import struct
from fighter_elf import Model
from fighter_geometry import Geometry
from fighter_model_compile import shape_bindings
from fighter_xsh import Textures,require


def renamed(model,textures,mapping):
    require(type(model) is Model and type(textures) is Textures and type(mapping) is dict,'Texture names need typed model/texture inputs')
    require(set(mapping)<=set(textures.name_sites)
            and all(type(value) is str and re.fullmatch('[A-Za-z0-9_]{4}',value) for value in mapping.values())
            and len(set(mapping.values()))==len(mapping),'Invalid explicit texture shape mapping')
    texture_data=textures.renamed(mapping);geometry=Geometry(model)
    parts=[b'']+[bytearray(model.data[row[4]:row[4]+row[5]]) for row in model.sections[1:]]
    for field,key,_imports in shape_bindings(model,geometry):
        if key in mapping:
            offset=model.local_pointer(field,5)
            at=model.data_range(offset,5)
            require(model.data[at:at+5]==key.encode()+b'\0','Texture shape key is not canonical')
            parts[1][offset:offset+4]=mapping[key].encode()
    strings=bytearray(b'\0');symbols=bytearray()
    for name,value,size,info,section in model.symbols:
        if not section:
            name=re.sub(r'SHAPENAME=([A-Za-z0-9_]{4}),1;',lambda m:'SHAPENAME='+mapping.get(m[1],m[1])+',1;',name)
        offset=len(strings) if name else 0
        if name:strings.extend(name.encode()+b'\0')
        symbols.extend(struct.pack('<IIIBBH',offset,value,size,info,0,section))
    parts[3],parts[4]=strings,symbols
    output=bytearray(model.data[:52]);rows=[model.sections[0]]
    for i in range(1,6):
        row=list(model.sections[i]);output.extend(bytes(-len(output)%row[8]));row[4:6]=len(output),len(parts[i]);output.extend(parts[i]);rows.append(row)
    output.extend(bytes(-len(output)%4));struct.pack_into('<I',output,32,len(output));output.extend(b''.join(struct.pack('<10I',*r) for r in rows))
    result=Model(bytes(output));Geometry(result).require_textures(Textures(texture_data),set(geometry.texture_shapes)-set(textures.name_sites))
    return result,texture_data

"""Append original UI drawable templates without accepting pack-supplied ELF.

Both inputs must come from a hash-verified original screens archive. This is a
template composer, not a validator/loader for arbitrary authored UI geometry.
Original symbols, relocations and data stay intact; cloned references are owned.
"""
import hashlib
import re
import struct
import copy

from fighter_assets import AssetError


def require(value, message):
    if not value:
        raise AssetError(message)


class UIModel:
    def __init__(self, data, expected_sha256):
        require(isinstance(data, bytes) and 52 <= len(data) <= 64 * 1024**2
                and hashlib.sha256(data).hexdigest() == expected_sha256, 'UI model needs its verified original template')
        self.data = data
        require(data[:16] == b'\x7fELF\x01\x01\x01' + bytes(9), 'Invalid UI ELF identification')
        header = struct.unpack_from('<HHIIIIIHHHHHH', data, 16)
        require(header[:5] == (1, 8, 1, 0, 0) and header[6:] == (0x20924000, 52, 0, 0, 40, 6, 3),
                'Unsupported original UI ELF layout')
        at = header[5]
        require(52 <= at <= len(data) - 240, 'Truncated UI section table')
        self.rows = [list(struct.unpack_from('<10I', data, at + i * 40)) for i in range(6)]
        require(self.rows[0] == [0] * 10, 'Invalid UI null section')
        ranges = [(0, 52), (at, at + 240)]
        self.parts = []
        for i, row in enumerate(self.rows):
            name, kind, flags, address, offset, size, link, info, align, width = row
            if i:
                require(kind == (0, 1, 9, 3, 2, 3)[i] and flags == (3 if i == 1 else 0)
                        and address == 0 and align in (1, 4, 16) and offset % align == 0
                        and 52 <= offset <= len(data) and size <= len(data) - offset, 'Invalid UI section')
                if size: ranges.append((offset, offset + size))
            self.parts.append(bytearray(data[offset:offset + size]))
        ordered = sorted(ranges)
        require(all(a[1] <= b[0] for a, b in zip(ordered, ordered[1:])), 'Overlapping UI sections')
        require([self.string(3, row[0]) for row in self.rows] == ['', '.data', '.rel.data', '.shstrtab', '.symtab', '.strtab'],
                'Unexpected UI section names')
        require(self.rows[2][6:8] == [4, 1] and self.rows[2][9] == 8 and len(self.parts[2]) % 8 == 0,
                'Invalid UI relocation table')
        require(self.rows[4][6] == 5 and self.rows[4][9] == 16 and len(self.parts[4]) % 16 == 0,
                'Invalid UI symbol table')
        self.symbols = [list(row) for row in struct.iter_unpack('<IIIBBH', self.parts[4])]
        require(0 < len(self.symbols) <= 262144 and self.symbols[0] == [0] * 6, 'Invalid UI symbols')
        self.names = [self.string(5, row[0]) for row in self.symbols]
        self.exports = {}
        for i, (name, value, size, info, other, section) in enumerate(self.symbols):
            require(other == 0 and section < 6 and info >> 4 in (0, 1, 2)
                    and info & 15 in (0, 1, 3) and (i < self.rows[4][7]) == (info >> 4 == 0), 'Invalid UI symbol')
            if info >> 4 and section:
                require(section == 1 and value <= len(self.parts[1]) and size <= len(self.parts[1]) - value
                        and self.names[i] not in self.exports, 'Invalid UI export')
                self.exports[self.names[i]] = value
        self.relocations = [tuple(row) for row in struct.iter_unpack('<II', self.parts[2])]
        self.pointers = {}
        for offset, info in self.relocations:
            symbol, method = info >> 8, info & 255
            require(method == 2 and 0 < symbol < len(self.symbols) and offset % 4 == 0
                    and 0 <= offset <= len(self.parts[1]) - 4 and offset not in self.pointers, 'Invalid UI relocation')
            _, value, _, _, _, section = self.symbols[symbol]
            addend = struct.unpack_from('<I', self.parts[1], offset)[0]
            require(section in (0, 1) and (section == 1 and value + addend < len(self.parts[1])
                    or section == 0 and value == addend == 0), 'Invalid UI relocation target')
            self.pointers[offset] = (symbol, None if section == 0 else value + addend)

    def string(self, section, offset):
        data = self.parts[section]
        require(0 <= offset < len(data), 'UI string is outside its section')
        end = data.find(b'\0', offset, min(len(data), offset + 4097))
        require(end >= offset and all(32 <= c < 127 for c in data[offset:end]), 'Invalid UI string')
        return data[offset:end].decode('ascii')

    def selected_grid(self,participants):
        """Isolate a hash-verified original grid closure, never package geometry."""
        require(type(participants) is int and participants in (2,3,4),'Unsupported selected-grid template')
        start,original_model,original_image={2:(0xF450,2,1),3:(0x2ACC0,4,3),4:(0x2AE10,4,3)}[participants]
        # The native Model consumes0xE0bytes, including optional patch lists at
        # +D0..DC. Keep its zero tail and alignment padding; ending at+448
        # places the next appended model-name string in those live fields.
        end=start+0x460
        require(end<=len(self.parts[1]) and self.exports.get(f'__Model:::{original_model}')==start+0x378,
                'Original selected-grid closure differs from its supported profile')
        require(self.parts[1][start+0x448:end]==bytes(24),'Selected-grid Model tail has unsupported controls')
        selected={f'__Model:::{original_model}',f'__BBOX:::{original_model}',
                  f'__VB:::__GPvb_9_0_{original_model}',f'__RM:::__GP_RM_{original_model}_0'}
        sites={at:row for at,row in self.pointers.items() if start<=at<end}
        require(len(sites)==42 and all(target is None or start<=target<end for _,target in sites.values())
                and not any(start<=target<end for at,(_,target) in self.pointers.items()
                            if not start<=at<end and target is not None),
                'Selected-grid closure has unrelated incoming/outgoing pointers')
        result=copy.deepcopy(self)
        result.parts[1]=bytearray(struct.pack('<I',4)+bytes(12)+self.parts[1][start:end])
        result.parts[5]=bytearray(b'\0');result.names=['',''];result.symbols=[[0]*6,[0,0,0,3,0,1]]
        result.exports={};result.relocations=[];remap={}
        imports={index for index,target in sites.values() if target is None}
        for index,row in enumerate(self.symbols):
            name=self.names[index]
            if index not in imports and name not in selected and name!='__EAGL_TOOLLIB_VERSION:::EAGL_TOOLLIB_VERSION-4':continue
            require(row[5] in (0,1),'Selected-grid symbol is not a supported local/import binding')
            new=row[:];new[0]=len(result.parts[5]);result.parts[5].extend(name.encode()+b'\0')
            if row[5]:new[1]=0 if name.startswith('__EAGL_TOOLLIB_VERSION:::') else 16+row[1]-start
            remap[index]=len(result.symbols);result.symbols.append(new);result.names.append(name)
            if row[5]:result.exports[name]=new[1]
        for at,(index,target) in sorted(sites.items()):
            field=16+at-start
            if target is None:
                require(struct.unpack_from('<I',self.parts[1],at)[0]==0,'Selected-grid import has an unsupported addend')
                binding=remap[index];value=0
            else:binding=1;value=16+target-start
            struct.pack_into('<I',result.parts[1],field,value)
            result.relocations.append((field,binding<<8|2))
        result.rows[4][7]=2
        data=result.compose();result=UIModel(data,hashlib.sha256(data).hexdigest())
        result._grid_profile=(16,original_model,original_image)
        return result

    def append_drawable(self, source, model_id, image_id):
        require(type(source) is UIModel and type(model_id) is int and type(image_id) is int
                and 1 <= model_id <= 9999 and 1 <= image_id <= 9999, 'Invalid owned UI drawable identity')
        origin,source_model,source_image=getattr(source,'_grid_profile',(0,2,1))
        exports = {f'__Model:::{source_model}': f'__Model:::{model_id}', f'__BBOX:::{source_model}': f'__BBOX:::{model_id}',
                   f'__VB:::__GPvb_9_0_{source_model}': f'__VB:::__GPvb_9_0_{model_id}',
                   f'__RM:::__GP_RM_{source_model}_0': f'__RM:::__GP_RM_{model_id}_0'}
        require(set(source.exports) == set(exports) | {'__EAGL_TOOLLIB_VERSION:::EAGL_TOOLLIB_VERSION-4'}
                and not set(exports.values()) & self.exports.keys(), 'Unsupported or colliding UI drawable exports')
        require(len(source.parts[1]) == (origin+0x460 if origin else 1120) and len(source.relocations) == 42
                and source.exports[f'__Model:::{source_model}'] == origin+0x378, 'Unsupported original UI drawable layout')
        sections = [i for i, row in enumerate(self.symbols) if row[1:] == [0, 0, 3, 0, 1]]
        require(len(sections) == 1, 'UI destination needs one local data section symbol')
        data = self.parts[1]; data.extend(bytes(-len(data) % 16)); base = len(data); data.extend(source.parts[1])
        def append_text(value):
            at = len(data); data.extend(value.encode('ascii') + b'\0'); return at
        model_name, image_name = append_text(str(model_id)), append_text(str(image_id))
        # The UI loader finds UV matrices by this typed parameter name before
        # multiplying them by the texture's reciprocal dimensions (1813E0).
        # Keeping the donor's image1 here binds an unrelated image's scale.
        matrix_field=origin+0x310
        require(matrix_field in source.pointers and source.pointers[matrix_field][1] is not None
                and source.string(1, source.pointers[matrix_field][1]) == f'ScaleMatrix::{source_image}::TextureMatrix',
                'Unexpected original UI texture-matrix name')
        matrix_name = append_text(f'ScaleMatrix::{image_id}::TextureMatrix')
        image_keys = (origin+0x25c, origin+0x32c)
        # The material-name pointer and shape-key table are separate consumers.
        require(all(at in source.pointers and source.pointers[at][1] is not None
                    and source.string(1, source.pointers[at][1]) == str(source_image) for at in image_keys),
                'Unexpected original UI image-name references')
        next_uid = 1 + max((int(m[1]) for name in self.names for m in [re.search(r'UID=(\d+);', name)] if m), default=0)
        remap = {}
        def symbol(name, value, size, info, section):
            if section == 0 and name in self.names:
                index = self.names.index(name)
                require(self.symbols[index][5] == 0, 'UI import collides with an export')
                return index
            require(name not in self.names, 'UI symbol identity collides')
            at = len(self.parts[5]); self.parts[5].extend(name.encode('ascii') + b'\0')
            self.symbols.append([at, value, size, info, 0, section]); self.names.append(name)
            return len(self.symbols) - 1
        for index, row in enumerate(source.symbols):
            name = source.names[index]
            if row[5] == 0 and name:
                if 'RUNTIME_ALLOC::' in name:
                    require(name.startswith(('__EAGL::TAR:::', '__EAGL::GeoPrimState:::'))
                            and len(re.findall(r'UID=\d+;', name)) == 1, 'Unsupported UI allocation template')
                    name = re.sub(r'UID=\d+;', f'UID={next_uid};', name)
                    name = name.replace(f'SHAPENAME={source_image},1;', f'SHAPENAME={image_id},1;')
                remap[index] = symbol(name, 0, 0, 0x10, 0)
            elif name in exports:
                symbol(exports[name], base + row[1], row[2], row[3], 1)
                self.exports[exports[name]] = base + row[1]
        for at, (index, target) in source.pointers.items():
            if target is None:
                binding, value = remap[index], 0
            else:
                binding = sections[0]
                value = (model_name if at == origin+0x42c else image_name if at in image_keys
                         else matrix_name if at == matrix_field else base + target)
            struct.pack_into('<I', data, base + at, value)
            self.relocations.append((base + at, binding << 8 | 2))
        return base

    def compose(self):
        self.parts[2] = bytearray(b''.join(struct.pack('<II', *row) for row in self.relocations))
        self.parts[4] = bytearray(b''.join(struct.pack('<IIIBBH', *row) for row in self.symbols))
        output, rows = bytearray(self.data[:52]), [[0] * 10]
        for i in range(1, 6):
            row = self.rows[i][:]; output.extend(bytes(-len(output) % row[8]))
            row[4:6] = [len(output), len(self.parts[i])]; output.extend(self.parts[i]); rows.append(row)
        output.extend(bytes(-len(output) % 4)); at = len(output)
        output.extend(b''.join(struct.pack('<10I', *row) for row in rows)); struct.pack_into('<I', output, 32, at)
        result = bytes(output); UIModel(result, hashlib.sha256(result).hexdigest())
        return result

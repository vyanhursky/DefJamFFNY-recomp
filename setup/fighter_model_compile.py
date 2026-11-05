"""Compile typed geometry into a verified retail model's rendering structure.

Input control records are never emitted. A template fixes material/mesh layout,
render programs and state objects. Only separately checked geometry, skin data,
rig transforms and texture identities are copied. Native acceptance is a separate
gate; this module does not authorize activation of its output.
"""
import re
import struct

from fighter_elf import Model, ModelError, MAX_BYTES
from fighter_geometry import Geometry
from fighter_render import RenderProgram
from fighter_rig import Skeleton, RECORD_BYTES
from fighter_skin import Skin


def require(value, message):
    if not value:
        raise ModelError(message)


def texture_family(name):
    return re.sub(r'SHAPENAME=[A-Za-z0-9_]{4},1;', 'SHAPENAME=XXXX,1;',
                  re.sub(r'UID=[0-9]+;', 'UID=0;', name))


def layout(geometry):
    return ([group['render_resources'] for group in geometry.groups],
            [(mesh['strides'], mesh['render_program']['sha256']) for mesh in geometry.meshes])


def shape_bindings(model, geometry):
    """Read the counted shape-key table consumed by112310/1130A0.

    The tail is a u16 bit count plus its bitmap (113270), padded to four
    bytes. Records end at an unrelocated zero key, not a fixed row count.
    Only verified template records are emitted by the compiler.
    """
    root = model.export_offset('__Model:::' + geometry.name)
    if root + 0xbc not in model.pointers:
        require(model.data_words(root + 0xbc, 1) == (0,), 'Invalid template shape table')
        return []
    at = model.local_pointer(root + 0xbc, 4)
    result = []
    while at in model.pointers:
        require(len(result) < 4096, 'Template shape table exceeds its budget')
        key = geometry.text(model.local_pointer(at, 1))
        require(re.fullmatch(r'[A-Za-z0-9_]{4}', key), 'Invalid template shape key')
        count, = model.data_words(at + 4, 1)
        require(0 < count <= 65535, 'Invalid template shape binding count')
        tail = at + 8 + count * 4
        bits, = model.unpack('<H', model.data_range(tail, 2))
        require(bits >= count, 'Template shape bitmap is too short')
        end = tail + ((2 + (bits + 7) // 8 + 3) & ~3)
        model.data_range(at, end - at)
        items = [model.pointers.get(at + 8 + i * 4) for i in range(count)]
        require(all(p and p['imported'] and p['symbol'].startswith('__EAGL::TAR:::')
                    for p in items), 'Unsupported template shape binding')
        result.append((at, key, [p['symbol'] for p in items]))
        at = end
    require(model.data_words(at, 1) == (0,), 'Unterminated template shape table')
    return result


def compile_geometry(source, template, native_name=None):
    """The caller must obtain template bytes from its hash-verified own dump."""
    source_geometry, target_geometry = Geometry(source), Geometry(template)
    name = source_geometry.name if native_name is None else native_name + '_alpha'
    require(re.fullmatch(r'[A-Za-z0-9_]{1,64}', name), 'Invalid compiled model namespace')
    source_skin, target_skin = Skin(source), Skin(template)
    source_rig, target_rig = source_skin.skeleton, target_skin.skeleton
    require(layout(source_geometry) == layout(target_geometry),
            'Geometry needs a retail template with the same material and render layout')
    require(source_rig.topology_sha256 == target_rig.topology_sha256
            and source_rig.permutation == target_rig.permutation, 'Geometry template rig differs')
    start, length = template.sections[1][4:6]
    payload = bytearray(template.data[start:start + length])
    pointers = {at: dict(pointer) for at, pointer in template.pointers.items()}
    moved, texture_imports = {}, {}

    def allocate(data):
        require(len(payload) + len(data) + 16 <= MAX_BYTES, 'Compiled model exceeds its data budget')
        payload.extend(bytes(-len(payload) % 16))
        at = len(payload); payload.extend(data)
        return at

    def word(at, value):
        struct.pack_into('<I', payload, at, value)

    def local(at, target):
        pointers[at] = {'symbol': '', 'imported': False, 'target': target}

    def scalar(model, geometry, at, size):
        begin = geometry.scalars(at, size)
        return model.data[begin:begin + size]

    def resources(model, kind, name):
        if kind == 'rm':
            return {i: model.export_offset(f'__RM:::__GP_RM_{name}_{i}')
                    for i in range(len(source_geometry.meshes))}
        result = {}
        for symbol in model.exports:
            match = re.fullmatch(r'__VB:::__GPvb_([0-9]+)_([0-9]+)_' + re.escape(name), symbol)
            if match:
                result[int(match[2]), int(match[1])] = model.export_offset(symbol)
        # Export numbers identify stream resources; op9 uses their ordinal in
        # the mesh's sorted stream list, not necessarily that export number.
        return {(mesh, ordinal): result[key] for mesh in range(len(source_geometry.meshes))
                for ordinal, key in enumerate(sorted(key for key in result if key[0] == mesh))}

    source_vbs = resources(source, 'vb', source_geometry.name)
    target_vbs = resources(template, 'vb', target_geometry.name)
    require(source_vbs.keys() == target_vbs.keys(), 'Geometry template stream slots differ')
    for targets in (list(target_vbs.values()),
                    [template.local_pointer(vb + 16, 1) for vb in target_vbs.values()],
                    [template.local_pointer(vb, 8) for vb in target_vbs.values()]):
        require(len(targets) == len(set(targets)), 'Geometry template aliases stream storage')
    for key, old in sorted(target_vbs.items()):
        incoming = source_geometry.vertex_buffer(source_vbs[key])
        existing = target_geometry.vertex_buffer(old)
        require(incoming['stride'] == existing['stride'], 'Geometry template stream stride differs')
        # Native op9 derives the VB header by subtracting20 from its data pointer.
        require(existing['data'] == old + 20, 'Template stream has unsupported header adjacency')
        header = bytearray(template.data[template.data_range(old, 20):template.data_range(old, 20) + 20])
        struct.pack_into('<I', header, 4, incoming['bytes'])
        new = allocate(header + scalar(source, source_geometry, incoming['data'], incoming['bytes']))
        moved[old], moved[existing['data']] = new, new + 20
        local(new, template.local_pointer(old, 8))
        local(new + 16, new + 20)

    source_rms = resources(source, 'rm', source_geometry.name)
    target_rms = resources(template, 'rm', target_geometry.name)
    for index, old in sorted(target_rms.items()):
        before = RenderProgram(template, old)
        after = RenderProgram(source, source_rms[index])
        for target, incoming in zip(before.commands, after.commands):
            require((target.opcode, target.arguments) == (incoming.opcode, incoming.arguments),
                    'Geometry template command differs')
            if target.opcode in (14, 31):
                count, = source.data_words(incoming.parameter, 1)
                # 1187C0 stores op31's count in3A61A8; 118B00 passes that
                # count to118E30, which bounds the two uploaded banks by it.
                # The source Skin check bounds count and every selector.
                size = count * (2 if target.opcode == 14 else 16)
                data = source.local_pointer(incoming.parameter + 4, size)
                replacement = allocate(scalar(source, source_geometry, data, size))
                word(target.parameter, count); local(target.parameter + 4, replacement)
            elif target.opcode == 2:
                # Geometry already checks this four-word draw header against op14.
                data = source.local_pointer(incoming.parameter + 4, 16)
                replacement = allocate(scalar(source, source_geometry, data, 16))
                local(target.parameter + 4, replacement)
            elif target.opcode == 9:
                require(target.arguments[0] == 0, 'Unsupported template stream instance')
                stream = target.arguments[1]
                require((index, stream) in target_vbs, 'Template command names a missing stream')
                old_data = target_geometry.vertex_buffer(target_vbs[index, stream])['data']
                require(template.local_pointer(target.parameter + 4, 1) == old_data,
                        'Template stream command does not reference its own VB')
                word(target.parameter, source_geometry.meshes[index]['vertex_count'])
            elif target.opcode == 15:
                a, b = template.pointers[target.parameter + 4], source.pointers[incoming.parameter + 4]
                require(a['imported'] and b['imported'] and a['symbol'].startswith('__EAGL::TAR:::')
                        and texture_family(a['symbol']) == texture_family(b['symbol']),
                        'Geometry texture binding differs from its template family')
                shape = re.search(r'SHAPENAME=([A-Za-z0-9_]{4}),1;', b['symbol'])
                replacement = (re.sub(r'SHAPENAME=[A-Za-z0-9_]{4},1;',
                                     'SHAPENAME=' + shape[1] + ',1;', a['symbol'])
                               if shape else a['symbol'])
                # Keep the verified allocation UID and every state expression.
                previous = texture_imports.setdefault(a['symbol'], replacement)
                require(previous == replacement, 'One template texture cannot map to multiple shapes')

    for at, key, imports in shape_bindings(template, target_geometry):
        replacements = set()
        for imported in imports:
            before = re.search(r'SHAPENAME=([A-Za-z0-9_]{4}),1;', imported)
            after = re.search(r'SHAPENAME=([A-Za-z0-9_]{4}),1;', texture_imports.get(imported, imported))
            require(before and after and before[1] == key, 'Template shape key and import disagree')
            replacements.add(after[1])
        require(len(replacements) == 1, 'One template shape key cannot map to multiple shapes')
        local(at, allocate(replacements.pop().encode('ascii') + b'\0'))

    # Rig bytes have a checked fixed schema; preserve authored bind transforms.
    rig_size = 16 + len(source_rig.rows) * RECORD_BYTES
    source_root, target_root = source.export_offset('__Skeleton:::root'), template.export_offset('__Skeleton:::root')
    payload[target_root:target_root + rig_size] = scalar(source, source_geometry, source_root, rig_size)
    source_root = source.export_offset('__Model:::' + source_geometry.name)
    target_root = template.export_offset('__Model:::' + target_geometry.name)
    payload[target_root + 12:target_root + 76] = scalar(source, source_geometry, source_root + 12, 64)
    local(target_root + 0xb4, allocate(name.encode('ascii') + b'\0'))
    for old in target_rms.values():
        if old + 0x30 in template.pointers:
            debug = target_geometry.text(template.local_pointer(old + 0x30, 1))
            local(old + 0x30, allocate(debug.replace(target_geometry.name, name).encode('ascii') + b'\0'))

    # Rebuild all relocations with one section-local base. No raw source pointer,
    # source export or source rendering object is copied into the result.
    section_symbols = [i for i, row in enumerate(template.symbols)
                       if row == ('', 0, 0, 3, 1)]
    inserted = not section_symbols
    section_symbol = section_symbols[0] if section_symbols else 1
    symbols = [('', 0, 0, 0, 0)] + ([('', 0, 0, 3, 1)] if inserted else [])
    for symbol_name, value, size, info, section in template.symbols[1:]:
        renamed = (symbol_name.replace(target_geometry.name, name) if section
                   else texture_imports.get(symbol_name, symbol_name))
        symbols.append((renamed, moved.get(value, value) if section else value,
                        size, info, section))
    imports = {name: i for i, (name, _, _, _, section) in enumerate(symbols) if name and section == 0}
    relocations = bytearray()
    # Preserve the template's relocation ordering; append only the new VB fixups.
    for at, pointer in pointers.items():
        if pointer['imported']:
            symbol = imports[texture_imports.get(pointer['symbol'], pointer['symbol'])]
            word(at, 0)
        else:
            symbol = section_symbol
            word(at, moved.get(pointer['target'], pointer['target']))
        relocations.extend(struct.pack('<II', at, symbol << 8 | 2))
    strings, table = bytearray(b'\0'), bytearray()
    for name, value, size, info, section in symbols:
        at = len(strings) if name else 0
        if name: strings.extend(name.encode('ascii') + b'\0')
        table.extend(struct.pack('<IIIBBH', at, value, size, info, 0, section))
    names = template.sections[2]
    sections = [b'', bytes(payload), template.data[names[4]:names[4] + names[5]], bytes(strings), bytes(table), bytes(relocations)]
    image, rows = bytearray(template.data[:52]), [(0,) * 10]
    for i in range(1, 6):
        row = list(template.sections[i]); align = row[8]
        image.extend(bytes(-len(image) % align)); row[4:6] = [len(image), len(sections[i])]
        if i == 4: row[7] += int(inserted)
        image.extend(sections[i]); rows.append(tuple(row))
    image.extend(bytes(-len(image) % 4)); section_at = len(image)
    image.extend(b''.join(struct.pack('<10I', *row) for row in rows))
    struct.pack_into('<I', image, 32, section_at)
    result = Model(bytes(image))
    Geometry(result); Skin(result)
    return result

"""Owned static thumbnail frames from verified original result-movie templates.

All executable actions and geometry come from the original UI or this compiler.
Custom input is the pixel-only result texture emitted by the portrait compiler.
The original frame bank and all semantic identity consumers remain intact.
"""
import hashlib
import struct

import fighter_apt as apt
from fighter_archive import Archive, store
from fighter_assets import unpack
from fighter_menu import Action
from fighter_portrait import PortraitBaseline, UITextures, require, variant_path
from fighter_ui_model import UIModel
from fighter_resource_files import portrait_target


class GridStates:
    """Trusted selected-grid geometry with two independently authored rasters."""
    def __init__(self,movie,constants,model,participants,normal,selected):
        require(type(model) is UIModel and type(normal) is UITextures and type(selected) is UITextures,
                'Grid states need original geometry and two compiled pixel sources')
        self.model=model.selected_grid(participants)
        root,_=apt.parse_const(constants)
        count,characters=struct.unpack_from('<II',movie,root+20)
        identity=2 if participants==2 else 4
        require(identity<count,'Selected-grid shape is absent')
        at,=struct.unpack_from('<I',movie,characters+4*identity)
        self.shape=movie[at:at+28]
        require(len(self.shape)==28 and struct.unpack_from('<II',self.shape)==(1,0x09876543)
                and struct.unpack_from('<4f',self.shape,8)==(-18.5,-18.5,18.5,18.5)
                and struct.unpack_from('<I',self.shape,24)[0]==identity,
                'Original selected-grid shape differs from its verified contract')
        # selectChar uses token+1; redraw/deselectChar use token+150.
        # append_grid addresses their zero-based frames as token/token+149.
        self.textures=(selected,normal)


def append_grid(movie, constants, model, textures, templates):
    """templates: presentation-token -> (original result APT/O, compiled XSH)."""
    require(0 < len(templates) <= 4096, 'Invalid custom grid population')
    root, _ = apt.parse_const(constants)
    require(movie[:8] == b'Apt Data', 'Unsupported grid movie')
    char_count, chars = struct.unpack_from('<II', movie, root + 20)
    require(char_count <= 9999 and chars + char_count * 4 <= len(movie), 'Invalid grid character table')
    exports = struct.unpack_from('<I', movie, 8)[0]
    require(exports <= 4096 and 12 + exports * 8 <= len(movie), 'Invalid grid export table')
    thumbs = [identity for offset, identity in struct.iter_unpack('<II', movie[12:12 + exports * 8])
              if apt.read_cstr(movie, offset) == 'thumbAll']
    require(len(thumbs) == 1 and thumbs[0] < char_count, 'Missing unique thumbAll export')
    sprite = struct.unpack_from('<I', movie, chars + thumbs[0] * 4)[0]
    require(struct.unpack_from('<II', movie, sprite) == (5, 0x09876543), 'Invalid thumbnail sprite')
    count, frames = struct.unpack_from('<II', movie, sprite + 8)
    require(count == 300 and frames + count * 8 <= len(movie), 'Unsupported original thumbnail frame bank')
    state_frames = [frame for token in templates for frame in (token, token + 149)]
    require(all(type(token) is int and 300 <= token <= 65000 for token in templates)
            and len(set(state_frames)) == len(state_frames), 'Custom grid state frames collide')
    output = bytearray(movie)
    def append(data):
        output.extend(bytes(-len(output) % 4)); at = len(output); output.extend(data); return at
    new_characters, new_frames, images = [], {}, {}
    next_id = max([char_count - 1] + [int(image['name']) for image in textures.images]
                  + [int(name.split(':::')[1]) for name in model.exports if name.startswith('__Model:::')]) + 1
    # Image initialization passes the APT character index to the UV-matrix
    # lookup. The runtime batches model initialization beyond the original512
    # scratch slots; the remaining four-digit image namespace is independent.
    require(next_id == char_count, 'Grid image IDs must match their APT character indices')
    require(next_id + 2 * sum(2 if type(value) is GridStates else 1 for value in templates.values()) <= 10000,
            'Custom grid exceeds the four-digit UI image namespace')
    for token,value in sorted(templates.items()):
        if type(value) is GridStates:
            for frame,texture in zip((token,token+149),value.textures):
                image_id,model_id=next_id,next_id+1;next_id+=2
                model.append_drawable(value.model,model_id,image_id);images[image_id]=texture
                new_characters.append(append(struct.pack('<III',7,0x09876543,image_id)))
                shape=bytearray(value.shape);struct.pack_into('<I',shape,24,model_id)
                shape_character=char_count+len(new_characters);new_characters.append(append(shape))
                code=Action(len(output));code.op('Stop');code_at=append(code.finish())
                stop=append(struct.pack('<II',1,code_at))
                # All verified/source grid placements have identity transforms;
                # make that identity explicit when replacing an existing state.
                placement=append(struct.pack('<IIII6f',3,7,1,shape_character,1.,0.,0.,1.,0.,0.)
                                 +struct.pack('<6I',0xffffffff,0,0,0,0xffffffff,0))
                new_frames[frame]=(2,append(struct.pack('<II',stop,placement)))
            continue
        source_movie,source_model,source_texture=value
        require(type(source_model) is UIModel and type(source_texture) is UITextures, 'Grid requires typed original templates')
        # The hash-verified original result movie has Image1 and Shape2.
        result_root = 24
        source_count, source_chars = struct.unpack_from('<II', source_movie, result_root + 20)
        require(source_count == 3, 'Unsupported result movie character set')
        shape_at = struct.unpack_from('<I', source_movie, source_chars + 8)[0]
        shape = bytearray(source_movie[shape_at:shape_at + 28])
        require(len(shape) == 28 and struct.unpack_from('<II', shape) == (1, 0x09876543)
                and struct.unpack_from('<I', shape, 24)[0] == 2, 'Unsupported result shape')
        x, y, width, height = struct.unpack_from('<4f', shape, 8)
        require(x == y == 0 and width == height and width in (32, 39, 44), 'Unsupported result shape bounds')
        image_id, model_id = next_id, next_id + 1; next_id += 2
        model.append_drawable(source_model, model_id, image_id)
        images[image_id] = source_texture
        new_characters.append(append(struct.pack('<III', 7, 0x09876543, image_id)))
        struct.pack_into('<I', shape, 24, model_id)
        shape_character = char_count + len(new_characters)
        new_characters.append(append(shape))
        for index in (token, token + 149):
            # Native loading fixes pointers in place. Each timeline state owns
            # its records even though the immutable drawable is shared.
            append(b'')
            code = Action(len(output)); code.op('Stop'); code_at = append(code.finish())
            stop = append(struct.pack('<II', 1, code_at))
            placement = append(struct.pack('<IIII6f', 3, 7, 1, shape_character,
                                          37 / width, 0., 0., 37 / height, -18.5, -18.5)
                               + struct.pack('<6I', 0xffffffff, 0, 0, 0, 0xffffffff, 0))
            items = append(struct.pack('<II', stop, placement))
            new_frames[index] = (2, items)
    frame_count = max(state_frames) + 1
    frame_bytes = bytearray(movie[frames:frames + count * 8] + bytes((frame_count - count) * 8))
    for index, row in new_frames.items(): struct.pack_into('<II', frame_bytes, index * 8, *row)
    frame_at = append(frame_bytes)
    chars_at = append(movie[chars:chars + char_count * 4] + struct.pack('<' + 'I' * len(new_characters), *new_characters))
    struct.pack_into('<II', output, root + 20, char_count + len(new_characters), chars_at)
    struct.pack_into('<II', output, sprite + 8, frame_count, frame_at)
    require(len(output) <= 16 * 1024**2, 'Custom grid movie exceeds budget')
    return bytes(output), model.compose(), textures.appended(images)


def compose_grid(screens, report, baseline,*,resource_files=None):
    require(type(baseline) is PortraitBaseline, 'Grid templates require the verified original screens')
    archive, replacements = Archive(screens), {}
    resources = sorted(set(report['portrait_bindings'].values()))
    tokens = {identifier: 300 + (i // 149) * 300 + i % 149 for i, identifier in enumerate(resources)}
    bindings = {report['bindings'][key]['selection_key']: tokens[value] for key, value in report['portrait_bindings'].items()}
    for count in (2, 3, 4):
        stem = f'chooseF{count}'; path = f'screens/battle/{stem}.big'
        current = Archive(unpack(archive.read(path)))
        original = Archive(unpack(baseline.archive.read(path)))
        model_bytes = original.read(stem + '.o')
        require(current.read(stem + '.o') == model_bytes and current.read(stem + '.xsh') == original.read(stem + '.xsh'),
                'Another mod already owns the selector image/model data')
        model = UIModel(model_bytes, hashlib.sha256(model_bytes).hexdigest())
        templates = {}
        for identifier in resources:
            info = report['portrait_resources'][identifier]
            if f'grid_normal_{count}p' in info['variants']:
                require(type(resource_files) is dict,'Authored grid states need their compiled files')
                states=[]
                for state in ('normal','selected'):
                    resource_path=portrait_target(identifier,f'grid_{state}_{count}p')
                    require(resource_path in resource_files and resource_path in report['portrait_files']
                            and hashlib.sha256(resource_files[resource_path]).hexdigest()==report['portrait_files'][resource_path],
                            'Compiled grid state differs from its receipt')
                    states.append(UITextures(resource_files[resource_path]))
                templates[tokens[identifier]]=GridStates(original.read(stem+'.apt'),original.read(stem+'.const'),
                    UIModel(model_bytes,hashlib.sha256(model_bytes).hexdigest()),count,*states)
                continue
            donor_path, donor_stem = variant_path(f'result_{count}p', info['donor_selection'])
            donor = Archive(unpack(baseline.archive.read(donor_path)))
            template = donor.read(donor_stem + '.o')
            selection = next(key for key, token in bindings.items() if token == tokens[identifier])
            result_path, result_stem = variant_path(f'result_{count}p', selection)
            texture = Archive(unpack(archive.read(result_path))).read(result_stem + '.xsh')
            templates[tokens[identifier]] = (donor.read(donor_stem + '.apt'),
                UIModel(template, hashlib.sha256(template).hexdigest()), UITextures(texture))
        movie, model, textures = append_grid(current.read(stem + '.apt'), current.read(stem + '.const'), model,
                                            UITextures(original.read(stem + '.xsh')), templates)
        replacements[path] = store(current.compose(replacements={stem + '.apt': movie, stem + '.o': model, stem + '.xsh': textures}))
    return archive.compose(replacements=replacements), bindings

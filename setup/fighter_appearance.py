"""General research appearance composition, with explicit unfulfilled gates.

New geometry/textures get a resource-owned native name and registrations. The
first adapter reuses verified donor facial animation data. Unknown face curves
and render parameter semantics remain separate gates; no public launch capability
is implied by this module. All archive changes are composed in memory.
"""
import hashlib
import re

from fighter_archive import Archive, store
from fighter_assets import AssetError, unpack, MAX_ASSET
from fighter_cinematics import Cinematics
from fighter_elf import Model, ModelError
from fighter_entity import Entities, Entity
from fighter_geometry import Geometry
from fighter_registry import fingerprint, key
from fighter_render import RenderProgram
from fighter_resource_files import appearance_source, resource_name
from fighter_rig import Skeleton
from fighter_skin import Skin
from fighter_xsh import Textures
from fighter_model_compile import compile_geometry, layout

MAX_APPEARANCE_BYTES = 256 * 1024**2


def require(condition, message):
    if not condition:
        raise AssetError(message)


def normalized_import(name):
    # Only per-object allocation identity and four-character texture identity
    # may differ. Shader/state expressions must otherwise match the own dump.
    return re.sub(r'SHAPENAME=[A-Za-z0-9_]{4},1;', 'SHAPENAME=XXXX,1;',
                  re.sub(r'UID=[0-9]+;', 'UID=0;', name))


class Appearance:
    def __init__(self, identifier, source, files, baseline, donor_model, budget=MAX_APPEARANCE_BYTES):
        key(identifier); appearance_source(source)
        require(set(files) == {'model', 'textures', 'face'}, 'Appearance needs all three data resources')
        for part, data in files.items():
            require(hashlib.sha256(data).hexdigest() == source[part]['sha256'], 'Appearance source hash changed')
        require(type(budget) is int and 0 < budget <= MAX_APPEARANCE_BYTES, 'Appearance data budget is exhausted')
        decoded, remaining = {}, budget
        for part, data in files.items():
            decoded[part] = unpack(data, maximum=min(MAX_ASSET, remaining))
            remaining -= len(decoded[part])
        model, face = Model(decoded['model']), Model(decoded['face'])
        geometry, skin, skeleton = Geometry(model), Skin(model), Skeleton(model)
        textures = Textures(decoded['textures'])
        require(set(textures.controls.values()) <= baseline.texture_controls,
                'Appearance texture controls need a verified retail template')
        geometry.require_textures(textures, baseline.shared_shapes)
        require(not set(map(normalized_import, model.imports | face.imports)) - baseline.imports,
                'Appearance imports require an unsupported native data library')
        programs = {RenderProgram(model, model.export_offset(name)).sha256
                    for name in model.exports if name.startswith('__RM:::')}
        require(programs <= baseline.programs, 'Appearance uses an unreviewed native render program')
        donor = Skeleton(Model(unpack(baseline.models.read(donor_model + '.o'))))
        require(skeleton.topology_sha256 == donor.topology_sha256 and skeleton.permutation == donor.permutation,
                'Appearance skeleton differs from its inherited animation rig')
        require(decoded['face'] == unpack(baseline.models.read(donor_model + '_F.o')),
                'Authored face curves need the pose-palette adapter; reuse the verified donor face for now')
        compiled, template_name = baseline.compile_model(model, geometry, skeleton, resource_name(identifier))
        Geometry(compiled).require_textures(textures, baseline.shared_shapes)
        decoded['model'] = compiled.data
        self.identifier, self.donor = identifier, source['donor']
        self.texture_shapes = {image['name']: image['content_sha256'] for image in textures.images}
        self.name, self.donor_model = resource_name(identifier), donor_model
        self.source_sha256 = fingerprint(source)
        self.baseline_sha256 = baseline.sha256
        self.files = {self.name + suffix: store(decoded[part])
                      for part, suffix in [('model', '.o'), ('textures', '.xsh'), ('face', '_F.o')]}
        self.byte_count = sum(map(len, self.files.values()))
        require(self.byte_count <= budget, 'Composed appearance data exceeds its aggregate budget')
        self.summary = {'resource': identifier, 'native_name': self.name, 'donor': self.donor,
                        'source_sha256': self.source_sha256, 'baseline_sha256': baseline.sha256,
                        'decoded_sha256': {part: hashlib.sha256(data).hexdigest() for part, data in decoded.items()},
                        'topology_sha256': skeleton.topology_sha256, 'face_policy': 'verified-retail-donor',
                        'render_control_policy': 'verified-retail-template', 'render_template': template_name,
                        'texture_control_policy': 'verified-retail-template',
                        'runtime_ready': False, 'render_parameters_validated': False}


class AppearanceBaseline:
    def __init__(self, files, pins):
        expected = {'models': 'v2ip_sha256', 'shared': 'blingfx_sha256', 'entities': 'entities_sha256',
                    'cinematics': 'nis_sha256', 'banks': 'v2ta_sha256'}
        require(set(files) == set(expected), 'Incomplete original appearance resources')
        for name, pin in expected.items():
            require(isinstance(files[name], bytes) and hashlib.sha256(files[name]).hexdigest() == pins.get(pin),
                    'Appearance adapter requires hash-verified original ' + name)
        self.sha256 = fingerprint({name: pins[pin] for name, pin in expected.items()})
        self.models = Archive(files['models'])
        self.entities = Entities(files['entities'], pins['entities_sha256'])
        self.cinematic_archive = Archive(files['cinematics'])
        xml = unpack(self.cinematic_archive.read('assets/IntroExtro.xml'))
        self.cinematics = Cinematics(xml, pins['intro_extro_sha256'])
        self.banks = {entry.name[:-4] for entry in Archive(files['banks']).entries if entry.name.endswith('.viv')}
        shared = Textures(unpack(Archive(files['shared']).read('assets/blingtex.xsh')))
        self.shared_shapes = {image['name'] for image in shared.images}
        self.texture_controls = set(shared.controls.values())
        self.texture_shapes = {}
        for textures in [shared] + [Textures(unpack(self.models.read(entry.name)))
                                   for entry in self.models.entries if entry.name.endswith('.xsh')]:
            self.texture_controls.update(textures.controls.values())
            for image in textures.images:
                self.texture_shapes.setdefault(image['name'], set()).add(image['content_sha256'])
        self.programs, self.imports, self.templates = set(), set(), {}
        for entry in self.models.entries:
            if not entry.name.endswith('.o'):
                continue
            model = Model(unpack(self.models.read(entry.name)))
            self.imports.update(map(normalized_import, model.imports))
            self.programs.update(RenderProgram(model, model.export_offset(name)).sha256
                                 for name in model.exports if name.startswith('__RM:::'))
            if any(name.startswith('__Model:::') for name in model.exports):
                try:
                    geometry, skeleton = Geometry(model), Skeleton(model)
                    Skin(model)
                except ModelError:
                    continue  # Unsupported original layouts are not templates.
                signature = fingerprint([layout(geometry), skeleton.topology_sha256])
                self.templates.setdefault(signature, []).append((entry.name, model))

    def compile_model(self, model, geometry, skeleton, native_name=None):
        signature = fingerprint([layout(geometry), skeleton.topology_sha256])
        failures = []
        for name, template in sorted(self.templates.get(signature, []), key=lambda pair: pair[0]):
            try:
                return compile_geometry(model, template, native_name), name
            except ModelError as error:
                failures.append(str(error))
        detail = failures[0] if failures else 'No verified retail template has this material/render layout'
        raise AssetError('Appearance geometry cannot be compiled: ' + detail)

    def compose(self, appearances):
        require(isinstance(appearances, dict) and len(appearances) <= 16384, 'Invalid appearance resource set')
        additions, entities, cinematics = {}, [], []
        shapes = {name: (set(values), 'retail') for name, values in self.texture_shapes.items()}
        used = 0
        for identifier, appearance in sorted(appearances.items()):
            require(type(appearance) is Appearance and appearance.identifier == identifier
                    and appearance.baseline_sha256 == self.sha256, 'Appearance belongs to a different resource or baseline')
            require(not additions.keys() & appearance.files.keys(), 'Appearance resource names collide')
            for name, digest in appearance.texture_shapes.items():
                if name in shapes:
                    values, owner = shapes[name]
                    require(values == {digest}, 'Texture shape ' + name + ' conflicts between ' + owner
                            + ' and ' + identifier + '; rename the shape in both model and texture data')
                else:
                    shapes[name] = ({digest}, identifier)
            used += appearance.byte_count
            require(used <= MAX_APPEARANCE_BYTES, 'Appearance snapshot exceeds its aggregate data budget')
            additions.update(appearance.files)
            entities.append(Entity(appearance.name, appearance.name, appearance.name))
            cinematics.append(self.cinematics.inherit(appearance.name, appearance.donor_model))
        # Validate registrations before allocating the much larger model archive.
        entity = self.entities.compose(entities)
        cinematic = self.cinematics.compose(cinematics, self.banks)
        return {'assets/v2ip.viv': self.models.compose(additions=additions), 'assets/entity.xml': entity,
                'assets/nis.viv': self.cinematic_archive.compose(replacements={'assets/IntroExtro.xml': store(cinematic)})}

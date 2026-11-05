"""Pixel-only portrait texture compilation against an original UI template.

UI movie-local numeric texture IDs are separate from model shape identities.
This low-level compiler does not register movies, grid frames or a pack source.
The caller must derive the template and digest from a hash-verified original
screens archive. All original controls/IDs/layout bytes are retained.
"""
import hashlib
import re

from fighter_archive import Archive, store
from fighter_assets import unpack
from fighter_registry import fingerprint, key
from fighter_resource_files import PORTRAIT_PARTS, portrait_source, resource_name
from fighter_xsh import Textures, require


class UITextures(Textures):
    @staticmethod
    def _name_bytes(value):
        require(isinstance(value, str) and len(value) == 4
                and re.fullmatch(r'[1-9][0-9]{0,3} *', value)
                and str(int(value)).ljust(4) == value,
                'UI texture ID must be a canonical space-padded positive number')
        return value.encode('ascii')

    @staticmethod
    def _material_name_bytes(value):
        return value.rstrip().encode('ascii').ljust(4, b'\0')

    def appended(self, images):
        """Append single-image typed UI containers, preserving existing pixels."""
        import struct
        require(type(images) is dict and len(self.images) + len(images) <= 4096, 'UI image directory exceeds capacity')
        if not images:
            return self.data
        directory_end = 16 + len(self.images) * 8
        growth = (len(images) * 8 + 127) & ~127
        output = bytearray(self.data[:directory_end] + bytes(growth) + self.data[directory_end:])
        struct.pack_into('<I', output, 8, len(self.images) + len(images))
        for index in range(len(self.images)):
            at = 20 + index * 8
            struct.pack_into('<I', output, at, struct.unpack_from('<I', self.data, at)[0] + growth)
        for index, (identifier, image) in enumerate(sorted(images.items()), len(self.images)):
            require(type(identifier) is int and 1 <= identifier <= 9999 and type(image) is UITextures
                    and len(image.images) == 1, 'Expected one owned numeric UI image')
            name = str(identifier).ljust(4)
            require(name not in self.name_sites, 'UI image identity collides')
            original_name = image.images[0]['name']
            root = struct.unpack_from('<I', image.data, 20)[0]
            payload = bytearray(image.data[root:])
            for site in image.name_sites[original_name][1:]:
                payload[site - root:site - root + 4] = self._material_name_bytes(name)
            # Preserve the source raster's alignment, not just its header's.
            # Original UI roots can be112 mod128 with pixels16 bytes later.
            output.extend(bytes((root - len(output)) % 128)); offset = len(output); output.extend(payload)
            struct.pack_into('<4sI', output, 16 + index * 8, self._name_bytes(name), offset)
        struct.pack_into('<I', output, 4, len(output))
        result = bytes(output); UITextures(result)
        return result


class PortraitTextureTemplate:
    def __init__(self, template, expected_sha256):
        require(isinstance(template, bytes) and hashlib.sha256(template).hexdigest() == expected_sha256,
                'Portrait needs its verified original texture template')
        self.template = UITextures(template)
        require(all(image['kind'] in (0x60, 0x61, 0x62, 0x7d) for image in self.template.images),
                'Indexed UI portraits need a separate palette adapter')
        self.sha256 = expected_sha256

    def compile(self, source):
        authored = UITextures(source)
        images = {image['name']: image for image in authored.images}
        require(set(images) == set(self.template.name_sites), 'Portrait tiles differ from the selected layout')
        require(authored.controls == self.template.controls,
                'Portrait crop/material controls differ from the selected layout')
        output = bytearray(self.template.data)
        for target in self.template.images:
            image = images[target['name']]
            require(all(image[field] == target[field] for field in
                        ('kind', 'width', 'height', 'swizzled', 'pixels_bytes')),
                    'Portrait tile format or dimensions differ from the selected layout')
            destination, origin, size = target['pixels_offset'], image['pixels_offset'], image['pixels_bytes']
            output[destination:destination + size] = source[origin:origin + size]
        compiled = bytes(output)
        UITextures(compiled)
        return compiled

    def metadata(self):
        return {'template_sha256': self.sha256,
                'tiles': [{key: image[key] for key in ('name', 'kind', 'width', 'height')}
                          for image in self.template.images],
                'control_policy': 'original-template-pixels-only',
                'movie_registration_validated': False, 'runtime_ready': False}


def variant_path(part, selection):
    require(part in PORTRAIT_PARTS and type(selection) is int and 0 <= selection <= 0x7ffffffe,
            'Invalid portrait variant or selection identity')
    role, count = part.split('_')
    stem = f'p_cf_{selection + 1}_{count}' if role == 'selector' else f't_MS_{selection}_{count}'
    return ('screens/portrait/p_CF/' if role == 'selector' else 'screens/portrait/t_MS/') + stem + '.big', stem


class PortraitBaseline:
    def __init__(self, screens, expected_sha256):
        require(hashlib.sha256(screens).hexdigest() == expected_sha256,
                'Portrait adapter requires hash-verified original screens')
        self.archive, self.sha256 = Archive(screens), expected_sha256


class Portrait:
    def __init__(self, identifier, source, files, baseline, donor_selection, budget=16 * 1024**2):
        key(identifier); portrait_source(source)
        require(type(baseline) is PortraitBaseline and set(files) == set(PORTRAIT_PARTS),
                'Portrait needs an original baseline and all six texture variants')
        require(type(budget) is int and budget > 0, 'Portrait resource budget is exhausted')
        self.identifier, self.donor = identifier, source['donor']
        self.donor_selection = donor_selection
        self.source_sha256, self.baseline_sha256 = fingerprint(source), baseline.sha256
        self.files, summaries = {}, {}
        remaining = budget
        for part in PORTRAIT_PARTS:
            require(hashlib.sha256(files[part]).hexdigest() == source[part]['sha256'], 'Portrait source hash changed')
            path, stem = variant_path(part, donor_selection)
            movie = Archive(unpack(baseline.archive.read(path)))
            expected = {stem + suffix for suffix in ('.apt', '.const', '.o', '.xsh')}
            require({entry.name for entry in movie.entries} == expected, 'Unsupported original portrait envelope')
            require(not any(stem.encode('ascii') in movie.read(name) for name in expected),
                    'Portrait template has embedded filename references')
            template_bytes = unpack(movie.read(stem + '.xsh'))
            template = PortraitTextureTemplate(template_bytes, hashlib.sha256(template_bytes).hexdigest())
            authored = unpack(files[part], maximum=min(remaining, 16 * 1024**2))
            compiled = template.compile(authored)
            remaining -= len(authored)
            new = resource_name(identifier) + '_' + part
            # The movie container is RefPack-wrapped; its XSH member is raw.
            # This loader does not perform another decompression at that leaf.
            output = store(movie.compose(replacements={stem + '.xsh': compiled},
                                         renames={name: new + name[len(stem):] for name in expected}))
            require(len(output) <= remaining, 'Composed portrait exceeds its resource budget')
            remaining -= len(output)
            self.files[f'portraits/{resource_name(identifier)}/{part}.big'] = output
            summaries[part] = template.metadata()
        self.byte_count = budget - remaining
        self.summary = {'resource': identifier, 'donor': self.donor,
                        'donor_selection': donor_selection, 'source_sha256': self.source_sha256,
                        'baseline_sha256': self.baseline_sha256, 'variants': summaries,
                        'grid_policy': 'requires-owned-grid-composition', 'runtime_ready': False}


def apply_portraits(screens, bindings, resources):
    """Replace only already-owned custom aliases; original paths remain intact."""
    archive, replacements = Archive(screens), {}
    for selection, (identifier, files) in sorted(bindings.items()):
        key(identifier)
        for part in PORTRAIT_PARTS:
            path, stem = variant_path(part, selection)
            require(path.lower() in archive.by_name and path not in replacements,
                    'Authored portrait needs one owned selection alias')
            relative = f'portraits/{resource_name(identifier)}/{part}.big'
            require(relative in resources and relative in files, 'Missing compiled portrait variant')
            data = resources[relative]
            require(hashlib.sha256(data).hexdigest() == files[relative], 'Compiled portrait receipt differs')
            movie = Archive(unpack(data))
            old = resource_name(identifier) + '_' + part
            expected = {old + suffix for suffix in ('.apt', '.const', '.o', '.xsh')}
            require({entry.name for entry in movie.entries} == expected, 'Invalid compiled portrait envelope')
            replacements[path] = store(movie.compose(renames={name: stem + name[len(old):] for name in expected}))
    return archive.compose(replacements=replacements)

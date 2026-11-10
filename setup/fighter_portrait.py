"""Pixel-only portrait texture compilation against an original UI template.

UI movie-local numeric texture IDs are separate from model shape identities.
This low-level compiler does not register movies, grid frames or a pack source.
The caller must derive the template and digest from a hash-verified original
screens archive. All original controls/IDs/layout bytes are retained.
"""
import hashlib
import re
import struct

from fighter_archive import Archive, store
from fighter_assets import unpack
from fighter_registry import fingerprint, key
from fighter_resource_files import (PORTRAIT_PARTS,PORTRAIT_EXTENDED_PARTS,PORTRAIT_GRID_PARTS,PORTRAIT_ALL_PARTS,
                                    portrait_parts,portrait_source,resource_name,portrait_target)
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

    def single_image(self,identifier):
        """Canonical one-image UI source; no atlas pointers leave this container."""
        name=str(identifier).ljust(4)
        require(name in self.name_sites,'UI atlas has no requested image')
        root=struct.unpack_from('<I',self.data,self.name_sites[name][0]+4)[0]
        at=root
        for _ in range(64):
            require(0<=at<=len(self.data)-16,'Truncated UI image attachment')
            word,=struct.unpack_from('<I',self.data,at)
            kind,delta=word&255,word>>8
            if kind==0x70 and not delta:break
            require(delta>0 and at+delta>at and at+delta<=len(self.data)-16,'Invalid UI image attachment chain')
            at+=delta
        else:raise ValueError('UI image attachment chain exceeds budget')
        payload=bytearray(self.data[root:at+16])
        for site in self.name_sites[name][1:]:
            require(root<=site<=at+12,'UI image material name escapes its attachment chain')
            payload[site-root:site-root+4]=b'1\0\0\0'
        header=bytearray(self.data[:16]);struct.pack_into('<II',header,4,112+len(payload),1)
        result=bytes(header)+struct.pack('<4sI',b'1   ',112)+bytes(88)+payload
        parsed=UITextures(result)
        require(len(parsed.images)==1 and parsed.images[0]['name']=='1   ','Canonical UI image differs')
        return result

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
    require(part in PORTRAIT_EXTENDED_PARTS and type(selection) is int and 0 <= selection <= 0x7ffffffe,
            'Invalid portrait variant or selection identity')
    role,count=part.rsplit('_',1)
    prefix,base,increment={
        'selector':('screens/portrait/p_CF/','p_cf_',1),
        'result':('screens/portrait/t_MS/','t_MS_',0),
        'selector_logo':('screens/portrait/l_CF/','l_CF_',0),
        'result_logo':('screens/portrait/','l_MS_',0),
        'loading':('screens/match/3_fighters/','p_ML_',1),
        'loading_logo':('screens/match/3_fighters/','l_ML_',0)}[role]
    stem=f'{base}{selection+increment}_{count}'
    return prefix+stem+'.big',stem


class PortraitBaseline:
    def __init__(self, screens, expected_sha256):
        require(hashlib.sha256(screens).hexdigest() == expected_sha256,
                'Portrait adapter requires hash-verified original screens')
        self.archive, self.sha256 = Archive(screens), expected_sha256

    def grid_template(self,part):
        require(part in PORTRAIT_GRID_PARTS,'Unsupported thumbnail state role')
        count=int(part.rsplit('_',1)[1][0])
        if not hasattr(self,'_grid_templates'):self._grid_templates={}
        if count not in self._grid_templates:
            stem=f'chooseF{count}'
            movie=Archive(unpack(self.archive.read(f'screens/battle/{stem}.big')))
            data=UITextures(unpack(movie.read(stem+'.xsh'))).single_image(1 if count==2 else 3)
            self._grid_templates[count]=data
        return self._grid_templates[count]

    def matching_layouts(self, files, candidates):
        """Find exact six-slot layouts independently of combat/appearance donors.

        This suggests templates, never substitutes their pixels. The ordinary
        Portrait compiler still validates and composes the selected candidate.
        """
        require(type(files) is dict and set(files) in (set(PORTRAIT_PARTS),set(PORTRAIT_EXTENDED_PARTS),set(PORTRAIT_ALL_PARTS))
                and type(candidates) is dict and 0 < len(candidates) <= 4096
                and all(type(name) is str and type(selection) is int and 0 <= selection < 0x7fffffff
                        for name, selection in candidates.items()),
                'Portrait layout matching needs six files and bounded candidates')

        def profile(texture):
            return {'controls': texture.controls, 'tiles': {image['name']: {
                field: image[field] for field in ('kind', 'width', 'height', 'swizzled', 'pixels_bytes')}
                for image in texture.images}}

        parts=PORTRAIT_ALL_PARTS if len(files)==24 else PORTRAIT_EXTENDED_PARTS if len(files)==18 else PORTRAIT_PARTS
        authored = {part: profile(UITextures(unpack(files[part]))) for part in parts}
        if not hasattr(self, '_layout_profiles'):
            self._layout_profiles = {}
        matches = []
        for identifier, selection in sorted(candidates.items()):
            cache_key=(selection,parts)
            if cache_key not in self._layout_profiles:
                try:
                    layouts = {}
                    for part in parts:
                        if part in PORTRAIT_GRID_PARTS:
                            data=self.grid_template(part)
                            layouts[part]=profile(PortraitTextureTemplate(data,hashlib.sha256(data).hexdigest()).template)
                            continue
                        path, stem = variant_path(part, selection)
                        movie = Archive(unpack(self.archive.read(path)))
                        data = unpack(movie.read(stem + '.xsh'))
                        template = PortraitTextureTemplate(data, hashlib.sha256(data).hexdigest())
                        layouts[part] = profile(template.template)
                    self._layout_profiles[cache_key] = layouts
                except ValueError:
                    self._layout_profiles[cache_key] = None
            if self._layout_profiles[cache_key] == authored:
                matches.append(identifier)
        return matches


class Portrait:
    def __init__(self, identifier, source, files, baseline, donor_selection, budget=16 * 1024**2):
        key(identifier); portrait_source(source)
        if source['format']=='eagl-portrait-png-1':
            from fighter_ui_art import render
            native,hd,receipt=render(source,files,baseline,donor_selection)
            internal={'format':'eagl-portrait-3','donor':source['donor'],**{
                part:{'path':part+'.xsh','sha256':hashlib.sha256(raw).hexdigest()} for part,raw in native.items()}}
            self.__init__(identifier,internal,native,baseline,donor_selection,budget)
            self.source_sha256=fingerprint(source);self.summary['source_sha256']=self.source_sha256
            self.summary['png_import']=receipt;self.hd_images=hd
            self.byte_count+=sum(map(len,hd.values()))
            require(self.byte_count<=budget,'Compiled PNG portraits exceed their resource budget')
            return
        parts=portrait_parts(source)
        require(type(baseline) is PortraitBaseline and set(files) == set(parts),
                'Portrait needs an original baseline and all six texture variants')
        require(type(budget) is int and budget > 0, 'Portrait resource budget is exhausted')
        self.identifier, self.donor = identifier, source['donor']
        self.donor_selection = donor_selection
        self.source_sha256, self.baseline_sha256 = fingerprint(source), baseline.sha256
        self.files, summaries = {}, {}
        remaining = budget
        for part in parts:
            require(hashlib.sha256(files[part]).hexdigest() == source[part]['sha256'], 'Portrait source hash changed')
            if part in PORTRAIT_GRID_PARTS:
                original=baseline.grid_template(part)
                template=PortraitTextureTemplate(original,hashlib.sha256(original).hexdigest())
                authored=unpack(files[part],maximum=min(remaining,16*1024**2))
                compiled=template.compile(authored);remaining-=len(authored)+len(compiled)
                require(remaining>=0,'Composed grid state exceeds its resource budget')
                self.files[portrait_target(identifier,part)]=compiled;summaries[part]=template.metadata()
                continue
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
            self.files[portrait_target(identifier,part)] = output
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
        prefix=f'portraits/{resource_name(identifier)}/'
        parts=tuple(part for part in PORTRAIT_EXTENDED_PARTS if prefix+part+'.big' in files)
        require(set(parts) in (set(PORTRAIT_PARTS),set(PORTRAIT_EXTENDED_PARTS)),'Incomplete compiled portrait role set')
        for part in parts:
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

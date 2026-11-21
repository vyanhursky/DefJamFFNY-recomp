"""Typed Team-card pixels over verified original movies, geometry and materials."""
import hashlib
import io
from fighter_archive import Archive, store
from fighter_assets import unpack
from fighter_resource_files import TEAM_PARTS, TEAM_IMAGE_ROLES, portrait_target, resource_name, require


def template(baseline, selection, part):
    from fighter_portrait import variant_path, UITextures
    from fighter_ui_model import UIModel
    from fighter_caf_portrait import tiles
    path, stem = variant_path(part, selection)
    movie = Archive(unpack(baseline.archive.read(path)))
    expected = {stem + suffix for suffix in ('.apt', '.const', '.o', '.xsh')}
    require({entry.name for entry in movie.entries} == expected, 'Unsupported Team movie envelope')
    require(not any(stem.encode() in movie.read(name) for name in expected), 'Embedded Team filename reference')
    original = unpack(movie.read(stem + '.xsh'))
    geometry = unpack(movie.read(stem + '.o'))
    texture = UITextures(original)
    model = UIModel(geometry, hashlib.sha256(geometry).hexdigest())
    rows = tiles(model, texture)
    require(set(rows) == ({1} if part == 'team_portrait' else {1, 3}), 'Unsupported Team image states')
    return movie, stem, original, texture, rows


def reference(baseline, selection, role):
    from fighter_ui_art import _retail_tile
    part = 'team_portrait' if role == 'team_portrait' else 'team_icon'
    _, _, _, texture, rows = template(baseline, selection, part)
    row = rows[3 if role == 'team_icon_selected' else 1]
    return _retail_tile(texture, row['image']).resize(row['logical'])


def render(images, baseline, selection, scale):
    from PIL import Image, ImageOps
    from fighter_portrait import PortraitTextureTemplate
    from fighter_ui_art import native_hash, _retail_tile
    native, hd, receipts = {}, {}, {}
    for part in TEAM_PARTS:
        roles = ('team_portrait',) if part == 'team_portrait' else ('team_icon', 'team_icon_selected')
        if not any(role in images for role in roles):
            continue
        _, _, original, texture, rows = template(baseline, selection, part)
        output = bytearray(original); canvases = {}; sources = {}
        for identity, row in rows.items():
            role = 'team_icon_selected' if identity == 3 else part
            picture = images.get(role)
            if picture is None and identity == 3 and part in images:
                picture = images[part]
                # Match the native muted picked state when no separate PNG is supplied.
                alpha = picture.getchannel('A')
                picture = ImageOps.colorize(ImageOps.grayscale(picture), '#12120c', '#c6c1a0').convert('RGBA')
                picture.putalpha(alpha); source = 'derived picked state'
            elif picture is None:
                picture = _retail_tile(texture, row['image']).crop((0, 0, *row['logical']))
                source = 'donor'
            else:
                source = role
            tile = row['image']; width, height = row['logical']
            def canvas(factor):
                if source == 'donor':
                    return _retail_tile(texture, tile).resize((tile['width'] * factor, tile['height'] * factor), Image.Resampling.LANCZOS)
                size = (width * factor, height * factor)
                fitted = (ImageOps.contain if part == 'team_portrait' else ImageOps.fit)(picture, size, Image.Resampling.LANCZOS)
                out = Image.new('RGBA', size)
                out.paste(fitted, ((size[0] - fitted.width)//2, (size[1] - fitted.height)//2))
                # Team's logical size is a display rectangle, not a padded
                # pixel extent. Original movies sample the full raster.
                return out.resize((tile['width'] * factor, tile['height'] * factor), Image.Resampling.LANCZOS)
            require(tile['kind'] in (0x60, 0x61, 0x62) and not tile['swizzled'], 'Unsupported Team raster')
            encoded = io.BytesIO(); canvas(1).save(encoded, format='DDS', pixel_format={0x60:'DXT1',0x61:'DXT3',0x62:'DXT5'}[tile['kind']])
            pixels = original[tile['pixels_offset']:tile['pixels_offset'] + tile['pixels_bytes']] if source == 'donor' else encoded.getvalue()[128:]
            require(len(pixels) == tile['pixels_bytes'], 'Team raster encoder size differs')
            at = tile['pixels_offset']; output[at:at+len(pixels)] = pixels
            canvases[tile['name']] = canvas(scale); sources[tile['name']] = source
        native[part] = PortraitTextureTemplate(original, hashlib.sha256(original).hexdigest()).compile(bytes(output))
        from fighter_portrait import UITextures
        summary = []
        for tile in UITextures(native[part]).images:
            digest = native_hash(UITextures(native[part]), tile)
            if scale > 1:
                encoded = io.BytesIO(); canvases[tile['name']].save(encoded, format='PNG'); png = encoded.getvalue()
                require(digest not in hd or hd[digest] == png, 'Conflicting Team state HD pixels'); hd[digest] = png
            summary.append(dict(source=sources[tile['name']], state=tile['name'].strip(), native_id=digest,
                                native_size=[tile['width'],tile['height']], hd_size=list(canvases[tile['name']].size)))
        receipts[part] = dict(source=part, tiles=summary)
    return native, hd, receipts


def compile_movies(identifier, native, baseline, selection):
    from fighter_portrait import PortraitTextureTemplate
    files, summaries = {}, {}
    for part, raw in native.items():
        require(part in TEAM_PARTS, 'Unsupported compiled Team role')
        movie, stem, original, _, _ = template(baseline, selection, part)
        checked = PortraitTextureTemplate(original, hashlib.sha256(original).hexdigest())
        compiled = checked.compile(raw); new = resource_name(identifier) + '_' + part
        files[portrait_target(identifier, part)] = store(movie.compose(
            replacements={stem+'.xsh': compiled},
            renames={entry.name:new+entry.name[len(stem):] for entry in movie.entries}))
        summaries[part] = checked.metadata()
    return files, summaries

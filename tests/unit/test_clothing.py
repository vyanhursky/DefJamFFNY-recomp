"""Custom Story clothing (docs/custom-clothing.md): the pack compiler, the mod manager's Clothing
packs, and the game side (src/patches/clothing.c with src/hooks/pc_sod.c and pc_big.c) against a
synthetic Clothing database, synthetic archives and synthetic guest memory. No game bytes.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'setup'))

import clothing_pack as cp  # noqa: E402
from fighter_sod import Database, name_hash  # noqa: E402
from fighter_xsh import Textures  # noqa: E402


# ---- a synthetic Clothing database ------------------------------------------------------------

CLOTHING = name_hash('Clothing')
VENUE = name_hash('Venue')
LIST = 0x03000000
FIELDS = {'Model': (1, 2), 'Variant': (2, 1), 'Color': (3, LIST), 'Cost': (4, 2), 'DisplayName': (5, 1),
          'Fit': (6, LIST), 'Order': (7, 2), 'Type': (8, 4)}
# name, model, variant, colours, cost, type
ROWS = [('Jeans_Base', 27, 'A04', 2, 45, 5), ('T_Base', 7, 'A01', 3, 15, 4), ('Hat_Other', 3, 'B01', 1, 20, 12)]


def clothing_database():
    image = bytearray(24)
    strings = [None]

    def emit(data):
        while len(image) % 4:
            image.append(0)
        offset = len(image)
        image.extend(data)
        return offset

    def words(values):
        return struct.pack(f'<{len(values)}I', *values)

    def intern(text):
        strings.append(text)
        return len(strings) - 1

    def index(tag, keys, values, stride):
        head = ([] if tag is None else [tag]) + [len(values), stride]
        return emit(words(head + (keys if stride else []) + [w for v in values for w in v]))

    schema = {CLOTHING: (0, 0x02000000), VENUE: (0, 0x02000000)}
    schema.update({CLOTHING ^ name_hash(name): value for name, value in FIELDS.items()})
    keys = sorted(schema)
    schema_at = index(int.from_bytes(b'SKMA', 'little'), keys, [schema[k] for k in keys], 2)
    tables = sorted([CLOTHING, VENUE])
    data_at = emit(words([int.from_bytes(b'DATA', 'little'), 2, 1] + tables + [0, 0]))
    records, types = [], []
    for name, model, variant, colours, cost, kind in ROWS:
        at = len(image) + (-len(image) % 4)
        # record (9 words), colour list (count + pointers), colour records (3 words), fit list (1 fit)
        colour_list = at + 36
        colour_records = colour_list + 4 + 4 * colours
        fit_list = colour_records + 12 * colours
        fit_record = fit_list + 8
        row = [intern(name), model, intern(variant), colour_list, cost, intern('Display ' + name), fit_list, 100, kind]
        row += [colours] + [colour_records + 12 * c for c in range(colours)]
        for c in range(colours):
            row += [0, intern(f'Colour{c}'), c + 1]
        row += [1, fit_record, 0, 0, 0]
        assert emit(words(row)) == at
        records.append(at)
        types.append(kind)
    venue_record = emit(words([intern('Venue_One'), 0]))
    pairs = sorted((name_hash(r[0]), o) for r, o in zip(ROWS, records))
    name_index = index(CLOTHING, [p[0] for p in pairs], [(p[1],) for p in pairs], 1)
    type_key = CLOTHING ^ name_hash('Type')
    by_type = sorted(zip(types, records))
    type_index = index(type_key, [t for t, _ in by_type], [(o,) for _, o in by_type], 1)
    record_list = index(name_hash('ClothingRows'), [], [(o,) for o in records], 0)
    table_at = emit(words([CLOTHING, 0, 0, len(records)]))
    primary = index(None, sorted([CLOTHING, type_key]),
                    [(name_index if k == CLOTHING else type_index,) for k in sorted([CLOTHING, type_key])], 1)
    secondary = index(None, [name_hash('ClothingRows')], [(record_list,)], 1)
    struct.pack_into('<II', image, table_at + 4, primary, secondary)
    venue_name = index(VENUE, [name_hash('Venue_One')], [(venue_record,)], 1)
    venue_at = emit(words([VENUE, 0, 0, 1]))
    venue_primary = index(None, [VENUE], [(venue_name,)], 1)
    venue_secondary = index(None, [], [], 1)
    struct.pack_into('<II', image, venue_at + 4, venue_primary, venue_secondary)
    headers = {CLOTHING: table_at, VENUE: venue_at}
    for i, key in enumerate(tables):
        struct.pack_into('<I', image, data_at + 12 + 8 + i * 4, headers[key])
    offsets = [0] + [emit(s.encode('ascii') + b'\0') for s in strings[1:]]
    strings_at = emit(words([int.from_bytes(b'STRT', 'little'), len(strings)]
                            + [w for s, o in zip(strings, offsets) for w in ((name_hash(s) if s else 0), o)]))
    struct.pack_into('<4s5I', image, 0, b'SODB', 2, 0x1234, schema_at, data_at, strings_at)
    return bytes(image)


def ranks(data):
    """{row name: rank} from the Clothing name index, and the table's rank in the directory."""
    db = Database(data)
    header = db.directory[CLOTHING]
    primary = db.index(db.word(header + 4))
    ordered = db.index(primary.values[primary.keys.index(CLOTHING)][0], tagged=True)
    names = {db.symbol(db.word(p)): r for r, (p,) in enumerate(ordered.values)}
    return names, sorted(db.directory).index(CLOTHING), db


def test_synthetic_database_is_valid():
    names, table_rank, _ = ranks(clothing_database())
    assert set(names) == {r[0] for r in ROWS} and table_rank == sorted([CLOTHING, VENUE]).index(CLOTHING)


# ---- the pack compiler's own parts ----------------------------------------------------------

def shpx(width=32, height=32, alpha=(0x80, 0xFF)):
    """A one-image indexed SHPX texture with two alpha classes."""
    pixels = bytes((i % 2) * 128 + (i % 7) for i in range(width * height))
    palette = b''.join(bytes((c, 255 - c, c // 2, alpha[0] if i < 128 else alpha[1])) for i, c in enumerate(range(256)))
    image_at = 24
    palette_at = image_at + 16 + len(pixels)
    size = palette_at + 16 + len(palette)
    data = bytearray()
    data += b'SHPX' + struct.pack('<II', size, 1) + b'G354'
    data += b'0000' + struct.pack('<I', image_at)
    data += bytes([0x7b]) + (palette_at - image_at).to_bytes(3, 'little') + struct.pack('<HH', width, height) + bytes(8)
    data += pixels
    data += bytes([0x2a, 0, 0, 0]) + struct.pack('<H', 256) + bytes(10)
    data += palette
    assert len(data) == size
    Textures(bytes(data))
    return bytes(data)


def png(width, height, colour=(200, 10, 10)):
    from PIL import Image
    buffer = io.BytesIO()
    Image.new('RGB', (width, height), colour).save(buffer, format='PNG')
    return buffer.getvalue()


def test_limits_match_the_game():
    header = (ROOT / 'src/patches/clothing.h').read_text()
    assert int(re.search(r'CLOTHING_MAX_ITEMS (\d+)', header).group(1)) == cp.MAX_ITEMS
    assert int(re.search(r'CLOTHING_MAX_NAME (\d+)', header).group(1)) == cp.MAX_NAME


def test_paint_keeps_format_size_and_material_alpha():
    from fighter_appearance_authoring import raster
    native = shpx()
    painted = cp.paint(native, png(32, 32))
    before, after = Textures(native), Textures(painted)
    assert len(painted) == len(native) and before.controls == after.controls
    old, new = raster(before, before.images[0]), raster(after, after.images[0])
    assert old.getchannel('A').tobytes() == new.getchannel('A').tobytes()
    r, g, b, _ = new.getpixel((5, 5))
    assert r > 150 and g < 60 and b < 60
    assert cp.paint(native, png(64, 64)) == cp.paint(native, png(64, 64))      # 2x art is downscaled
    with pytest.raises(cp.ClothingError, match='must be 32x32'):
        cp.paint(native, png(48, 32))


def test_set_digest_follows_the_packs_not_their_order(tmp_path):
    a, b = write_pack(tmp_path / 'a'), write_pack(tmp_path / 'b')
    digest = cp.set_digest([a, b])
    assert digest == cp.set_digest([b, a]) and re.fullmatch('[0-9a-f]{64}', digest)
    assert cp.set_digest([a]) != digest
    value = json.loads((b / cp.MANIFEST).read_text())
    value['items'][0]['price'] = 7
    (b / cp.MANIFEST).write_text(json.dumps(value))
    assert cp.set_digest([a, b]) != digest


def test_archive_and_thumbnail_helpers():
    members = {'b.xsh': b'\x01' * 300, 'a.big': b'abc'}
    archive = cp.RetailArchive(cp.build_archive(members))
    assert sorted(archive.names) == ['a.big', 'b.xsh'] and archive.read('B.XSH') == members['b.xsh']
    thumb = b'xxV2TN_121_0027_A04_01.aptxxV2TN_121_0027_A04_01.o'
    assert cp.renamed_thumb(thumb, 'V2TN_121_0027_A04_01', 'V2TN_121_0027_Z01_01').count(b'Z01') == 2
    with pytest.raises(cp.ClothingError):
        cp.renamed_thumb(thumb, 'V2TN_121_0027_A04_01', 'V2TN_121_0027_Z1_01')


def write_pack(folder, items=None, extra=None):
    folder = Path(folder)
    (folder / 'one').mkdir(parents=True, exist_ok=True)
    raw = png(32, 32)
    (folder / 'one' / '01.png').write_bytes(raw)
    spec = {'path': 'one/01.png', 'sha256': hashlib.sha256(raw).hexdigest()}
    value = {'format': cp.FORMAT, 'name': folder.name, 'items': items or [
        {'id': 'one', 'name': 'Red Jeans', 'base': 'Jeans_Base', 'textures': {'01': spec}},
        {'id': 'two', 'name': 'Shop Tee', 'base': 'T_Base', 'availability': 'shop', 'price': 9, 'textures': {'01': spec}}]}
    (folder / cp.MANIFEST).write_text(json.dumps(value))
    for name, data in (extra or {}).items():
        (folder / name).write_bytes(data)
    return folder


@pytest.mark.parametrize('change, message', [
    (lambda v: v.update(format='clothing-pack-0'), 'format'),
    (lambda v: v['items'][0].update(id='Bad Id'), 'slug'),
    (lambda v: v['items'][0].update(availability='free'), 'availability'),
    (lambda v: v['items'][0].update(price=-1), 'price'),
    (lambda v: v['items'][0].update(name='x' * 41), 'printable'),
    (lambda v: v['items'][0]['textures'].update({'1': v['items'][0]['textures']['01']}), 'colour numbers'),
    (lambda v: v['items'][0]['textures']['01'].update(path='../x.png'), 'path'),
    (lambda v: v['items'].append(dict(v['items'][0])), 'Duplicate'),
])
def test_manifest_validation(tmp_path, change, message):
    folder = write_pack(tmp_path / 'pack')
    value = json.loads((folder / cp.MANIFEST).read_text())
    change(value)
    (folder / cp.MANIFEST).write_text(json.dumps(value))
    with pytest.raises(cp.ClothingError, match=message):
        cp.load_manifest(folder)


def test_receipt_counts_items_and_refuses_unlisted_files(tmp_path):
    folder = write_pack(tmp_path / 'pack')
    assert cp.receipt(folder) == {'capabilities': ['clothing-v1'], 'texture_ids': [], 'wide_ids': [],
                                  'category': 'clothing', 'clothing_count': 2}
    (folder / 'one' / '01.png').write_bytes(png(32, 32, (1, 2, 3)))
    with pytest.raises(cp.ClothingError, match='hash'):
        cp.receipt(folder)
    folder = write_pack(tmp_path / 'other', extra={'script.py': b'print(1)'})
    with pytest.raises(cp.ClothingError, match='not part of the clothing pack'):
        cp.receipt(folder)


class FakeGame:
    def __init__(self, used=(), fits=None):
        self.rows = {r[0]: {'name': r[0], 'model': r[1], 'variant': r[2], 'colours': r[3], 'cost': r[4],
                            'type': r[5], 'category': cp.TYPE_CATEGORY[r[5]], 'fits': (fits or {}).get(r[0], [0])}
                     for r in ROWS}
        self.used = set(used)

    def base(self, name):
        return self.rows[name]

    def fits(self, row):
        return row['fits']

    def used_variants(self):
        return self.used


def test_variant_codes_are_unique_per_mesh_and_skip_used_ones(tmp_path):
    a = write_pack(tmp_path / 'a')
    b = write_pack(tmp_path / 'b')
    # The pack order makes no difference (FFNY Online's two-order check).
    strip = lambda items: [(i['key'], i['variant'], i['fits']) for i in items]
    assert strip(cp.plan(FakeGame(), [a, b])) == strip(cp.plan(FakeGame(), [b, a]))
    items = cp.plan(FakeGame(used={(121, 27, 'Z01')}), [b, a])
    assert [(i['key'], i['variant']) for i in items] == [
        ('a/one', 'Z02'), ('a/two', 'Z01'), ('b/one', 'Z03'), ('b/two', 'Z02')]
    # Fit models: a code must be free on every fit model (model + offset) of the base, and the
    # fit ranges of two bases can overlap, so their items cannot share a code there.
    game = FakeGame(used={(121, 29, 'Z01')}, fits={'Jeans_Base': [0, 2, 3]})
    jeans = cp.plan(game, [a])[0]
    assert jeans['fits'] == [0, 2, 3] and jeans['variant'] == 'Z02'
    game.rows['T_Base'].update(category=121, model=28, fits=[0, 1])      # models 28, 29: 29 overlaps
    tee = cp.plan(game, [a])
    assert [i['variant'] for i in tee] == ['Z02', 'Z03']
    fit_pack = write_pack(tmp_path / 'fitpack', items=[{'id': 'x', 'name': 'X', 'base': 'Jeans_Base',
                                                         'textures': {'01@3': {'path': 'one/01.png', 'sha256': '0' * 64}}}])
    assert cp.plan(FakeGame(fits={'Jeans_Base': [0, 3]}), [fit_pack])[0]['fits'] == [0, 3]
    with pytest.raises(cp.ClothingError, match='fit offsets 0'):
        cp.plan(FakeGame(), [fit_pack])
    big = write_pack(tmp_path / 'big', items=[{'id': 'x', 'name': 'X', 'base': 'Jeans_Base',
                                                 'textures': {'03': {'path': 'one/01.png', 'sha256': '0' * 64}}}])
    with pytest.raises(cp.ClothingError, match='colours 01-02'):
        cp.plan(FakeGame(), [big])


# ---- the mod manager -------------------------------------------------------------------------

def test_mod_manager_installs_enables_and_disables_clothing(tmp_path, monkeypatch):
    import mods
    pack = write_pack(tmp_path / 'src' / 'my-clothes')
    archive = tmp_path / 'my-clothes.zip'
    with zipfile.ZipFile(archive, 'w') as bundle:
        for path in sorted(pack.rglob('*')):
            if path.is_file():
                bundle.write(path, 'my-clothes/' + path.relative_to(pack).as_posix())
    compiled = []

    def fake_compile(game, packs, output):
        compiled.append([Path(p).name for p in packs])
        Path(output).mkdir(parents=True)
        (Path(output) / 'items.txt').write_text('clothing-items-1\n')
        return {'items': ['my-clothes/one', 'my-clothes/two']}
    monkeypatch.setattr(cp, 'compile_packs', fake_compile)
    data = tmp_path / 'data'
    manager = mods.Manager(data, capabilities=('clothing-v1',), game=tmp_path / 'game')
    manager.install_local(archive)
    state = manager.state()
    assert state['installed']['my-clothes']['category'] == 'clothing'
    assert state['installed']['my-clothes']['clothing_count'] == 2
    manager.activate_clothing('my-clothes', True)
    assert manager.state()['clothing'] == ['my-clothes'] and (data / 'cache/clothing/items.txt').is_file()
    manager.view()
    view = (data / 'mod-manager/view.ini').read_text()
    assert 'category=clothing' in view and 'enabled=1' in view and 'fighters=2' in view
    manager.activate_clothing('my-clothes', False)
    assert manager.state()['clothing'] == [] and not (data / 'cache/clothing').exists()
    assert compiled == [['my-clothes']]
    with pytest.raises(mods.ModError, match='Install this Clothing pack'):
        manager.activate_clothing('missing', True)
    # Removing an enabled pack drops it from the enabled list and rebuilds without it.
    manager.activate_clothing('my-clothes', True)
    manager.remove('my-clothes')
    assert manager.clothing_changed and manager.state().get('clothing') == []
    manager.refresh_clothing()
    assert not (data / 'cache/clothing').exists()


def test_clothing_zip_needs_the_capability(tmp_path):
    import mods
    pack = write_pack(tmp_path / 'src' / 'p')
    archive = tmp_path / 'p.zip'
    with zipfile.ZipFile(archive, 'w') as bundle:
        for path in sorted(pack.rglob('*')):
            if path.is_file():
                bundle.write(path, 'p/' + path.relative_to(pack).as_posix())
    manager = mods.Manager(tmp_path / 'data', capabilities=('fighters-v1',), game=tmp_path / 'game')
    with pytest.raises(mods.ModError, match='does not support Clothing'):
        manager.install_local(archive)


# ---- the game side ------------------------------------------------------------------------

DRIVER = r'''
#include "host.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "recomp/gen/recomp_types.h"
#include "hooks/pc_sod.h"
#include "patches/clothing.h"

unsigned char memory[0x800000];
uint32_t g_eax, g_ecx, g_edx, g_ebx, g_esp = 0x7F0000, g_ebp, g_esi, g_edi;
int g_fp_top;
#if defined(_WIN32)
typedef WCHAR xbox_host_char;
#else
typedef char xbox_host_char;
#endif
BOOL (*g_xbox_game_file_redirect)(const char *, xbox_host_char *, DWORD);
static uint32_t next_alloc = 0x600000;
static const char *studio;              /* STUDIO_DIR: a layer serving v2cp_2/3.viv before ours */
static BOOL studio_redirect(const char *relative, xbox_host_char *host, DWORD size)
{
    char path[1024];
    if (strcmp(relative, "assets/v2cp_2.viv") && strcmp(relative, "assets/v2cp_3.viv")) return FALSE;
    snprintf(path, sizeof path, "%s/%s", studio, relative + 7);
#if defined(_WIN32)
    return MultiByteToWideChar(CP_UTF8, 0, path, -1, host, (int)size) != 0;
#else
    return (size_t)snprintf(host, size, "%s", path) < size;
#endif
}
void sub_00029680(void) { uint32_t size = MEM32(g_esp + 4); g_eax = next_alloc; next_alloc += (size + 15u) & ~15u; g_esp += 4; }

#define P      0x100000u
#define ROW    (P + 0x1788u)
#define SET    (P + 0x1594u)
#define A1     (ROW + 0x5558u + 12u * 4u)   /* part 12 of the outfit worn */
#define A2     (ROW + 0x5618u + 13u * 4u)   /* part 13 of the creator's undo copy */

static void served(const char *name)
{
    xbox_host_char host[1024];
    char text[1024];
    if (!g_xbox_game_file_redirect || !g_xbox_game_file_redirect(name, host, 1024)) { printf("served %s -\n", name); return; }
#if defined(_WIN32)
    WideCharToMultiByte(CP_UTF8, 0, host, -1, text, sizeof text, NULL, NULL);
#else
    snprintf(text, sizeof text, "%s", host);
#endif
    printf("served %s %s\n", name, text);
}

static uint32_t call(int op, uint32_t a1, uint32_t a2, uint32_t a3)
{
    uint32_t r = 0xDEADu;
    int handled = clothing_set_call(op, SET, a1, a2, a3, &r);
    return handled ? r : 0xBEEFu;
}

int main(int argc, char **argv)
{
    /* argv: data, game, table rank, the jeans' rank, the tee's rank [, the handle to load at A1] */
    unsigned table = (unsigned)strtoul(argv[3], NULL, 0);
    uint32_t custom0 = table << 24 | (unsigned)strtoul(argv[4], NULL, 0);
    uint32_t custom1 = table << 24 | (unsigned)strtoul(argv[5], NULL, 0);
    MEM32(0x002FB148u + 0x18u * 4u) = 0x2F0000u;
    MEM32(0x2F0004u) = P;
    MEM32(P + 0x5AC7Cu) = 0;                  /* profile slot 0 */
    MEM32(SET + 0x4Cu) = P + 0x5AC7Cu;
    memcpy(&MEM8(ROW), "VY2", 4);
    studio = getenv("STUDIO_DIR");
    if (studio && *studio) g_xbox_game_file_redirect = studio_redirect;
    clothing_start(argv[1], argv[2]);
    printf("digest %s\n", clothing_set_digest());
    printf("base %08X %08X\n", clothing_base_handle(custom0 | 1u << 16), clothing_base_handle(table << 24 | 1u));
    served("assets/djv2.sod"); served("assets/v2cp_0.viv"); served("assets/v2cp_1.viv"); served("assets/v2cp_3.viv");
    served("screens/screens.viv"); served("assets/v2cp_2.viv");
    /* Item states: wardrobe items owned, shop items unlocked; retail keys go to the game. */
    printf("get0 %u get1 %u getbad %u retail %u\n", call(CLOTHING_GET, custom0, 0, 0), call(CLOTHING_GET, custom1, 0, 0),
           call(CLOTHING_GET, custom0 | 7u << 16, 0, 0), call(CLOTHING_GET, table << 24 | 1u, 0, 0));
    call(CLOTHING_CLEAR, custom1, 3, 0);
    call(CLOTHING_OR, custom1 | 1u << 16, 2, 0);
    printf("any1 %u get1c1 %u\n", call(CLOTHING_ANY, custom1, 0, 0), call(CLOTHING_GET, custom1 | 1u << 16, 0, 0));
    call(CLOTHING_SET, custom1, 3, 0);
    /* A filled set keeps only retail keys. */
    MEM32(SET + 4) = 0x210000u;
    MEM32(0x210000u) = table << 24 | 0u; MEM32(0x210004u) = custom0; MEM32(0x210008u) = table << 24 | 2u | 1u << 16;
    MEM32(0x21000Cu) = custom1 | 2u << 16;
    MEM32(SET + 8) = 4;
    clothing_after_build(SET);
    printf("keys %u %08X %08X\n", MEM32(SET + 8), MEM32(0x210000u), MEM32(0x210004u));
    /* A save holds base items; the row is put back right after. */
    MEM32(A1) = custom0 | 1u << 16;
    MEM32(A2) = custom1;
    clothing_before_save(ROW);
    uint32_t saved_a1 = argc > 6 ? (uint32_t)strtoul(argv[6], NULL, 0) : MEM32(A1);
    printf("saving %08X %08X\n", MEM32(A1), MEM32(A2));
    clothing_after_save();
    printf("after %08X %08X\n", MEM32(A1), MEM32(A2));
    /* A load of that save, in a new run: states start over, then the file. */
    MEM32(A1) = saved_a1;
    call(CLOTHING_SET, custom1, 1, 0);
    clothing_after_row_load();
    clothing_on_funccall("Crib.Enter()");
    printf("loaded %08X get1 %u\n", MEM32(A1), call(CLOTHING_GET, custom1, 0, 0));
    /* Names. */
    uint32_t text = clothing_localized(pc_sod_hash("Red Jeans"), 0), keep = clothing_localized(pc_sod_hash("Red Jeans"), 0x1234u);
    char name[64] = {0};
    for (int i = 0; text && i < 63 && MEM16(text + 2u * (uint32_t)i); i++) name[i] = (char)MEM16(text + 2u * (uint32_t)i);
    printf("name %s native %X\n", name, keep);
    return 0;
}
'''


@pytest.fixture(scope='module')
def clothing_tool(tmp_path_factory):
    compiler = shutil.which('cl') if os.name == 'nt' else shutil.which('cc')
    if not compiler:
        pytest.skip('native clothing fixture needs a C compiler')
    folder = tmp_path_factory.mktemp('clothing-native')
    inc = folder / 'recomp/gen'
    inc.mkdir(parents=True)
    (inc / 'recomp_types.h').write_text(
        '#include <stdint.h>\nextern unsigned char memory[];\n'
        'extern uint32_t g_eax, g_ecx, g_edx, g_ebx, g_esp, g_ebp, g_esi, g_edi;\nextern int g_fp_top;\n'
        '#define GUEST(a) ((uint32_t)(a) >= 0x80000000u ? (uint32_t)(a) - 0x80000000u + 0x700000u : (uint32_t)(a))\n'
        '#define MEM32(a) (*(uint32_t *)(memory + GUEST(a)))\n'
        '#define MEM16(a) (*(uint16_t *)(memory + GUEST(a)))\n'
        '#define MEM8(a) (*(uint8_t *)(memory + GUEST(a)))\n')
    if os.name == 'nt':
        host = '#include <windows.h>\n#define HOST_SEP "\\\\"\n#define HOST_SEP_CHAR \'\\\\\'\n'
    else:
        host = ('typedef int BOOL;\ntypedef unsigned int DWORD;\n#define TRUE 1\n#define FALSE 0\n'
                '#define HOST_SEP "/"\n#define HOST_SEP_CHAR \'/\'\n')
    (folder / 'host.h').write_text(host)
    driver = folder / 'driver.c'
    driver.write_text(DRIVER)
    exe = folder / ('clothing.exe' if os.name == 'nt' else 'clothing')
    includes = [folder, ROOT / 'src', ROOT / 'src/hooks']
    sources = [driver, ROOT / 'src/patches/clothing.c', ROOT / 'src/hooks/pc_sod.c', ROOT / 'src/hooks/pc_big.c']
    if os.name == 'nt':
        cmd = [compiler, '/nologo', '/O2', '/W3', '/TC', *['/I' + str(p) for p in includes], *map(str, sources), '/Fe:' + str(exe)]
    else:
        cmd = [compiler, '-O2', '-Wall', *['-I' + str(p) for p in includes], *map(str, sources), '-o', str(exe)]
    result = subprocess.run(cmd, cwd=folder, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


def catalogue_block(stem, sets):
    """One mesh of createplayer_parts.xml (CRLF, tabs) with its texture sets {code: colours}."""
    lines = ['\t\t\t<model>', f'\t\t\t\t<name>{stem}C</name>', f'\t\t\t\t<count>{len(sets)}</count>']
    for code, colours in sets.items():
        lines += ['\t\t\t\t<texture>', f'\t\t\t\t\t<name>{stem}{code}_01</name>']
        if colours > 1:
            lines.append(f'\t\t\t\t\t<count>{colours - 1}</count>')
            for c in range(2, colours + 1):
                lines += ['\t\t\t\t\t<colour>', f'\t\t\t\t\t\t<name>{stem}{code}_{c:02d}</name>', '\t\t\t\t\t</colour>']
        lines.append('\t\t\t\t</texture>')
    lines.append('\t\t\t</model>')
    return '\r\n'.join(lines) + '\r\n'


RETAIL_PARTS = ('<partslist>\r\n\t<parts>\r\n\t\t<contents>\r\n'
                + catalogue_block('V2CP_115_0007_', {'A01': 3}) + catalogue_block('V2CP_121_0027_', {'A04': 2})
                + catalogue_block('V2CP_121_0028_', {'A04': 2}) + '\t\t</contents>\r\n\t</parts>\r\n</partslist>\r\n')


def synthetic_game(root):
    (root / 'assets').mkdir(parents=True)
    (root / 'screens').mkdir()
    (root / 'assets' / 'djv2.sod').write_bytes(clothing_database())
    parts = cp.store(RETAIL_PARTS.encode())
    archives = {
        'v2cp_0.viv': {'createplayer_parts.xml': parts, 'cp_def0.xml': b'def'},
        'v2cp_1.viv': {'V2CP_115_0007_A01_01.xsh': b'retail tee'},
        'v2cp_2.viv': {'V2CP_121_0027_A04_01.xsh': b'retail jeans 1', 'V2CP_121_0027_A04_02.xsh': b'retail jeans 2'},
        'v2cp_3.viv': {'createplayer_parts.xml': parts, 'V2CP_141_0003_B01_01.xsh': b'hat'},
    }
    for name, members in archives.items():
        (root / 'assets' / name).write_bytes(cp.build_archive(members))
    (root / 'screens' / 'screens.viv').write_bytes(cp.build_archive({'screens/feflow.xml': b'<flow/>'}))
    return archives


DIGEST = 'ab' * 32


def synthetic_cache(cache):
    cache.mkdir(parents=True)
    (cache / 'items.txt').write_text('clothing-items-1\n'
                                     f'#clothing-set-1\t{DIGEST}\n'
                                     'p/one\tJeans_Base\tZ01\t2\t45\twardrobe\tRed Jeans\n'
                                     'p/two\tT_Base\tZ01\t3\t9\tshop\tShop Tee\n')
    # The jeans have two fits (models 27 and 28); the tee one.
    (cache / 'parts-add.txt').write_text('clothing-parts-1\np/one\t121\t27\tA04\np/one\t121\t28\tA04\n'
                                         'p/two\t115\t7\tA01\n')
    (cache / 'v2cp_2-add.viv').write_bytes(cp.build_archive({
        f'V2CP_121_00{m}_Z01_0{c}.xsh': f'new jeans {m} {c}'.encode() for m in (27, 28) for c in (1, 2)}))
    (cache / 'v2cp_1-add.viv').write_bytes(cp.build_archive({
        f'V2CP_115_0007_Z01_0{c}.xsh': f'new tee {c}'.encode() for c in (1, 2, 3)}))
    thumb = cp.store(b'xxV2TN_121_0027_Z01_01.apt..V2TN_121_0027_Z01_01.o..')
    (cache / 'screens-add.viv').write_bytes(cp.build_archive({'screens/shopThumbs/100/V2TN_121_0027_Z01_01.big': thumb}))


def added_ranks():
    """The ranks pc_sod.c gives the two added rows: the hashes above the table's highest, in items.txt order."""
    return len(ROWS), len(ROWS) + 1


def catalogue(path):
    from fighter_assets import unpack
    return unpack(cp.RetailArchive(Path(path).read_bytes()).read('createplayer_parts.xml')).decode()


def run_tool(tool, data, game, *ranks_args, studio=None):
    env = dict(os.environ, STUDIO_DIR=str(studio) if studio else '')
    result = subprocess.run([str(tool), str(data), str(game), *map(str, ranks_args)], capture_output=True, text=True,
                            timeout=60, env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    return {line.split(' ', 1)[0] + (' ' + line.split(' ')[1] if line.startswith('served') else ''): line
            for line in result.stdout.splitlines()}, result.stderr


def test_game_side_serves_states_saves_and_names(clothing_tool, tmp_path):
    game, data = tmp_path / 'game', tmp_path / 'data'
    archives = synthetic_game(game)
    synthetic_cache(data / 'cache' / 'clothing')
    names, table_rank, _ = ranks(clothing_database())
    retail = len(ROWS)
    # The added rows sort after the retail ones; which of the two is first follows their (salted) name hashes.
    jeans_rank, tee_rank = added_ranks()
    out, err = run_tool(clothing_tool, data, game, table_rank, jeans_rank, tee_rank)
    assert '2 custom item(s)' in err, err
    served = {key.split(' ')[1]: line.split(' ', 2)[2] for key, line in out.items() if key.startswith('served')}
    assert served['assets/v2cp_1.viv'] != '-' and out['digest'] == 'digest ' + DIGEST
    assert out['base'] == f"base {table_rank << 24 | 1 << 16 | names['Jeans_Base']:08X} {table_rank << 24 | 1:08X}"
    database = Path(served['assets/djv2.sod']).read_bytes()
    after, after_rank, db = ranks(database)
    assert after_rank == table_rank and all(after[n] == names[n] for n in names)      # retail ranks hold
    added = sorted((r, n) for n, r in after.items() if n not in names)
    assert [r for r, _ in added] == [retail, retail + 1]
    jeans = next(n for _, n in added if n.startswith('Custom_p/one'))
    # The added jeans row is the base row with its own texture set, price and name.
    header = db.directory[CLOTHING]
    by_name = {db.symbol(db.word(o)): o for o in db._tables[CLOTHING].records}
    new, base = by_name[jeans], by_name['Jeans_Base']
    assert db.symbol(db.word(new + 8)) == 'Z01' and db.word(new + 16) == 45 and db.symbol(db.word(new + 20)) == 'Red Jeans'
    assert db.word(new + 4) == db.word(base + 4) and db.word(new + 12) == db.word(base + 12)   # model, colour list
    assert db._tables[CLOTHING].count == retail + 2 and header
    # Archives: added files appended, the catalogue replaced, the game's own files unchanged.
    v2 = cp.RetailArchive(Path(served['assets/v2cp_2.viv']).read_bytes())
    assert v2.read('V2CP_121_0028_Z01_02.xsh') == b'new jeans 28 2'
    assert all(v2.read(n) == d for n, d in archives['v2cp_2.viv'].items())
    v3 = cp.RetailArchive(Path(served['assets/v2cp_3.viv']).read_bytes())
    assert v3.read('V2CP_141_0003_B01_01.xsh') == b'hat' and len(v3.names) == 2
    # The catalogue: the served one with the items' sets under every fit mesh, in its own layout.
    text = catalogue(served['assets/v2cp_3.viv'])
    assert text == catalogue(served['assets/v2cp_0.viv'])
    assert text == (RETAIL_PARTS.replace(catalogue_block('V2CP_115_0007_', {'A01': 3}),
                                         catalogue_block('V2CP_115_0007_', {'A01': 3, 'Z01': 3}))
                    .replace(catalogue_block('V2CP_121_0027_', {'A04': 2}), catalogue_block('V2CP_121_0027_', {'A04': 2, 'Z01': 2}))
                    .replace(catalogue_block('V2CP_121_0028_', {'A04': 2}), catalogue_block('V2CP_121_0028_', {'A04': 2, 'Z01': 2})))
    screens = cp.RetailArchive(Path(served['screens/screens.viv']).read_bytes())
    assert screens.read('screens/feflow.xml') == b'<flow/>'
    # States, by rank: the jeans are a wardrobe item (owned), the tee a shop item (unlocked).
    assert after[jeans] == jeans_rank
    # The names hit their target hashes exactly (no search): highest retail hash + 1, + 2.
    top = max(name_hash(r[0]) for r in ROWS)
    assert sorted(name_hash(n) for n in after if n not in names) == [top + 1, top + 2]
    assert re.fullmatch(r'Custom_p/one~[0-P]{7}', jeans)
    get = out['get0'].split()
    assert (get[1], get[3]) == ('3', '1')
    assert get[5] == str(0xFFFFFFFF) and get[7] == str(0xBEEF)
    assert out['keys'].split()[1] == '2'
    # Save: the custom items are their base items while the row is copied, then come back.
    saving = [int(x, 16) for x in out['saving'].split()[1:3]]
    assert all(h >> 24 == table_rank and h & 0xFFFF < retail for h in saving)          # base items only
    state = (data / 'clothing-state' / 'VY2.txt').read_text().splitlines()
    assert state[0] == 'clothing-state-1' and sum(line.startswith('worn') for line in state) == 2
    assert [int(line.split('\t')[2], 16) for line in state if line.startswith('worn')] == saving
    after_save = [int(x, 16) for x in out['after'].split()[1:3]]
    assert sorted(h & 0xFFFF for h in after_save) == [retail, retail + 1]              # the row is back
    # The shop tee was bought (colour 0 owned) and its colour 1 changed: both are remembered.
    bought = [line for line in state if line.startswith('state')]
    assert bought == ['state\tp/two\t0\t3', 'state\tp/two\t1\t3']
    # Load: the base item at the recorded place becomes the custom item again; bought states return.
    loaded = out['loaded'].split()
    assert int(loaded[1], 16) == after_save[0] and loaded[3] == '3'
    assert out['name'] == 'name Red Jeans native 1234'
    # The next start reuses the merged archives while their inputs are unchanged.
    _, again = run_tool(clothing_tool, data, game, table_rank, jeans_rank, tee_rank)
    assert again.count('the merged copy is current') == 5, again


def test_game_side_with_the_pack_off_keeps_base_items(clothing_tool, tmp_path):
    game, data = tmp_path / 'game', tmp_path / 'data'
    synthetic_game(game)
    synthetic_cache(data / 'cache' / 'clothing')
    names, table_rank, _ = ranks(clothing_database())
    jeans_rank, tee_rank = added_ranks()
    run_tool(clothing_tool, data, game, table_rank, jeans_rank, tee_rank)
    shutil.rmtree(data / 'cache' / 'clothing')
    worn = [line.split('\t') for line in (data / 'clothing-state' / 'VY2.txt').read_text().splitlines()
            if line.startswith('worn')]
    recorded = next(int(w[2], 16) for w in worn if w[1] == '5588')
    out, err = run_tool(clothing_tool, data, game, table_rank, jeans_rank, tee_rank, hex(recorded))
    assert 'custom item' not in err.split('profile slot')[0]
    assert out['served assets/djv2.sod'].endswith(' -')
    assert int(out['loaded'].split()[1], 16) == recorded   # the hero keeps the base item
    assert 'left as their base items' in err
    # The file still remembers the custom item for when the pack is enabled again.
    assert any(line.startswith('worn') for line in (data / 'clothing-state' / 'VY2.txt').read_text().splitlines())


def test_game_side_takes_codes_and_the_catalogue_from_the_layer_before_it(clothing_tool, tmp_path):
    """A layer served before ours (a fork's clothing tool) already uses Z01 on the jeans' model and
    has a line of its own in the catalogue: the jeans move to Z02, everything of that layer stays."""
    game, data, studio = tmp_path / 'game', tmp_path / 'data', tmp_path / 'studio'
    archives = synthetic_game(game)
    synthetic_cache(data / 'cache' / 'clothing')
    studio.mkdir()
    (studio / 'v2cp_2.viv').write_bytes(cp.build_archive(dict(archives['v2cp_2.viv'], **{'V2CP_121_0027_Z01_01.xsh': b'studio'})))
    studio_parts = RETAIL_PARTS.replace(catalogue_block('V2CP_115_0007_', {'A01': 3}),
                                        catalogue_block('V2CP_115_0007_', {'A01': 3, 'Y01': 1}))
    (studio / 'v2cp_3.viv').write_bytes(cp.build_archive(dict(archives['v2cp_3.viv'], **{'createplayer_parts.xml': cp.store(studio_parts.encode())})))
    names, table_rank, _ = ranks(clothing_database())
    jeans_rank, tee_rank = added_ranks()
    out, err = run_tool(clothing_tool, data, game, table_rank, jeans_rank, tee_rank, studio=studio)
    assert 'p/one: Z01 is taken in the files served before ours; it uses Z02' in err, err
    assert '2 custom item(s)' in err
    served = {key.split(' ')[1]: line.split(' ', 2)[2] for key, line in out.items() if key.startswith('served')}
    v2 = cp.RetailArchive(Path(served['assets/v2cp_2.viv']).read_bytes())
    assert v2.read('V2CP_121_0027_Z01_01.xsh') == b'studio'
    assert v2.read('V2CP_121_0027_Z02_01.xsh') == b'new jeans 27 1' and v2.read('V2CP_121_0028_Z02_02.xsh') == b'new jeans 28 2'
    assert not any(n.startswith('V2CP_121_0028_Z01') for n in v2.names)
    text = catalogue(served['assets/v2cp_3.viv'])
    assert text == (studio_parts.replace(catalogue_block('V2CP_115_0007_', {'A01': 3, 'Y01': 1}),
                                         catalogue_block('V2CP_115_0007_', {'A01': 3, 'Y01': 1, 'Z01': 3}))
                    .replace(catalogue_block('V2CP_121_0027_', {'A04': 2}), catalogue_block('V2CP_121_0027_', {'A04': 2, 'Z02': 2}))
                    .replace(catalogue_block('V2CP_121_0028_', {'A04': 2}), catalogue_block('V2CP_121_0028_', {'A04': 2, 'Z02': 2})))
    from fighter_assets import unpack
    screens = cp.RetailArchive(Path(served['screens/screens.viv']).read_bytes())
    thumb = unpack(screens.read('screens/shopThumbs/100/V2TN_121_0027_Z02_01.big'))
    assert thumb == b'xxV2TN_121_0027_Z02_01.apt..V2TN_121_0027_Z02_01.o..'
    db = Database(Path(served['assets/djv2.sod']).read_bytes())
    rows = {db.symbol(db.word(o)): o for o in db._tables[CLOTHING].records}
    jeans = next(n for n in rows if n.startswith('Custom_p/one'))
    tee = next(n for n in rows if n.startswith('Custom_p/two'))
    assert db.symbol(db.word(rows[jeans] + 8)) == 'Z02' and db.symbol(db.word(rows[tee] + 8)) == 'Z01'

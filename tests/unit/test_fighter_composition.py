"""Language archive provenance and bounded composition before fighter edits."""
import hashlib
from pathlib import Path
import struct
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
from fighter_archive import Archive, store
from fighter_assets import AssetError, unpack
from fighter_composition import apply_delta, language_base
from test_langpack import lp, big, runtime_tool, dump, run_runtime


def test_nested_language_base_matches_the_existing_format_byte_for_byte():
    inner = big([('z.const', b'unchanged'), ('a.apt', b'old movie'), ('b.txt', b'old label')])
    original = big([('z.big', store(inner)), ('a.txt', b'old root'), ('untouched', b'exact bytes')])
    edits = [(('a.txt',), lp.delta_make(b'old root', b'translated root')),
             (('Z.BIG', 'b.txt'), lp.delta_make(b'old label', b'translated label')),
             (('z.big', 'a.apt'), lp.delta_make(b'old movie', b'new movie'))]
    result, receipt = language_base(original, edits, hashlib.sha256(original).hexdigest())
    assert result == lp.rebuild(original, [(list(parts), delta) for parts, delta in edits])
    assert result == language_base(original, list(reversed(edits)), receipt['source_sha256'])[0]
    assert receipt == language_base(original, list(reversed(edits)), receipt['source_sha256'])[1]
    archive = Archive(result)
    assert archive.read('untouched') == b'exact bytes'
    assert Archive(unpack(archive.read('z.big'))).read('z.const') == b'unchanged'
    assert receipt['base_sha256'] == hashlib.sha256(result).hexdigest()
    assert original != result


def test_native_language_cache_is_the_same_composed_base(runtime_tool, dump):
    temporary, game, pack = dump
    _, files = lp.read_pack(pack)
    edits = [(tuple(parts[1:]), (pack / patch).read_bytes()) for parts, patch in files
             if parts[0].lower() == 'screens/screens.viv']
    original = (game / 'screens/screens.viv').read_bytes()
    expected, _ = language_base(original, edits, hashlib.sha256(original).hexdigest())
    lines, _ = run_runtime(runtime_tool, temporary / 'composition-data', game,
                           'screens/screens.viv', RECOMP_LANGUAGE_PACK='xx-test', RECOMP_TEXTURE_ROOT=str(pack.parent))
    served = next(line.split(None, 2)[2] for line in lines if line.startswith('serve screens/screens.viv '))
    assert Path(served).read_bytes() == expected


@pytest.mark.parametrize('case', ['valid', 'unicode', 'bad-base', 'bad-final', 'malformed-hash',
                                 'missing-output', 'unserved', 'corrupt-cache'])
def test_native_adoption_requires_both_exact_files_and_preserves_the_previous_owner(runtime_tool, dump, case):
    temporary, game, pack = dump
    data = temporary / 'adoption-data'
    relative = 'gconfig.xml'
    base = lp.apply_pack(pack, game)[relative]
    final = temporary / ('final-\N{SNOWMAN}.xml' if case == 'unicode' else 'final.xml')
    final.write_bytes(b'verified semantic overlay')
    options = {'RECOMP_LANGUAGE_PACK': 'xx-test', 'RECOMP_TEXTURE_ROOT': str(pack.parent),
               'TEST_COMPOSE_BASE': hashlib.sha256(base).hexdigest(),
               'TEST_COMPOSE_FINAL': str(final), 'TEST_COMPOSE_HASH': hashlib.sha256(final.read_bytes()).hexdigest(),
               'TEST_COMPOSE_RELATIVE': relative}
    if case == 'unicode': options['TEST_COMPOSE_FINAL_HEX'] = str(final).encode('utf-8').hex()
    elif case == 'bad-base': options['TEST_COMPOSE_BASE'] = '0' * 64
    elif case == 'bad-final': final.write_bytes(b'changed after compilation')
    elif case == 'malformed-hash': options['TEST_COMPOSE_HASH'] = 'not a digest'
    elif case == 'missing-output': final.unlink()
    elif case == 'unserved': options['TEST_COMPOSE_RELATIVE'] = 'unserved.xml'
    elif case == 'corrupt-cache':
        lines, _ = run_runtime(runtime_tool, data, game, relative, RECOMP_LANGUAGE_PACK='xx-test',
                                RECOMP_TEXTURE_ROOT=str(pack.parent))
        cached = Path(next(line.split(None, 2)[2] for line in lines if line.startswith('serve ')))
        cached.write_bytes(b'corrupted cached base')
    lines, _ = run_runtime(runtime_tool, data, game, relative, 'assets/misc.viv', **options)
    adopted = case in ('valid', 'unicode')
    assert lines[0] == 'adopt ' + ('1' if adopted else '0' if case == 'unserved' else '-1')
    served = {line.split()[1]: Path(line.split(None, 2)[2]) for line in lines if line.startswith('serve ')}
    assert (served[relative] == final) == adopted
    assert served[relative].read_bytes() == (final.read_bytes() if adopted else b'corrupted cached base' if case == 'corrupt-cache' else base)
    assert served['assets/misc.viv'].read_bytes() == lp.apply_pack(pack, game)['assets/misc.viv']


def test_whole_file_delta_and_its_receipt():
    source, result = b'original text', b'translated text'
    composed, receipt = language_base(source, [((), lp.delta_make(source, result))],
                                       hashlib.sha256(source).hexdigest())
    assert composed == result
    assert receipt['edits'][0]['target'] == ''
    with pytest.raises(AssetError, match='verified original source'):
        language_base(source, [((), lp.delta_make(source, result))], '0' * 64)


@pytest.mark.parametrize('mutation', ['header', 'source', 'target', 'truncated', 'missing-end',
                                     'trailing', 'opcode', 'copy-range', 'copy-truncated',
                                     'literal-range', 'literal-truncated', 'output-budget'])
def test_rejects_corrupt_language_delta_before_a_shared_cache_can_be_used(mutation):
    source = b'original'
    target = b'translated'
    delta = bytearray(lp.delta_make(source, target))
    if mutation == 'header': delta[0] = 0
    elif mutation == 'source': delta[16] ^= 1
    elif mutation == 'target': delta[48] ^= 1
    elif mutation == 'truncated': delta = delta[:79]
    elif mutation == 'missing-end': delta = delta[:-1]
    elif mutation == 'trailing': delta += b'\0'
    elif mutation == 'opcode': delta[80:] = b'\x03\0'
    elif mutation == 'copy-range': delta[80:] = b'\x01' + struct.pack('<II', 8, 1) + b'\0'
    elif mutation == 'copy-truncated': delta[80:] = b'\x01\0'
    elif mutation == 'literal-range': delta[80:] = b'\x02' + struct.pack('<I', 0xffffffff) + b'\0'
    elif mutation == 'literal-truncated': delta[80:] = b'\x02\0'
    elif mutation == 'output-budget': struct.pack_into('<I', delta, 12, 2**32 - 1)
    with pytest.raises(AssetError):
        apply_delta(source, bytes(delta))


@pytest.mark.parametrize('parts', [(('../escape',),), (('a\\b',),), (('a|b',),), (('a',) * 9,)])
def test_unsafe_language_target_paths_fail_closed(parts):
    source = big([('a', b'original')])
    with pytest.raises(AssetError):
        language_base(source, [(parts[0], lp.delta_make(b'original', b'new'))], hashlib.sha256(source).hexdigest())


def test_ambiguous_missing_and_recursive_targets_fail_closed():
    source = big([('a', b'original')])
    delta = lp.delta_make(b'original', b'new')
    digest = hashlib.sha256(source).hexdigest()
    for edits in [[], [(('a',), delta), (('A',), delta)], [(('absent',), delta)],
                  [((), lp.delta_make(source, source)), (('a',), delta)],
                  [(('a',), delta), (('a', 'child'), delta)]]:
        with pytest.raises(AssetError):
            language_base(source, edits, digest)


def test_compressed_nested_expansion_is_bounded():
    malformed = b'\x10\xfb\xff\xff\xff\xfc'
    source = big([('a.big', malformed)])
    with pytest.raises(AssetError):
        language_base(source, [(('a.big', 'a'), lp.delta_make(b'old', b'new'))],
                      hashlib.sha256(source).hexdigest())

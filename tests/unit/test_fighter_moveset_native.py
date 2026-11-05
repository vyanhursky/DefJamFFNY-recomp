"""Independent native reconstruction rejects malformed action selection proofs."""
import hashlib
import struct
import subprocess

import pytest

from test_fighter_motion_native import tool
from test_fighter_moveset import fixture
from fighter_motion_compile import MotionCoreTemplates
from fighter_moveset import compose_selected_cores


@pytest.fixture
def files(tmp_path):
    data, start, plan = fixture()
    original = data + data[start - 8:start + 852] * 138
    compiler = MotionCoreTemplates(original, hashlib.sha256(original).hexdigest())
    data, report, table = compose_selected_cores(compiler, {'alpha/core': {
        'donor': 2, 'envelope': plan.bank.envelope,
        'bank_sha256': hashlib.sha256(plan.bank.envelope.model.data).hexdigest(),
        'selections': {2: 1}}, 'beta/core': 2})
    path, bindings = tmp_path / 'motion.dat', tmp_path / 'proof.bin'
    path.write_bytes(data); bindings.write_bytes(table)
    return path, bindings, report


def test_native_selected_move_and_parameter_dispatch_preserve_abi(tool, files):
    path, table, report = files
    result = subprocess.run([tool, path, table, report['sha256'], 'selected'], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('offset,value,width', [(4, 1, 4), (72, 0, 4), (72, 1000, 4),
    (80, 2, 2), (80, 31, 2), (80, 65535, 2), (76, 1, 2), (80, 65534, 2), (352, 2, 4)])
def test_invalid_selection_proof_is_rejected_before_registration(tool, files, offset, value, width):
    path, table, report = files
    raw = bytearray(table.read_bytes()); struct.pack_into('<I' if width == 4 else '<H', raw, offset, value)
    table.write_bytes(raw)
    result = subprocess.run([tool, path, table, report['sha256'], 'reject'], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('relative', [0, 64, 72 + 2 * 6, 72 + 2 * 6 + 2, 72 + 2 * 6 + 4, 72 + 3 * 6])
def test_motion_edits_outside_the_reconstructed_action_fail_even_with_matching_hash(tool, files, relative):
    path, table, report = files
    data = bytearray(path.read_bytes())
    data[report['bindings']['alpha/core']['parameters_offset'] + relative] ^= 1
    path.write_bytes(data)
    digest = hashlib.sha256(data).digest()
    raw = bytearray(table.read_bytes()); raw[24:56] = digest; table.write_bytes(raw)
    result = subprocess.run([tool, path, table, digest.hex(), 'reject'], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_aliasing_action_outside_the_native_range_owner_is_rejected(tool, files):
    from fighter_motion import MotionIndex
    path, table, report = files
    data = bytearray(path.read_bytes())
    index = MotionIndex(bytes(data))
    # Keep every inherited/appended pair consistent except for the forbidden
    # selection's second, non-owning action reference into its target range.
    for core in (2, 141, 142):
        struct.pack_into('<3H', data, index.core_spans[core] + 72 + 98 * 6, 1, 1, 2)
    path.write_bytes(data)
    digest = hashlib.sha256(data).digest()
    proof = bytearray(table.read_bytes()); proof[24:56] = digest; table.write_bytes(proof)
    result = subprocess.run([tool, path, table, digest.hex(), 'reject'], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr

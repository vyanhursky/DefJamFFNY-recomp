"""Materialize native profiles and their extension as one supervised session.

The launcher supplies its own Store and session parent after adoption. Import
is read-only and happens once; subsequent launches, including zero-pack ones,
use the committed Store. Never export a working tree over the import source.
Activation/UI policy stays with the caller; this module does not enable mods.
"""
from dataclasses import dataclass
from pathlib import Path
import uuid

from fighter_profile_store import require
from fighter_save_journal import Monitor, encode_unlock_state, initialize
from mods import ordinary_path


def _separate(left, right):
    require(not left.is_relative_to(right) and not right.is_relative_to(left),
            'Profile source, Store and session roots must be separate')


@dataclass
class Session:
    root: Path
    data_root: Path
    journal: Path
    unlock_state: Path
    generation: dict | None
    monitor: Monitor

    @property
    def environment(self):
        return {'DEFJAM_DATA': str(self.data_root),
                'RECOMP_FIGHTER_SAVE_JOURNAL': str(self.journal),
                'RECOMP_FIGHTER_UNLOCKS': str(self.unlock_state)}

    def finish(self, *, require_complete):
        """Stop verification; a clean game exit may not leave a pending intent.

        A failed run still retains committed generations, and its abandoned
        workspace remains diagnostic evidence. Recovery never replays it.
        """
        self.monitor.stop()
        if require_complete:
            require(not (self.journal / f'{self.monitor.next:06}.batch').exists(),
                    'Native run ended with an unverified fighter save batch; committed generation was preserved')


def prepare(store, ledger, sessions_root, *, source=None, fresh=False):
    """Prepare, but do not start, one fresh native save transaction session.

    ``fresh`` is for isolated first-save acceptance only; it cannot reset an
    adopted Store. With an existing head, the source is never read again.
    Call monitor.start() before launching native code and finish() afterwards.
    """
    sessions_root = ordinary_path(sessions_root)
    store_root = ordinary_path(store.root)
    _separate(sessions_root, store_root)
    if source is not None:
        source = ordinary_path(source)
        _separate(source, store_root)
        _separate(source, sessions_root)
    previous = store.load()
    if fresh:
        require(previous is None and source is None, 'Fresh profile session requires an empty Store and no import source')
        generation = None
    else:
        require(previous is not None or source is not None, 'First profile session requires a verified import source')
        generation = initialize(store, source, ledger)
    sessions_root.mkdir(parents=True, exist_ok=True)
    root = ordinary_path(sessions_root / uuid.uuid4().hex)
    root.mkdir()  # Exclusive: never reuse an abandoned session or its receipts.
    data_root = root / 'fighter-runtime-probe'
    save = data_root / 'save'
    save.mkdir(parents=True)
    for name, data in (generation['files'] if generation else {}).items():
        path = ordinary_path(save / name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    journal = root / 'journal'
    journal.mkdir()
    unlock_state = root / 'fighter-unlocks.bin'
    unlock_state.write_bytes(encode_unlock_state(generation, store.baseline))
    monitor = Monitor(store, save, journal, ledger,
                      expected_head=generation['generation'] if generation else None)
    return Session(root, data_root, journal, unlock_state, generation, monitor)

# Toolkit optimization workstreams

Owner direction: November 22, 2026. Baseline is public main `f80a792`,
toolkit `d108a64`. This records the requested experiment scope; GitHub remains
the source for release scope and existing issues.

| Stream | Scope | State |
|---|---|---|
| 1: build time | Independent body-lifting parallelism, generated-source chunk balance, benchmark tooling and Windows/Linux validation | Active experiment; draft PR for the owner's low-spec Linux test. |
| 2: runtime overhead | Persistent Windows shader bytecode, notified fence-progress waits, reuse of render states/constants | On hold until the owner's explicit signal. |
| 3: D3D interception | Identify XDK 5849 calls and inline command writers, then evaluate a coherent high-level rendering path | On hold until the owner's explicit signal. |

Stream 1 measures lifting separately from configure, clean compile/link and
no-op builds. It preserves generated function semantics and tests forced spawn
on every host. Parallelism and line-based chunk budgets are opt-in toolkit
options; the existing serial/function-count defaults remain available.
Build throughput does not establish higher gameplay FPS.

The design review considered [DirectXbox-Recomp](https://github.com/phobos665/DirectXbox-Recomp)
and [XboxXBERecomp](https://github.com/TGP482/XboxXBERecomp). The Stream 1
implementation is independently written against the current toolkit; it does
not import their code. The owner intends to seek author permission and give
credit after testing. Do not contact authors, merge, release, or begin Streams
2/3 as part of this experiment. Keep code provenance and any future reuse
decisions explicit.

Use a separate worktree, writable analysis/generated/build/log directories and
save root. The extracted dump can be shared read-only. Run timed builds and
game checks serially on a machine; do not interfere with another test lane.

Stream 1 results and the reproducible Linux comparison are in
[build-time-stream1.md](build-time-stream1.md).

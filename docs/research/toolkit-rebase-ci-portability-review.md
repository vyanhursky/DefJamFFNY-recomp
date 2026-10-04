# Toolkit rebase: Ubuntu CI portability review

2026-10-03. Bounded read-only review of the save-compatibility and lift-audit tests, pipeline-state script, their harness test consumers and the existing workflow. AGENTS.md, PROGRESS.md and the existing save/pipeline reports were read. No source edits, builds, tests, game runs, generated-code reads or escalated calls were performed. Only this report was written.

**No concrete Ubuntu python-tools CI breakage was found in the reviewed paths.** The workflow uses Python 3.12 and runs tests/unit without checking out submodules ([workflow, line 26](C:/Users/Vlad/code/defjam-recomp/.github/workflows/ci.yml:26)). The new tests do not require the real toolkit checkout or game data.

## Save fixture

- [Compiler selection, line 76](C:/Users/Vlad/code/defjam-recomp/tests/unit/test_save_compat.py:76) uses MSVC when available, otherwise cc/gcc/clang with ordinary Unix flags. Compiler failure is asserted; absence of every compiler skips the fixture rather than causing a collection error. The filename save_compat.exe is harmless on POSIX: the selected native compiler determines the executable format, and subprocess invokes the resulting path directly.
- [Lines 28–33](C:/Users/Vlad/code/defjam-recomp/tests/unit/test_save_compat.py:28) provide the non-Windows LONG/InterlockedIncrement shim required by the extracted manual wrapper. [Lines 59–70](C:/Users/Vlad/code/defjam-recomp/tests/unit/test_save_compat.py:59) select wmain/wide APIs only under _WIN32 and supply ordinary main/fopen otherwise. No unconditional Windows header or API reaches the POSIX driver.
- [Lines 16 and 74–75](C:/Users/Vlad/code/defjam-recomp/tests/unit/test_save_compat.py:16) read only parent-owned recomp_manual.c and src/hooks/save_compat.c. The helper's [POSIX stat branch](C:/Users/Vlad/code/defjam-recomp/src/hooks/save_compat.c:31) and [fopen branch](C:/Users/Vlad/code/defjam-recomp/src/hooks/save_compat.c:54) are present. A missing submodule does not affect these inputs.

## Lift audit and pipeline state

- [test_lift_audit.py, line 56](C:/Users/Vlad/code/defjam-recomp/tests/unit/test_lift_audit.py:56) writes synthetic ASCII C to pytest's temporary directory. Imports and paths use the standard library; no compiler, toolkit or Windows fixture is required. The new dynamic-flag refusal and unknown-metric tests match the script's [explicit rejection paths](C:/Users/Vlad/code/defjam-recomp/scripts/lift-audit.py:121).
- [pipeline-state.py, line 29](C:/Users/Vlad/code/defjam-recomp/scripts/pipeline-state.py:29) uses hashlib.file_digest, supported by the workflow's Python 3.12. Importing the module does not open the default toolkit, load Windows libraries or start a subprocess; its CLI is protected by the [main guard](C:/Users/Vlad/code/defjam-recomp/scripts/pipeline-state.py:213).
- [test_harness.py, line 212](C:/Users/Vlad/code/defjam-recomp/tests/unit/test_harness.py:212) builds a complete synthetic repository/toolkit input tree under tmp_path. Lifter execution is mocked at [line 243](C:/Users/Vlad/code/defjam-recomp/tests/unit/test_harness.py:243). The launch-failure case supplies synthetic exe/XBE filenames and mocks Popen at [line 284](C:/Users/Vlad/code/defjam-recomp/tests/unit/test_harness.py:284), so it never executes a Windows binary on Ubuntu. The .exe suffix is also just a synthetic filename in freshness checks. Harness [taskkill is guarded by os.name == nt](C:/Users/Vlad/code/defjam-recomp/scripts/harness.py:309), and guard/launch tests additionally replace kill_stray.

## Coverage gaps and minimal remedies

These are coverage gaps, not identified failures of the current Ubuntu job:

1. Compiler absence silently skips the compiled save tests. If those tests must be mandatory in CI, explicitly provide/select a native compiler and fail on its absence in that job rather than relying on the fixture skip policy.
2. Ubuntu tests exercise the POSIX helper, not Windows UTF-8 conversion and wide filesystem APIs. The [Windows job, lines 39–54](C:/Users/Vlad/code/defjam-recomp/.github/workflows/ci.yml:39) activates MSVC and builds the runtime, but does not run parent pytest tests. Minimal additional gate: set up Python/pytest there and run python -m pytest -q tests/unit/test_save_compat.py after MSVC activation. This would cover the Windows Unicode-root branch and guest-wrapper fixture without game data.
3. Real analysis/lift/build verification needs a populated toolkit and local game artifacts; the Ubuntu job intentionally does not perform those stages. Do not add submodule checkout merely to satisfy the synthetic pipeline tests. If actual toolkit Python tests are added later, explicitly check out the candidate toolkit and install its requirements in that separate gate.

The earlier save-root/encoding and pipeline-provenance findings are marked closed in their existing reports; this source review does not reopen them. Runtime/game acceptance remains the parent's independent gate. No source remedy is required for a proven Ubuntu portability failure because none was found, and no Linux execution result is claimed here.

## Execution closure

The subsequent private CI run at parent `7068110` (private development record)
passed all three jobs. Ubuntu ran 67 parent tests in 0.66 seconds, including the
native POSIX save fixture. Windows now runs the recommended native MSVC fixture:
19 passed in 6.61 seconds, covering Unicode-root and guest-wrapper paths, then the
runtime builds successfully from the freshly fetched published `aa1a1b9` submodule.
There are no root CTest targets in this configuration, so its successful empty
invocation is not fixture coverage. The standalone kernel/audio/USB/VSH results
remain separate local gates in `toolkit-rebase-acceptance.md`. This validates the
reviewed Ubuntu tooling paths; no Linux game execution is claimed.

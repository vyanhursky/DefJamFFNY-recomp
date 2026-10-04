# src/hooks — HLE hooks and stubs

Hand-written C that intercepts guest behaviour without touching the lifted code:
- hardware pokes the PC has no equivalent for (TV encoder, PCI config space, interrupt connect),
- file-IO redirection (mod override directories for textures in `.viv` archives and music tracks),
- diagnostics (per-subsystem logging toggles).

Register overrides via `recomp_lookup_manual()` in `src/recomp_manual.c`. One file per subsystem, e.g.
`hw_stubs.c`, `fs_overrides.c`. Everything in this directory is picked up by CMake automatically.

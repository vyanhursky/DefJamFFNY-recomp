# Project Plan: AI-Assisted Def Jam Fight for NY Native PC Port

## 🎯 Executive Summary
The goal of this project is to create a native PC port of **Def Jam: Fight for NY** running smoothly on Windows and Steam Deck at 60+ FPS with local multiplayer support. 

Based on architecture maturity, tool prevalence, and asset quality, the project will begin using the **`xboxrecomp`** pipeline rather than a full decompilation. Full decompilation will be deferred for long-term stretch goals (custom fighters, rollback netcode).

---

## 🛠️ Tech Stack & Framework Selection
* **Target Version:** Original Xbox Image (`default.xbe`) -> Chosen for superior asset quality over PS2.
* **Core Framework:** `sp00nznet/xboxrecomp`
* **Target Platforms:** Windows (compiled via MSVC) and Steam Deck / Linux (compiled via GCC/Clang).
* **Graphics API Layer:** Direct3D 11 / Vulkan via `xboxrecomp` High-Level Emulation (HLE) shims.
* **Input Layer:** Native SDL2 / XInput (built into the recomp runtime).

---

## 📋 Priority Matrix

| Feature | Difficulty via Recomp | Status / Strategy |
| :--- | :--- | :--- |
| **Windows & Steam Deck Support** | Low | Natively supported via portable C code translation. |
| **60+ FPS Support** | Medium | Supported; AI must write custom delta-time patches for game loop physics. |
| **Local Multiplayer** | Low | Natively supported via built-in modern XInput/SDL2 controller mapping. |
| **Improved Textures** | Medium | Can be handled via external texture injection hooked into the D3D layer. |
| **Soundtrack Modding (Add Songs)**| Medium | AI will write custom file-system hook scripts to intercept audio playback calls. |
| **Custom Fighters** | High | Requires Engine Structure modification. Defers to a **Full Decomp**. |
| **Online Multiplayer (Netcode)** | Critical | Requires game loop decoupling. Defers to a **Full Decomp**. |

---

## 🗺️ Execution Roadmap (Instructions for AI Agent)

### Phase 1: Environment Setup & Asset Extraction
1. **Extract Media & Binaries:** Extract `default.xbe` and all asset containers from a clean, legal Xbox ISO dump.
2. **Initialize Workspace:** Clone `sp00nznet/xboxrecomp`. Provide this file, along with the toolkit's official documentation, to your context window.
3. **Automated Analysis:** Execute the recomp tool's binary analyzer on the `default.xbe` to map functions, jumps, and global tables into a `.toml` configuration layout.

### Phase 2: Code Lifting & Automated Translation
1. Generate the initial C-translated codebase using `xboxrecomp`. 
2. Group the thousands of generated raw functions into an organized CMake project layout.

### Phase 3: AI-Driven Debugging & Compiler Shimming
1. **Error Loop Processing:** Run the compiler, catch standard compilation syntax or pointer errors, and feed them into the AI engine.
2. **Implement Shims:** Work with the AI agent to resolve missing kernel dependencies by mapping older Xbox hardware calls cleanly into contemporary API substitutes (`xbox_kernel`, `xbox_d3d8`).
3. **Memory Safeguards:** Identify and refactor rigid memory pools to prevent memory access violations on modern Windows environments.

### Phase 4: Media Hooking & Game Loop Tuning
1. **Delta-Time Adaptation:** Prompt the AI to isolate the hardcoded 30/60Hz update constraints within the engine loop. Introduce a dynamic delta-time scalar to unlink graphics processing from game physics.
2. **Audio/Texture Overrides:** Program an explicit IO asset hook that routes asset read calls toward uncompressed external local directories (e.g., loading HD textures or `.mp3`/`.wav` music files).

---

## 🤖 Prompt Strategies for Later Development Phases

### For Compiler Troubleshooting:
> *"Here is a compiler stack trace error originating from my `xboxrecomp` setup concerning a specific unmapped hardware vector layout or kernel function. Based on the toolkit's design rules, generate the appropriate C/C++ proxy stub to resolve this mismatch cleanly."*

### For Framerate Stabilization:
> *"Analyze this lifted engine main execution loop function. The original codebase ties animation frames explicitly to the game tick. Rewrite this block to use high-precision delta-time tracking so physics remain consistent when running at modern frame rates like 144Hz."*

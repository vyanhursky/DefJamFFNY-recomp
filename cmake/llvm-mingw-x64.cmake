# Experimental native Windows toolchain for issue #189. Unpack the pinned
# UCRT LLVM-MinGW archive and set LLVM_MINGW_ROOT to that directory.
# CMake and Ninja must also be supplied explicitly; no VsDevCmd/SDK is used.
set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR AMD64)
file(TO_CMAKE_PATH "$ENV{LLVM_MINGW_ROOT}" _llvm_mingw_root)
if(NOT EXISTS "${_llvm_mingw_root}/bin/clang.exe")
    message(FATAL_ERROR "Set LLVM_MINGW_ROOT to the unpacked LLVM-MinGW UCRT toolchain")
endif()
# CMake's REAL_PATH can retain Windows junctions, including those above a file.
# Python is already required by the project and uses Windows' native resolver.
# Keep one physical compiler/DLL prefix to avoid the measured startup stall.
if(DEFINED ENV{LLVM_MINGW_PYTHON})
    set(_llvm_mingw_python "$ENV{LLVM_MINGW_PYTHON}")
else()
    find_program(_llvm_mingw_python NAMES python python3
        HINTS "$ENV{Python_ROOT_DIR}" "$ENV{Python3_ROOT_DIR}" "$ENV{pythonLocation}")
endif()
if(NOT _llvm_mingw_python OR NOT EXISTS "${_llvm_mingw_python}")
    message(FATAL_ERROR "Set LLVM_MINGW_PYTHON to the project's Python 3 interpreter")
endif()
execute_process(COMMAND "${_llvm_mingw_python}" -I -X utf8 -c
    "import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve(strict=True))"
    "${_llvm_mingw_root}"
    RESULT_VARIABLE _llvm_resolve_status OUTPUT_VARIABLE _llvm_physical_root
    OUTPUT_STRIP_TRAILING_WHITESPACE)
if(NOT _llvm_resolve_status STREQUAL "0")
    message(FATAL_ERROR "Cannot resolve LLVM_MINGW_ROOT to its physical directory")
endif()
file(TO_CMAKE_PATH "${_llvm_physical_root}" _llvm_mingw_root)
set(CMAKE_C_COMPILER "${_llvm_mingw_root}/bin/clang.exe")
set(CMAKE_CXX_COMPILER "${_llvm_mingw_root}/bin/clang++.exe")
set(CMAKE_RC_COMPILER "${_llvm_mingw_root}/bin/llvm-windres.exe")
set(CMAKE_AR "${_llvm_mingw_root}/bin/llvm-ar.exe")
set(CMAKE_RANLIB "${_llvm_mingw_root}/bin/llvm-ranlib.exe")
set(CMAKE_OBJDUMP "${_llvm_mingw_root}/bin/llvm-objdump.exe")
# The application calls GetDpiForWindow and supports Windows 10 and newer.
set(CMAKE_C_FLAGS_INIT "-D_WIN32_WINNT=0x0A00 -DWINVER=0x0A00")
set(CMAKE_CXX_FLAGS_INIT "-D_WIN32_WINNT=0x0A00 -DWINVER=0x0A00")
# Carry libc++/unwind in the executable; do not require compiler DLLs in PATH.
set(CMAKE_EXE_LINKER_FLAGS_INIT "-static")

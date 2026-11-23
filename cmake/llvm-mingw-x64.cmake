# Experimental native Windows toolchain for issue #189. Unpack the pinned
# UCRT LLVM-MinGW archive and set LLVM_MINGW_ROOT to that directory.
# CMake and Ninja must also be supplied explicitly; no VsDevCmd/SDK is used.
set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR AMD64)
file(TO_CMAKE_PATH "$ENV{LLVM_MINGW_ROOT}" _llvm_mingw_root)
# Use one physical compiler/DLL prefix. Qualification found a parallel-startup
# stall when the compiler was reached through a directory junction on Windows.
file(REAL_PATH "${_llvm_mingw_root}" _llvm_mingw_root)
if(NOT EXISTS "${_llvm_mingw_root}/bin/clang.exe")
    message(FATAL_ERROR "Set LLVM_MINGW_ROOT to the unpacked LLVM-MinGW UCRT toolchain")
endif()
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

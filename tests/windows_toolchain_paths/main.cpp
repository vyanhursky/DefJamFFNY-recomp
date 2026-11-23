#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <d3d11.h>
#include <mfapi.h>
#include <xaudio2.h>
#include <dbghelp.h>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>
extern "C" int host_tls_check(void);

int main()
{
    // Reference these imports without opening a device or playing audio.
    auto volatile d3d = &D3D11CreateDevice;
    auto volatile media = &MFStartup;
    auto volatile audio = &XAudio2Create;
    auto volatile symbols = &SymFromAddr;
    if (!d3d || !media || !audio || !symbols || host_tls_check()) return 1;
    if (GetACP() != 65001) return 2;
    const char *name = u8"caf\u00e9-\u043f\u0440\u043e\u0431\u0430.txt";
    const auto path = std::filesystem::u8path(name);
    std::vector<int> values{2, 3, 5};
    {
        std::ofstream stream(name);
        stream << values.at(2);
        if (!stream) return 3;
    }
    if (GetFileAttributesW(L"caf\u00e9-\u043f\u0440\u043e\u0431\u0430.txt") == INVALID_FILE_ATTRIBUTES) return 4;
    std::ifstream stream(name);
    int value = 0;
    stream >> value;
    if (value != 5 || !std::filesystem::exists(path)) return 5;
    stream.close();
    if (!std::filesystem::remove(path)) return 6;
    std::cout << "C/C++/archive/TLS/Windows imports/manifest/UTF-8 paths: pass\n";
    return 0;
}

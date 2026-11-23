<# Experimental, opt-in LLVM-MinGW build checks (#189). Does not run the app or game, install
   prerequisites, or change Setup's default. Use standalone CMake/Ninja and the pinned UCRT archive.
   Full game builds require an existing fresh lift in this checkout. #>
param(
    [Parameter(Mandatory=$true)][string]$ToolchainRoot,
    [Parameter(Mandatory=$true)][string]$CMakePath,
    [Parameter(Mandatory=$true)][string]$NinjaPath,
    [ValidateSet('runtime','app','game-sources','game')][string]$Mode = 'runtime',
    [string]$ToolkitDir = '',
    [ValidateRange(1,64)][int]$Jobs = 8
)
$ErrorActionPreference = 'Stop'
$repo189 = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$root189 = (Resolve-Path -LiteralPath $ToolchainRoot).Path
$cmake189 = (Resolve-Path -LiteralPath $CMakePath).Path
$ninja189 = (Resolve-Path -LiteralPath $NinjaPath).Path
$toolkit189 = if ($ToolkitDir) { (Resolve-Path -LiteralPath $ToolkitDir).Path } else {
    (Resolve-Path -LiteralPath (Join-Path $repo189 'tools/xboxrecomp')).Path
}
$build189 = Join-Path $repo189 "build/llvm-mingw-$Mode"
$logs189 = Join-Path $repo189 "logs/windows-toolchain-spike/$Mode"
New-Item -ItemType Directory -Force $logs189,(Join-Path $logs189 'tmp') | Out-Null
$saved189 = @{}
foreach ($name189 in 'PATH','TMP','TEMP','LLVM_MINGW_ROOT','LLVM_MINGW_PYTHON','INCLUDE','LIB','LIBPATH','CL','_CL_') {
    $saved189[$name189] = [Environment]::GetEnvironmentVariable($name189, 'Process')
}
function Invoke-Spike189([string]$program189, [string[]]$arguments189, [string]$step189) {
    $log189 = Join-Path $logs189 "$step189.log"
    & $program189 @arguments189 *> $log189
    $exit189 = $LASTEXITCODE
    Get-Content -LiteralPath $log189 -Tail 20
    if ($exit189) { throw "$step189 failed ($exit189): $log189" }
}
Push-Location $repo189
try {
    $env:LLVM_MINGW_ROOT = $root189
    $python189 = (Get-Command python -ErrorAction Stop).Source
    $env:LLVM_MINGW_PYTHON = $python189
    $env:PATH = "$root189/bin;$(Split-Path $cmake189);$(Split-Path $ninja189);$env:PATH"
    $env:TMP = Join-Path $logs189 'tmp'
    $env:TEMP = $env:TMP
    # A developer shell must not silently supply SDK headers/libraries or injected flags.
    foreach ($name189 in 'INCLUDE','LIB','LIBPATH','CL','_CL_') {
        [Environment]::SetEnvironmentVariable($name189, $null, 'Process')
    }
    Invoke-Spike189 "$root189/bin/clang.exe" @('--version') 'compiler'
    $type189 = if ($Mode -eq 'game') { 'RelWithDebInfo' } else { 'Release' }
    $args189 = @("-DCMAKE_TOOLCHAIN_FILE=$repo189/cmake/llvm-mingw-x64.cmake",
        "-DCMAKE_MAKE_PROGRAM=$ninja189", "-DCMAKE_BUILD_TYPE=$type189", "-DXBOXRECOMP_DIR=$toolkit189")
    if ($Mode -eq 'game-sources') {
        $compile189 = @('scripts/compile-game-sources.py', '--build', $build189)
        foreach ($arg189 in $args189) { $compile189 += "--cmake-arg=$arg189" }
        Invoke-Spike189 $python189 $compile189 'game-sources'
    } else {
        $game189 = if ($Mode -eq 'game') { 'ON' } else { 'OFF' }
        $app189 = if ($Mode -eq 'app') { 'ON' } else { 'OFF' }
        if ($Mode -eq 'game' -and -not (Test-Path 'src/recomp/gen/recomp_0000.c')) {
            throw 'Full game mode needs a fresh lift; no stand-in game will be certified.'
        }
        if ($Mode -eq 'game') {
            $state189 = @('scripts/pipeline-state.py')
            $identity189 = @('--preset','llvm-mingw-game','--toolkit',$toolkit189)
            Invoke-Spike189 $python189 ($state189 + @('verify-lift') + $identity189) 'verify-lift'
            Invoke-Spike189 $python189 ($state189 + @('begin-build') + $identity189) 'begin-build'
        }
        Invoke-Spike189 $cmake189 (@('-S','.', '-B',$build189,'-G','Ninja',
            "-DDEFJAM_BUILD_GAME=$game189", "-DDEFJAM_BUILD_APP=$app189") + $args189) 'configure'
        $targets189 = if ($Mode -eq 'app') { @('--target','defjam_app') } else { @() }
        Invoke-Spike189 $cmake189 (@('--build',$build189) + $targets189 + @('--','-k','0','-j',"$Jobs")) 'build'
        if ($Mode -eq 'game') {
            Invoke-Spike189 $python189 ($state189 + @('record-build') + $identity189) 'record-build'
            Invoke-Spike189 $python189 ($state189 + @('verify-build') + $identity189) 'verify-build'
        }
    }
    Write-Host "PASS: $Mode build check. No gameplay, installer or performance qualification is implied. Logs: $logs189"
} finally {
    Pop-Location
    foreach ($name189 in $saved189.Keys) {
        [Environment]::SetEnvironmentVariable($name189, $saved189[$name189], 'Process')
    }
}

<#
.SYNOPSIS
  Launch xemu on the same disc image the port runs, as a behaviour reference.

.DESCRIPTION
  xemu is the low-level emulator we compare against: ground truth for what the title should be showing on a
  given screen, and for its native frame rate. It is not part of the port and nothing in the repository
  depends on it.

  The console files it needs are the user's own and are copyrighted, so xemu and its BIOS, boot ROM, hard
  disk image and EEPROM all live with the game data under $env:DEFJAM_DATA\tools\xemu. None of it is ever
  copied into this repository.

  Screenshots use xemu's own capture, from its menu, which writes only the emulator's output to
  $env:DEFJAM_DATA\reference. Do not screenshot the desktop to capture a reference: it captures whatever
  else is on screen, and the result is both useless and a privacy problem.

  Reference images stay out of the repository as well. They are frames of a commercial game. Per
  docs/02-test-plan.md, tests/golden holds hashes and diff masks, never imagery.

.EXAMPLE
  .\scripts\xemu-reference.ps1
#>
param(
    [string]$DataDir = $(if ($env:DEFJAM_DATA) { $env:DEFJAM_DATA } else { "C:\Users\Vlad\code\defjam" })
)
$ErrorActionPreference = "Stop"
$xemu = Join-Path $DataDir "tools\xemu\xemu.exe"
if (-not (Test-Path $xemu)) { throw "xemu not found at $xemu" }

$iso = Get-ChildItem (Join-Path $DataDir "xiso") -Filter *.iso -ErrorAction SilentlyContinue |
       Select-Object -First 1
if (-not $iso) { throw "no disc image under $DataDir\xiso" }

$shots = Join-Path $DataDir "reference"
New-Item -ItemType Directory -Force $shots | Out-Null

Write-Host "disc:        $($iso.Name)"
Write-Host "screenshots: $shots   (capture from xemu's own menu)"
Start-Process -FilePath $xemu | Out-Null

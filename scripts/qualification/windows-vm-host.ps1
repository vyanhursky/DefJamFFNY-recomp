<# Scoped Hyper-V worker for the owner's disposable Windows setup qualification.
   Requests/results stay in a private root. It never formats host disks, changes
   host features/security, uninstalls software, or controls unrelated VMs. #>
param([Parameter(Mandatory=$true)][string]$Root, [int]$Minutes = 240)
$ErrorActionPreference = 'Stop'
$vmRoot = [IO.Path]::GetFullPath($Root).TrimEnd('\')
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Hyper-V worker requires administrator elevation' }
Import-Module Hyper-V
New-Item -ItemType Directory -Force -Path "$vmRoot/control/requests","$vmRoot/control/results","$vmRoot/vms","$vmRoot/logs" | Out-Null
function Save-Result($id, $value) {
    $file = Join-Path $vmRoot "control/results/$id.json"
    $text = $value | ConvertTo-Json -Depth 12
    [IO.File]::WriteAllText($file + '.pending', $text, [Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath ($file + '.pending') -Destination $file -Force
}
function Private-Path([string]$value) {
    $path = [IO.Path]::GetFullPath($value)
    if (-not $path.StartsWith($vmRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Path outside the private VM root' }
    return $path
}
function Owned-VM([string]$name) {
    if ($name -notin 'DefJam-Toolchain-Win11','DefJam-Toolchain-Win10') { throw 'Unexpected VM name' }
    $vm = Get-VM -Name $name -ErrorAction Stop
    if ($vm.Notes -ne "DefJam setup qualification; root=$vmRoot") { throw 'VM ownership marker differs' }
    return $vm
}
function Guest-Credential {
    $secret = Get-Content -Raw -Encoding UTF8 -LiteralPath "$vmRoot/secrets/guests.json" | ConvertFrom-Json
    Add-Type -AssemblyName System.Security
    $bytes = [Security.Cryptography.ProtectedData]::Unprotect(
        [Convert]::FromBase64String($secret.admin_dpapi), $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)
    $password = [Text.Encoding]::UTF8.GetString($bytes)
    $credential = [PSCredential]::new($secret.admin_name, (ConvertTo-SecureString $password -AsPlainText -Force))
    [Array]::Clear($bytes, 0, $bytes.Length); $password = $null
    return $credential
}
function Execute-Request($request) {
    $name = [string]$request.vm
    if ($request.operation -eq 'inspect') {
        return @{ switches=@(Get-VMSwitch | Select-Object Name,SwitchType); vms=@(Get-VM | Where-Object Name -like 'DefJam-Toolchain-*' | Select-Object Name,State,ProcessorCount,MemoryStartup,Uptime,Heartbeat) }
    }
    if ($name -notin 'DefJam-Toolchain-Win11','DefJam-Toolchain-Win10') { throw 'Unexpected VM name' }
    if ($request.operation -eq 'create') {
        if (Get-VM -Name $name -ErrorAction SilentlyContinue) { $vm=Owned-VM $name; return @{vm=$name;state=[string]$vm.State;reused=$true} }
        $switch = Get-VMSwitch -Name 'Default Switch' -ErrorAction Stop
        $folder = Private-Path "$vmRoot/vms/$name"
        New-Item -ItemType Directory -Force -Path $folder | Out-Null
        $disk = Join-Path $folder 'system.vhdx'
        if (Test-Path -LiteralPath $disk) { throw 'Unregistered disk exists; refusing to overwrite it' }
        New-VHD -Path $disk -Dynamic -SizeBytes 64GB | Out-Null
        $vm = New-VM -Name $name -Path $folder -Generation 2 -VHDPath $disk -MemoryStartupBytes 6GB -SwitchName $switch.Name
        Set-VM -VM $vm -Notes "DefJam setup qualification; root=$vmRoot" -AutomaticStartAction Nothing -AutomaticStopAction ShutDown -AutomaticCheckpointsEnabled $false
        Set-VMProcessor -VMName $name -Count 2
        Set-VMMemory -VMName $name -DynamicMemoryEnabled $false
        Set-VMFirmware -VMName $name -EnableSecureBoot On -SecureBootTemplate MicrosoftWindows
        if ($name -like '*Win11') { Set-VMKeyProtector -VMName $name -NewLocalKeyProtector; Enable-VMTPM -VMName $name }
        Enable-VMIntegrationService -VMName $name -Name 'Guest Service Interface'
        return @{vm=$name;state='Off';cpu=2;ram_gib=6;disk_max_gib=64}
    }
    $vm = Owned-VM $name
    switch ($request.operation) {
        'attach' {
            if ($vm.State -ne 'Off') { throw 'Media attachment requires the owned VM to be off' }
            $iso = Private-Path ([string]$request.iso)
            $answer = Private-Path ([string]$request.answer_iso)
            if (-not (Test-Path -LiteralPath $iso) -or -not (Test-Path -LiteralPath $answer)) { throw 'Missing installation media' }
            if ([IO.Path]::GetExtension($iso) -ne '.iso' -or [IO.Path]::GetExtension($answer) -ne '.iso') { throw 'Expected ISO media' }
            if ([string]$request.iso_sha256 -notmatch '^[a-fA-F0-9]{64}$' -or
                (Get-FileHash -LiteralPath $iso -Algorithm SHA256).Hash -ne $request.iso_sha256) { throw 'Windows ISO does not match the expected published SHA256' }
            if (Get-VMDvdDrive -VMName $name) { throw 'Media already attached; inspect before replacing it' }
            $dvd = Add-VMDvdDrive -VMName $name -Path $iso -Passthru
            Add-VMDvdDrive -VMName $name -Path $answer | Out-Null
            Set-VMFirmware -VMName $name -FirstBootDevice $dvd
            return @{vm=$name;media_attached=$true}
        }
        'start' {
            if ($vm.State -ne 'Off') { throw 'Guest must be off before starting it' }
            $others = @(Get-VM | Where-Object { $_.Name -like 'DefJam-Toolchain-*' -and $_.Name -ne $name -and $_.State -ne 'Off' })
            if ($others.Count) { throw 'Only one qualification VM may run at a time' }
            if ((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory -lt 12MB) { throw 'Require at least 12 GiB free host RAM before starting a guest' }
            if ($request.boot_installer -eq $true -and @(Get-VMDvdDrive -VMName $name).Count -ne 2) { throw 'Installer boot requires both private ISOs' }
            Start-VM -VM $vm | Out-Null
            if ($request.boot_installer -eq $true) {
                # Only a space during this fresh DVD boot, never arbitrary text
                # or keys in a host window. Microsoft Msvm_Keyboard TypeKey API.
                $keyboard = Get-CimInstance -Namespace root/virtualization/v2 -ClassName Msvm_Keyboard -Filter "SystemName='$($vm.Id)'"
                if (-not $keyboard) { throw 'Owned guest keyboard was not found' }
                foreach ($attempt in 1..8) {
                    Start-Sleep -Seconds 1
                    $key = Invoke-CimMethod -InputObject $keyboard -MethodName TypeKey -Arguments @{keyCode=[uint32]32}
                    if ($key.ReturnValue -ne 0) { throw 'Guest DVD boot key failed' }
                }
            }
            return @{vm=$name;state=[string](Get-VM -Name $name).State}
        }
        'stop' { Stop-VM -VM $vm -TurnOff -Force; return @{vm=$name;state='Off';forced=$true} }
        'network' {
            if ($request.connected -eq $true) {
                Connect-VMNetworkAdapter -VMName $name -SwitchName 'Default Switch'
            } elseif ($request.connected -eq $false) {
                Disconnect-VMNetworkAdapter -VMName $name
            } else { throw 'Network request requires a boolean connected field' }
            return @{vm=$name;network=@(Get-VMNetworkAdapter -VMName $name | Select-Object Name,SwitchName,Connected)}
        }
        'checkpoint' {
            if ([string]$request.label -notmatch '^[A-Za-z0-9_-]{1,60}$') { throw 'Invalid checkpoint label' }
            $snapshot = Checkpoint-VM -VM $vm -SnapshotName $request.label -Passthru
            return @{vm=$name;snapshot=[string]$snapshot.Id;label=$request.label}
        }
        'restore' {
            if ($vm.State -ne 'Off') { throw 'Checkpoint restore requires the owned VM to be off' }
            if ([string]$request.label -notmatch '^[A-Za-z0-9_-]{1,60}$') { throw 'Invalid checkpoint label' }
            $snapshots = @(Get-VMSnapshot -VMName $name -Name $request.label)
            if ($snapshots.Count -ne 1) { throw 'Require exactly one matching checkpoint' }
            Restore-VMSnapshot -VMSnapshot $snapshots[0] -Confirm:$false
            return @{vm=$name;restored=$request.label}
        }
        'guest' {
            $script = Private-Path ([string]$request.script)
            if (-not $script.StartsWith("$vmRoot\guest-scripts\", [StringComparison]::OrdinalIgnoreCase)) { throw 'Guest script outside the staged guest-scripts folder' }
            $timeout = [Math]::Min(3600, [Math]::Max(30, [int]$request.timeout_seconds))
            $job = Invoke-Command -VMName $name -Credential (Guest-Credential) -FilePath $script -ArgumentList @($request.arguments) -AsJob
            if (-not (Wait-Job -Job $job -Timeout $timeout)) {
                if ($request.readiness_probe -eq $true) {
                    Stop-Job -Job $job
                    Remove-Job -Job $job -Force
                    return @{ready=$false;reason='PowerShell Direct is not ready yet'}
                }
                Stop-VM -VM $vm -TurnOff -Force
                Stop-Job -Job $job
                throw 'Guest command timed out; the disposable guest was powered off'
            }
            try {
                $output = @(Receive-Job -Job $job -ErrorAction Stop)
                if ($job.State -ne 'Completed') { throw 'Guest job did not complete successfully' }
                return $output
            } finally { Remove-Job -Job $job -Force }
        }
        'copy' {
            $source = Private-Path ([string]$request.source)
            if ([string]$request.destination -notmatch '^C:\\DJQual\\' -or
                ([string]$request.destination).Substring(3) -match '(^|[\\/])\.\.($|[\\/])|:') { throw 'Guest destination must be under C:\DJQual' }
            Copy-VMFile -VMName $name -SourcePath $source -DestinationPath $request.destination -FileSource Host -CreateFullPath
            return @{vm=$name;copied=$true}
        }
        default { throw 'Unsupported VM operation' }
    }
}
Save-Result 'worker' @{ready=$true;elevated=$true;deadline_utc=(Get-Date).ToUniversalTime().AddMinutes($Minutes).ToString('o')}
$deadline = (Get-Date).AddMinutes([Math]::Min(480, [Math]::Max(10,$Minutes)))
while ((Get-Date) -lt $deadline -and -not (Test-Path -LiteralPath "$vmRoot/control/stop")) {
    foreach ($file in @(Get-ChildItem -LiteralPath "$vmRoot/control/requests" -Filter '*.json' -File | Sort-Object Name)) {
        if ($file.BaseName -notmatch '^[A-Za-z0-9_-]+$') { continue }
        $id = $file.BaseName
        if (Test-Path -LiteralPath "$vmRoot/control/results/$id.json") { continue }
        try { $request=Get-Content -Raw -Encoding UTF8 -LiteralPath $file.FullName | ConvertFrom-Json; $data=Execute-Request $request; Save-Result $id @{success=$true;data=$data;utc=(Get-Date).ToUniversalTime().ToString('o')} }
        catch { Save-Result $id @{success=$false;error=$_.Exception.Message;utc=(Get-Date).ToUniversalTime().ToString('o')} }
    }
    Start-Sleep -Seconds 2
}
# Stop only this worker's owned guests when its bounded lifetime ends.
foreach ($name in 'DefJam-Toolchain-Win11','DefJam-Toolchain-Win10') {
    try { $vm=Owned-VM $name; if ($vm.State -ne 'Off') { Stop-VM -VM $vm -TurnOff -Force } } catch { }
}
Save-Result 'worker-stopped' @{stopped=$true;utc=(Get-Date).ToUniversalTime().ToString('o')}

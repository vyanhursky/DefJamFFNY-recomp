<# Runs through PowerShell Direct inside a disposable qualification guest only.
   Host credentials are not arguments. Interactive scheduled tasks run under
   the guest's standard test account and record token/account evidence. #>
param($Settings)
$ErrorActionPreference = 'Stop'
$root = 'C:\DJQual'
New-Item -ItemType Directory -Force -Path $root,"$root\jobs","$root\evidence" | Out-Null
if ($Settings.mode -eq 'inventory') {
    $os = Get-CimInstance Win32_OperatingSystem
    $vs = @('C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe',
            'C:\Program Files (x86)\Windows Kits\10\Include', 'C:\Program Files\Microsoft Visual Studio')
    $present = @($vs | Where-Object { Test-Path -LiteralPath $_ })
    $administrators = @(Get-LocalGroupMember -SID 'S-1-5-32-544' | Select-Object -ExpandProperty Name)
    $result = @{os=$os.Caption;version=$os.Version;build=$os.BuildNumber;architecture=$os.OSArchitecture;
        developer_paths_present=$present;administrators=$administrators;
        standard_account=([string]"$env:COMPUTERNAME\DJQualUser");
        standard_is_administrator=($administrators -contains "$env:COMPUTERNAME\DJQualUser");
        free_disk_bytes=(Get-PSDrive C).Free;cpu_count=$env:NUMBER_OF_PROCESSORS;
        standard_desktop_present=(@(Get-Process -Name explorer -IncludeUserName -ErrorAction SilentlyContinue | Where-Object UserName -eq "$env:COMPUTERNAME\DJQualUser").Count -gt 0);
        free_memory_kib=$os.FreePhysicalMemory}
    $result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath "$root\evidence\clean-inventory.json" -Encoding UTF8
    if ($present.Count -or $result.standard_is_administrator) { throw 'Guest is not the required clean standard-account environment' }
    return $result
}
if ($Settings.mode -ne 'run-standard') { throw 'Unsupported guest operation' }
$id = [string]$Settings.id
if ($id -notmatch '^[A-Za-z0-9_-]{1,60}$') { throw 'Invalid guest job ID' }
if (-not ([string]$Settings.program).StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Program outside qualification workspace' }
$taskName = 'DefJamQualification-' + $id
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) { throw 'Guest task already exists' }
$request = "$root\jobs\$id.json"
$done = "$root\evidence\$id-result.json"
if (Test-Path -LiteralPath $done) { throw 'Guest evidence ID already exists' }
$Settings | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $request -Encoding UTF8
# Allow the standard test user to write only this disposable qualification tree.
$acl = Get-Acl -LiteralPath $root
$rule = [Security.AccessControl.FileSystemAccessRule]::new("$env:COMPUTERNAME\DJQualUser",'Modify','ContainerInherit,ObjectInherit','None','Allow')
$acl.SetAccessRule($rule)
Set-Acl -LiteralPath $root -AclObject $acl
$wrapper = "$root\jobs\$id.ps1"
$body = @'
param([string]$Request)
$ErrorActionPreference = 'Stop'
$settings = Get-Content -Raw -LiteralPath $Request | ConvertFrom-Json
$id = $settings.id
$root = 'C:\DJQual'
$principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
$result = @{id=$id;account=[Security.Principal.WindowsIdentity]::GetCurrent().Name;
    elevated=$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator);
    started_utc=(Get-Date).ToUniversalTime().ToString('o')}
try {
    if ($result.elevated) { throw 'Test must execute as the standard user' }
    $arguments = @($settings.arguments | ForEach-Object { [string]$_ })
    Set-Location -LiteralPath $root
    if (-not (Test-Path -LiteralPath $settings.program -PathType Leaf)) { throw 'Qualification program is missing' }
    # Windows PowerShell represents native stderr as error records. Preserve
    # the program's actual exit code for intentionally failing scenarios.
    $ErrorActionPreference = 'Continue'
    & $settings.program @arguments *> "$root\evidence\$id.out"
    $result.exit_code = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
} catch { $result.error=$_.Exception.Message; $result.exit_code=-1 }
$result.finished_utc=(Get-Date).ToUniversalTime().ToString('o')
$result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath "$root\evidence\$id-result.json" -Encoding UTF8
'@
[IO.File]::WriteAllText($wrapper,$body,[Text.UTF8Encoding]::new($true))
$action = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Argument "-NoProfile -File `"$wrapper`" -Request `"$request`"" -WorkingDirectory $root
$principal = New-ScheduledTaskPrincipal -UserId "$env:COMPUTERNAME\DJQualUser" -LogonType Interactive -RunLevel Limited
$options = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 50) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
try {
    Register-ScheduledTask -TaskName $taskName -Action $action -Principal $principal -Settings $options | Out-Null
    Start-ScheduledTask -TaskName $taskName
    $deadline = (Get-Date).AddSeconds([Math]::Min(3000,[Math]::Max(30,[int]$Settings.timeout_seconds)))
    while (-not (Test-Path -LiteralPath $done) -and (Get-Date) -lt $deadline) { Start-Sleep -Seconds 2 }
    if (-not (Test-Path -LiteralPath $done)) {
        Stop-ScheduledTask -TaskName $taskName
        throw 'Standard-user task timed out; power off the disposable guest before retrying'
    }
    return (Get-Content -Raw -LiteralPath $done | ConvertFrom-Json)
} finally { Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue }

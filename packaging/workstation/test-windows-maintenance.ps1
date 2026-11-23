param(
    [Parameter(Mandatory)][string]$Compiler,
    [Parameter(Mandatory)][string]$Python,
    [Parameter(Mandatory)][string]$Scratch
)

$ErrorActionPreference = 'Stop'
$Scratch = (New-Item -ItemType Directory -Path $Scratch).FullName
$appId = 'EMFixture-' + [guid]::NewGuid().ToString('N').Substring(0, 16)
$app = Join-Path $Scratch 'installed'
$key = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\${appId}_is1"
$environmentKey = 'HKCU:\Environment'
$environmentRegistry = Get-Item -LiteralPath $environmentKey
$readRaw = [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames
$originalPath = $environmentRegistry.GetValue('Path', $null, $readRaw)
$originalPathKind = if ($null -ne $originalPath) { $environmentRegistry.GetValueKind('Path') }
$originalLocalAppData = $env:LOCALAPPDATA
$originalCodexHome = $env:CODEX_HOME
$originalClaudeHome = $env:CLAUDE_CONFIG_DIR
$env:LOCALAPPDATA = Join-Path $Scratch 'localappdata'
$env:CODEX_HOME = Join-Path $Scratch 'codex-profile'
$env:CLAUDE_CONFIG_DIR = Join-Path $Scratch 'claude-profile'
$profile = Join-Path $env:LOCALAPPDATA 'EngineeringMemory'
foreach ($directory in (Join-Path $profile 'config'), (Join-Path $profile 'data/archive'), $env:CODEX_HOME, $env:CLAUDE_CONFIG_DIR) {
    $null = New-Item -ItemType Directory -Path $directory -Force
}
Set-Content -LiteralPath (Join-Path $profile 'config/compose.env') -Value @(
    'PRODUCT_PROVIDER_MODEL=custom_openai/fixture',
    'PRODUCT_PROVIDER_API_KEY=test-fixture-only',
    'WORKSTATION_HINDSIGHT_PORT=4501',
    'WORKSTATION_HTTP_PROXY=http://127.0.0.1:4502'
)
Set-Content -LiteralPath (Join-Path $profile 'config/app.env') -Value 'ENGINEERING_MEMORY_LLM__BASE_URL=http://127.0.0.1:4500/v1'
Set-Content -LiteralPath (Join-Path $profile 'data/archive/conversation.json') -Value '{"content":"synthetic fixture"}'
Set-Content -LiteralPath (Join-Path $profile 'data/import-state.db') -Value 'synthetic import state'
Set-Content -LiteralPath (Join-Path $env:CODEX_HOME 'config.toml') -Value '[mcp_servers.unrelated]'
Set-Content -LiteralPath (Join-Path $env:CLAUDE_CONFIG_DIR '.claude.json') -Value '{"mcpServers":{"unrelated":{}}}'

function Get-PrivateSnapshot {
    foreach ($directory in $profile,$env:CODEX_HOME,$env:CLAUDE_CONFIG_DIR) {
        Get-ChildItem -LiteralPath $directory -Recurse -File | Sort-Object FullName | ForEach-Object {
            "$($_.FullName)|$((Get-FileHash -LiteralPath $_.FullName).Hash)"
        }
    }
}
$profileBefore = (Get-PrivateSnapshot) -join '`n'

function Compile-Fixture([string]$Name, [string]$Version, [string]$Content) {
    $folder = (New-Item -ItemType Directory -Path (Join-Path $Scratch $Name)).FullName
    $payload = (New-Item -ItemType Directory -Path (Join-Path $folder 'payload')).FullName
    $runtime = (New-Item -ItemType Directory -Path (Join-Path $payload '_internal')).FullName
    Set-Content -LiteralPath (Join-Path $payload 'engineering-memory.exe') -Value 'fixture launcher'
    Set-Content -LiteralPath (Join-Path $runtime 'engine.dll') -Value $Content
    if ($Name -eq 'first') {
        Set-Content -LiteralPath (Join-Path $runtime 'obsolete.dll') -Value 'retired fixture'
        $metadata = (New-Item -ItemType Directory -Path (Join-Path $runtime 'fixture-0.0.2.dist-info')).FullName
        Set-Content -LiteralPath (Join-Path $metadata 'METADATA') -Value 'Version: 0.0.2'
    }
    if ($Name -eq 'newer') {
        $upcoming = (New-Item -ItemType Directory -Path (Join-Path $payload 'upcoming')).FullName
        Set-Content -LiteralPath (Join-Path $upcoming 'new.dll') -Value 'new runtime file'
    }
    $identity = & $Python "$PSScriptRoot/windows_manifest.py" $Version $payload
    if ($LASTEXITCODE -ne 0) { throw 'Manifest generation failed' }
    if ($Name -eq 'bad') { Set-Content -LiteralPath (Join-Path $runtime 'engine.dll') -Value 'mismatched bytes' }
    & $Compiler '/Qp' "/DAppVersion=$Version" "/DAppIdentity=$appId" "/DBuildIdentity=$identity" "/DPayload=$payload" "/O$folder" "$PSScriptRoot/windows.iss" | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Failed to compile $Name" }
    return @{
        Installer = Join-Path $folder "engineering-memory-$Version-windows-x64-setup.exe"
        Identity = $identity
    }
}

function Get-InstalledSnapshot {
    $entries = @(Get-ChildItem -LiteralPath $app -Recurse -File | Sort-Object FullName | ForEach-Object {
        "$(($_.FullName).Substring($app.Length))|$((Get-FileHash -LiteralPath $_.FullName).Hash)|$($_.LastWriteTimeUtc.Ticks)"
    })
    $registration = Get-Item -LiteralPath $key
    $values = @($registration.GetValueNames() | Sort-Object | ForEach-Object { "$_=$($registration.GetValue($_))" })
    $envPath = $environmentRegistry.GetValue('Path', $null, $readRaw)
    return ($entries -join "`n") + "`n" + ($values -join "`n") + "`n" + $envPath
}

function Invoke-Fixture($Build, [string]$Switch, [string]$ExpectedMode, [bool]$Succeeds) {
    $log = Join-Path $Scratch ([guid]::NewGuid().ToString('N') + '.log')
    $p = Start-Process -FilePath $Build.Installer -ArgumentList $Switch,'/SUPPRESSMSGBOXES','/NORESTART',('/DIR="' + $app + '"'),('/LOG="' + $log + '"') -WindowStyle Hidden -Wait -PassThru
    if (($p.ExitCode -eq 0) -ne $Succeeds -or -not (Select-String -LiteralPath $log -SimpleMatch "EM-MAINTENANCE: $ExpectedMode" -Quiet)) {
        Get-Content -LiteralPath $log | Select-Object -Last 30 | Out-Host
        throw "Expected $ExpectedMode ($Switch), got exit code $($p.ExitCode). Log: $log"
    }
    if (Select-String -LiteralPath $log -SimpleMatch 'setup --installer-ui' -Quiet) {
        throw 'The silent installer attempted to run the configuration helper'
    }
}

function Assert-Build($Build) {
    $actual = (Get-FileHash -LiteralPath (Join-Path $app 'engineering-memory.build')).Hash
    if ($actual -ne $Build.Identity) { throw 'Wrong installed identity' }
}

try {
    $first = Compile-Fixture 'first' '0.0.2' 'A'
    $different = Compile-Fixture 'different' '0.0.2' 'B'
    $newer = Compile-Fixture 'newer' '0.0.10' 'C'
    $bad = Compile-Fixture 'bad' '0.0.11' 'D'
    Invoke-Fixture $first '/VERYSILENT' 'fresh' $true
    Assert-Build $first
    foreach ($switch in '/SILENT','/VERYSILENT') {
        $unchanged = Get-InstalledSnapshot
        Invoke-Fixture $first $switch 'identical' $true
        Invoke-Fixture $different $switch 'different-build' $false
        if ((Get-InstalledSnapshot) -cne $unchanged) { throw 'Same-build no-op or blocked replacement changed installation' }
    }
    $separate = (New-Item -ItemType Directory -Path (Join-Path $Scratch 'outside')).FullName
    $link = Join-Path $app 'upcoming'
    $null = New-Item -ItemType Junction -Path $link -Target $separate
    Invoke-Fixture $newer '/SILENT' 'The package cannot be copied to this location.' $false
    if (Get-ChildItem -LiteralPath $separate) { throw 'The update wrote through a junction' }
    (Get-Item -LiteralPath $link).Delete()

    Invoke-Fixture $newer '/SILENT' 'update' $true
    Assert-Build $newer
    if (Test-Path -LiteralPath (Join-Path $app '_internal/obsolete.dll')) { throw 'An obsolete payload file survived the update' }
    if (Test-Path -LiteralPath (Join-Path $app '_internal/fixture-0.0.2.dist-info')) { throw 'An obsolete metadata directory survived the update' }
    foreach ($switch in '/SILENT','/VERYSILENT') {
        $unchanged = Get-InstalledSnapshot
        Invoke-Fixture $first $switch 'downgrade' $false
        if ((Get-InstalledSnapshot) -cne $unchanged) { throw 'Blocked downgrade changed installation' }
    }
    $file = Join-Path $app '_internal/engine.dll'
    Set-Content -LiteralPath $file -Value 'damaged bytes'
    Invoke-Fixture $newer '/SILENT' 'repair' $false
    Invoke-Fixture $first '/VERYSILENT' 'downgrade' $false
    Remove-Item -LiteralPath $file
    Invoke-Fixture $newer '/VERYSILENT' 'repair' $false
    if (Test-Path -LiteralPath $file) { throw 'Silent repair copied the missing file' }
    Copy-Item -LiteralPath (Join-Path $Scratch 'newer/payload/_internal/engine.dll') -Destination $file
    Invoke-Fixture $bad '/VERYSILENT' 'installation verification failed' $false
    if ((Get-Item -LiteralPath $key).GetValueNames() -match 'BuildIdentity$') {
        throw 'An unverified update recorded its build identity'
    }
    $profileAfter = (Get-PrivateSnapshot) -join '`n'
    if ($profileBefore -ne $profileAfter) { throw 'Silent update changed fixture private state' }
    Write-Output 'Compiled Windows maintenance matrix passed.'
} finally {
    $env:LOCALAPPDATA = $originalLocalAppData
    $env:CODEX_HOME = $originalCodexHome
    $env:CLAUDE_CONFIG_DIR = $originalClaudeHome
    $uninstaller = Get-ChildItem -LiteralPath $app -Filter 'unins*.exe' -File -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($uninstaller) {
        $null = Start-Process -FilePath $uninstaller.FullName -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART' -WindowStyle Hidden -Wait -PassThru
    }
    $currentPath = $environmentRegistry.GetValue('Path', $null, $readRaw)
    if ($null -eq $originalPath -and $currentPath -ceq '') {
        Remove-ItemProperty -LiteralPath $environmentKey -Name Path
    } elseif ($null -ne $originalPath -and ($currentPath -cne $originalPath -or $environmentRegistry.GetValueKind('Path') -ne $originalPathKind)) {
        New-ItemProperty -LiteralPath $environmentKey -Name Path -Value $originalPath -PropertyType $originalPathKind -Force | Out-Null
    }
}

param(
    [Parameter(Mandatory)][string]$Compiler,
    [Parameter(Mandatory)][string]$Python,
    [Parameter(Mandatory)][string]$Scratch
)

$ErrorActionPreference = 'Stop'
$Scratch = (New-Item -ItemType Directory -Path $Scratch).FullName
$payload = (New-Item -ItemType Directory -Path (Join-Path $Scratch 'payload')).FullName
Set-Content -LiteralPath (Join-Path $payload 'engineering-memory.exe') -Value 'fixture launcher'
$runtime = (New-Item -ItemType Directory -Path (Join-Path $payload '_internal')).FullName
Set-Content -LiteralPath (Join-Path $runtime 'fixture.dll') -Value 'fixture runtime'
$version = '0.0.2'
$identity = & $Python "$PSScriptRoot/windows_manifest.py" $version $payload
if ($LASTEXITCODE -ne 0) { throw 'Manifest generation failed' }
Copy-Item -LiteralPath "$PSScriptRoot/windows-maintenance.iss" -Destination $Scratch

# Use the installer events and controls with a synthetic helper in the test build.
$source = Get-Content -LiteralPath "$PSScriptRoot/windows.iss" -Raw
if (-not $source.Contains('    if not ExecAndCaptureOutput(AddBackslash(WizardDirValue)')) {
    throw 'The helper substitution point changed. Update the isolated fixture before running it.'
}
$source = $source.Replace('function RunSetupHelper(const Action: String; var Output: TArrayOfString): Boolean;',
    "function FixtureHelper(const Action: String; var Output: TArrayOfString): Boolean; forward;" + [Environment]::NewLine +
    "procedure FixtureTrace(const Line: String); forward;" + [Environment]::NewLine +
    'function RunSetupHelper(const Action: String; var Output: TArrayOfString): Boolean;')
$source = $source.Replace('    if not ExecAndCaptureOutput(AddBackslash(WizardDirValue)',
    "    Result := FixtureHelper(Action, Output);" + [Environment]::NewLine +
    "    Exit;" + [Environment]::NewLine +
    '    if not ExecAndCaptureOutput(AddBackslash(WizardDirValue)')
# The fixture can run on an elevated CI runner because it never opens user profiles.
$source = $source.Replace('  if IsAdmin then', '  if False then')
$source = $source.Replace('  Result := MsgBox(Prompt, mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES;', @'
  FixtureTrace('maintenance confirmation');
  Result := True;
'@.TrimEnd())
$source = $source.Replace('then UpdatePath(True)', "then Log('MCP fixture: PATH left unchanged')")
$source = $source.Replace("  if Summary <> '' then MsgBox(Summary, mbInformation, MB_OK);", '')
$source = $source.Replace('procedure CurPageChanged(CurPageID: Integer);', 'procedure ProductionPageChanged(CurPageID: Integer);')
$check = 'NextButtonClick(McpPage.ID);'
$retry = ''
$reorder = ''
if ($source.Contains('McpCheckButton')) {
    $check = 'McpCheckButton.OnClick(McpCheckButton);'
    $retry = @'
  McpRescanButton.OnClick(McpRescanButton);
  FixtureTrace('rescan ' + McpChoices.Items[1]);
  McpChoices.Checked[1] := True;
  McpCheckButton.OnClick(McpCheckButton);
  FixtureTrace('retry ' + McpChoices.Items[1]);
'@
    $reorder = @'
  if GetEnv('EM_MCP_TEST_MODE') = 'rescan-reorder' then
  begin
    McpRescanButton.OnClick(McpRescanButton);
    if McpChoices.Checked[0] and not McpChoices.Checked[1] and not McpChoices.Checked[2] then
      FixtureTrace('only unchanged review selected');
  end;
'@
    $source = $source.Replace("  Result := MsgBox('Replace the existing Engineering Memory registration for ", @'
  if Pos('conflict-', GetEnv('EM_MCP_TEST_MODE')) = 1 then
  begin
    Result := GetEnv('EM_MCP_TEST_MODE') <> 'conflict-decline';
    if GetEnv('EM_MCP_TEST_MODE') = 'conflict-stale' then
      SaveStringToFile(GetEnv('EM_MCP_TEST_PROFILE'), 'external fixture registration', False);
    Exit;
  end;
  Result := MsgBox('Replace the existing Engineering Memory registration for
'@.TrimEnd() + ' ')
}

$fixture = @'
var
  FixtureStarted, FixtureInCheck: Boolean;
  FixtureAttempts, FixtureScans: Integer;

function FixturePostMessage(Handle: HWND; Msg: LongWord; WParam, LParam: LongWord): Boolean;
  external 'PostMessageW@user32.dll stdcall';
procedure FixtureExit(Code: LongWord);
  external 'ExitProcess@kernel32.dll stdcall';

procedure FixtureTrace(const Line: String);
begin
  SaveStringToFile(GetEnv('EM_MCP_TEST_TRACE'), AnsiString(Line + #13#10), True);
end;

function FixtureEncode(const Value: String): String;
var
  I, Code: Integer;
  Digits: String;
begin
  Digits := '0123456789abcdef';
  Result := 'v';
  for I := 1 to Length(Value) do
  begin
    Code := Ord(Value[I]);
    Result := Result + Digits[1 + Code div 16] + Digits[1 + Code mod 16];
  end;
end;

procedure FixtureRow(var Output: TArrayOfString; Offset: Integer;
  const Token, State, LabelText, Profile, Diagnostic: String);
begin
  Output[Offset] := Token;
  Output[Offset + 1] := State;
  Output[Offset + 2] := FixtureEncode(LabelText);
  Output[Offset + 3] := FixtureEncode(Profile);
  Output[Offset + 4] := FixtureEncode(Diagnostic);
end;

function FixtureHelper(const Action: String; var Output: TArrayOfString): Boolean;
var
  Request: String;
  Profile: AnsiString;
  Index: Integer;
begin
  Result := False;
  if (Action = 'read') or (Action = 'read-maintenance') then
  begin
    SetArrayLength(Output, 10);
    Output[0] := InstallerProtocol;
    Output[1] := '1';
    Output[2] := StringOfChar('e', 64);
    for Index := 3 to 9 do Output[Index] := 'v';
    Result := True;
  end
  else if Action = 'save' then
  begin
    FixtureTrace('settings saved');
    SetArrayLength(Output, 1);
    Output[0] := 'saved';
    Result := True;
  end
  else if Action = 'mcp-scan' then
  begin
    FixtureScans := FixtureScans + 1;
    SetArrayLength(Output, 16);
    Output[0] := McpProtocol;
    FixtureRow(Output, 1, StringOfChar('a', 64), 'matching',
      'Codex CLI, Codex Desktop', 'C:\fixture\codex.toml', 'service_tier warning');
    if (GetEnv('EM_MCP_TEST_MODE') = 'rescan-reorder') and (FixtureScans > 1) then
    begin
      FixtureRow(Output, 6, StringOfChar('c', 64), 'absent',
        'Claude Code', 'C:\fixture\claude.json', '');
      FixtureRow(Output, 11, StringOfChar('e', 64), 'conflict',
        'Claude Desktop', 'C:\fixture\desktop.json', '');
      Result := True;
      Exit;
    end;
    if LoadStringFromFile(GetEnv('EM_MCP_TEST_PROFILE'), Profile) and
      (Profile = 'Claude Desktop fixture registration') then
      FixtureRow(Output, 6, StringOfChar('d', 64), 'matching',
        'Claude Desktop', 'C:\fixture\desktop.json', '')
    else if Pos('conflict-', GetEnv('EM_MCP_TEST_MODE')) = 1 then
      FixtureRow(Output, 6, StringOfChar('f', 64), 'conflict',
        'Claude Desktop', 'C:\fixture\desktop.json', '')
    else
      FixtureRow(Output, 6, StringOfChar('b', 64), 'absent',
        'Claude Desktop', 'C:\fixture\desktop.json', '');
    FixtureRow(Output, 11, StringOfChar('c', 64), 'absent',
      'Claude Code', 'C:\fixture\claude.json', '');
    Result := True;
  end
  else if Action = 'mcp-apply' then
  begin
    Request := GetEnv('EM_INSTALLER_UI_MCP');
    FixtureAttempts := FixtureAttempts + 1;
    FixtureTrace('apply ' + Copy(Request, 1, 1) + Copy(Request, 65, 8));
    if (Request = StringOfChar('a', 64) + ':keep') and
      (GetEnv('EM_MCP_TEST_MODE') = 'first-fails') then Exit;
    SetArrayLength(Output, 4);
    Output[0] := McpProtocol;
    Output[2] := 'passed';
    Output[3] := FixtureEncode('Restart the client.');
    if (Request = StringOfChar('a', 64) + ':keep') and
      (GetEnv('EM_MCP_TEST_MODE') = 'malformed-reply') then
    begin
      Output[1] := 'unexpected result';
      Output[3] := FixtureEncode('Unexpected process output.');
    end
    else if (Request = StringOfChar('a', 64) + ':keep') and
      (GetEnv('EM_MCP_TEST_MODE') = 'malformed-utf8') then
    begin
      Output[1] := 'already configured';
      Output[3] := 'vff';
    end
    else if (Request = StringOfChar('f', 64) + ':replace') and
      LoadStringFromFile(GetEnv('EM_MCP_TEST_PROFILE'), Profile) and
      (Profile <> 'original fixture registration') then
    begin
      Output[1] := 'blocked';
      Output[2] := 'skipped';
      Output[3] := FixtureEncode('The target or its configuration changed.');
    end
    else if (Request = StringOfChar('b', 64) + ':keep') or
      (Request = StringOfChar('f', 64) + ':replace') then
    begin
      Output[1] := 'saved';
      SaveStringToFile(GetEnv('EM_MCP_TEST_PROFILE'), 'Claude Desktop fixture registration', False);
      if GetEnv('EM_MCP_TEST_MODE') = 'saved-probe-fails' then
      begin
        Output[2] := 'failed';
        Output[3] := FixtureEncode('The installed MCP server could not complete initialization.');
      end;
    end
    else if (Request = StringOfChar('a', 64) + ':keep') or
      (Request = StringOfChar('d', 64) + ':keep') then Output[1] := 'already configured'
    else Output[1] := 'failed';
    Result := True;
  end;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  ProductionPageChanged(CurPageID);
  if WizardSilent then Exit;
  if CurPageID = wpReady then
    FixturePostMessage(WizardForm.NextButton.Handle, $00F5, 0, 0);
  if not HelpersEnabled then Exit;
  if DecisionPage <> nil then
    if CurPageID = DecisionPage.ID then
    begin
      DecisionPage.SelectedValueIndex := 0;
      FixturePostMessage(WizardForm.NextButton.Handle, $00F5, 0, 0);
    end;
  if CurPageID = SettingsPage.ID then
  begin
    DeferCheck.Checked := not ConfigureExisting;
    if ConfigureExisting then Edits[1].Text := 'fixture/model';
    UpdateSettingsButton(nil);
    FixturePostMessage(WizardForm.NextButton.Handle, $00F5, 0, 0);
  end;
  if CurPageID <> McpPage.ID then Exit;
  if FixtureInCheck then FixtureTrace('returned after ' + IntToStr(FixtureAttempts));
  if FixtureStarted then Exit;
  FixtureStarted := True;
  FixtureInCheck := True;
  McpChoices.Checked[0] := Pos('conflict-', GetEnv('EM_MCP_TEST_MODE')) <> 1;
  McpChoices.Checked[1] := True;
  __REORDER__
  if GetEnv('EM_MCP_TEST_MODE') = 'continue-with-selection' then
  begin
    if NextButtonClick(McpPage.ID) then FixtureTrace('continued with pending selection');
    FixtureExit(0);
  end;
  __CHECK__
  FixtureInCheck := False;
  FixtureTrace('first ' + McpChoices.Items[0]);
  FixtureTrace('second ' + McpChoices.Items[1]);
  FixtureTrace('third ' + McpChoices.Items[2]);
  McpChoices.ItemIndex := 0;
  ShowMcpTarget(nil);
  if Pos('service_tier', McpDetails.Text) > 0 then FixtureTrace('codex warning');
  if Pos('Could not get a client setup result.', McpDetails.Text) > 0 then FixtureTrace('fixed failure diagnostic');
  if Pos('Unexpected process output.', McpDetails.Text) > 0 then FixtureTrace('unexpected diagnostic shown');
  McpChoices.ItemIndex := 1;
  ShowMcpTarget(nil);
  if Pos('Restart the client.', McpDetails.Text) > 0 then FixtureTrace('restart guidance');
  if ConfigureExisting and (WizardForm.NextButton.Caption = '&Apply') then FixtureTrace('maintenance Apply');
  if NextButtonClick(McpPage.ID) then FixtureTrace('can continue');
  if GetEnv('EM_MCP_TEST_MODE') = 'saved-probe-fails' then
  begin
  __RETRY__
  end;
  FixtureExit(0);
end;
'@
$fixture = $fixture.Replace('__CHECK__', $check).Replace('__RETRY__', $retry).Replace('__REORDER__', $reorder)
$script = Join-Path $Scratch 'windows.iss'
Set-Content -LiteralPath $script -Value ($source + [Environment]::NewLine + $fixture) -Encoding utf8
$appId = 'EMMcpFixture-' + [guid]::NewGuid().ToString('N')
& $Compiler '/Qp' "/DAppVersion=$version" "/DAppIdentity=$appId" "/DBuildIdentity=$identity" "/DPayload=$payload" "/O$Scratch" $script
if ($LASTEXITCODE -ne 0) { throw 'MCP fixture installer compilation failed' }

$installer = Join-Path $Scratch "engineering-memory-$version-windows-x64-setup.exe"
foreach ($mode in 'both-pass', 'first-fails', 'malformed-reply', 'malformed-utf8', 'saved-probe-fails', 'rescan-reorder', 'continue-with-selection', 'conflict-decline', 'conflict-accept', 'conflict-stale', 'maintenance') {
    $trace = Join-Path $Scratch "$mode.txt"
    $profile = Join-Path $Scratch "$mode-claude.txt"
    $log = Join-Path $Scratch "$mode.log"
    $app = Join-Path $Scratch "$mode-install"
    $environment = @{
        EM_MCP_TEST_MODE = $mode
        EM_MCP_TEST_TRACE = $trace
        EM_MCP_TEST_PROFILE = $profile
    }
    if ($mode -like 'conflict-*') { [IO.File]::WriteAllText($profile, 'original fixture registration') }
    $arguments = @('/NORESTART', ('/DIR="' + $app + '"'))
    $p = $null
    try {
        if ($mode -eq 'maintenance') {
            $setup = Start-Process -FilePath $installer -ArgumentList ($arguments + @('/VERYSILENT','/SUPPRESSMSGBOXES')) -WindowStyle Hidden -Wait -PassThru
            if ($setup.ExitCode -ne 0) { throw "Could not prepare the maintenance fixture: $($setup.ExitCode)." }
        }
        $p = Start-Process -FilePath $installer -ArgumentList ($arguments + ('/LOG="' + $log + '"')) -Environment $environment -WindowStyle Hidden -PassThru
        if (-not $p.WaitForExit(20000)) { throw "MCP test timed out in $mode. See $log and $trace." }
        if ($p.ExitCode -ne 0) { throw "MCP test exited with $($p.ExitCode). See $log." }
        $lines = @(Get-Content -LiteralPath $trace)
        $applies = @($lines | Where-Object { $_ -like 'apply *' }) -join ', '
        if ($mode -eq 'continue-with-selection') {
            if ($applies -or 'continued with pending selection' -notin $lines -or (Test-Path -LiteralPath $profile)) {
                throw "Navigation unexpectedly applied a pending selection. See $trace."
            }
            "MCP wizard $mode passed."
            continue
        }
        if ($mode -eq 'rescan-reorder') {
            if ($applies -ne 'apply a:keep' -or 'only unchanged review selected' -notin $lines -or
                (Test-Path -LiteralPath $profile)) {
                throw "Expected only the unchanged profile after a reordered rescan. See $trace."
            }
            "MCP wizard $mode passed."
            continue
        }
        if ($mode -like 'conflict-*') {
            $expected = @{
                'conflict-decline' = @('', '^second .*kept.*skipped', 'original fixture registration')
                'conflict-accept' = @('apply f:replace', '^second .*saved.*passed', 'Claude Desktop fixture registration')
                'conflict-stale' = @('apply f:replace', '^second .*blocked.*skipped', 'external fixture registration')
            }[$mode]
            if ($applies -ne $expected[0] -or -not ($lines -match $expected[1]) -or
                (Get-Content -LiteralPath $profile -Raw) -ne $expected[2]) {
                throw "Unexpected replacement outcome in $mode. See $trace."
            }
            "MCP wizard $mode passed."
            continue
        }
        $expectedApplies = 'apply a:keep, apply b:keep'
        if ($mode -eq 'saved-probe-fails' -and $retry) { $expectedApplies += ', apply d:keep' }
        $returnIndex = [Array]::IndexOf($lines, 'returned after 1')
        if ($returnIndex -le [Array]::IndexOf($lines, 'apply a:keep')) { throw "No progress return after first attempt in $mode." }
        if ($applies -ne $expectedApplies -or $returnIndex -ge [Array]::IndexOf($lines, 'apply b:keep')) {
            throw "Expected both selected profiles after progress return in $mode. Requests: $applies."
        }
        if ((Get-Content -LiteralPath $profile -Raw) -ne 'Claude Desktop fixture registration') {
            throw "Claude Desktop registration was not persisted in $mode."
        }
        $codex = if ($mode -in 'first-fails', 'malformed-reply', 'malformed-utf8') { 'failed.*unavailable' } else { 'already configured.*passed' }
        $claude = if ($mode -eq 'saved-probe-fails') { 'saved.*failed' } else { 'saved.*passed' }
        if (-not ($lines -match "^first .*$codex") -or
            -not ($lines -match "^second .*$claude") -or
            -not ($lines -match '^third .*skipped') -or
            'codex warning' -notin $lines -or 'can continue' -notin $lines -or
            ($mode -ne 'saved-probe-fails' -and 'restart guidance' -notin $lines)) {
            throw "Unexpected inline results in $mode. See $trace."
        }
        if ($mode -in 'first-fails', 'malformed-reply' -and
            ('fixed failure diagnostic' -notin $lines -or 'unexpected diagnostic shown' -in $lines)) {
            throw "Unexpected failure detail in $mode. See $trace."
        }
        if ($mode -eq 'saved-probe-fails' -and (-not ($lines -match '^rescan .*saved.*failed') -or
            -not ($lines -match '^retry .*already configured.*passed'))) {
            throw "Unexpected rescan or retry result. See $trace."
        }
        if ($mode -eq 'maintenance') {
            $confirmed = [Array]::IndexOf($lines, 'maintenance confirmation')
            $saved = [Array]::IndexOf($lines, 'settings saved')
            $first = [Array]::IndexOf($lines, 'apply a:keep')
            if ($confirmed -lt 0 -or $saved -le $confirmed -or $first -le $saved -or
                'maintenance Apply' -notin $lines -or @($lines -eq 'settings saved').Count -ne 1) {
                throw "Maintenance must confirm, save once and apply in that order. See $trace."
            }
        }
        "MCP wizard $mode passed."
    } finally {
        if ($null -ne $p -and -not $p.HasExited) { Stop-Process -Id $p.Id -Force }
        $key = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$($appId)_is1"
        if (Test-Path -LiteralPath $key) { Remove-Item -LiteralPath $key }
    }
}

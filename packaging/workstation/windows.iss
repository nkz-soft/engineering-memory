#ifndef AppIdentity
  #define AppIdentity "EngineeringMemory"
#endif

[Setup]
AppId={#AppIdentity}
AppName=Engineering Memory
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\EngineeringMemory
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible and not arm64
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.22000
DisableDirPage=yes
Uninstallable=ShouldInstallPayload
CreateUninstallRegKey=ShouldInstallPayload
ChangesEnvironment=ShouldInstallPayload
SetupMutex={#AppIdentity}-setup
OutputBaseFilename=engineering-memory-{#AppVersion}-windows-x64-setup
SolidCompression=yes

[Files]
Source: "{#Payload}\engineering-memory.build"; Flags: dontcopy
Source: "{#Payload}\*"; DestDir: "{app}"; Excludes: "\engineering-memory.build"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: ShouldInstallPayload
Source: "{#Payload}\engineering-memory.build"; DestDir: "{app}"; Flags: ignoreversion; Check: ShouldInstallPayload; AfterInstall: VerifyInstalledPayload

[Code]
#include "windows-maintenance.iss"

const
  UserEnvironment = 'Environment';

procedure UpdatePath(Add: Boolean);
var
  CurrentPath, InstalledPath, Part, UpdatedPath: String;
  Separator: Integer;
  Found: Boolean;
begin
  InstalledPath := ExpandConstant('{app}');
  RegQueryStringValue(HKCU, UserEnvironment, 'Path', CurrentPath);
  Found := False;
  UpdatedPath := '';
  while CurrentPath <> '' do
  begin
    Separator := Pos(';', CurrentPath);
    if Separator = 0 then Separator := Length(CurrentPath) + 1;
    Part := Copy(CurrentPath, 1, Separator - 1);
    Delete(CurrentPath, 1, Separator);
    if CompareText(RemoveBackslashUnlessRoot(Part), InstalledPath) = 0 then
      Found := True
    else if Part <> '' then
    begin
      if UpdatedPath <> '' then UpdatedPath := UpdatedPath + ';';
      UpdatedPath := UpdatedPath + Part;
    end;
  end;
  if Add then
  begin
    if Found then Exit;
    if UpdatedPath <> '' then UpdatedPath := UpdatedPath + ';';
    UpdatedPath := UpdatedPath + InstalledPath;
  end
  else if not Found then Exit;
  if not RegWriteExpandStringValue(HKCU, UserEnvironment, 'Path', UpdatedPath) then
    Log('Could not update the user PATH.');
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and ShouldInstallPayload then
  begin
    if PayloadVerified and BuildRecorded then UpdatePath(True)
    else
    begin
      Log('EM-MAINTENANCE: installation verification failed');
      if not WizardSilent then
        MsgBox('Setup could not verify the installed build. Close running Engineering Memory processes and rerun this installer to repair it.', mbError, MB_OK);
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then UpdatePath(False);
end;

const
  InstallerProtocol = 'EM1';
  McpProtocol = 'EM-MCP1';
  SetupFieldCount = 8;
  KeyField = 7;

var
  SettingsPage, McpPage: TWizardPage;
  McpChoices: TNewCheckListBox;
  McpDetails: TNewMemo;
  McpTokens, McpStates, McpNames, McpNotes: TArrayOfString;
  McpReplacements: array of Boolean;
  OriginalFields: array[0..6] of String;
  StartPage: TInputOptionWizardPage;
  ProgressPage: TOutputMarqueeProgressWizardPage;
  Edits: array[0..7] of TNewEdit;
  HelpersEnabled, Loaded, Deferred: Boolean;
  SettingsToken: String;
  KeyLabel: TNewStaticText;
  DeferCheck: TNewCheckBox;

function SetProcessEnv(const Name, Value: String): Boolean;
  external 'SetEnvironmentVariableW@kernel32.dll stdcall';
function DeleteProcessEnv(const Name: String; Value: LongWord): Boolean;
  external 'SetEnvironmentVariableW@kernel32.dll stdcall';
function ProcessEnvSize(const Name: String; Buffer, Size: LongWord): LongWord;
  external 'GetEnvironmentVariableW@kernel32.dll stdcall';

function RunSetupHelper(const Action: String; var Output: TArrayOfString): Boolean;
var
  ExitCode: Integer;
  Captured: TExecOutput;
begin
  Result := False;
  SetArrayLength(Output, 0);
  if not HelpersEnabled then Exit;
  if ConfigureExisting then
  begin
    if not InstallationUnchanged then Exit;
  end
  else if not (PayloadVerified and BuildRecorded) then Exit;
  try
    if not ExecAndCaptureOutput(AddBackslash(WizardDirValue) + 'engineering-memory.exe',
      'setup --installer-ui ' + Action, WizardDirValue, SW_SHOWNORMAL,
      ewWaitUntilTerminated, ExitCode, Captured) then Exit;
    if Captured.Error then Exit;
    Output := Captured.StdOut;
    Result := ExitCode = 0;
  except
    { Keep child output and exceptions out of the setup log and UI. }
  end;
end;

function HelperStatus(const Output: TArrayOfString): String;
begin
  Result := '';
  if GetArrayLength(Output) = 1 then Result := Output[0];
end;

function DecodeField(const Encoded: String; var Value: String): Boolean;
var
  Index, CodeByte: Integer;
  Bytes: AnsiString;
begin
  Result := False;
  Value := '';
  if (Length(Encoded) < 1) or ((Length(Encoded) - 1) mod 2 <> 0) then Exit;
  if Encoded[1] <> 'v' then Exit;
  SetLength(Bytes, (Length(Encoded) - 1) div 2);
  for Index := 1 to Length(Bytes) do
  begin
    CodeByte := StrToIntDef('$' + Copy(Encoded, Index * 2, 2), -1);
    if (CodeByte < 32) or (CodeByte = 127) then Exit;
    Bytes[Index] := Chr(CodeByte);
  end;
  Value := Utf8Decode(Bytes);
  Result := True;
end;

procedure ShowMcpTarget(Sender: TObject);
var
  Index: Integer;
begin
  Index := McpChoices.ItemIndex;
  if (Index >= 0) and (Index < GetArrayLength(McpNotes)) then
    McpDetails.Text := McpNotes[Index];
end;

procedure LoadMcpTargets;
var
  Output: TArrayOfString;
  Token, State, Names, Profile, Diagnostic: String;
  Count, Index, Offset: Integer;
begin
  McpChoices.Items.Clear;
  McpDetails.Text := 'Client discovery failed. You can finish installation and retry from setup.';
  SetArrayLength(McpTokens, 0);
  SetArrayLength(McpStates, 0);
  SetArrayLength(McpNames, 0);
  SetArrayLength(McpNotes, 0);
  if not RunSetupHelper('mcp-scan', Output) then Exit;
  Count := GetArrayLength(Output);
  if Count < 1 then Exit;
  if (Output[0] <> McpProtocol) or ((Count - 1) mod 5 <> 0) or (Count > 21) then Exit;
  Count := (Count - 1) div 5;
  if Count = 0 then
  begin
    McpDetails.Text := 'No supported client installations were found.';
    Exit;
  end;
  for Index := 0 to Count - 1 do
  begin
    Offset := 1 + Index * 5;
    Token := Output[Offset];
    State := Output[Offset + 1];
    if not DecodeField(Output[Offset + 2], Names) then Break;
    if not DecodeField(Output[Offset + 3], Profile) then Break;
    if not DecodeField(Output[Offset + 4], Diagnostic) then Break;
    if State = 'absent' then State := 'add'
    else if State = 'matching' then State := 'verify'
    else if State = 'conflict' then State := 'conflict'
    else if (State <> 'blocked') or (Token <> '-') then Break;
    if (State <> 'blocked') and (Length(Token) <> 64) then Break;
    SetArrayLength(McpTokens, Index + 1);
    SetArrayLength(McpStates, Index + 1);
    SetArrayLength(McpNames, Index + 1);
    SetArrayLength(McpNotes, Index + 1);
    McpTokens[Index] := Token;
    McpStates[Index] := State;
    McpNames[Index] := Names;
    McpNotes[Index] := Profile;
    if Diagnostic <> '' then
    begin
      if Profile <> '' then McpNotes[Index] := Profile + #13#10;
      McpNotes[Index] := McpNotes[Index] + Diagnostic;
    end;
    McpChoices.AddCheckBox(Names + ' (' + State + ')', '', 0, False,
      State <> 'blocked', False, False, nil);
  end;
  if McpChoices.Items.Count > 0 then
  begin
    McpChoices.ItemIndex := 0;
    ShowMcpTarget(nil);
  end;
end;

function ApplyMcpTarget(const Token, Decision: String; var Output: TArrayOfString): Boolean;
var
  Name, Previous: String;
  Existed: Boolean;
begin
  Result := False;
  Name := 'EM_INSTALLER_UI_MCP';
  Existed := ProcessEnvSize(Name, 0, 0) > 0;
  Previous := GetEnv(Name);
  if not SetProcessEnv(Name, Token + ':' + Decision) then Exit;
  try
    Result := RunSetupHelper('mcp-apply', Output);
  finally
    if Existed then SetProcessEnv(Name, Previous)
    else DeleteProcessEnv(Name, 0);
  end;
end;

function ConfirmMcpReplacement(Index: Integer): Boolean;
begin
  Result := MsgBox('Replace the existing Engineering Memory registration for ' + McpNames[Index] +
    '?' + #13#10#13#10 + McpNotes[Index], mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES;
end;

procedure ConfirmMcpReplacements;
var
  Index: Integer;
begin
  SetArrayLength(McpReplacements, GetArrayLength(McpTokens));
  for Index := 0 to GetArrayLength(McpTokens) - 1 do
  begin
    McpReplacements[Index] := False;
    if McpChoices.Checked[Index] and (McpStates[Index] = 'conflict') then
    begin
      McpReplacements[Index] := ConfirmMcpReplacement(Index);
      if not McpReplacements[Index] then McpChoices.Checked[Index] := False;
    end;
  end;
end;

function ApplyMcpTargets: Boolean;
var
  Output: TArrayOfString;
  Summary, Decision, Diagnostic: String;
  Index: Integer;
  Success: Boolean;
begin
  Result := True;
  Summary := '';
  for Index := 0 to GetArrayLength(McpTokens) - 1 do
  begin
    if not McpChoices.Checked[Index] or (McpStates[Index] = 'blocked') then Continue;
    if Summary <> '' then Summary := Summary + #13#10#13#10;
    Summary := Summary + McpNames[Index] + ': ';
    Decision := 'keep';
    if McpStates[Index] = 'conflict' then
    begin
      if ConfigureExisting then
      begin
        if not McpReplacements[Index] then Continue;
      end
      else if not ConfirmMcpReplacement(Index) then
      begin
        Summary := Summary + 'Kept existing registration. Local MCP check: skipped.';
        Continue;
      end;
      Decision := 'replace';
    end;
    ProgressPage.SetText('Checking the installed MCP server...', McpNames[Index]);
    ProgressPage.Show;
    try
      Success := ApplyMcpTarget(McpTokens[Index], Decision, Output);
    finally
      ProgressPage.Hide;
    end;
    if Success then Success := GetArrayLength(Output) = 4;
    if Success then
      Success := (Output[0] = McpProtocol) and DecodeField(Output[3], Diagnostic);
    if not Success then
    begin
      Summary := Summary + 'Could not run client setup. Go back to rescan or rerun setup later.';
      Result := False;
      Continue;
    end;
    Summary := Summary + Output[1] + '. Local MCP check: ' + Output[2] + '.';
    if Diagnostic <> '' then Summary := Summary + ' ' + Diagnostic;
    if (Output[1] = 'blocked') or (Output[1] = 'failed') or
       ((Output[2] <> 'passed') and (Output[2] <> 'skipped')) then Result := False;
  end;
  if not Result then
  begin
    Summary := Summary + #13#10#13#10 +
      'Select a target to retry, or continue without selecting one.';
    LoadMcpTargets;
  end;
  if Summary <> '' then MsgBox(Summary, mbInformation, MB_OK);
end;

function StatusMessage(const Status: String): String;
begin
  case Status of
    'provider': Result := 'Enter a LiteLLM provider name, such as openrouter or openai.';
    'model': Result := 'Enter a model ID for the selected provider.';
    'api_base': Result := 'Enter an HTTP or HTTPS base URL without credentials, query or fragment, or leave it blank.';
    'backend_port': Result := 'Enter a memory backend port from 1 to 65535.';
    'litellm_port': Result := 'Enter a LiteLLM port from 1 to 65535 that differs from the memory backend port.';
    'archive': Result := 'Enter an absolute archive directory outside the installation and private configuration directories.';
    'sqlite', 'storage': Result := 'Check the archive and SQLite paths. Use an absolute SQLite file path outside the installation and private configuration directories.';
    'api_key': Result := 'Enter a valid API key. A saved key can be kept for its existing provider.';
    'overrides': Result := 'Close the installer and remove workstation environment overrides before running setup again.';
    'recovery-required': Result := 'The private profile has an unfinished settings write. Run engineering-memory setup from a regular terminal to recover it, or keep the existing settings.';
    'user': Result := 'Run engineering-memory setup from a regular terminal as the user who will use Engineering Memory.';
    'prerequisite': Result := 'Settings saved. Start Docker in Linux-container mode and check the Docker Engine, Compose and profile settings. You can retry or clear the checkbox to finish.';
    'startup': Result := 'Settings saved. The stack could not become ready. Check port conflicts, Docker resources and image access. You can retry or clear the checkbox to finish.';
    'bank': Result := 'Settings saved and stack started. The shared bank could not be provisioned. Check the backend and provider settings. You can retry or clear the checkbox to finish.';
    else Result := 'Could not complete this setup step. Check access and retry, or run engineering-memory setup later.';
  end;
end;

function LoadSetupFields: Boolean;
var
  Output: TArrayOfString;
  Action: String;
  Values: array[0..6] of String;
  Index: Integer;
begin
  Result := False;
  for Index := 0 to SetupFieldCount - 1 do Edits[Index].Enabled := False;
  Edits[KeyField].Text := '';
  Action := 'read';
  if ConfigureExisting then Action := 'read-maintenance';
  if not RunSetupHelper(Action, Output) then
  begin
    MsgBox(StatusMessage(HelperStatus(Output)), mbError, MB_OK);
    Exit;
  end;
  if GetArrayLength(Output) <> 10 then Exit;
  if (Output[0] <> InstallerProtocol) or (Length(Output[2]) <> 64) then Exit;
  for Index := 0 to KeyField - 1 do
    if not DecodeField(Output[Index + 3], Values[Index]) then Exit;
  for Index := 0 to KeyField - 1 do
  begin
    OriginalFields[Index] := Values[Index];
    Edits[Index].Text := Values[Index];
  end;
  if Output[1] = '1' then
    KeyLabel.Caption := '&API key (blank keeps saved key)'
  else
    KeyLabel.Caption := '&API key';
  SettingsToken := Output[2];
  for Index := 0 to SetupFieldCount - 1 do Edits[Index].Enabled := True;
  Result := True;
end;

function SaveSetupFields: String;
var
  Names, Values, Previous: array[0..9] of String;
  Existed: array[0..9] of Boolean;
  Output: TArrayOfString;
  Index, Applied: Integer;
begin
  Names[0] := 'VERSION';
  Names[1] := 'TOKEN';
  Names[2] := 'PROVIDER';
  Names[3] := 'MODEL';
  Names[4] := 'API_BASE';
  Names[5] := 'BACKEND_PORT';
  Names[6] := 'LITELLM_PORT';
  Names[7] := 'ARCHIVE';
  Names[8] := 'SQLITE';
  Names[9] := 'API_KEY';
  Values[0] := InstallerProtocol;
  Values[1] := SettingsToken;
  for Index := 0 to SetupFieldCount - 1 do Values[Index + 2] := 'v' + Edits[Index].Text;
  Result := '';
  Applied := 0;
  try
    for Index := 0 to 9 do
    begin
      Names[Index] := 'EM_INSTALLER_UI_' + Names[Index];
      Existed[Index] := ProcessEnvSize(Names[Index], 0, 0) > 0;
      Previous[Index] := GetEnv(Names[Index]);
      if not SetProcessEnv(Names[Index], Values[Index]) then Break;
      Applied := Index + 1;
    end;
    if Applied = 10 then
    begin
      if RunSetupHelper('save', Output) and (HelperStatus(Output) = 'saved') then
        Result := 'saved'
      else if HelperStatus(Output) <> 'saved' then
        Result := HelperStatus(Output);
    end;
  finally
    for Index := 0 to Applied - 1 do
      if Existed[Index] then
        SetProcessEnv(Names[Index], Previous[Index])
      else
        DeleteProcessEnv(Names[Index], 0);
  end;
end;

function AddSetupField(Index: Integer; const Caption: String; Left, Top, Width: Integer): TNewStaticText;
begin
  Result := TNewStaticText.Create(SettingsPage);
  Result.Parent := SettingsPage.Surface;
  Result.Caption := Caption;
  Result.Left := Left;
  Result.Top := ScaleY(Top);
  Edits[Index] := TNewEdit.Create(SettingsPage);
  Edits[Index].Parent := SettingsPage.Surface;
  Edits[Index].SetBounds(Left, ScaleY(Top + 14), Width, ScaleY(21));
  Edits[Index].MaxLength := 4096;
  Result.FocusControl := Edits[Index];
end;

procedure UpdateSettingsButton(Sender: TObject);
begin
  if DeferCheck.Checked then WizardForm.NextButton.Caption := '&Next'
  else if Loaded and ConfigureExisting then WizardForm.NextButton.Caption := '&Next'
  else if Loaded then WizardForm.NextButton.Caption := '&Save'
  else WizardForm.NextButton.Caption := '&Retry';
end;

procedure InitializeWizard;
var
  HalfWidth, Right, FullWidth: Integer;
begin
  InitializeMaintenance;
  if WizardSilent then Exit;
  if IsAdmin then
  begin
    MsgBox('Embedded configuration requires a regular user session. You can install now and run engineering-memory setup later as your own user.',
      mbInformation, MB_OK);
    Exit;
  end;
  if not ShouldInstallPayload and (MaintenanceMode <> 'identical') then Exit;
  ConfigureExisting := MaintenanceMode = 'identical';
  HelpersEnabled := True;
  if ConfigureExisting then
    SettingsPage := CreateCustomPage(DecisionPage.ID, 'Configure Engineering Memory',
      'Review your saved settings. Changes are applied after the MCP page.')
  else
    SettingsPage := CreateCustomPage(wpInstalling, 'Configure Engineering Memory',
      'Choose a provider and local settings. You can complete configuration later.');
  FullWidth := SettingsPage.SurfaceWidth;
  HalfWidth := (FullWidth - ScaleX(10)) div 2;
  Right := FullWidth - HalfWidth;
  AddSetupField(0, '&LiteLLM provider', 0, 0, HalfWidth);
  AddSetupField(1, '&Model ID', Right, 0, HalfWidth);
  AddSetupField(2, 'Provider API &base (optional)', 0, 35, HalfWidth);
  KeyLabel := AddSetupField(KeyField, '&API key', Right, 35, HalfWidth);
  Edits[KeyField].PasswordChar := '*';
  AddSetupField(3, 'Memory backend &port', 0, 70, HalfWidth);
  AddSetupField(4, 'LiteLLM p&ort', Right, 70, HalfWidth);
  AddSetupField(5, 'A&rchive directory', 0, 105, FullWidth);
  AddSetupField(6, 'S&QLite file', 0, 140, FullWidth);
  DeferCheck := TNewCheckBox.Create(SettingsPage);
  DeferCheck.Parent := SettingsPage.Surface;
  DeferCheck.SetBounds(0, ScaleY(181), FullWidth, ScaleY(19));
  if ConfigureExisting then DeferCheck.Caption := '&Keep saved settings'
  else DeferCheck.Caption := 'Con&figure later';
  DeferCheck.OnClick := @UpdateSettingsButton;

  McpPage := CreateCustomPage(SettingsPage.ID, 'Connect MCP clients',
    'Choose the installed clients that should use Engineering Memory.');
  McpChoices := TNewCheckListBox.Create(McpPage);
  McpChoices.Parent := McpPage.Surface;
  McpChoices.SetBounds(0, 0, McpPage.SurfaceWidth, ScaleY(106));
  McpChoices.OnClick := @ShowMcpTarget;
  McpDetails := TNewMemo.Create(McpPage);
  McpDetails.Parent := McpPage.Surface;
  McpDetails.SetBounds(0, ScaleY(114), McpPage.SurfaceWidth, ScaleY(79));
  McpDetails.ReadOnly := True;
  McpDetails.ScrollBars := ssVertical;

  StartPage := CreateInputOptionPage(McpPage.ID, 'Start Engineering Memory',
    'Your settings have been saved.',
    'Select the option to start now. Leave it unselected to finish without starting Docker services.',
    False, False);
  StartPage.Add('Start the local stack and provision the shared bank');
  StartPage.Values[0] := False;
  ProgressPage := CreateOutputMarqueeProgressPage('Starting Engineering Memory',
    'This can take several minutes on the first start.');
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  if (MaintenanceMode = 'identical') and (PageID = wpReady) then Result := True;
  if HelpersEnabled then
  begin
    if not ConfigureExisting and not (PayloadVerified and BuildRecorded) then
      if (PageID = SettingsPage.ID) or (PageID = McpPage.ID) or (PageID = StartPage.ID) then Result := True;
    if (PageID = StartPage.ID) and (Deferred or ConfigureExisting) then Result := True;
  end;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then
  begin
    if MaintenanceMode = 'identical' then
    begin
      WizardForm.FinishedHeadingLabel.Caption := 'Engineering Memory maintenance complete';
      WizardForm.FinishedLabel.Caption := 'The installed application files were kept.';
    end
    else if not (PayloadVerified and BuildRecorded) then
    begin
      WizardForm.FinishedHeadingLabel.Caption := 'Setup could not verify the installation';
      WizardForm.FinishedLabel.Caption := 'Close running Engineering Memory processes and rerun this installer to repair the installation.';
    end;
  end;
  if not HelpersEnabled then Exit;
  if CurPageID = SettingsPage.ID then
  begin
    StartPage.Values[0] := False;
    if not ConfigureExisting or not Loaded then Loaded := LoadSetupFields;
    UpdateSettingsButton(nil);
  end
  else if CurPageID = McpPage.ID then
  begin
    LoadMcpTargets;
    if ConfigureExisting then WizardForm.NextButton.Caption := '&Apply';
  end;
end;

function MaintenanceSettingsChanged: Boolean;
var
  Index: Integer;
begin
  Result := True;
  if Edits[KeyField].Text <> '' then Exit;
  for Index := 0 to KeyField - 1 do
    if Edits[Index].Text <> OriginalFields[Index] then Exit;
  Result := False;
end;

function ConfirmMaintenanceChanges: Boolean;
var
  Index: Integer;
  HasChanges: Boolean;
begin
  ConfirmMcpReplacements;
  HasChanges := not Deferred and MaintenanceSettingsChanged;
  for Index := 0 to GetArrayLength(McpTokens) - 1 do
    if McpChoices.Checked[Index] then HasChanges := True;
  Result := not HasChanges;
  if HasChanges then
    Result := MsgBox('Apply these settings and the selected MCP changes?', mbConfirmation,
      MB_YESNO or MB_DEFBUTTON2) = IDYES;
end;

function SaveMaintenanceSettings: Boolean;
var
  Status: String;
  Index: Integer;
begin
  Result := True;
  if Deferred or not MaintenanceSettingsChanged then Exit;
  Status := SaveSetupFields;
  if Status = 'saved' then
  begin
    Edits[KeyField].Text := '';
    for Index := 0 to KeyField - 1 do OriginalFields[Index] := Edits[Index].Text;
    { Refresh the snapshot before any later edit or retry. }
    Loaded := False;
    Deferred := True;
  end
  else
  begin
    Result := False;
    if Status = 'stale' then
    begin
      Loaded := False;
      Edits[KeyField].Text := '';
      MsgBox('Settings changed in another session. Go back to reload the saved settings.', mbInformation, MB_OK);
    end
    else MsgBox(StatusMessage(Status), mbError, MB_OK);
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Status: String;
  Output: TArrayOfString;
begin
  Result := True;
  if DecisionPage <> nil then
    if CurPageID = DecisionPage.ID then
    begin
      Result := (DecisionPage.CheckListBox.Items.Count > 0) and (DecisionPage.SelectedValueIndex >= 0);
      if Result and not InstallationUnchanged then
      begin
        MsgBox('The installed files or registration changed. Close Setup and run it again.', mbError, MB_OK);
        Result := False;
      end;
      Exit;
    end;
  if not HelpersEnabled then Exit;
  if CurPageID = SettingsPage.ID then
  begin
    Deferred := DeferCheck.Checked;
    if Deferred then
    begin
      Edits[KeyField].Text := '';
      Exit;
    end;
    Result := False;
    if not Loaded then
    begin
      Loaded := LoadSetupFields;
      UpdateSettingsButton(nil);
      Exit;
    end;
    if ConfigureExisting then
    begin
      Result := True;
      Exit;
    end;
    Status := SaveSetupFields;
    if Status = 'saved' then
    begin
      Edits[KeyField].Text := '';
      Result := True;
    end
    else if Status = 'stale' then
    begin
      MsgBox('Settings changed in another setup session. Reload the saved settings before editing again.',
        mbInformation, MB_OK);
      Loaded := False;
      Edits[KeyField].Text := '';
      UpdateSettingsButton(nil);
    end
    else
      MsgBox(StatusMessage(Status), mbError, MB_OK);
  end
  else if CurPageID = McpPage.ID then
  begin
    if ConfigureExisting then
    begin
      Result := False;
      if not InstallationUnchanged then
      begin
        MsgBox('The installed files or registration changed. Close Setup and run it again.', mbError, MB_OK);
        Exit;
      end;
      if not ConfirmMaintenanceChanges then Exit;
      if not SaveMaintenanceSettings then Exit;
    end;
    Result := ApplyMcpTargets;
  end
  else if CurPageID = StartPage.ID then
  begin
    if not StartPage.Values[0] then Exit;
    ProgressPage.SetText('Starting the stack and provisioning the shared bank...', '');
    ProgressPage.Show;
    try
      Result := RunSetupHelper('start', Output) and (HelperStatus(Output) = 'ready');
    finally
      ProgressPage.Hide;
    end;
    if Result then
    begin
      StartPage.Values[0] := False;
      MsgBox('The local stack is ready and the shared bank is provisioned.', mbInformation, MB_OK);
    end
    else
      MsgBox(StatusMessage(HelperStatus(Output)), mbError, MB_OK);
  end;
end;

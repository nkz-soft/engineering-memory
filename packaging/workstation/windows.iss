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

type
  TMcpRow = record
    Token, State, Name, Profile, ProfileKey, ScanNote: String;
    Registration, Probe, ResultNote: String;
    Selected, NeedsReview, PreviousResult: Boolean;
  end;
  TMcpRows = array of TMcpRow;
  TMcpAttempt = record
    RowIndex: Integer;
    Review: TMcpRow;
    Decision: String;
  end;

var
  SettingsPage, McpPage: TWizardPage;
  McpChoices: TNewCheckListBox;
  McpDetails: TNewMemo;
  McpCheckButton, McpRescanButton: TNewButton;
  McpRows: TMcpRows;
  McpMessage: String;
  McpLoaded, McpScanReady, McpBusy, McpHasChecked: Boolean;
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
  Result := Utf8Encode(Value) = Bytes;
end;

function McpActionable(const Row: TMcpRow): Boolean;
begin
  Result := (Row.State <> 'blocked') and not Row.NeedsReview;
end;

procedure LockMcpControls;
begin
  McpBusy := True;
  McpChoices.Enabled := False;
  McpCheckButton.Enabled := False;
  McpRescanButton.Enabled := False;
end;

function FindMcpRow(const Rows: TMcpRows; const Row: TMcpRow): Integer;
var
  Index: Integer;
begin
  Result := -1;
  if Row.Profile = '' then Exit;
  for Index := 0 to GetArrayLength(Rows) - 1 do
    if (Rows[Index].Name = Row.Name) and
      (CompareText(Rows[Index].ProfileKey, Row.ProfileKey) = 0) then
    begin
      if Result >= 0 then
      begin
        Result := -1;
        Exit;
      end;
      Result := Index;
    end;
end;

procedure ShowMcpTarget(Sender: TObject);
var
  Index: Integer;
  Details: String;
begin
  Details := McpMessage;
  Index := McpChoices.ItemIndex;
  if (Index >= 0) and (Index < GetArrayLength(McpRows)) then
  begin
    if Details <> '' then Details := Details + #13#10#13#10;
    Details := Details + McpRows[Index].Profile + #13#10 +
      'Current action: ' + McpRows[Index].State + '.';
    if McpRows[Index].PreviousResult then
      Details := Details + #13#10 + 'The list shows the previous result for this profile.';
    if McpRows[Index].Registration <> '' then
      Details := Details + #13#10 + 'Registration: ' + McpRows[Index].Registration +
        '. Local MCP check: ' + McpRows[Index].Probe + '.';
    if (McpRows[Index].ScanNote <> '') and
      (Pos(McpRows[Index].ScanNote, McpRows[Index].ResultNote) = 0) then
      Details := Details + #13#10 + McpRows[Index].ScanNote;
    if McpRows[Index].ResultNote <> '' then
      Details := Details + #13#10 + McpRows[Index].ResultNote;
    if McpRows[Index].NeedsReview then
      Details := Details + #13#10 + 'Rescan and select this profile to check it again.';
  end;
  McpDetails.Text := Trim(Details);
end;

procedure RenderMcpRows(Focus: Integer);
var
  Index: Integer;
  Caption: String;
  Actionable, HasActionable: Boolean;
begin
  McpChoices.Items.Clear;
  HasActionable := False;
  for Index := 0 to GetArrayLength(McpRows) - 1 do
  begin
    Caption := McpRows[Index].Name + ' (' + McpRows[Index].State + ')';
    if McpRows[Index].Registration <> '' then
      Caption := McpRows[Index].Name + ' (' + McpRows[Index].Registration +
        ' / ' + McpRows[Index].Probe + ')'
    else if McpRows[Index].State = 'blocked' then
      Caption := Caption + ' - check skipped'
    else if McpHasChecked and not McpRows[Index].Selected then
      Caption := Caption + ' - skipped';
    Actionable := McpScanReady and McpActionable(McpRows[Index]);
    HasActionable := HasActionable or Actionable;
    McpChoices.AddCheckBox(Caption, '', 0, McpRows[Index].Selected,
      Actionable, False, False, nil);
  end;
  if McpChoices.Items.Count > 0 then
  begin
    if (Focus < 0) or (Focus >= McpChoices.Items.Count) then Focus := 0;
    McpChoices.ItemIndex := Focus;
  end;
  McpChoices.Enabled := not McpBusy;
  McpCheckButton.Enabled := HasActionable and not McpBusy;
  McpRescanButton.Enabled := not McpBusy;
  ShowMcpTarget(nil);
end;

function ReadMcpRows(var Rows: TMcpRows): Boolean;
var
  Output: TArrayOfString;
  Count, Index, Offset: Integer;
begin
  Result := False;
  if not RunSetupHelper('mcp-scan', Output) then Exit;
  Count := GetArrayLength(Output);
  if Count < 1 then Exit;
  if (Output[0] <> McpProtocol) or ((Count - 1) mod 5 <> 0) or (Count > 21) then Exit;
  Count := (Count - 1) div 5;
  SetArrayLength(Rows, Count);
  for Index := 0 to Count - 1 do
  begin
    Offset := 1 + Index * 5;
    Rows[Index].Token := Output[Offset];
    Rows[Index].State := Output[Offset + 1];
    if not DecodeField(Output[Offset + 2], Rows[Index].Name) then Exit;
    if not DecodeField(Output[Offset + 3], Rows[Index].Profile) then Exit;
    if Rows[Index].Profile <> '' then
      Rows[Index].ProfileKey := ExpandFileName(Rows[Index].Profile);
    if not DecodeField(Output[Offset + 4], Rows[Index].ScanNote) then Exit;
    case Rows[Index].State of
      'absent': Rows[Index].State := 'add';
      'matching': Rows[Index].State := 'verify';
      'conflict', 'blocked': ;
      else Exit;
    end;
    if Rows[Index].State = 'blocked' then
    begin
      if Rows[Index].Token <> '-' then Exit;
    end
    else if not IsDigest(Rows[Index].Token) or (Rows[Index].Profile = '') then Exit;
  end;
  Result := True;
end;

procedure LoadMcpTargets;
var
  NewRows: TMcpRows;
  Index, Previous, OldFocus, Focus: Integer;
begin
  McpLoaded := True;
  OldFocus := McpChoices.ItemIndex;
  for Index := 0 to GetArrayLength(McpRows) - 1 do
    McpRows[Index].Selected := McpChoices.Checked[Index];
  LockMcpControls;
  try
    McpScanReady := ReadMcpRows(NewRows);
  finally
    McpBusy := False;
  end;
  Focus := OldFocus;
  if not McpScanReady then
    McpMessage := 'Client discovery failed. Rescan to retry, or continue.'
  else
  begin
    McpMessage := '';
    Focus := -1;
    for Index := 0 to GetArrayLength(NewRows) - 1 do
    begin
      Previous := FindMcpRow(McpRows, NewRows[Index]);
      if (Previous < 0) or (FindMcpRow(NewRows, NewRows[Index]) <> Index) then Continue;
      NewRows[Index].Selected := McpRows[Previous].Selected and
        (McpRows[Previous].Token = NewRows[Index].Token) and McpActionable(NewRows[Index]);
      NewRows[Index].Registration := McpRows[Previous].Registration;
      NewRows[Index].Probe := McpRows[Previous].Probe;
      NewRows[Index].ResultNote := McpRows[Previous].ResultNote;
      NewRows[Index].PreviousResult := McpRows[Previous].Registration <> '';
      if Previous = OldFocus then Focus := Index;
    end;
    McpRows := NewRows;
    if GetArrayLength(McpRows) = 0 then
      McpMessage := 'No supported client installations were found.';
  end;
  RenderMcpRows(Focus);
end;

procedure RescanMcpTargets(Sender: TObject);
begin
  if not McpBusy then LoadMcpTargets;
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

function ConfirmMcpReplacement(const Row: TMcpRow): Boolean;
begin
  Result := MsgBox('Replace the existing Engineering Memory registration for ' + Row.Name +
    '?' + #13#10#13#10 + Row.Profile + #13#10 + Row.ScanNote,
    mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES;
end;

function ReadMcpResult(const Output: TArrayOfString; var Row: TMcpRow): Boolean;
var
  Note: String;
begin
  Result := False;
  if GetArrayLength(Output) <> 4 then Exit;
  if (Output[0] <> McpProtocol) or not DecodeField(Output[3], Note) then Exit;
  case Output[1] of
    'saved', 'already configured':
      case Output[2] of
        'passed', 'failed', 'timeout', 'missing-tools': ;
        else Exit;
      end;
    'blocked', 'failed', 'declined': if Output[2] <> 'skipped' then Exit;
    else Exit;
  end;
  Row.Registration := Output[1];
  if Row.Registration = 'declined' then Row.Registration := 'kept';
  Row.Probe := Output[2];
  if Row.Probe = 'missing-tools' then Row.Probe := 'missing tools';
  Row.ResultNote := Note;
  Result := True;
end;

procedure RunMcpAttempt(const Attempt: TMcpAttempt; var Row: TMcpRow);
var
  Output: TArrayOfString;
  ReadResult: Boolean;
begin
  Row.Selected := False;
  Row.PreviousResult := False;
  if Attempt.Decision = 'decline' then
  begin
    Row.Registration := 'kept';
    Row.Probe := 'skipped';
    Row.ResultNote := 'Kept the existing registration.';
    Exit;
  end;
  Row.NeedsReview := True;
  ProgressPage.SetText('Checking the installed MCP server...', Attempt.Review.Name);
  ProgressPage.Show;
  try
    ReadResult := ApplyMcpTarget(Attempt.Review.Token, Attempt.Decision, Output);
  finally
    ProgressPage.Hide;
  end;
  if ReadResult then ReadResult := ReadMcpResult(Output, Row);
  if not ReadResult then
  begin
    Row.Registration := 'failed';
    Row.Probe := 'unavailable';
    Row.ResultNote := 'Could not get a client setup result.';
  end;
end;

function ConfirmMaintenanceChanges(HasMcpChanges: Boolean): Boolean; forward;
function SaveMaintenanceSettings: Boolean; forward;

function ReviewMaintenanceInstallation: Boolean;
begin
  Result := InstallationUnchanged;
  if not Result then
    MsgBox('The installed files or registration changed. Close Setup and run it again.', mbError, MB_OK);
end;

procedure CheckMcpTargets(Sender: TObject);
var
  Attempts: array of TMcpAttempt;
  Index, Count, Focus: Integer;
  HasMcpChanges: Boolean;
begin
  if McpBusy or not McpScanReady then Exit;
  Count := 0;
  Focus := McpChoices.ItemIndex;
  for Index := 0 to GetArrayLength(McpRows) - 1 do
  begin
    McpRows[Index].Selected := McpChoices.Checked[Index];
    if not McpRows[Index].Selected or not McpActionable(McpRows[Index]) then Continue;
    SetArrayLength(Attempts, Count + 1);
    Attempts[Count].RowIndex := Index;
    Attempts[Count].Review := McpRows[Index];
    Attempts[Count].Decision := 'keep';
    Count := Count + 1;
  end;
  if Count = 0 then
  begin
    McpMessage := 'Select a client to check, or rescan to review updated profiles.';
    ShowMcpTarget(nil);
    Exit;
  end;

  LockMcpControls;
  try
    if ConfigureExisting and not ReviewMaintenanceInstallation then Exit;
    HasMcpChanges := False;
    for Index := 0 to Count - 1 do
    begin
      if Attempts[Index].Review.State = 'conflict' then
      begin
        if ConfirmMcpReplacement(Attempts[Index].Review) then Attempts[Index].Decision := 'replace'
        else Attempts[Index].Decision := 'decline';
      end;
      if Attempts[Index].Decision <> 'decline' then HasMcpChanges := True;
    end;
    if ConfigureExisting then
    begin
      if not ConfirmMaintenanceChanges(HasMcpChanges) then Exit;
      if not SaveMaintenanceSettings then Exit;
    end;
    McpMessage := '';
    McpHasChecked := True;
    for Index := 0 to Count - 1 do
      RunMcpAttempt(Attempts[Index], McpRows[Attempts[Index].RowIndex]);
  finally
    McpBusy := False;
    RenderMcpRows(Focus);
  end;
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
    'Use Check selected clients to apply your choices and see the results here.');
  McpChoices := TNewCheckListBox.Create(McpPage);
  McpChoices.Parent := McpPage.Surface;
  McpChoices.SetBounds(0, 0, McpPage.SurfaceWidth, ScaleY(82));
  McpChoices.OnClick := @ShowMcpTarget;
  McpCheckButton := TNewButton.Create(McpPage);
  McpCheckButton.Parent := McpPage.Surface;
  McpCheckButton.SetBounds(0, ScaleY(88), ScaleX(126), ScaleY(24));
  McpCheckButton.Caption := 'Chec&k selected clients';
  McpCheckButton.OnClick := @CheckMcpTargets;
  McpRescanButton := TNewButton.Create(McpPage);
  McpRescanButton.Parent := McpPage.Surface;
  McpRescanButton.SetBounds(ScaleX(134), ScaleY(88), ScaleX(72), ScaleY(24));
  McpRescanButton.Caption := '&Rescan';
  McpRescanButton.OnClick := @RescanMcpTargets;
  McpDetails := TNewMemo.Create(McpPage);
  McpDetails.Parent := McpPage.Surface;
  McpDetails.SetBounds(0, ScaleY(118), McpPage.SurfaceWidth, McpPage.SurfaceHeight - ScaleY(118));
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
    if not McpBusy and not McpLoaded then LoadMcpTargets;
    if ConfigureExisting then WizardForm.NextButton.Caption := '&Apply';
  end;
end;

function BackButtonClick(CurPageID: Integer): Boolean;
begin
  Result := not McpBusy;
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

function ConfirmMaintenanceChanges(HasMcpChanges: Boolean): Boolean;
var
  Prompt: String;
begin
  Result := True;
  if HasMcpChanges then Prompt := 'Apply pending settings and check the selected MCP clients?'
  else if not Deferred and MaintenanceSettingsChanged then Prompt := 'Apply changes to the saved settings?'
  else Exit;
  Result := MsgBox(Prompt, mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES;
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
    Result := not McpBusy;
    if Result and ConfigureExisting then
      Result := ReviewMaintenanceInstallation and ConfirmMaintenanceChanges(False) and SaveMaintenanceSettings;
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

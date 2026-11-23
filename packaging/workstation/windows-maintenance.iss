const
  BuildManifest = 'engineering-memory.build';
  IncomingVersion = '{#AppVersion}';
  IncomingIdentity = '{#BuildIdentity}';
  UninstallKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppIdentity}_is1';

var
  MaintenanceMode, ObservedVersion, ObservedIdentity, ObservedDirectory: String;
  DecisionPage: TInputOptionWizardPage;
  ConfigureExisting, PayloadVerified, BuildRecorded: Boolean;
  IncomingLines, ObsoleteFiles: TArrayOfString;

function FileAttributes(const Name: String): LongWord;
  external 'GetFileAttributesW@kernel32.dll stdcall';

function IsDigest(const Value: String): Boolean;
var
  I: Integer;
begin
  Result := False;
  if Length(Value) <> 64 then Exit;
  for I := 1 to Length(Value) do
    if Pos(Value[I], '0123456789abcdef') = 0 then Exit;
  Result := True;
end;

function SafePath(const Path: String): Boolean;
var
  Part, Parent: String;
  Attributes: LongWord;
begin
  Result := False;
  Part := RemoveBackslashUnlessRoot(Path);
  while Part <> '' do
  begin
    Attributes := FileAttributes(Part);
    if (Attributes <> $FFFFFFFF) and ((Attributes and $400) <> 0) then Exit;
    Parent := ExtractFileDir(Part);
    if (Parent = Part) or (Length(Parent) <= 3) then Break;
    Part := Parent;
  end;
  Result := True;
end;

function SafeRelativePath(const Path: String): Boolean;
var
  I, First: Integer;
begin
  Result := False;
  if Path = '' then Exit;
  First := 1;
  for I := 1 to Length(Path) do
  begin
    if Path[I] = '/' then
    begin
      if (I = First) then Exit;
      if (Path[I - 1] = '.') or (Path[I - 1] = ' ') then Exit;
      First := I + 1;
    end
    else if Pos(Path[I], 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.()+@ -') = 0 then
      Exit;
  end;
  Result := (First <= Length(Path)) and (Path[Length(Path)] <> '.') and (Path[Length(Path)] <> ' ');
end;

function ReadManifest(const Root, Identity: String; var Lines: TArrayOfString): Boolean;
var
  Path: String;
begin
  Result := False;
  if not IsDigest(Identity) then Exit;
  Path := AddBackslash(Root) + BuildManifest;
  if not SafePath(Path) or not FileExists(Path) then Exit;
  try
    if Lowercase(GetSHA256OfFile(Path)) <> Identity then Exit;
    if not LoadStringsFromFile(Path, Lines) then Exit;
    if GetArrayLength(Lines) < 5 then Exit;
    Result := (Lines[0] = 'EM-BUILD-1') and IsDigest(Lines[2]);
  except
    Log('EM-MAINTENANCE: unable to read the installed manifest');
  end;
end;

function CheckPayload(const Root, Version: String; const Lines: TArrayOfString;
  VerifyContents: Boolean): Boolean;
var
  I: Integer;
  Entry, Relative, Previous, Path, Checksum: String;
  Launcher, Runtime: Boolean;
begin
  Result := False;
  if Lines[1] <> Version then Exit;
  Launcher := False;
  Runtime := False;
  Previous := '';
  try
    for I := 3 to GetArrayLength(Lines) - 1 do
    begin
      Entry := Lines[I];
      if Length(Entry) < 66 then Exit;
      if Entry[65] <> ' ' then Exit;
      Checksum := Copy(Entry, 1, 64);
      Relative := Copy(Entry, 66, Length(Entry));
      if not IsDigest(Checksum) or not SafeRelativePath(Relative) then Exit;
      if (Lowercase(Relative) <= Previous) or (CompareText(Relative, BuildManifest) = 0) then Exit;
      Previous := Lowercase(Relative);
      if Previous = 'engineering-memory.exe' then Launcher := True;
      if Pos('_internal/', Previous) = 1 then Runtime := True;
      StringChangeEx(Relative, '/', '\', True);
      Path := AddBackslash(Root) + Relative;
      if not SafePath(Path) or DirExists(Path) then Exit;
      if VerifyContents then
      begin
        if not FileExists(Path) then Exit;
        if Lowercase(GetSHA256OfFile(Path)) <> Checksum then Exit;
      end;
    end;
    Result := Launcher and Runtime;
  except
    Log('EM-MAINTENANCE: unable to verify the installed payload');
  end;
end;

function HasUninstaller(const Root: String): Boolean;
var
  Command, Executable, LogFile, Name: String;
  Quote, I: Integer;
begin
  Result := False;
  if not RegQueryStringValue(HKCU, UninstallKey, 'UninstallString', Command) then Exit;
  if Length(Command) < 2 then Exit;
  if Command[1] <> '"' then Exit;
  Delete(Command, 1, 1);
  Quote := Pos('"', Command);
  if Quote = 0 then Exit;
  Executable := Copy(Command, 1, Quote - 1);
  if CompareText(ExtractFileDir(Executable), Root) <> 0 then Exit;
  Name := Lowercase(ExtractFileName(Executable));
  if (Length(Name) <> 12) or (Copy(Name, 1, 5) <> 'unins') or (ExtractFileExt(Name) <> '.exe') then Exit;
  for I := 6 to 8 do
    if Pos(Name[I], '0123456789') = 0 then Exit;
  LogFile := ChangeFileExt(Executable, '.dat');
  Result := SafePath(Executable) and SafePath(LogFile) and FileExists(Executable) and FileExists(LogFile);
end;

function PackRelease(Version: String; var Packed: Int64): Boolean;
var
  I, Separator, Number: Integer;
  Part: String;
begin
  Result := False;
  Packed := 0;
  for I := 1 to 3 do
  begin
    Separator := Pos('.', Version);
    if I < 3 then
    begin
      if Separator = 0 then Exit;
      Part := Copy(Version, 1, Separator - 1);
      Delete(Version, 1, Separator);
    end
    else Part := Version;
    if Length(Part) > 5 then Exit;
    Number := StrToIntDef(Part, -1);
    if (Number < 0) or (Number > 65535) or (IntToStr(Number) <> Part) then Exit;
    Packed := Packed * 65536 + Number;
  end;
  Result := True;
end;

function ObserveInstallation(const Root: String; var Version, Identity: String): String;
var
  Registered, HasVersion: Boolean;
  PreviousDir: String;
  CurrentVersion, PackageVersion: Int64;
  Lines: TArrayOfString;
begin
  Result := 'unverified';
  Version := '';
  Identity := '';
  Registered := RegKeyExists(HKCU, UninstallKey);
  if Registered then
  begin
    RegQueryStringValue(HKCU, UninstallKey, 'DisplayVersion', Version);
    RegQueryStringValue(HKCU, UninstallKey, 'InstallLocation', PreviousDir);
    Identity := GetPreviousData('BuildIdentity', '');
  end;
  HasVersion := PackRelease(Version, CurrentVersion);
  if not PackRelease(IncomingVersion, PackageVersion) then Exit;
  if HasVersion and (PackageVersion < CurrentVersion) then
  begin
    Result := 'downgrade';
    Exit;
  end;
  if not SafePath(Root) then Exit;
  if not Registered then
  begin
    if not DirExists(Root) and not FileExists(Root) then Result := 'fresh'
    else if DirExists(Root) and not FileExists(AddBackslash(Root) + BuildManifest)
      and not FileExists(AddBackslash(Root) + 'engineering-memory.exe')
      and not DirExists(AddBackslash(Root) + '_internal')
      and not FileExists(AddBackslash(Root) + 'unins000.exe') then
      Result := 'fresh';
    Exit;
  end;

  if (PreviousDir = '') or not HasVersion then Exit;
  if CompareText(RemoveBackslashUnlessRoot(ExpandFileName(PreviousDir)), Root) <> 0 then Exit;
  Result := 'repair';
  if not ReadManifest(Root, Identity, Lines) then Exit;
  if Lines[1] <> Version then
  begin
    Result := 'unverified';
    Exit;
  end;
  if not CheckPayload(Root, Version, Lines, True) or not HasUninstaller(Root) then Exit;

  if PackageVersion > CurrentVersion then Result := 'update'
  else if Identity = IncomingIdentity then Result := 'identical'
  else Result := 'different-build';
end;

function ShouldInstallPayload: Boolean;
begin
  Result := (MaintenanceMode = 'fresh') or (MaintenanceMode = 'update') or
    (not WizardSilent and ((MaintenanceMode = 'different-build') or (MaintenanceMode = 'repair')));
end;

function DecisionDescription: String;
begin
  case MaintenanceMode of
    'identical': Result := 'This exact build is already installed. Open its settings and MCP pages, or cancel to exit without changes.';
    'update': Result := 'Update Engineering Memory from ' + ObservedVersion + ' to ' + IncomingVersion + '.';
    'different-build': Result := 'Both packages are version ' + IncomingVersion + '. Replace the installed build (' +
      Copy(ObservedIdentity, 1, 12) + ') with a different build (' + Copy(IncomingIdentity, 1, 12) + ').';
    'downgrade': Result := 'Installed version ' + ObservedVersion + ' is newer than this package (' +
      IncomingVersion + '). Close Setup and use the installed version or a newer verified installer.';
    'repair': Result := 'The installed payload or build identity could not be verified. Use this verified package to repair version ' +
      ObservedVersion + ' with version ' + IncomingVersion + '. Your private settings and data are kept.';
    else Result := 'Setup could not verify the existing installation location or version. Check the installed entry and obtain a matching or newer verified package before retrying.';
  end;
end;

procedure InitializeMaintenance;
begin
  ObservedDirectory := RemoveBackslashUnlessRoot(ExpandFileName(WizardDirValue));
  MaintenanceMode := ObserveInstallation(ObservedDirectory, ObservedVersion, ObservedIdentity);
  Log('EM-MAINTENANCE: ' + MaintenanceMode);
  if WizardSilent or (MaintenanceMode = 'fresh') then Exit;

  DecisionPage := CreateInputOptionPage(wpWelcome, 'Engineering Memory installation',
    DecisionDescription, 'Choose an action or click Cancel to exit.', True, False);
  case MaintenanceMode of
    'identical':
      if not IsAdmin then DecisionPage.Add('Open existing configuration')
      else DecisionPage.Add('Open configuration later from a regular user session');
    'update': DecisionPage.Add('Update in place');
    'different-build': DecisionPage.Add('Replace the installed build');
    'repair': DecisionPage.Add('Repair the installation');
  end;
end;

function InstallationUnchanged: Boolean;
var
  Version, Identity, Root, Mode: String;
begin
  Root := RemoveBackslashUnlessRoot(ExpandFileName(WizardDirValue));
  Mode := ObserveInstallation(Root, Version, Identity);
  Result := (CompareText(Root, ObservedDirectory) = 0) and
    (Mode = MaintenanceMode) and (Version = ObservedVersion) and (Identity = ObservedIdentity);
end;

function SafeInstallDestination: Boolean;
var
  PrivateRoot: String;
begin
  PrivateRoot := ExpandConstant('{localappdata}\EngineeringMemory');
  Result := (Pos(Lowercase(AddBackslash(PrivateRoot)), Lowercase(AddBackslash(ObservedDirectory))) <> 1) and
    (Pos(Lowercase(AddBackslash(ObservedDirectory)), Lowercase(AddBackslash(PrivateRoot))) <> 1);
end;

function PreparePayload: Boolean;
var
  Previous: TArrayOfString;
  OldIndex, NewIndex, Count: Integer;
  Relative, Path: String;
begin
  Result := False;
  SetArrayLength(ObsoleteFiles, 0);
  if not SafeInstallDestination then Exit;
  try
    if GetArrayLength(IncomingLines) = 0 then
    begin
      ExtractTemporaryFile(BuildManifest);
      if not ReadManifest(ExpandConstant('{tmp}'), IncomingIdentity, IncomingLines) then Exit;
    end;
    if not CheckPayload(ObservedDirectory, IncomingVersion, IncomingLines, False) then Exit;

    { An authenticated inventory names the old application files. Keep unrelated files. }
    if ReadManifest(ObservedDirectory, ObservedIdentity, Previous) then
    begin
      NewIndex := 3;
      Count := 0;
      for OldIndex := 3 to GetArrayLength(Previous) - 1 do
      begin
        Relative := Copy(Previous[OldIndex], 66, Length(Previous[OldIndex]));
        if not SafeRelativePath(Relative) then Exit;
        while NewIndex < GetArrayLength(IncomingLines) do
        begin
          if Lowercase(Copy(IncomingLines[NewIndex], 66, Length(IncomingLines[NewIndex]))) >= Lowercase(Relative) then Break;
          NewIndex := NewIndex + 1;
        end;
        if NewIndex < GetArrayLength(IncomingLines) then
          if CompareText(Copy(IncomingLines[NewIndex], 66, Length(IncomingLines[NewIndex])), Relative) = 0 then Continue;
        StringChangeEx(Relative, '/', '\', True);
        Path := AddBackslash(ObservedDirectory) + Relative;
        if not SafePath(Path) or DirExists(Path) then Exit;
        if FileExists(Path) then
        begin
          SetArrayLength(ObsoleteFiles, Count + 1);
          ObsoleteFiles[Count] := Path;
          Count := Count + 1;
        end;
      end;
    end;
    Path := AddBackslash(ObservedDirectory) + BuildManifest;
    Result := SafePath(Path) and not DirExists(Path);
  except
    Log('EM-MAINTENANCE: unable to prepare the incoming payload');
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if (MaintenanceMode <> 'identical') and not ShouldInstallPayload then
  begin
    if WizardSilent and ((MaintenanceMode = 'different-build') or (MaintenanceMode = 'repair')) then
      Result := 'Run the installer interactively to confirm replacement or repair.'
    else Result := DecisionDescription;
  end
  else if not InstallationUnchanged then
    Result := 'The installed files or registration changed while Setup was open. Close Setup and run it again.'
  else if ShouldInstallPayload and not PreparePayload then
    Result := 'The package cannot be copied to this location. Check the selected directory for redirected or conflicting files before retrying.';
  if Result <> '' then Log('EM-MAINTENANCE: ' + Result);
end;

procedure VerifyInstalledPayload;
var
  Lines: TArrayOfString;
  I: Integer;
begin
  PayloadVerified := False;
  if not ReadManifest(ObservedDirectory, IncomingIdentity, Lines) then Exit;
  if not CheckPayload(ObservedDirectory, IncomingVersion, Lines, True) then Exit;
  for I := 0 to GetArrayLength(ObsoleteFiles) - 1 do
  begin
    if not SafePath(ObsoleteFiles[I]) then Exit;
    if FileExists(ObsoleteFiles[I]) then
      if not DeleteFile(ObsoleteFiles[I]) then Exit;
  end;
  PayloadVerified := True;
end;

procedure RegisterPreviousData(PreviousDataKey: Integer);
begin
  if ShouldInstallPayload and PayloadVerified then
    BuildRecorded := SetPreviousData(PreviousDataKey, 'BuildIdentity', IncomingIdentity);
end;

function GetCustomSetupExitCode: Integer;
begin
  Result := 0;
  if ShouldInstallPayload and not (PayloadVerified and BuildRecorded) then Result := 20;
end;

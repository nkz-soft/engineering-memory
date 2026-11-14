[Setup]
AppId=EngineeringMemory
AppName=Engineering Memory
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\EngineeringMemory
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible and not arm64
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.22000
DisableDirPage=yes
ChangesEnvironment=yes
OutputBaseFilename=engineering-memory-{#AppVersion}-windows-x64-setup
SolidCompression=yes

[Files]
Source: "{#Payload}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Code]
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
  if CurStep = ssPostInstall then UpdatePath(True);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then UpdatePath(False);
end;

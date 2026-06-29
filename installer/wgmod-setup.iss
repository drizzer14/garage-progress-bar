; Research Progress Bar - Windows installer (Inno Setup 6.x)
;
; What it does, one double-click:
;   1. Detects the World of Tanks install folder (registry + common paths), lets
;      the user confirm/override it, and validates it (version.xml present).
;   2. Resolves the client version (e.g. 2.3.0.1) and targets mods\<version>\.
;   3. Installs the bundled OpenWG GameFace dependency ONLY if it isn't already
;      present (recursive check) -- many users already have it via ModsList/Aslain.
;   4. Cleans old copies of this mod (and stale loose res_mods leftovers), then
;      installs the mod's .wotmod.
;
; Build:  see installer\build_installer.ps1  (needs Inno Setup's ISCC + the mod
;         .wotmod already built into ..\dist by build\build_wotmod.py).

#define ModId        "com.drizzer14.wgmod"
#define ModVersion   "0.1.1"
#define ModWotmod    "com.drizzer14.wgmod_0.1.1.wotmod"
#define OpenWgWotmod "net.openwg.gameface_1.1.6.wotmod"

[Setup]
AppId={{8B6A1C3E-9D42-4F7A-BE1C-0D2F7C4A9E51}
AppName=Research Progress Bar
AppVersion={#ModVersion}
AppPublisher=drizzer14
AppPublisherURL=https://github.com/drizzer14/wgmod-research-progress
DefaultDirName={code:DetectWotRoot}
DisableProgramGroupPage=yes
DisableReadyPage=no
DirExistsWarning=no
AppendDefaultDirName=no
UsePreviousAppDir=no
OutputDir=..\dist
OutputBaseFilename=ResearchProgressBar-Setup-{#ModVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName=Research Progress Bar (WoT mod)

[Files]
; The mod itself -> mods\<version>\
Source: "..\dist\{#ModWotmod}"; DestDir: "{code:GetModsVersionDir}"; Flags: ignoreversion
; Bundled OpenWG dependency -> only copied when not already installed, and never
; removed on uninstall (other GameFace mods may depend on it).
Source: "vendor\{#OpenWgWotmod}"; DestDir: "{code:GetModsVersionDir}"; Flags: ignoreversion uninsneveruninstall; Check: NeedOpenWg

[Messages]
; Repurpose the "Select Destination Location" page for picking the WoT root.
SelectDirLabel3=Setup will install Research Progress Bar into the [name] mods folder of the World of Tanks installation below.
SelectDirBrowseLabel=Confirm your World of Tanks installation folder (the one containing version.xml). To continue, click Next. To choose a different folder, click Browse.

[Code]
var
  GVersion: string;   { resolved game version, e.g. 2.3.0.1 }

{ ---- helpers ------------------------------------------------------------- }

function IsWotRoot(Path: string): Boolean;
begin
  Path := RemoveBackslashUnlessRoot(Path);
  Result := (Path <> '') and
            (FileExists(Path + '\version.xml') or
             FileExists(Path + '\WorldOfTanks.exe'));
end;

{ Parse "<version> v.2.3.0.1 #892 </version>" -> "2.3.0.1" }
function ReadGameVersion(Root: string): string;
var
  S: AnsiString;
  ver: string;
  p, i: Integer;
begin
  Result := '';
  if not LoadStringFromFile(Root + '\version.xml', S) then
    Exit;
  p := Pos('v.', S);
  if p = 0 then
    Exit;
  i := p + 2;
  ver := '';
  while (i <= Length(S)) and (((S[i] >= '0') and (S[i] <= '9')) or (S[i] = '.')) do
  begin
    ver := ver + S[i];
    Inc(i);
  end;
  { trim a trailing dot if any }
  while (Length(ver) > 0) and (ver[Length(ver)] = '.') do
    ver := Copy(ver, 1, Length(ver) - 1);
  Result := ver;
end;

{ Best-effort: scan an Uninstall hive for a "World of Tanks" entry. }
function ScanUninstall(RootKey: Integer; SubPath: string): string;
var
  Names: TArrayOfString;
  i: Integer;
  dn, loc: string;
begin
  Result := '';
  if not RegGetSubkeyNames(RootKey, SubPath, Names) then
    Exit;
  for i := 0 to GetArrayLength(Names) - 1 do
  begin
    if RegQueryStringValue(RootKey, SubPath + '\' + Names[i], 'DisplayName', dn) then
    begin
      if Pos('World of Tanks', dn) > 0 then
      begin
        if RegQueryStringValue(RootKey, SubPath + '\' + Names[i], 'InstallLocation', loc) then
        begin
          if IsWotRoot(loc) then
          begin
            Result := RemoveBackslashUnlessRoot(loc);
            Exit;
          end;
        end;
      end;
    end;
  end;
end;

function DetectFromRegistry(): string;
begin
  Result := ScanUninstall(HKLM, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall');
  if Result = '' then
    Result := ScanUninstall(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall');
  if Result = '' then
    Result := ScanUninstall(HKCU, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall');
end;

function DetectFromCommonPaths(): string;
var
  cands: TArrayOfString;
  i: Integer;
begin
  Result := '';
  SetArrayLength(cands, 6);
  cands[0] := 'C:\Games\World_of_Tanks_EU';
  cands[1] := 'D:\Games\World_of_Tanks_EU';
  cands[2] := 'C:\Games\World_of_Tanks';
  cands[3] := 'D:\Games\World_of_Tanks';
  cands[4] := ExpandConstant('{autopf}\World_of_Tanks_EU');
  cands[5] := ExpandConstant('{autopf}\World_of_Tanks');
  for i := 0 to GetArrayLength(cands) - 1 do
    if IsWotRoot(cands[i]) then
    begin
      Result := cands[i];
      Exit;
    end;
end;

{ DefaultDirName callback. }
function DetectWotRoot(Param: string): string;
begin
  Result := DetectFromRegistry();
  if Result = '' then
    Result := DetectFromCommonPaths();
  if Result = '' then
    Result := 'C:\Games\World_of_Tanks_EU';  { harmless default; user confirms on the dir page }
end;

{ mods\<version> under the user-confirmed WoT root (the chosen app dir). }
function GetModsVersionDir(Param: string): string;
begin
  if GVersion = '' then
    GVersion := ReadGameVersion(ExpandConstant('{app}'));
  Result := ExpandConstant('{app}') + '\mods\' + GVersion;
end;

{ Recursive search for net.openwg.gameface*.wotmod under a directory. }
function FindOpenWgIn(Dir: string): Boolean;
var
  FR: TFindRec;
begin
  Result := False;
  { files in this dir }
  if FindFirst(Dir + '\net.openwg.gameface*.wotmod', FR) then
  begin
    try
      Result := True;
      Exit;
    finally
      FindClose(FR);
    end;
  end;
  { recurse into subdirs }
  if FindFirst(Dir + '\*', FR) then
  begin
    try
      repeat
        if (FR.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0 then
          if (FR.Name <> '.') and (FR.Name <> '..') then
            if FindOpenWgIn(Dir + '\' + FR.Name) then
            begin
              Result := True;
              Exit;
            end;
      until not FindNext(FR);
    finally
      FindClose(FR);
    end;
  end;
end;

{ [Files] Check: copy bundled OpenWG only when it's not already present. }
function NeedOpenWg(): Boolean;
begin
  Result := not FindOpenWgIn(GetModsVersionDir(''));
end;

{ ---- WoT-running guard (file locks) -------------------------------------- }

function IsWotRunning(): Boolean;
var
  rc: Integer;
  tmp: string;
  content: AnsiString;
begin
  Result := False;
  tmp := ExpandConstant('{tmp}\wot_tasklist.txt');
  if Exec(ExpandConstant('{cmd}'),
          '/C tasklist /FI "IMAGENAME eq WorldOfTanks.exe" /NH > "' + tmp + '"',
          '', SW_HIDE, ewWaitUntilTerminated, rc) then
  begin
    if LoadStringFromFile(tmp, content) then
      Result := Pos('WorldOfTanks.exe', content) > 0;
  end;
end;

{ ---- wizard flow --------------------------------------------------------- }

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = wpSelectDir then
  begin
    if not IsWotRoot(ExpandConstant('{app}')) then
    begin
      MsgBox('That folder does not look like a World of Tanks installation ' +
             '(no version.xml found). Please choose your WoT install folder ' +
             '(for example C:\Games\World_of_Tanks_EU).', mbError, MB_OK);
      Result := False;
      Exit;
    end;
    GVersion := ReadGameVersion(ExpandConstant('{app}'));
    if GVersion = '' then
    begin
      MsgBox('Could not read the client version from version.xml in that ' +
             'folder. Please make sure it is your World of Tanks install folder.',
             mbError, MB_OK);
      Result := False;
      Exit;
    end;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if IsWotRunning() then
    Result := 'World of Tanks is currently running. Please close the game ' +
              'completely (exit the launcher too), then run this installer again.';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  modsDir, resMods: string;
begin
  if CurStep = ssInstall then
  begin
    modsDir := GetModsVersionDir('');
    { remove older builds of THIS mod (keep filenames stable across versions) }
    DelTree(modsDir + '\' + '{#ModId}' + '_*.wotmod', False, True, False);
    { remove our stale loose res_mods leftovers (these would shadow the package) }
    resMods := ExpandConstant('{app}') + '\res_mods\' + GVersion;
    DeleteFile(resMods + '\scripts\client\gui\mods\mod_wgmod.py');
    DeleteFile(resMods + '\scripts\client\gui\mods\mod_wgmod.pyc');
    DelTree(resMods + '\scripts\client\wgmod_research', True, True, True);
  end;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  { Make the Ready page remind the user to fully restart the client. }
  if CurPageID = wpReady then
    WizardForm.ReadyMemo.Lines.Add(#13#10 +
      'After installing, fully restart World of Tanks to load the mod.');
end;

; Instalador do FamosoZora Studio (Inno Setup 6).
; Compilar: ISCC.exe /DVersao=1.0.0 build\instalador.iss   (depois de rodar build\montar_app.ps1)
#ifndef Versao
  #define Versao "0.0.0"
#endif

[Setup]
AppId={{6F1C2A9E-3B7D-4E55-9A1F-FA7020CA0001}
AppName=FamosoZora Studio
AppVersion={#Versao}
AppVerName=FamosoZora Studio {#Versao}
AppPublisher=FamosoZora
AppPublisherURL=https://www.youtube.com/@famosozora
DefaultDirName={localappdata}\Programs\FamosoZora Studio
DefaultGroupName=FamosoZora Studio
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=FamosoZora-Studio-Setup-{#Versao}
SetupIconFile=icone.ico
UninstallDisplayIcon={app}\icone.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "atalho"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Atalhos:"

[InstallDelete]
; atualizacao limpa: troca o Python e os scripts inteiros (seus videos e Shorts ficam na pasta de trabalho)
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\ferramentas"

[Files]
Source: "..\dist\app\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\FamosoZora Studio"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\ferramentas\main.py"""; WorkingDir: "{app}\ferramentas"; IconFilename: "{app}\icone.ico"
Name: "{group}\Novidades (patch notes)"; Filename: "{app}\CHANGELOG.md"
Name: "{group}\Desinstalar FamosoZora Studio"; Filename: "{uninstallexe}"
Name: "{userdesktop}\FamosoZora Studio"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\ferramentas\main.py"""; WorkingDir: "{app}\ferramentas"; IconFilename: "{app}\icone.ico"; Tasks: atalho

[Run]
Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\ferramentas\main.py"""; WorkingDir: "{app}\ferramentas"; Description: "Abrir o FamosoZora Studio agora"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\ferramentas"

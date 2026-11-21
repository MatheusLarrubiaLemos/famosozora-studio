; Instalador do FamosoZora Studio (Inno Setup 6).
; Compilar: ISCC.exe /DVersao=1.0.0 build\instalador.iss   (depois de rodar build\montar_app.ps1)
; Atualizacao automatica (desde a 1.9.0): o Studio roda este instalador com /VERYSILENT (ou /SILENT, so a barra de
; progresso) e, quando foi o "Atualizar agora", com /REABRIR=1 para abrir o Studio de novo no fim.
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
; as musicas e os efeitos que VEM COM O PROGRAMA tambem sao trocados inteiros (desde a 1.4.0 ficam em subpastas).
; Os que voce coloca ficam em %LOCALAPPDATA%\FamosoZora Studio e nao sao mexidos.
Type: filesandordirs; Name: "{app}\musicas"
Type: filesandordirs; Name: "{app}\efeitos"

[Files]
Source: "..\dist\app\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\FamosoZora Studio"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\ferramentas\main.py"""; WorkingDir: "{app}\ferramentas"; IconFilename: "{app}\icone.ico"
Name: "{group}\Novidades (patch notes)"; Filename: "{app}\CHANGELOG.md"
Name: "{group}\Desinstalar FamosoZora Studio"; Filename: "{uninstallexe}"
Name: "{userdesktop}\FamosoZora Studio"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\ferramentas\main.py"""; WorkingDir: "{app}\ferramentas"; IconFilename: "{app}\icone.ico"; Tasks: atalho

[Run]
Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\ferramentas\main.py"""; WorkingDir: "{app}\ferramentas"; Description: "Abrir o FamosoZora Studio agora"; Flags: nowait postinstall skipifsilent
; atualizacao automatica com "Atualizar agora": abre o Studio de novo sozinho
Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\ferramentas\main.py"""; WorkingDir: "{app}\ferramentas"; Flags: nowait; Check: Reabrir

[UninstallDelete]
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\ferramentas"

[Code]
// /REABRIR=1 na linha de comando: o Studio pediu para ser aberto de novo depois de atualizar
function Reabrir: Boolean;
begin
  Result := ExpandConstant('{param:REABRIR|0}') = '1';
end;

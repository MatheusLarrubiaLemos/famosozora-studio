# FamosoZora Studio

App para Windows que transforma os vídeos longos do canal [FamosoZora](https://www.youtube.com/@famosozora) em Shorts prontos para YouTube, TikTok e Instagram. O fluxo tem quatro passos:

1. Transcreve o vídeo com o Whisper.
2. O Claude escolhe os cortes, seguindo as [diretrizes do canal](DIRETRIZES%20DO%20CANAL.md).
3. O app gera os Shorts com gancho, transição suave, legenda colorida por pessoa que fala, música e final "Inscreva-se".
4. Ajuda a postar pelo Buffer.

## Instalar (qualquer PC com Windows 10/11)

1. Abra **[Releases](../../releases/latest)** e baixe o `FamosoZora-Studio-Setup-X.Y.Z.exe`.
2. Abra o arquivo. Se aparecer "O Windows protegeu o computador", clique em **Mais informações → Executar assim mesmo**.
3. Pronto: abra o **FamosoZora Studio** pelo atalho da Área de Trabalho.

Não precisa instalar Python, ffmpeg nem nada mais. Com placa NVIDIA, o app oferece ativar a aceleração; sem ela, tudo funciona no processador.

**Atualizar:** baixe o instalador da versão nova e instale por cima. Seus vídeos e Shorts não são apagados.

## Novidades

Veja o [CHANGELOG.md](CHANGELOG.md) (patch notes, com o número da versão e todas as mudanças).

## Para quem mexe no código

- A versão fica em `shorts/ferramentas/versao.py`.
- Para lançar uma versão:
  1. Aumente o número em `versao.py`.
  2. Escreva a seção da versão no `CHANGELOG.md`.
  3. Faça **Commit** e **Push**.
- O GitHub Actions (`.github/workflows/build.yml`) monta o instalador sozinho, usando `build/montar_app.ps1` e `build/instalador.iss`, e publica o Release.
- Continua dando para rodar direto da pasta clonada: `shorts/0 - Instalar (so na primeira vez).bat` e depois `FamosoZora Studio.bat`.
- Vídeos, transcrições e Shorts nunca vão para o GitHub (veja o `.gitignore`).

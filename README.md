# FamosoZora Studio

Programa que transforma os vídeos longos do canal [FamosoZora](https://www.youtube.com/@famosozora) em Shorts prontos para YouTube, TikTok e Instagram. Ele transcreve com o Whisper, gera cortes com legenda palavra por palavra, gancho, música e final "Inscreva-se", e ajuda a postar pelo Buffer.

## Instalar num computador novo (Windows)

1. Instale o **GitHub Desktop** e entre com a sua conta.
2. **File → Clone repository** → escolha este repositório → escolha a pasta (qualquer uma, ex.: `D:\canal famosozora`).
3. Abra a pasta e rode **`shorts\0 - Instalar (so na primeira vez).bat`**.
   - Instala ffmpeg, Python 3.12 e o Whisper. Se o Python for instalado agora, feche a janela e rode o arquivo de novo.
   - Com placa NVIDIA ele usa a GPU; sem NVIDIA usa o processador (funciona, só é mais lento).
4. Abra o **FamosoZora Studio** pelo atalho na Área de Trabalho.

Coloque os vídeos longos em `videos\`. O guia completo está em [`shorts/COMO USAR.md`](shorts/COMO%20USAR.md).

## Atualizar

No Studio: **Baixar atualização (GitHub)**, ou no GitHub Desktop: **Fetch origin → Pull origin**.

## Mandar uma mudança feita neste computador

GitHub Desktop → escreva um resumo embaixo à esquerda → **Commit to main** → **Push origin**.

## O que NÃO vai pro GitHub

Vídeos, transcrições, `cortes.json` e Shorts prontos (as pastas de cada vídeo dentro de `shorts\`) ficam só no computador onde foram feitos. Veja o `.gitignore`.

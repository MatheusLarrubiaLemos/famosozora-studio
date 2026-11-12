# Novidades do FamosoZora Studio (patch notes)

Os números de versão seguem o padrão **MAIOR.MENOR.CORREÇÃO**:

- **MAIOR**: muda o jeito de usar (ex.: virou app instalável).
- **MENOR**: recurso novo.
- **CORREÇÃO**: conserto de erro ou um ajuste pequeno.

Toda versão nova aparece aqui com todas as mudanças. O GitHub também gera o instalador sozinho, em *Releases*.

## [1.1.0] - 2026-11-12

Organização: o programa e os seus arquivos agora ficam **separados**.

### Pastas
- **Pasta de trabalho** (vídeos, Shorts e configurações) é uma só, tanto no app instalado quanto no modo desenvolvedor. Ela é escolhida na primeira vez que o Studio abre:
  - **SIM** = `Documentos\FamosoZora`;
  - **NÃO** = escolher outra pasta, por exemplo `F:\CLAUDE\canal famosozora`.
- O código no GitHub foi reorganizado:
  - `app\`: código do Studio;
  - `app\padrao\`: configurações iniciais;
  - `musicas\`;
  - `docs\`: guia e diretrizes do canal;
  - `build\`: monta o instalador.
- A pasta do GitHub não guarda mais vídeos nem Shorts. No PC ela passa a ser `F:\CLAUDE\famosozora-studio`.
- "Mudar pasta de trabalho" agora também funciona no modo desenvolvedor.

### Removido (não era mais usado)
- `FamosoZora Studio.bat`, `0 - Instalar (so na primeira vez).bat`, `1 - Transcrever video.bat`, `2 - Gerar Shorts.bat`, `3 - Marcar camera e gameplay.bat`, `Juntar Videos.bat` e `LEIA-ME.txt`. O app instalado e o Studio fazem tudo isso.
- No lugar deles, um único **`Studio (modo desenvolvedor).bat`** na pasta do GitHub, só para testar mudanças antes do instalador.

### Melhorias
- **Juntar vídeos** abre direto na pasta `videos` da pasta de trabalho.
- O GitHub monta o instalador a cada Push (pula quando a versão já foi publicada), então mudar as pastas não exige mais editar o arquivo do GitHub.
- O aviso "Node.js 20 is deprecated" do GitHub foi corrigido (`checkout@v5`, `setup-python@v6`).
- Correção na montagem do instalador: o pip não é mais apagado sem querer (era o erro da primeira tentativa da 1.0.0).

## [1.0.0] - 2026-11-11

O FamosoZora Studio agora é um **app de verdade**, que roda em qualquer PC com Windows 10 ou 11 (64 bits).

### App instalável
- Instalador `FamosoZora-Studio-Setup-1.0.0.exe`: não precisa de administrador, Python, ffmpeg nem `.bat`, porque já vem tudo junto.
- O app fica em `%LOCALAPPDATA%\Programs\FamosoZora Studio`, com atalho na Área de Trabalho e no Menu Iniciar.
- **Pasta de trabalho**: seus vídeos, transcrições e Shorts ficam numa pasta à sua escolha (padrão: `Documentos\FamosoZora`). Para trocar: *Mais opções → Mudar pasta de trabalho*. Atualizar ou desinstalar o app não apaga essa pasta.
- As configurações (`config.json`, `vocabulario.txt`, `correcoes.txt`) ficam em `configuracoes\`, dentro da pasta de trabalho. Se você usar a pasta antiga (`canal famosozora`), elas são aproveitadas automaticamente.
- **Placa NVIDIA opcional**: se o app achar uma placa NVIDIA, ele pergunta se você quer ativar a aceleração (baixa cerca de 1 GB, uma vez só). Também dá para fazer depois em *Mais opções → Ativar placa de vídeo NVIDIA*. Sem NVIDIA, tudo funciona no processador.
- A versão aparece no título e no canto da janela. O botão **"Novidades da versão"** mostra estas notas, e elas abrem sozinhas depois de cada atualização.
- **"Procurar atualização"** abre a página de versões no GitHub. Para atualizar, é só instalar a versão nova por cima.
- Ícone novo.
- Botões menos usados foram para o menu **"Mais opções ▾"**: músicas, configurações, vocabulário, correções, diretrizes, guia, pasta de trabalho e GPU.

### Build automática no GitHub
- Quando o número em `versao.py` muda e vai para o GitHub (Push), o GitHub monta o instalador e publica em *Releases*, com o texto desta página.
- Quem ainda usa a pasta clonada pelo GitHub Desktop continua funcionando como antes.

### Shorts: visual
- **Removido o título amarelo** (a caixa amarela do gancho no começo do Short). Ele pode voltar com `"mostrar_texto_gancho": true`, mas agora como texto branco limpo, sem caixa.
- **Transição suave do gancho**: a abertura (cold open) se mistura no corte com um *fade* de 0,45 s, no vídeo e no áudio, no lugar do flash branco. Dá para ajustar com `"transicao"` (ex.: `"fade"`, `"fadeblack"`, `"smoothleft"`, `"nenhuma"`) e `"duracao_transicao"`.
- **Legendas novas**:
  - sem o amarelo;
  - **letra maior** (96, era 84) e **borda mais fina** (4, era 7);
  - a palavra falada fica cheia e um pouco maior, e as outras ficam levemente apagadas.
- **Cor por pessoa que fala**: o app identifica as vozes de cada corte. Quem fala mais fica em branco e as outras pessoas ganham outras cores (ciano, rosa, verde, laranja).
  - A legenda troca de linha quando muda quem fala.
  - Dá para ajustar com `"cor_por_falante"`, `"cores_falantes"` e `"sensibilidade_falantes"`. Valor maior junta mais as vozes; valor menor separa mais.
  - Usa modelos pequenos (cerca de 45 MB, baixados uma vez) e roda no processador. Os resultados ficam guardados em `falantes_cache.json`.

### Claude e as diretrizes do canal
- Arquivo novo, **`DIRETRIZES DO CANAL.md`**, com o Memo nº 01:
  - YouTube como TV;
  - Short apresenta, vídeo longo aprofunda;
  - título honesto;
  - foco nas partes jogando;
  - séries com roteiro;
  - conteúdo global.
- O botão **"2 Pedir cortes ao Claude"** agora manda essas regras junto com o pedido:
  - só momentos jogando;
  - cortes que se entendem sozinhos;
  - título honesto;
  - pouca hashtag;
  - palavrão pode ficar.
- Título e descrição em **inglês** (`youtube_titulo_en`, `youtube_descricao_en`). Aparecem em `textos_para_postar.txt` e nos botões **"Título EN"** e **"Desc. EN"** da janela Publicar.

## [0.4.0] - 2026-11-11

### No GitHub
- O programa foi para um repositório privado no GitHub, publicado pelo GitHub Desktop.
- Novo `.gitignore`: só o programa vai para o GitHub. Vídeos, transcrições e Shorts ficam no computador.
- Botão **"Baixar atualização (GitHub)"** no Studio.
- `README.md` e a seção "Usar em outro computador" no guia.

## [0.3.0] - 2026-11-10

### FamosoZora Studio (painel único)
- Painel com os 4 passos: **Transcrever → Pedir cortes ao Claude → Gerar Shorts → Publicar (Buffer)**.
- Janela **Publicar**: copia título, descrição e tags do YouTube e as legendas do TikTok e do Instagram, abre o Buffer e marca "Postado" em cada rede.
- `cortes.json` versão 2:
  - abertura (cold open);
  - texto do gancho;
  - legenda corrigida pelo Claude (`[[ ]]` marca o que é incerto);
  - textos por rede.
- Legenda de alta precisão: com GPU, retranscreve cada corte com o Whisper large-v3 e alinha com a legenda do Claude.
- Final de 3,5 s borrado, com "VÍDEO COMPLETO NO CANAL / INSCREVA-SE / youtube.com/famosozora".
- Músicas de fundo "idle" próprias, que abaixam sozinhas quando alguém fala (*ducking*).
- Layout padronizado: câmera de 1080×600 em cima e jogo de 1080×1320 embaixo. A câmera é marcada uma vez em *Marcar câmera e gameplay*.
- Vocabulário (nomes do canal) e correções automáticas da transcrição.
- Ao refazer os Shorts, os antigos vão para `prontos\antigos\<data>`.

## [0.1.0] - 2026-11-10

### Primeira versão
- Transcrição com Whisper (`1 - Transcrever video.bat`): gera o `.srt` do vídeo completo e a transcrição para o Claude.
- Geração de Shorts a partir dos cortes escolhidos pelo Claude (`2 - Gerar Shorts.bat`), com legenda palavra por palavra.
- **Juntar Vídeos**: junta as partes de uma live num vídeo só.
- Instalador por `.bat`: ffmpeg, Python 3.12, Whisper e GPU NVIDIA.

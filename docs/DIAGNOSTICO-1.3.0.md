# Diagnóstico do FamosoZora Studio (Fase 0 da versão 1.3.0)

Feito em 12/11/2026, na branch `v1.3.0`. Nesta fase **nada do código foi alterado**: só li tudo e escrevi este relatório.

## 0. Antes de tudo: o plano fala em 1.2.0, mas ela já existe

O plano foi escrito quando a versão era a 1.1.0. Hoje a **1.2.0 já está no GitHub** (commit `ae29e6f`, "Editar vídeo longo"). Por isso:

- este trabalho vira a **versão 1.3.0** (branch `v1.3.0`, seção `## [1.3.0]` no CHANGELOG);
- o "espaço reservado para a ideia futura" da aba Vídeos longos **já existe de verdade**: é o passo 5 (Editar vídeo longo). Na Fase 2 ele entra na aba como recurso pronto, não como espaço vazio.

Se preferir outro número de versão, me diga antes da Fase 1.

## 1. O que cada arquivo faz

### `app\` (o programa)

| Arquivo | Linhas | O que faz |
|---|---|---|
| `painel.py` | 956 | A janela do Studio: lista de projetos, botões dos 5 passos, janela Publicar, janela de revisão do vídeo longo e janela de novidades. |
| `comum.py` | 419 | Funções usadas por todos: pastas, `config.json`, ajustes, ffmpeg, Whisper, layout 9:16 e janelas de escolher arquivo. |
| `transcrever.py` | 105 | Passo 1: transcreve o vídeo com o Whisper e grava a transcrição e a legenda `.srt`. |
| `gerar_shorts.py` | 660 | Passo 3: monta cada Short (legenda, abertura, final, música) e os textos para postar. |
| `falantes.py` | 96 | Descobre quem está falando em cada trecho, para a cor da legenda por pessoa. |
| `pedido_edicao.py` | 444 | Passo 5: pedido para o Claude, conferência do `edicao.json`, bordas no silêncio e capítulos. |
| `editar_episodio.py` | 345 | Passo 5: renderiza o episódio, a prévia de 10 min e o clipe de "Ouvir emenda". |
| `marcar_camera.py` | 225 | Janela para marcar onde ficam a câmera e a gameplay. |
| `ativar_gpu.py` | 25 | Baixa as bibliotecas da NVIDIA para o Whisper (app instalado). |
| `juntar_videos_gui.ps1` | 590 | Janela (em PowerShell) que junta as partes de uma live num vídeo só. |
| `versao.py` | 3 | O número da versão. |
| `requirements.txt` | 2 | Bibliotecas que o app precisa. |
| `padrao\` | | `config.json`, `vocabulario.txt` e `correcoes.txt` iniciais, copiados para a pasta de trabalho na primeira vez. |

### `build\` (monta o instalador)

| Arquivo | O que faz |
|---|---|
| `montar_app.ps1` | Junta Python + bibliotecas + ffmpeg + scripts em `dist\app` e testa se os módulos abrem. |
| `instalador.iss` | Receita do instalador (Inno Setup): onde instala, atalhos e o que apaga ao atualizar. |
| `ler_versao.py` | Lê o número de `app/versao.py` para o GitHub. |
| `notas_da_versao.py` | Tira do CHANGELOG a seção da versão, que vira o texto do Release. |
| `github-actions-build.yml` | Cópia do workflow. **Conferi: está idêntica** ao `.github/workflows/build.yml`. |
| `icone.ico` | Ícone do app. |

### `docs\` e raiz

| Arquivo | O que faz |
|---|---|
| `docs\COMO USAR.md` | Guia de uso (vai junto no app). |
| `docs\DIRETRIZES DO CANAL.md` | Regras do canal que o Claude segue. |
| `CHANGELOG.md` | Patch notes de cada versão. |
| `README.md` | Apresentação do projeto no GitHub. |
| `Studio (modo desenvolvedor).bat` | Roda o Studio direto da pasta do GitHub. |
| `musicas\` | As duas trilhas que vêm com o app. |

## 2. Problemas encontrados

Em ordem de importância. Entre parênteses, a fase em que proponho consertar.

### 2.1 Bugs

1. **`cortes.json` com erro passa despercebido** — `gerar_shorts.py:540`. O código lê o arquivo com um valor reserva `{}` e depois confere se veio `None`, o que nunca acontece. Resultado: um `cortes.json` quebrado vira "0 cortes" sem mensagem nenhuma. O mesmo vale para a lista do painel, onde o projeto aparece como se não tivesse cortes. (Fase 1)
2. **A placa NVIDIA deste PC não está sendo usada para montar vídeo.** O ffmpeg que vai no app é sempre o "mais novo do dia" (`montar_app.ps1` baixa o `master-latest`), e ele exige o driver NVIDIA 610 ou mais novo. Este PC tem o 595.97. O app cai para o processador **sem avisar**. Proponho travar o build numa versão estável do ffmpeg (que aceita drivers mais antigos) e mostrar um aviso quando a placa existe mas não funciona. (Fase 1, com teste)
3. **Marcar câmera salva imagens dentro da pasta do programa** — `marcar_camera.py:177-179` grava `marcacao_camera.png` e `previa_short.png` ao lado do código. No modo desenvolvedor isso suja a pasta do GitHub, e essas imagens (com o seu rosto) podem ir para o GitHub sem querer, porque não estão no `.gitignore`. No app instalado, elas somem a cada atualização. O lugar certo é a pasta `configuracoes`. (Fase 1)
4. **Padrão do layout não bate** — `comum.py:91` diz `desfocado`, mas o `padrao\config.json` e o guia dizem `camera`. Funciona hoje só porque o arquivo padrão é copiado. (Fase 1)
5. **O `padrao\config.json` leva a SUA marcação de câmera** para qualquer PC onde o app for instalado. Num PC novo o certo é vir sem marcação e pedir para marcar. (Fase 1)
6. **Mensagens que falam de botões que não existem mais:** "Instalar / atualizar" (`comum.py:233`, `painel.py:564`) e "apague os da pasta prontos" (`marcar_camera.py:185`). (Fase 1)
7. **Dois vídeos com o mesmo nome em pastas diferentes** caem no mesmo projeto (`transcrever.py` usa só o nome do arquivo). Risco baixo, mas pode sobrescrever uma transcrição. (Fase 1: avisar)
8. **Gravação de arquivos não é à prova de queda** — `gravar_json` (`comum.py:161`) escreve direto por cima. Se o PC desligar no meio, o `publicacao.json` (com os "Postado") ou o `edicao.json` podem ficar pela metade. Conserto simples: gravar num temporário e trocar. (Fase 1)
9. **Legenda temporária com nome fixo** — `gerar_shorts.py:627` usa sempre `temp_legenda.ass` na pasta do projeto. Gerar dois Shorts do mesmo projeto ao mesmo tempo mistura as legendas. Vai importar na Fase 3 ("renderizar de novo só este Short"). (Fase 3)

### 2.2 Erros sem tratamento

- **Não existe arquivo de log.** Quando algo falha, a única pista é o print da janela preta. A Fase 4 pede log, então proponho criar `%LOCALAPPDATA%\FamosoZora Studio\logs\`. (Fase 1)
- `salvar_config` (`comum.py:142`) dá erro se a pasta `configuracoes` ainda não existe (marcar câmera antes da primeira abertura do Studio).
- Se o ffmpeg não for achado numa tela sem janela preta (painel, marcar câmera), o programa fecha calado.
- Mover os Shorts antigos para `antigos` falha com erro genérico se um deles estiver aberto no player.
- `falantes.py:20` baixa os modelos sem limite de tempo; com internet ruim, trava. E `falantes.py:30` usa uma forma de extrair arquivos que o Python vai mudar (já dá aviso no 3.12).
- A transcrição carrega o áudio inteiro na memória: uma live de 3 h usa cerca de 1,4 GB. No PC de mesa passa; **no notebook pode pesar**.

### 2.3 Código repetido

| O que | Onde |
|---|---|
| Teste da placa NVIDIA e parâmetros do codificador | `gerar_shorts.py:345-362` e `editar_episodio.py:29-48` |
| Ler o fps do vídeo | `gerar_shorts.py:365` e `pedido_edicao.py:227` |
| Formatar tempo (5 funções parecidas) | `tempo_txt`, `ass_tempo`, `srt_tempo`, `fmt_tempo`, `tempo_yt` |
| Mover os antigos para `antigos\<data>` | `painel.py:363` e `painel.py:928` |
| "Mostrar erro amigável e pedir print" | `comum.rodar`, `painel.py` e `marcar_camera.py` |
| Lista de extensões de vídeo | `comum.py` e `juntar_videos_gui.ps1` |

Observação honesta: as duas primeiras linhas fui eu que criei na 1.2.0, porque a regra era não mexer no `gerar_shorts.py`. Agora dá para juntar.

### 2.4 Código morto

- `transcrever.py`: `import json` e a variável `info` não são usados.
- `marcar_camera.py`: `import os` não é usado, e o "formato livre" do retângulo nunca acontece.
- `painel.py`: a lista `IGNORAR` ainda cita a pasta antiga `ferramentas`.
- `comum.py`: comentários apontam para `shorts\ferramentas\vocabulario.txt`, caminho de antes da 1.0.

### 2.5 Funções gigantes

| Função | Linhas | Como dividir |
|---|---|---|
| `editar_episodio.main` | 134 | um pedaço para cada modo (emenda, prévia, episódio) |
| `gerar_shorts.main` | 129 | preparar → gerar um Short → resumo |
| `painel.Studio.__init__` | 100 | topo, lista, botões e menu separados |
| `pedido_edicao.normalizar` | 96 | cortes, abertura e capítulos separados |
| `transcrever.main` | 82 | transcrever e gravar arquivos separados |
| `gerar_shorts.montar_ass` | 80 | estilos, título, legendas e final separados |
| `gerar_shorts.montar_comando` | 68 | vídeo, áudio e música separados |

O `painel.py` inteiro (956 linhas, 4 janelas num arquivo só) é o que mais atrapalha achar as coisas.

### 2.6 Caminhos fixos

- **Não há nenhum `F:\...` nem `C:\Users\mathe\...` no código.** Só aparecem como exemplo no guia e no CHANGELOG, o que está certo.
- Único caso: `painel.py:39` procura o `nvidia-smi` em `C:\Windows\System32`. Troco pela variável do Windows. (Fase 1)
- Endereços do canal, do repositório e do Buffer estão espalhados por `comum.py`, `painel.py` e `gerar_shorts.py`. Junto num lugar só.

### 2.7 Dependências (`requirements.txt`)

| Biblioteca | Pedido | Instalado no app | Situação |
|---|---|---|---|
| `faster-whisper` | `>=1.1.0` | 1.2.1 | usada (transcrição) |
| `sherpa-onnx` | `>=1.12` | 2.0.1 | usada (falantes) |
| `numpy` | não listado | 2.5.4 | **usada direto pelo código**, mas só vem "de carona" |

- Nenhuma biblioteca sobrando.
- **Problema: as versões são abertas** (`>=`). Cada build pega a mais nova do dia: o `sherpa-onnx` já pulou de 1.x para 2.x sozinho. Um dia isso quebra o app sem nenhuma mudança sua. Proponho travar as versões exatas que funcionam hoje e listar o `numpy`.
- O mesmo vale para o ffmpeg do build (item 2.1.2).
- Novas, para as próximas fases: `pyspellchecker` (corretor, Fase 3), `pytest`, `black` e `ruff` (só para desenvolvimento, não vão no instalador).

### 2.8 O que ainda só funciona neste PC (para a Fase 4.5)

- **Nada no código depende deste PC.** Mas:
- **A pasta `.venv` não existe aqui**, então o `Studio (modo desenvolvedor).bat` nunca foi rodado depois da reorganização da 1.1.0. Vou testar do zero.
- O `.bat` só instala as bibliotecas na primeira vez: se o `requirements.txt` mudar, ele não percebe.
- O modo desenvolvedor usa o ffmpeg do winget (9.0.2) e o app usa outro. Os dois podem se comportar diferente. Proponho o `.bat` baixar o **mesmo** ffmpeg do app para uma pasta `bin\` (fora do Git).
- O `.gitignore` não cobre: imagens geradas, logs, caches do `pytest`/`ruff`, arquivos de token.

## 3. Como o app vê as atualizações hoje (para a Fase 4)

- Hoje o botão "Procurar atualização" **só abre a página do GitHub no navegador**. O app não consulta nada sozinho.
- **Testei:** como o repositório é privado, a consulta automática sem senha responde "não encontrado" (erro 404). Para o aviso automático funcionar, é preciso escolher um caminho:

| Opção | Como fica | Contras |
|---|---|---|
| **A. Tornar o repositório público** | Funciona sem senha, em qualquer PC, para sempre. | O código e as diretrizes do canal ficam visíveis para qualquer pessoa. Vídeos e Shorts não, porque nunca foram para lá. |
| **B. Um token por PC** | O repositório continua privado. Você cria no GitHub um token "só leitura" e cola uma vez no Studio. Ele fica guardado no `ajustes.json` do PC, fora do código. | Um passo manual em cada PC, e o token vence (no máximo 1 ano). |
| **C. Um segundo repositório público só com os instaladores** | Código privado, instaladores públicos. | Precisa mudar o workflow (você cola pelo site) e criar um segredo no GitHub. É a mais trabalhosa. |

Minha recomendação: **A**, se você não se importa de o código ser público (não tem senha nem dado pessoal nele). Senão, **B**.

## 4. Proposta de estrutura (Fase 1)

A sua sugestão, com três ajustes: entram os arquivos do vídeo longo da 1.2.0, o `painel.py` vira várias telas, e as funções de ffmpeg/Whisper saem do `comum.py`.

```
famosozora-studio/
├─ app/
│  ├─ main.py                      ← ponto de entrada (abre a janela)
│  ├─ versao.py
│  ├─ interface/                   ← tudo que é tela
│  │  ├─ janela_principal.py       ← janela com as abas e o menu geral
│  │  ├─ aba_shorts.py
│  │  ├─ aba_videos_longos.py
│  │  ├─ janela_publicar.py        ← hoje dentro do painel.py
│  │  ├─ janela_edicao.py          ← revisão do vídeo longo (hoje dentro do painel.py)
│  │  ├─ janela_texto.py           ← novidades
│  │  ├─ editor_legendas.py        ← Fase 3
│  │  ├─ aviso_atualizacao.py      ← Fase 4
│  │  └─ marcar_camera.py
│  ├─ shorts/
│  │  ├─ gerar_shorts.py           ← só o "maestro"
│  │  ├─ legendas.py               ← palavras, alinhamento e arquivo .ass
│  │  ├─ montagem.py               ← comando do ffmpeg e música
│  │  ├─ textos.py                 ← textos para postar e publicacao.json
│  │  ├─ censura.py                ← Fase 3
│  │  └─ falantes.py
│  ├─ videos_longos/
│  │  ├─ pedido_edicao.py
│  │  ├─ editar_episodio.py
│  │  └─ juntar_videos_gui.ps1     ← ver decisão 3
│  ├─ nucleo/                      ← usado por todo mundo
│  │  ├─ comum.py                  ← caminhos, ajustes, config, textos
│  │  ├─ video.py                  ← ffmpeg: duração, fps, placa NVIDIA
│  │  ├─ whisper.py                ← carregar o modelo
│  │  ├─ transcrever.py
│  │  ├─ ativar_gpu.py
│  │  ├─ registro.py               ← arquivo de log
│  │  └─ atualizacao.py            ← Fase 4
│  └─ padrao/                      ← config.json, vocabulario.txt, correcoes.txt, censura.txt
├─ testes/
├─ musicas/  docs/  build/
├─ pyproject.toml                  ← configuração do black e do ruff
├─ requirements.txt  requirements-dev.txt
├─ CHANGELOG.md  README.md
└─ Studio (modo desenvolvedor).bat
```

**Como faço sem quebrar nada:**

1. **Primeiro commit: só mover**, sem mudar o conteúdo das funções. Rodo o mesmo teste da 1.2.0 (gerar o Short 04 do Bully 11 e comparar byte a byte com o atual). Só sigo se sair idêntico.
2. **Segundo commit: dividir as funções grandes** e aplicar `black` e `ruff` (linha de até 120 caracteres, como o código já usa). Repito o teste.
3. **Terceiro commit: os consertos** da seção 2.

**O que muda fora de `app\`:** o atalho do instalador passa de `painel.py` para `main.py` (`instalador.iss`), e o `montar_app.ps1` copia as pastas novas. O **workflow do GitHub não precisa mudar**, porque ele só chama os scripts de `build\`.

**Formatos:** `cortes.json` v2, `edicao.json` e `config.json` **não mudam**. Os projetos `Bully 11` e `bully12` continuam abrindo como estão.

## 5. O que você precisa decidir antes da Fase 1

1. **Versão:** pode ser **1.3.0**?
2. **Atualização automática:** opção **A**, **B** ou **C** da seção 3?
3. **Juntar vídeos:** reescrever em Python ou manter o PowerShell? Recomendo **manter por enquanto**, só mudando de pasta. Ele funciona, e a versão em Python perderia o "arrastar arquivos do Explorer para a lista" (o tkinter não faz isso sem uma biblioteca extra).
4. **ffmpeg travado numa versão estável** (item 2.1.2): posso testar? Se der certo, a placa NVIDIA volta a montar os vídeos neste PC sem atualizar o driver.
5. **Marcação de câmera padrão** (item 2.1.5): tirar a sua do arquivo padrão? No seu PC nada muda, porque a sua marcação fica na pasta de trabalho.

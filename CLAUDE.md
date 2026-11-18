# Instruções para o Claude neste repositório

- **Sem atribuição ao Claude:** não colocar "Generated with Claude Code", "Co-Authored-By: Claude", link de sessão
  nem nada parecido em commits, descrições de pull request, comentários ou qualquer outro texto do repositório.
- Escrever em português simples (o dono tem pouca experiência com código) e explicar o que mudou e por quê.
- Nomes e comentários do código em português; cada arquivo novo começa com um comentário dizendo para que serve.
- Toda mudança entra no `CHANGELOG.md`, na seção da versão em andamento.
- **O repositório é PÚBLICO: nada pessoal nele** (nome, e-mail, caminhos com o nome de usuário, chaves, senhas).
- **Bugs reportados pelo app — revisar antes de TODA versão nova:** o botão direito > "🐞 Reportar bug" do Studio
  abre issues no GitHub com a etiqueta `bug-do-app` e a marca `<!-- relato-do-app: bug-do-app -->` no texto
  (procurar pelas duas: a etiqueta só entra se existir no repositório). O relato traz versão, tela, vídeos
  selecionados, últimos cliques, erros e o fim do `studio.log`. Antes de mudar `app/versao.py` para lançar uma
  versão, ler as issues abertas com essa etiqueta ou marca, investigar e corrigir o que der; anotar cada conserto no
  `CHANGELOG.md` citando a issue e, depois de o dono aprovar, fechar a issue dizendo em qual versão saiu. O que não
  der para corrigir: explicar na issue o porquê. Fora desse momento, não precisa olhar as issues (a não ser que o
  dono peça).

---

# Conhecimento do projeto (memória para qualquer conversa nova)

Atualize esta parte quando mudar algo importante na estrutura. O detalhe "quero mudar X → abra Y" está no
`README.md`; os ajustes do `config.json` estão em `docs/COMO USAR.md` (seção 11).

## O que é
App de Windows (Python 3.12 + Tkinter) que transforma as lives de gameplay do canal em **Shorts** e em
**episódios editados** (vídeo longo) e agenda no YouTube pelo Claude do PC. Fluxo dos Shorts: transcrever
(Whisper) → o Claude escolhe os cortes (`cortes.json`) → gerar os Shorts (ffmpeg) → revisar legendas → publicar.
Fluxo do vídeo longo: transcrever → o Claude marca o que sai (`edicao.json`) → revisar → gerar o episódio → publicar.

## Dois jeitos de rodar
- **Instalado** (instalador `.exe` do GitHub Releases): existe `ferramentas\APP_INSTALADO`. Código em
  `<app>\ferramentas`, Python portátil em `<app>\python`, ffmpeg em `<app>\bin`.
- **Modo desenvolvedor**: `Studio (modo desenvolvedor).bat` → `build/preparar_dev.ps1` (cria `.venv`, baixa ffmpeg
  para `bin\`, bibliotecas da NVIDIA se tiver placa) e abre `app/main.py` com `pythonw`.
- `app/nucleo/comum.py` decide tudo: `FERRAMENTAS` (pasta do código), `PASTA_APP` (raiz), `APP_INSTALADO`,
  `PASTA_BIN` (entra no PATH).

## Onde cada coisa é gravada
- **`DADOS_APP`** = `%LOCALAPPDATA%\FamosoZora Studio`: `ajustes.json` (pasta de trabalho, última tela, playlists...),
  `logs\studio.log` (`nucleo/registro.py`), `temp\` (trechos para ouvir, instalador baixado), `bugs\` (cópia dos
  relatos), `modelos\falantes\` (modelos de voz), `gpu\` (bibliotecas NVIDIA do app instalado), `marcar_camera\`.
  No instalado também `configuracoes\`, `musicas\`, `efeitos\` (o que for acrescentado neste PC).
- **Configurações do canal**: no modo dev = `app/padrao/` (vai para o GitHub); no instalado = as de `padrao` + as
  deste PC por cima (`PASTA_CONFIG`). Arquivos: `config.json`, `pessoas.json`, `vocabulario.txt`,
  `correcoes.txt`, `censura.txt`. `carregar_config()` = padrões no código + `padrao/config.json` + o deste PC.
- **Pasta de trabalho** (`PASTA_CANAL`, escolhida no Studio; padrão `Documentos\FamosoZora`, descartável):
  `videos\` (lives), `shorts\<projeto>\` (um por vídeo), `outro\` (final dos episódios), `publicar\` (pacotes para o
  Claude publicar), `configuracoes\` (`fila_publicacao.json`, `lote.json`).
- **Projeto** = `shorts\<nome_seguro(nome do vídeo)>\`: `projeto.json` (vídeo, duração, `limpo_em`,
  `link_video_completo`, `episodio_publicado`), `transcricao.json` (segmentos com palavras `{i, f, p}`),
  `transcricao_para_claude.txt`, `legenda_video_completo.srt`, `cortes.json` (versão 3; `cortes_anterior.json`,
  `cortes.bak.json`), `prontos\` (`NN - título.mp4`, `publicacao.json`, `textos_para_postar.txt`, `antigos\`,
  `_gerando_NN.mp4` temporário), `legendas\NN_original.json` / `NN_editada.json` (com o trecho; as de outro trecho
  vão para `legendas\antigas`), `edicao_shorts\NN_sugestao.json` / `NN_edicao.json`, `falantes.json` (voz → pessoa
  por Short, com o trecho), `retranscricao_cache.json`, `falantes_cache.json`, `edicao.json` (vídeo longo,
  versão 2), `episodio\` (episódio, `episodio.json`, `textos_episodio.txt`, `_temp\`), `miniatura.png`.
- Todo JSON é gravado com `gravar_json` (arquivo `.gravando` + troca: nunca fica pela metade). Nada de mídia é
  apagado de vez: vai para a Lixeira (`nucleo/limpeza.py`, que tenta de novo se o Windows estiver segurando o arquivo).

## Como as partes conversam
- **A tela** (`app/interface/`) roda os passos pesados como **processos separados**: `rodar_script("modulo", ...)`
  abre uma janela preta (`python -m nucleo.transcrever`, `shorts.gerar_shorts`, `videos_longos.editar_episodio`...).
  Cada script usa `comum.rodar(main)` (erro → registro + código de saída 1; `--pausar` espera o ENTER).
- **Trabalho curto na própria tela** vai em segundo plano com `utilidades.em_segundo_plano` (o Tkinter só aceita
  mexer na tela pela linha principal). Nunca rodar ffmpeg/cópia de vídeo direto num botão.
- **Janelas que abrem uma vez só**: `utilidades.janela_ja_aberta(chave)` / `lembrar_janela(chave, obj)` (publicar,
  revisão do vídeo longo, Claude por projeto, Excluir); o editor de legendas usa `EditorLegendas.abrir()`.
- **Menus de botão direito**: `interface/menus.py` (todo menu ganha "🐞 Reportar bug" no fim). Cores e estilos:
  `interface/tema.py`. Avisos no canto: `notificacao.notificar`.
- A lista de projetos é recalculada a cada 4 s (`Studio.auto_atualizar` → `nucleo/projetos.listar_projetos`) e só
  redesenha quando a "assinatura" muda.
- `subprocess` chamado a partir da tela (pythonw) precisa de `creationflags=CREATE_NO_WINDOW`, senão pisca uma
  janela preta (`nucleo/video.SEM_JANELA`).

## Shorts (detalhes)
- `shorts/gerar_shorts.py`: mede o corte, prepara a legenda (`legendas.py`: retranscrição com Whisper mais preciso
  só com placa NVIDIA, conferida com a original; alinha o texto do Claude no tempo das palavras), vozes
  (`falantes.py`, sherpa-onnx), música e efeitos (`audio_short.py`, `biblioteca.py`, edição em `edicao.py`),
  censura (`censura.py`) e monta o ffmpeg (`montagem.py`: abertura + corte + final borrado com INSCREVA-SE, ducking).
  Enquanto um ffmpeg roda, a legenda do próximo já é preparada (um render por vez).
- `--so N` renderiza só o Short N (editor). O número do Short = posição do corte no `cortes.json`.
- **Lote** (`shorts/lote.py`, telas `janela_preparar_lote.py` e `janela_lote.py`): vários vídeos; duas linhas ao
  mesmo tempo (linha 1: transcrever + Claude; linha 2: gerar Shorts), processos escondidos, estado em `lote.json`
  (retoma se o app fechar). O progresso vem lendo a saída (`[n/total]`, `xx%`).

## Claude no PC
- **Sem janela** (`nucleo/claude_local.py`): `claude -p --output-format json --tools "" --no-session-persistence`,
  pedido pela entrada do programa; tenta 3 vezes; JSON errado = pede de novo uma vez; live longa = partes
  (`dividir_transcricao`) pedidas ao mesmo tempo (`pedir_partes`, 2 por padrão). Usado por
  `shorts/cortes_com_claude.py` e `videos_longos/edicao_com_claude.py`; tela de progresso `janela_claude.py`.
- **Publicar** (`publicacao/`): `rascunhos.py` (título, descrição, horário) → revisão `janela_publicar.py` →
  `fila.py` (status na fila/enviando/agendado/publicado/erro) → `pacote.py` (pasta em `publicar\` com o vídeo
  LIGADO por hard link ou copiado, thumb, `dados.txt`) → `claude_pc.py` (abre o Claude Code com `--chrome`, ou
  copia o pedido para o Cowork). O Claude grava `resultado.json` no pacote; a tela Publicação confere a cada 4 s.
  Horários sempre de Brasília (`horario.py`): Shorts às 12:00, um por dia.

## Vídeo longo
- `videos_longos/pedido_edicao.py` (pedido, formato e normalização do `edicao.json`, plano de trechos),
  `editar_episodio.py` (cada trecho recodificado com corte exato, 2 trechos ao mesmo tempo, depois junta sem
  recodificar; outro no fim com `outro.py`), revisão `interface/janela_edicao.py`.

## Testes
- `python -m pytest` = rápidos; `python -m pytest -m lento` = de ponta a ponta (ffmpeg de verdade) e telas botão a
  botão (`testes/test_telas.py`, precisa de tkinter; no Linux, rodar com `xvfb-run`). Alguns só rodam no Windows.
- `testes/conftest.py` troca `%LOCALAPPDATA%` e a pasta de trabalho por pastas temporárias (nunca mexe nos dados reais).
- Os testes de tela trocam `subprocess`, `rodar_script`, `abrir` etc. por funções que só anotam no `registro`.
  O que roda em segundo plano: esperar com `_esperar(st, condição)`.
- Conferir o código: `python -m ruff check app testes` (formatação: black, linha de 120).

## Lançar uma versão
1. Revisar os bugs reportados (regra lá em cima). 2. Aumentar `app/versao.py`. 3. Escrever a seção no
`CHANGELOG.md` (o texto vira as notas do Release). 4. Commit + push na `main`: o GitHub Actions
(`.github/workflows/build.yml`) monta o instalador (`build/montar_app.ps1` + `build/instalador.iss`) e publica o
Release, só se a versão ainda não tiver Release. Mudou a versão sem querer lançar? Não faça push na `main`.

## Armadilhas conhecidas
- Windows segura arquivos abertos (player, Explorer fazendo miniatura, antivírus): mandar para a Lixeira pode
  falhar na primeira tentativa (`limpeza.mandar_para_lixeira` já tenta de novo).
- Pacotes de publicação usam hard link: excluir o Short em `prontos\` não libera o espaço enquanto o pacote em
  `publicar\` existir (os pacotes ainda não são limpos sozinhos).
- Placa NVIDIA: Whisper na placa (float16) e NVENC; sem placa, tudo cai para o processador. A transcrição e a
  geração de Shorts do lote podem usar a placa ao mesmo tempo.
- Nomes de projeto vêm de `nome_seguro(nome do vídeo)`: dois vídeos com o mesmo nome caem no mesmo projeto
  (o transcrever avisa).

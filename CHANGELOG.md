# Novidades do FamosoZora Studio (patch notes)

Os números de versão seguem o padrão **MAIOR.MENOR.CORREÇÃO**:

- **MAIOR**: muda o jeito de usar (ex.: virou app instalável).
- **MENOR**: recurso novo.
- **CORREÇÃO**: conserto de erro ou um ajuste pequeno.

Toda versão nova aparece aqui com todas as mudanças. O GitHub também gera o instalador sozinho, em *Releases*.

## [1.9.2] - 2026-11-22

Versão de **correção e ajuste**: o vídeo do editor volta a tocar e **tudo abre dentro da janela do Studio**, sem janelas soltas.

### Tudo dentro do Studio (sem abrir outra janela)
- **Antes:** Revisar legendas, o editor do vídeo longo, Publicar, Excluir, Reportar bug, Pessoas e cores, o lote etc. abriam cada um numa janela separada do Windows.
- **Agora:** abrem **no lugar das páginas**, dentro da própria janela do Studio. Em cima aparece **"← Voltar"**, que faz o mesmo que fechar a janela antes (pergunta se quer salvar etc.).
- Na barra da esquerda aparece **"Abertas agora"**: clicar numa página (Shorts, Publicação...) não fecha o que estava aberto. Dá para voltar clicando nela ali, ou fechar no **✕**. Ao sair da tela do editor, o vídeo pausa sozinho.
- **Sem janela preta:** Transcrever, Gerar Shorts, Renderizar um Short, Gerar o episódio e Ativar a placa de vídeo rodam escondidos. O andamento fica numa tela **Tarefa**, dentro do Studio: o texto do programa, a barra com a %, e a % também aparece em "Abertas agora". Se o programa fizer uma pergunta, a tela vem para a frente com uma caixa para responder. No fim aparece o aviso de pronto (ou de erro) no canto.
- **Marcar câmera e gameplay** também abre dentro do Studio (antes era um programa à parte).
- Continuam como janelinhas do Windows só as perguntas rápidas (Sim/Não, avisos) e a escolha de arquivo/pasta.
- Arquivos: `app/interface/telas.py` (novo: as telas internas e a navegação), `app/interface/tela_tarefa.py` (novo: a tela Tarefa), `utilidades.rodar_script` (roda escondido com o Studio aberto), `interface/marcar_camera.py` (`abrir_no_studio`) e todas as telas que usavam `tk.Toplevel` (agora `nova_janela`).

### Publicação: botão "🧹 Limpar a lista"
- Tira da lista de uma vez os vídeos **agendados, no ar e com erro**. Os que ainda estão **na fila** ou **com o Claude** continuam aparecendo, porque ainda estão andando.
- **Não apaga nada e não cancela nada no YouTube**, só esconde: os dias já ocupados continuam contando para o próximo dia livre dos Shorts (senão um Short novo poderia cair num dia que já tem Short), o mesmo vídeo continua sem poder ser publicado duas vezes e os pacotes antigos continuam sendo limpos sozinhos.
- **"Mostrar os escondidos (N)"** traz tudo de volta.
- Arquivos: `app/publicacao/fila.py` (`limpar_concluidos`, `mostrar_escondidos`) e `app/interface/pagina_publicacao.py`.

### Correções
- **O vídeo do editor não tocava (tela preta, relógio parado em 00:00:00)** e, por isso, clicar na timeline também não levava o vídeo a lugar nenhum. A causa: o app baixa sempre o mpv mais novo, e a partir do mpv 0.38 o comando que abre o vídeo mudou de formato (o ponto de partida virou outra coisa), então o vídeo nunca chegava a abrir. Agora o ponto de partida é passado de um jeito que funciona em qualquer versão do mpv (`app/editor/player.py`).
- O mesmo defeito deixava o **editor do vídeo longo** parado em "Abrindo...", com a tela preta e sem as sugestões: também resolvido.
- Os erros do próprio mpv (vídeo que não abre, filtro errado) agora vão para o `studio.log`, para dar para descobrir o que houve se o player falhar de novo.

### Removido
- **"Outro editor"** (exportar o episódio para Premiere/DaVinci em XML ou um arquivo por trecho para o CapCut): saiu do editor e do botão direito da live, a pedido do dono. Arquivo `app/videos_longos/exportar_outro_editor.py` apagado, com os testes e a seção no `docs/COMO USAR.md`.

## [1.9.1] - 2026-11-21

Versão de **ajuste**: a revisão dos Shorts virou uma **tela de edição estilo CapCut**, que já abre com tudo montado, e o editor do vídeo longo segue o mesmo jeito. Letras menores e mais fácil de entender.

### Editor mais limpo e mais fácil de entender (Short e vídeo longo)
- **Letras e botões menores** no editor e na tela do Short (sobra mais espaço para o vídeo e a timeline). Estilos novos `Editor.TButton`, `EditorPasso.TButton` e `Editor.Treeview` em `interface/tema.py`.
- **Nomes claros:** "▶ Tocar" / "⏸ Pausar", "Velocidade", "Assistir: Original · Prévia do resultado · Só o que vai sair", "✨ Analisar a live", "✨ Sugerir cortes", "✔ Aceitar", "✖ Recusar", "🎬 Gerar o episódio", "🎬 Renderizar", "📅 Publicar".
- **Dica ao passar o mouse** em cada botão, dizendo o que ele faz e o atalho (`interface/dica.py`, novo).
- **Legenda das cores** logo em cima da timeline (silêncio, sem jogo, sem ação, dúvida, corte seu, fica, sai, acelera) e a lembrança "clique para pular · arraste as bordas · botão direito: mais opções".
- **Editor do vídeo longo no mesmo jeito:** abre ocupando a tela toda (Windows), com a **lista das lives à esquerda** (clique noutra live para trocar sem sair do editor; ● = já analisada), o vídeo no meio, as sugestões à direita e a timeline embaixo.

### "Revisar legendas" agora é uma tela de edição, estilo CapCut
- **Antes:** a revisão era só uma lista de falas. Para ver o vídeo era preciso clicar em "✂ Ajustar corte", que abria outra janela.
- **Agora:** é uma tela só, que já abre com tudo pronto (no Windows, ocupando a tela inteira):
  - **à esquerda**, a lista de Shorts do projeto. Clicar num Short já carrega tudo dele;
  - **no meio**, o **vídeo do Short** (prévia vertical: câmera em cima, jogo embaixo), com tocar/pausar, velocidade (1x, 1,5x, 2x, 4x, com a voz normal) e **Prévia** (toca já sem os pedaços cortados);
  - **à direita**, as abas **Legenda** (as falas e a caixa para editar), **Falantes** e **Áudio e edição**, e os botões **Salvar**, **Renderizar** e **Publicar**, sempre à vista;
  - **embaixo, na largura toda, a timeline** com as faixas:
    - **vídeo**: miniaturas, onda do som, sugestões de corte e o que fica e o que sai;
    - **LEGENDA**: cada fala é um bloco (a selecionada em laranja, a que está tocando em azul); clicar num bloco seleciona a fala;
    - **MÚSICA**: a música do Short, as trocas de música e os efeitos sonoros (♪).
- **Clicar numa fala** (na lista ou na faixa LEGENDA) leva o vídeo até ela. **Espaço** na lista toca o vídeo a partir da fala selecionada (antes tocava só o áudio). A fala da vez fica destacada enquanto toca.
- Na timeline dá para arrastar o começo e o fim do Short, cortar com I, O e X (com o foco na timeline) e aceitar ou recusar as sugestões de corte (◀ ▶ ✔ ✖ Todas, na linha de cima da timeline). Tudo é salvo sozinho, e o **Renderizar** já gera o Short com os cortes e a legenda acompanhando.
- O botão "✂ Ajustar corte" saiu (o editor agora está na própria tela).
- Cabe numa tela de 1366x768: a lista de Shorts e as faixas da timeline ficam mais finas em telas pequenas.
- Sem o player (`libmpv-2.dll`), o meio mostra a miniatura do ponto atual, e o Espaço volta a tocar só o áudio da fala.
- Arquivos: `app/interface/editor_legendas.py` (a tela), `app/editor/janela_editor.py` (o editor ganhou uma versão "encaixada", para ficar dentro de outra janela) e `app/editor/timeline.py` (faixas extras LEGENDA e MÚSICA; faixas mais finas em tela pequena).

## [1.9.0] - 2026-11-21

Versão do **Auto-Edit**: o Studio analisa a live bruta e sugere sozinho onde cortar (silêncio, sem jogo, sem ação, papo fora do jogo), e você revisa num editor de vídeo dentro do próprio Studio.

### Bugs reportados pelo app (issues #7 e #8)
- **Problema:** "os vídeos não estão seguindo o padrão do canal" e "a descrição também não pega a do canal". O Studio não tinha onde guardar o texto padrão das descrições do canal: cada episódio saía só com o que o Claude escrevia.
- **Agora:** **Configurações → Legenda e Shorts → "Descrição padrão do canal (vídeo longo)"** abre o `descricao_padrao.txt`. O que você escrever lá (links, redes, hashtags; `{canal}` vira o link do canal) **vai sozinho no fim da descrição de todo vídeo longo**, depois dos capítulos. O Claude também recebe esse texto no pedido da edição, para escrever no mesmo estilo (sem repetir). Arquivos: `nucleo/comum.py`, `publicacao/rascunhos.py`, `videos_longos/pedido_edicao.py`, `interface/pagina_configuracoes.py`, `padrao/descricao_padrao.txt`.
- Se o "padrão do canal" que você quis dizer também é do **título** (por exemplo "Série - Ep. 3: ..."), me conte como é o formato que eu coloco nas regras.

### Instalador e testes
- O instalador leva as pastas novas (`autoedit`, `editor`), a biblioteca `python-mpv` e o **`libmpv-2.dll`** (o player), baixado da compilação de shinchiro do mpv. Se esse download falhar, o instalador sai mesmo assim e o editor abre só com as miniaturas. O modo desenvolvedor (`preparar_dev.ps1`) também baixa o `libmpv-2.dll` (precisa do 7-Zip).
- Testes novos: `testes/test_1_9_0.py` (regras, consistência, trechos, mapa de tempo, desfazer, migração, capítulos, introdução protegida, continuar de onde parou, XML, descrição padrão; e, com o ffmpeg, um vídeo de amostra com fala, silêncio, tela parada, tela preta, "menu" e jogo), `testes/test_editor_telas.py` (o editor tecla a tecla) e `testes/test_ponta_a_ponta_1_9_0.py` (episódio com corte e trecho acelerado, Short com corte por dentro, exportar). Vídeo de amostra: `testes/amostra_autoedit.py`. O Claude é sempre "de mentira" nos testes.
- Diagnóstico e resultados: `docs/relatorios/DIAGNOSTICO-1.9.0.md` e `docs/relatorios/TESTES-1.9.0.md`. Guia: seções novas no `COMO USAR.md` (editar vídeo longo, ajustar corte do Short, atalhos, predefinições, exportar para outro editor).

### Auto-Edit: o motor de análise (novo)
- Pasta nova `app/autoedit/`. "Analisar a live" faz, uma vez só por live (fica guardado em `<projeto>\analise\`):
  1. **Versão leve** para o editor (`proxy.mp4`, 540p, quadro-chave a cada 0,5 s; NVENC com placa NVIDIA, x264 sem placa);
  2. **Som**: volume do jogo a cada 0,1 s e a onda para a timeline. A fala vem dos tempos das palavras da transcrição, reforçada pelo detector de voz que já vem no faster-whisper;
  3. **Imagem**: movimento só na **área do jogo** (a câmera fica de fora, porque ela sempre mexe), tela congelada, tela preta e trocas de cena;
  4. **Miniaturas** da timeline (uma a cada 5 s);
  5. **O Claude olha a tela**: mosaicos de 16 miniaturas; ele diz o que é menu, loading, espera, área de trabalho, cutscene ou jogo. Só vão os trechos em que o som e a imagem não têm certeza;
  6. **O Claude lê a conversa**: marca o papo fora do jogo (só como sugestão amarela) e acha a **introdução do episódio**;
  7. **Decide os cortes** com as regras da predefinição. É sempre a mesma conta: o mesmo vídeo com a mesma predefinição dá o mesmo resultado.
- Sem o Claude Code no PC, a análise roda sem as etapas 5 e 6 e avisa.
- Um projeto pode ter a sua própria área da câmera (`camera_area`/`gameplay_area` no `projeto.json`); sem ela, vale a do canal.

### Predefinições de corte (novo)
- Duas de fábrica, em `app/padrao/predefinicoes_corte.json`: **Longo (TV)** (corta só tempo morto de verdade e mantém as pausas naturais do jogo, como pedem as diretrizes) e **Short (dinâmico)** (cortes mais justos). Cada regra tem margem antes/depois, mínimo de cada tipo, juntar cortes próximos, nunca cortar no meio da palavra, ímã nas trocas de cena e fade de áudio em todo corte.
- Opção "acelerar em vez de cortar" (desligada por padrão): o trecho sem ação passa em 2x em vez de sair.

### Editor de vídeo dentro do Studio (novo)
- Pasta nova `app/editor/`. Na aba **Vídeos longos**, o botão principal agora é **"Editar"**: abre o editor com a live inteira.
  - **Em cima, o player** (mpv dentro da janela), de **0,5x a 4x**, com a voz normal (sem voz de esquilo). Embaixo dele: tempo atual, duração original e **duração final** (muda na hora).
  - **Embaixo, a timeline**: miniaturas, onda de som, **sugestões coloridas** (vermelho = silêncio, cinza = sem jogo, roxo = sem ação, amarelo = dúvida/papo fora, laranja = corte seu), **resultado** (verde fica, riscado sai, azul acelera) e marcadores (⭐ Short, 📑 capítulo, 📝 nota). Ctrl + roda do mouse dá zoom; arrastar a borda de um trecho ajusta (com ímã nas palavras e trocas de cena; com Alt, sem ímã).
  - **Do lado, a lista das sugestões** com filtro por motivo, "Aceitar todas deste tipo" e clique para ir até ela.
  - **Três jeitos de assistir:** "Original", **"Prévia do resultado"** (pula sozinha o que sai; é assim que dá para ver a live em 4x) e "Só o que vai sair" (para conferir rápido que nada bom foi embora).
  - **Atalhos de editor profissional:** J/K/L, Espaço, I/O/X, C, Delete, R, N/B, Enter/Backspace, setas (quadro, 5 s, troca de cena), M, Ctrl+Z / Ctrl+Shift+Z sem limite e **?** para ver todos. Dica discreta nas primeiras vezes.
  - **Botão direito num trecho:** Manter, Cortar, Acelerar 2x, Ouvir só este trecho, Mandar para Shorts, Virar capítulo, Nota, marcar a introdução.
  - **Relatório** ao lado da predefinição ("Saem 41 min: 18 de silêncio, 15 de sem jogo...") e, se você recusar muitas sugestões de um tipo, a sugestão de afrouxar a regra (você decide).
  - **"Analisar de novo com esta predefinição"**: refaz as sugestões na hora, sem perder os seus cortes.
  - **Salva sozinho** (no máximo 1 s depois de cada mudança) no `edicao.json`; na primeira gravação, a versão de antes vira `edicao.anterior.json`.
  - **Sem o player** (falta o `libmpv-2.dll`), o editor abre do mesmo jeito, mostrando a miniatura do ponto atual, e avisa.
  - Cabe numa tela de 1366x768. Um botão apertado enquanto o vídeo ainda está abrindo só avisa "espere".
- **Vídeo longo:**
  - **Introdução do episódio**: o Claude acha e ela aparece destacada no começo. É protegida: cortar dentro dela pede confirmação. Para episódio de série sem introdução, o editor avisa.
  - **Capítulos**: um marcador 📑 vira capítulo do `edicao.json`, e os tempos são recalculados para o vídeo final.
  - **"Mandar para Shorts"** (⭐): cria o corte no `cortes.json` do projeto, com começo e fim sugeridos (encaixados nas pausas da fala), e ele aparece no estúdio de Shorts.
  - **"Gerar o episódio"** sai do editor já com o outro padrão (avisa se o outro não estiver escolhido).
  - **Vários de uma vez:** selecione várias lives → **"Analisar as N lives (Auto-Edit)"** (com ou sem o Claude). Elas são analisadas uma depois da outra, e a revisão continua sendo uma por uma.
- **Shorts: botão "✂ Ajustar corte"** no editor de Shorts. Abre o mesmo editor no modo Short, só com a janela do Short (10 s antes e depois), a **prévia vertical** (câmera em cima, jogo embaixo, igual ao render) e a predefinição **Short (dinâmico)**. Dá para arrastar o começo e o fim e cortar respiros e silêncios dentro do Short. O botão **"Renderizar este Short"** fica no próprio editor.
  - **As legendas acompanham os cortes:** a conta "tempo original → tempo final" (`autoedit/trechos.py`, `MapaTempo`) vale para todas as legendas e para a cor por falante. As palavras de dentro de um pedaço cortado somem da legenda.
  - O render (`shorts/montagem.py`) corta cada pedaço com tempo exato e junta, com um fade curtinho no áudio de cada emenda. O que foi feito fica em `edicao_shorts\NN_autoedit.json`; se o corte mudar depois (Claude de novo), essa edição deixa de valer.
- **Configurações → "Cortes automáticos"**: as regras das duas predefinições, com "Salvar" (a versão da predefinição sobe) e **"Voltar ao padrão"**.

### Exportar para outro editor (novo)
- No editor ("Outro editor ▾") e no botão direito da live: **XML** para Premiere / DaVinci Resolve (FCP7 XML, já com os cortes, apontando para o vídeo original) e **um arquivo por trecho** (para arrastar no CapCut na ordem). Fica em `episodio\outro_editor\` (`videos_longos/exportar_outro_editor.py`).
- **Não** gera projeto do CapCut: o formato dele muda e às vezes vem criptografado.

### edicao.json versão 3
- O arquivo de edição do vídeo longo ganhou os campos do Auto-Edit e do editor: `tipo`, `video_original`, `predefinicao`, `introducao`, `serie`, `trechos`, `marcadores`, `historico_versao_app`. A parte do Claude (`remover`, `manter`, `capitulos`, título...) continua igual.
- **Os arquivos antigos são convertidos sozinhos**, com cópia de segurança (`edicao.bak.json`, ou `edicao.v2.bak.json` se a anterior já existir).
- Pedir a edição de novo ao Claude **não apaga** os seus trechos, marcadores e a introdução.

### Episódio: cortes do Auto-Edit, trechos acelerados e continuar de onde parou
- O episódio passa a usar os trechos do Auto-Edit e do editor. Quando a live foi analisada, o corte de pausas da 1.8.0 fica desligado (o Auto-Edit faz esse trabalho, com as regras da predefinição), para não cortar duas vezes.
- A introdução do episódio e os momentos que o Claude marcou em `manter` ficam protegidos das sugestões automáticas.
- Corte pequeno do Auto-Edit é **seco** (sem escurecer), com o fade de áudio da predefinição; corte grande (mais de 30 s) ganha o fade curto.
- Trecho acelerado: imagem e som mais rápidos, com a voz normal (sem voz de esquilo).
- Os capítulos são recalculados com os cortes e as acelerações (o tempo bate com o vídeo final).
- **Se o app fechar no meio da geração do episódio**, na próxima vez ele continua de onde parou (os trechos prontos não são refeitos), desde que a edição não tenha mudado.
- Arquivos: `videos_longos/pedido_edicao.py`, `videos_longos/editar_episodio.py`, `videos_longos/edicao_com_claude.py`, `nucleo/claude_local.py` (o Claude pode ler as imagens de uma pasta).

## [1.8.0] - 2026-11-21

Versão com **vídeo longo "cortadinho"**: o Studio corta sozinho as pausas em que você fica calado. E a tela Publicação agora deixa escolher vários vídeos de uma vez.

### Vídeo longo: cortes automáticos nas pausas (novo)
- **Problema:** o episódio editado só tirava os trechos grandes que o Claude marcava (30 s ou mais). As pausas em que você ficava calado continuavam todas, e o vídeo ficava arrastado.
- **Agora**, como nos vídeos de gameplay editados (jump cuts): o Studio acha sozinho as pausas sem fala maiores que **4 s** e corta, deixando:
  - **3 s antes** de você voltar a falar (o contexto do que vai acontecer);
  - **1 s depois** de você parar de falar (a reação respira);
  - os **momentos de ação** do jogo: o Studio mede o som do jogo (uma vez, guardado em `atividade.json`) e não corta os picos (explosão, briga, morte...);
  - os momentos que o **Claude** marcar em `manter`: o pedido agora explica que as pausas são cortadas sozinhas e pede para ele marcar o que é importante mesmo sem fala (cutscene, chefe, momento tenso).
- A emenda de uma pausa é um **corte seco** (sem escurecer a tela), com um fade bem curto só no áudio, para não estalar. Os trechos grandes do Claude continuam com a transição suave.
- Na revisão do vídeo longo aparece quantas pausas saem e quanto tempo isso tira, e uma caixinha para **desligar** o corte das pausas só naquele vídeo.
- Dá para ajustar no `config.json`: `episodio_cortar_pausas`, `episodio_pausa_minima`, `episodio_contexto_antes`, `episodio_contexto_depois` e `episodio_acao_sensibilidade` (guia, seção 11).
- Arquivo novo: `app/videos_longos/pausas.py`. Mudaram `pedido_edicao.py` (plano e pedido ao Claude), `editar_episodio.py` e `interface/janela_edicao.py`.

### Publicação: escolher vários vídeos de uma vez (issue #4)
- **Problema (relatado pelo "Reportar bug"):** na tela Publicação só dava para selecionar um vídeo por vez.
- **Agora:** Ctrl + clique, Shift + clique e **Ctrl + A** escolhem vários. O botão direito com vários selecionados manda todos de novo para o Claude, marca todos como publicados ou tira todos da fila (`app/interface/pagina_publicacao.py`).
- A outra parte do relato, o limite de 10 MB do envio, já foi resolvida na 1.7.2: você arrasta os vídeos e o Claude agenda.

## [1.7.2] - 2026-11-19

Versão de **correção**: publicar Shorts grandes (você envia, o Claude confere e agenda).

### Shorts com erro "a ferramenta de upload aceita no máximo ~10 MB"
- **Problema:** o Claude in Chrome só consegue enviar arquivos de até uns 10 MB. A maioria dos Shorts é maior, então dava erro (só os pequenos eram agendados).
- **Agora:** o envio do arquivo fica com você, e o resto com o Claude:
  1. Ao publicar, o Studio junta todos os vídeos numa pasta só (`publicar\_para_enviar`, sem gastar espaço: é ligação do mesmo arquivo) e abre ela junto com o Claude Code.
  2. Quando o Claude pedir, selecione todos (Ctrl+A), arraste para o YouTube Studio (Criar > Enviar vídeos) e responda **"pronto"** na janela do Claude.
  3. O Claude acha cada rascunho pelo nome do arquivo e, um por um, confere, preenche título, descrição, tags e playlist e agenda. Nomes repetidos ganham "(2)" para ele não confundir.
- (`app/publicacao/pacote.py`, `app/publicacao/claude_pc.py`)
- **Para os vídeos com erro ou parados "com o Claude...":** na tela Publicação, botão direito em qualquer vídeo → **"Mandar de novo todos os com erro ou parados"**. Vão todos juntos, numa pasta só (`app/interface/pagina_publicacao.py`).

## [1.7.1] - 2026-11-19

Versão de **correção**: publicar pelo Claude Code voltou a funcionar.

### A janela do Claude Code abria e não fazia nada
- **Problema:** ao publicar, a janela do Claude Code abria parada, com o aviso "was read as a value of --add-dir, not as a prompt", e nada era agendado.
- **Causa:** o Claude Code mudou: agora tudo o que vem depois de `--add-dir` é lido como mais pastas. O Studio mandava o pedido ("Leia o arquivo pedido_....txt...") depois dessa opção, então o pedido virava um "nome de pasta".
- **Conserto** (`app/publicacao/claude_pc.py`): o pedido agora vai logo depois do `claude`, antes de qualquer opção. O `--add-dir` (que libera a pasta `publicar` para o Claude ler o vídeo e gravar o `resultado.json`) ficou no fim do comando, onde não engole mais nada.
- **Pergunta de permissão da pasta `publicar`:** pode responder **Sim**. Na primeira vez numa pasta nova, o Claude Code pergunta se pode confiar nela. Enquanto ele espera a resposta, a aba do Chrome pode fechar sozinha; depois do Sim, ele lembra.
- **Para os vídeos que ficaram "com o Claude...":** na tela Publicação, clique com o botão direito no vídeo e escolha **"Mandar para o Claude de novo"**.

## [1.7.0] - 2026-11-18

Versão **bonita**: revisão geral do programa inteiro (bugs, velocidade e organização), **"Reportar bug" dentro do app** e várias correções: excluir na primeira tentativa, a tecla Delete funcionando, publicar vários vídeos de uma vez e nenhuma janela repetida.

### Revisão geral: bugs corrigidos
- **Legenda editada indo para o corte errado (importante):** a legenda que você editava no editor ficava guardada pelo NÚMERO do Short (`legendas\01_editada.json`), sem dizer de qual trecho do vídeo ela era. Se você pedisse cortes novos ao Claude e gerasse de novo, o Short 01 novo (outro trecho) saía com a legenda editada do Short 01 antigo: texto e tempos de outro momento. Agora a legenda editada guarda o trecho e só vale nele; a de outro trecho vai para `legendas\antigas` (nada se perde). O mesmo vale para "qual voz é qual pessoa" (`falantes.json`). (`app/shorts/revisao.py`, `app/shorts/pessoas.py`, `app/shorts/gerar_shorts.py`, editor)
- **O mesmo Short podia ser agendado duas vezes:** a revisão antes de publicar podia ser aberta mais de uma vez; confirmando nas duas, o vídeo ia duas vezes para o YouTube. Agora só abre uma revisão por vez (clicar de novo traz a aberta para a frente) e, ao confirmar, o Studio confere de novo se o vídeo já está na fila.
- **Janelas repetidas:** além do editor de legendas, também abriam várias vezes a revisão do vídeo longo, a janela do Claude (gerar cortes / editar vídeo longo: pedia duas vezes ao Claude) e a janela Excluir. Agora cada uma abre uma vez só.
- **Tela travada ("Não respondendo"):** o "Ouvir trecho" do editor de legendas e o "Mandar para o Claude de novo" da tela Publicação faziam o trabalho pesado (cortar o vídeo, copiar o vídeo para o pacote) na mesma linha da tela, que travava. Agora rodam em segundo plano.
- **Janela preta piscando:** ao medir um vídeo pela tela (e na ferramenta de marcar a câmera), cada consulta ao ffmpeg abria uma janelinha preta por um instante. Agora roda escondido.
- **A lista de vídeos voltava para o topo** sozinha a cada atualização (e, com um lote rodando, a cada poucos segundos). Agora ela fica onde você estava.
- **Miniaturas:** num PC novo, o Studio abria um ffmpeg para CADA projeto sem miniatura, todos ao mesmo tempo. Agora faz no máximo 2 de cada vez.
- **Corte com tempo errado** (fim antes do início) não entra mais na lista de Shorts para publicar.
- **Ajustes perdidos:** o `ajustes.json` (pasta de trabalho, última tela...) era gravado direto; se o PC desligasse no meio, podia ficar pela metade. Agora é gravado de forma segura, como os outros arquivos.
- **Transcrever vários vídeos de uma vez:** um erro num vídeo parava todos os outros. Agora ele segue para o próximo e, no fim, diz quais deram erro.

### Pacotes de publicação não acumulam mais
- **Problema:** cada vídeo agendado ganha um pacote na pasta `publicar` (vídeo, thumb e dados para o Claude), e nenhum era apagado. O vídeo do pacote é uma "ligação" do mesmo arquivo do Short: por isso **excluir o projeto não liberava o espaço** enquanto o pacote existisse. E se a pasta de trabalho estiver em outro disco, cada pacote era uma cópia inteira do vídeo.
- **Agora:** uma semana depois de o vídeo entrar no ar, o pacote vai **sozinho para a Lixeira** (o Studio confere ao abrir e avisa no canto). Ajuste `publicar_limpar_pacotes_dias` (`0` = nunca). O **Excluir** também leva os pacotes dos vídeos daquele projeto que já estão no ar (os que ainda vão sair ficam, com o aviso de sempre), e a conta de "quanto vai liberar" agora não conta duas vezes o mesmo vídeo. Só mexe em pastas de dentro de `publicar`. (`app/publicacao/pacote.py`, `app/interface/janela_excluir.py`, `app/interface/janela_principal.py`, `app/nucleo/limpeza.py`)

### Revisão geral: mais rápido (trabalho em paralelo)
- **Episódio (vídeo longo):** os trechos eram montados um de cada vez. Agora são montados **2 ao mesmo tempo** (cada trecho é independente, e um ffmpeg sozinho não usa o PC inteiro). Ajuste `episodio_partes_simultaneas` (`1` = como antes).
- **Live longa com o Claude:** quando a transcrição é dividida em partes, as partes iam ao Claude uma depois da outra. Agora vão **2 ao mesmo tempo** (gerar cortes e editar vídeo longo). Se uma parte der erro, as outras param. Ajuste `claude_pedidos_simultaneos`.
- **Shorts:** enquanto o ffmpeg monta um Short, a legenda do próximo (Whisper e detector de vozes) já vai sendo preparada. Continua um ffmpeg por vez. Ajuste `shorts_preparar_enquanto_renderiza` (`false` = como antes).
- **Transcrever vários vídeos:** o Whisper é carregado uma vez só (antes era carregado de novo a cada vídeo).
- **Lista de projetos:** o `config.json` era lido de novo para cada projeto, a cada 4 segundos. Agora é lido uma vez por atualização.

### Revisão geral: organização
- **Testes antes de lançar:** o GitHub agora roda os testes automáticos (e o conferidor de código) numa máquina separada ANTES de montar o instalador. Se algum falhar, a versão não sai, e você não recebe um instalador quebrado. Num pull request para a `main`, ele também roda os testes, para ver se está tudo certo antes de juntar. (`.github/workflows/build.yml`)
- Os relatórios antigos (`DIAGNOSTICO-*.md` e `TESTES-*.md`) foram para `docs/relatorios/`. Em `docs/` ficam só os guias.
- Saiu o `build/github-actions-build.yml`, que era uma cópia idêntica do `.github/workflows/build.yml`.
- O `CLAUDE.md` ganhou o mapa completo do projeto (para o Claude saber como tudo funciona em qualquer conversa nova).
- Os ajustes novos estão no guia (`docs/COMO USAR.md`, seção 11) e no README.

### Reportar bug pelo app (novo)
- **Botão direito em qualquer lugar do Studio** (em qualquer tela e em qualquer janela, como o editor de legendas e a revisão de publicação) tem agora **"🐞 Reportar bug..."** no fim do menu. Também tem o atalho **"🐞 Reportar bug"** embaixo, na barra da esquerda.
- Abre uma janelinha para você contar o que aconteceu (a primeira linha vira o título).
- O Studio **junta o contexto sozinho**: versão, Windows, tela aberta, vídeos selecionados (com a etapa e quantos Shorts), janelas abertas, se tem lote rodando, os **últimos cliques** (quais botões você apertou, em qual janela), os **erros que aconteceram na tela** e o fim do registro de erros (`studio.log`).
- **Nada pessoal vai para o GitHub** (ele é público): antes de montar o relato, o Studio troca a sua pasta de usuário por `%USERPROFILE%`, o seu nome de usuário do Windows por `%USERNAME%`, o nome do computador por `%COMPUTERNAME%`, esconde e-mails e qualquer coisa com cara de senha ou chave (tokens, `senha=...`, `Bearer ...`). Isso vale para o texto, os cliques e o log. Mesmo assim, confira no navegador antes de clicar em Create.
- Ao clicar em **Enviar**, ele guarda uma cópia em `%LOCALAPPDATA%\FamosoZora Studio\bugs` e **abre o navegador com uma "issue" do GitHub já preenchida** (com a etiqueta `bug-do-app`). É só conferir e clicar em **Create**. Nenhuma senha fica guardada no app.
- **Antes de cada versão nova**, o Claude lê essas issues, investiga e corrige o que der (a regra ficou escrita no `CLAUDE.md`).
- Os erros que acontecem dentro de um botão agora também vão para o `studio.log` (antes sumiam no app instalado).
- Arquivos novos: `app/nucleo/relato_bug.py` (monta o relato) e `app/interface/reportar_bug.py` (a janela e o botão direito).

### Excluir precisava de 2 ou 3 cliques
- **Problema:** ao excluir um Short ou um vídeo pelo Studio, às vezes ele não sumia e era preciso mandar excluir de novo, 2 ou 3 vezes.
- **Causa:** no Windows, logo depois de um vídeo ser gerado ou aparecer numa pasta aberta, algum programa (o Explorer fazendo a miniatura, o antivírus, a busca do Windows) ainda segura o arquivo por um instante. O Studio tentava mandar para a Lixeira **uma vez só** e desistia. Pior: mandava todos os itens de uma vez, então um arquivo preso fazia os outros ficarem também.
- **Conserto** (`app/nucleo/limpeza.py`): agora manda **um item por vez** (um arquivo preso não segura os outros) e, se sobrar algum, **espera um pouco e tenta de novo sozinho** (até 4 tentativas, uns 2,5 segundos no total). Continua indo tudo para a Lixeira: nada é apagado de vez.

### Publicar com vários vídeos selecionados só pegava um
- **Problema:** com 5 vídeos selecionados na tela Shorts, o "Publicar os Shorts prontos" mostrava só os Shorts do primeiro vídeo.
- **Causa:** o botão Publicar só olhava o primeiro vídeo da seleção.
- **Conserto** (`app/interface/aba_shorts.py` e `app/interface/janela_principal.py`): com vários selecionados, a revisão junta os Shorts prontos de **todos eles**, um por dia, começando pelo vídeo mais antigo. O botão direito com vários selecionados também ganhou "📅 Publicar os Shorts dos N selecionados".

### A tecla Delete não excluía
- **Problema:** apertar Delete com um vídeo selecionado não fazia nada.
- **Causa:** na lista de projetos, o Delete só funcionava se a lista estivesse com o foco do teclado; depois de clicar num botão, no painel da direita ou trocar de tela, o foco saía dela. E na lista de Shorts do editor de legendas o Delete nem estava ligado.
- **Conserto:** nas telas Shorts e Vídeos longos, o Delete agora abre o Excluir do que está selecionado **em qualquer lugar da janela** (`app/interface/janela_principal.py`). Numa caixa de texto ele continua só apagando a letra. No editor de legendas, Delete na **lista de Shorts** (esquerda) exclui o Short; na legenda continua excluindo a linha.

### Revisar legendas abria várias janelas iguais
- **Problema:** clicando várias vezes para revisar as legendas do mesmo vídeo, abria uma janela nova a cada clique.
- **Conserto** (`app/interface/editor_legendas.py`): o Studio lembra quais editores estão abertos. Se o daquele vídeo já está aberto, ele **só traz a janela para a frente** (e volta se estava minimizada). Vale para a tela Shorts e para o botão Revisar da janela do lote. Depois de fechar, o próximo clique abre normalmente.

## [1.6.2] - 2026-11-18

Versão de **correção e velocidade**: lote mais rápido e legenda fora do tempo em Short longo.

### Legenda toda fora do tempo em Short longo
- **Problema:** um Short de mais de 2 minutos saiu com a legenda inteira fora do tempo (os mais curtos estavam certos). Gerar de novo não adiantava.
- **Causa:** no PC com placa NVIDIA, cada corte é transcrito de novo com o modelo mais preciso. Essa segunda transcrição usava opções diferentes da primeira (sem o filtro que pula os silêncios e "lembrando" o trecho anterior). Em trecho longo, com barulho de jogo e música, o Whisper ia "escorregando" os tempos a cada pedaço de 30 s. E o resultado ficava guardado em `retranscricao_cache.json`, então gerar de novo reaproveitava os tempos errados.
- **Consertos** (`app/shorts/legendas.py`):
  - a segunda transcrição usa as **mesmas opções da transcrição do vídeo** (com o filtro de silêncio);
  - **conferência:** os tempos da segunda transcrição são comparados com os da primeira, em pedaços de 30 s. Se em algum pedaço as palavras ficaram, no meio, mais de 1 s fora do lugar, o Studio usa a transcrição original naquele Short;
  - o `retranscricao_cache.json` ganhou número de versão (2). O antigo vira `retranscricao_cache.bak.json` e é refeito sozinho.
- **Para consertar o Short que saiu errado:** no editor, botão direito no Short → **Renderizar de novo**. Se você já tinha revisado a legenda à mão, use antes **Voltar ao original**, porque a legenda revisada mantém os tempos que estavam nela.
- Testes novos em `testes/test_1_6_0.py`.

### O lote ficou mais rápido: duas linhas ao mesmo tempo
- **Antes:** o lote fazia tudo em fila. Enquanto o Claude pensava (1 a 5 minutos por vídeo), o PC ficava parado; enquanto o PC renderizava, o Claude ficava parado.
- **Agora** (`app/shorts/lote.py`) o lote trabalha em **duas linhas ao mesmo tempo**:
  - **linha 1:** transcreve e pede os cortes ao Claude, um vídeo depois do outro;
  - **linha 2:** gera os Shorts dos vídeos que já têm os cortes, na ordem do lote.
- Enquanto um vídeo renderiza, o próximo já está sendo transcrito ou com o Claude. Com vários vídeos, o tempo de espera do Claude some quase todo (só o primeiro vídeo espera).
- Um vídeo com os cortes prontos esperando a vez aparece como **⏳ na fila** com o detalhe "cortes prontos: esperando a vez de renderizar".
- Os Shorts continuam sendo gerados **um vídeo por vez** (dois ao mesmo tempo disputariam o processador e a placa de vídeo, e cada um ficaria mais lento).
- Pausar, Cancelar, "Tentar de novo só este" e "Continuar de onde parou" funcionam igual, com as duas linhas.
- Testes novos: o Claude do próximo vídeo roda enquanto o anterior renderiza, e cancelar com as duas linhas rodando para as duas.

### O tempo do lote ficava parado
- **Problema:** enquanto o Claude escolhia os cortes, a tela do lote mostrava "0 s passados" e o tempo não andava. Parecia que o lote tinha travado.
- **Causa:** o relógio só andava quando a etapa dava notícia, e o Claude passa minutos pensando sem dar notícia.
- **Conserto** (`app/shorts/lote.py`): o relógio agora anda sozinho, a cada segundo. O tempo de cada vídeo também aparece enquanto ele roda, na coluna **Tempo**, e não só no fim.
- A coluna **Detalhe** da etapa dos cortes avisa: "costuma levar de 1 a 5 min por parte".
- Teste novo em `testes/test_1_6_0.py`.

## [1.6.1] - 2026-11-17

Versão de **correção**.

### Escolher vários vídeos para transcrever
- **Problema:** a janela que abre no botão **1 Transcrever vídeo novo** (e no "Transcrever a live" dos vídeos longos) só deixava escolher **um** vídeo.
- **Conserto:** agora dá para escolher **vários** de uma vez: `Ctrl` + clique em cada um, `Shift` + clique para um intervalo ou `Ctrl` + `A` para todos da pasta. Eles são transcritos um depois do outro, na mesma janela preta (como já acontecia ao arrastar vários vídeos). Função nova `escolher_arquivos` em `app/nucleo/comum.py`.
- `docs/COMO USAR.md` (passo 1) explica como escolher vários.
- Teste novo em `testes/test_1_6_0.py`.

## [1.6.0] - 2026-11-17

Versão para **gerar os Shorts de vários vídeos de uma vez** (lote).

### Selecionar vários vídeos (tela Shorts e Vídeos longos)
- **Caixinha de marcar** em cada linha (coluna ☐/☑). Clicar na caixinha marca ou desmarca só aquele vídeo, sem tirar os outros.
- **`Ctrl` + clique** marca um a um e **`Shift` + clique** marca o intervalo (do último clique até o vídeo clicado). `Ctrl` + `Shift` soma o intervalo ao que já estava marcado.
- Botões **"Selecionar todos"** e **"Limpar seleção"** em cima da lista, e um **contador discreto** ("3 vídeos selecionados"). A caixinha do cabeçalho também marca/desmarca todos.
- Depois de "Limpar seleção", a lista não volta a marcar o primeiro vídeo sozinha quando se atualiza.
- Duplo clique na caixinha só marca/desmarca (não dispara o próximo passo sem querer).
- **Coluna "Etapa"** na tela Shorts: não transcrito · transcrito · com cortes · com Shorts.
- Com **2 ou mais** vídeos marcados na tela Shorts, o botão laranja vira **"Gerar Shorts dos selecionados (N)"** e o cartão mostra os nomes escolhidos. Com 1 vídeo, tudo continua como antes.
- As colunas ficaram um pouco mais estreitas para tudo continuar cabendo em telas de 1366×768.
- A regra da seleção ficou num arquivo novo, sem tela (`app/nucleo/selecao.py`), para dar para testar.

### Preparar lote (tudo perguntado no começo)
- Nova janela **"Preparar lote"** (`app/interface/janela_preparar_lote.py`), que abre pelo botão laranja **"Gerar Shorts dos selecionados (N)"**:
  - lista dos vídeos com **o que vai ser feito** em cada um (ex.: "transcrever → cortes com o Claude → gerar Shorts", ou só "gerar Shorts");
  - **ordem:** arraste a linha para cima ou para baixo, ou use **▲ Subir / ▼ Descer**. O padrão é a ordem da lista;
  - **vídeo que já tem Shorts:** começa como **Pular**. Dá para trocar por **Gerar de novo** (clique na coluna "Já tem Shorts?" ou nos botões), com a opção **"aplicar a todos"**. "Gerar de novo" manda os Shorts antigos para a **Lixeira**;
  - **área da câmera:** todos usam a **área padrão**. Se ela ainda não foi marcada, aparece o botão **"Marcar agora"** (vale para todos); dá para mudar pelo **"Mudar..."**. A janela percebe sozinha quando a área foi salva;
  - **sem placa NVIDIA** (notebook): aviso de que o lote vai demorar mais;
  - **sem o Claude Code:** aviso em vermelho explicando o que fazer, e o botão **Começar** fica desligado (só quando algum vídeo ainda precisa dos cortes);
  - botão **Começar**. Depois dele, o lote não pergunta mais nada.

### Rodar o lote
- **Motor do lote novo** (`app/shorts/lote.py`), sem janelas: um vídeo depois do outro, **transcrever** (se ainda não foi) → **pedir os cortes ao Claude** (se ainda não tem) → **gerar os Shorts**. Cada vídeo continua sendo um projeto separado (a sua pasta, os seus Shorts, o seu `cortes.json`).
- Roda **em segundo plano**: a janela do Studio não trava. A transcrição e a geração dos Shorts rodam em processos **escondidos** (sem a janela preta); o Studio lê o progresso deles.
- **Tela do lote** (`app/interface/janela_lote.py`): cada vídeo com a sua etapa (⏳ na fila · 🎙 transcrevendo · ✂ cortando · 🎬 renderizando · ✅ pronto · ❌ erro · ⏭ pulado), o detalhe (ex.: "Short 3 de 8"), quantos Shorts e quanto tempo levou; **barra geral** com a porcentagem, o **tempo estimado** e o tempo passado.
- **Pausar** (termina a etapa que está rodando e espera), **Continuar** e **Cancelar** (pede confirmação, para na hora sem deixar arquivo quebrado: apaga o Short que estava pela metade e o arquivo temporário da legenda; os Shorts que já ficaram prontos continuam).
- Pode **fechar a tela do lote**: ele continua. Para ver de novo, o botão laranja da tela Shorts vira **"Ver o lote em andamento"**.
- **Vídeo com erro:** o lote guarda o erro (em português) e segue para o próximo. No fim, selecione o vídeo e clique em **"Tentar de novo só este"**.
- **Fechou o app ou o PC desligou:** o estado fica em `configuracoes\lote.json` (com número de versão), gravado a cada passo. Ao abrir de novo, o Studio pergunta **"Continuar o lote de onde parou?"**. Nada que já estava pronto é refeito. Se você fechar o Studio com um lote rodando, ele pergunta antes e para a etapa atual direitinho.
- **Só um lote por vez:** enquanto um roda, não dá para começar outro.
- A transcrição ganhou a opção `--sem-perguntas` (usada pelo lote) e as partes do programa que rodam separadas agora avisam com um código de erro quando falham (o lote usa isso para saber que aquele vídeo deu erro).

### Resumo no fim
- A tela do lote vira o **resumo**: "Lote pronto: 14 Shorts de 3 vídeo(s)", quanto tempo levou, quantos Shorts de cada vídeo e quais deram erro (o primeiro com erro já fica selecionado, com a mensagem embaixo).
- Botão **"✏ Revisar"** (ou duplo clique no vídeo): abre o editor de Shorts daquele projeto.
- **Notificação discreta no canto** quando o lote termina, mesmo com a tela do lote fechada: "Lote pronto: 14 Shorts de 3 vídeos".
- **Nada é publicado sozinho.** Os Shorts ficam prontos para você revisar.

### Fechamento
- `app/versao.py` → **1.6.0**.
- `docs/COMO USAR.md`: seção nova **"Gerar Shorts de vários vídeos de uma vez"** (passo a passo), duas linhas novas em "Problemas comuns", o `lote.json` em "Onde fica cada coisa" e o "refazer todos" indo para a Lixeira.
- `README.md`: os arquivos novos no mapa "quero mudar X → abra Y".
- **Instalador:** nenhuma biblioteca nova (o lote usa só o que já vinha, como o `Send2Trash`). O teste do instalador (`build/montar_app.ps1`) agora abre também os módulos novos. O `.github/workflows/build.yml` não mudou.

### Consertos achados nos testes
- Projeto com transcrição, mas sem o texto para o Claude, não é mais transcrito de novo à toa quando já tem cortes.
- Erros técnicos comuns do lote viram explicação em português (sem internet para baixar o modelo do Whisper, falta de memória, disco cheio).
- Enquanto o lote roda, a limpeza da memória é feita pela linha da tela (antes, raramente, a tela podia travar alguns segundos depois de fechar uma janela).
- As colunas da tela do lote e da janela Preparar lote ficaram mais largas (os textos não aparecem mais cortados), e a coluna "Etapa" mostra "não transcrito" inteiro.

### Lixeira no "refazer todos"
- No botão **Gerar Shorts** de um vídeo só, a opção **SIM = refazer todos** agora manda os Shorts antigos para a **Lixeira** (antes iam para a pasta `antigos` do projeto). Se não conseguir mandar (vídeo aberto em outro programa), avisa e não refaz.

### Documentos antigos
- Tiradas as menções aos serviços de publicação que não são mais usados do `CHANGELOG.md` e dos documentos de diagnóstico e testes das versões 1.3.0 e 1.5.0.

### Documentos
- Novo `docs/DIAGNOSTICO-selecao-multipla.md`: por que hoje não dá para gerar de vários vídeos, como cada etapa funciona, o que pergunta no meio do caminho, riscos, a ordem sugerida e as decisões aprovadas.

### Testes
- Novo `testes/test_1_6_0.py`: clique simples, Ctrl, Shift, Ctrl+Shift, caixinha, todos, nenhum, contador, a coluna Etapa e o lote com o Claude e o Whisper falsos: montar o lote na ordem, cada vídeo no seu projeto, pular vídeo com erro, "Tentar de novo só este", Pular / Gerar de novo (Lixeira), cancelar no meio sem arquivo quebrado (inclusive parando um processo de verdade), pausar e continuar, fechar o app no meio, salvar e retomar o `lote.json`, migração do formato antigo com `lote.bak.json`, dois lotes ao mesmo tempo e tempo estimado.
- Novo `testes/test_ponta_a_ponta_lote.py` (lento): 3 vídeos de amostra de 20 s feitos com o ffmpeg (um sem transcrição, um sem cortes e um que já tinha Shorts, com "Gerar de novo"), sem área da câmera marcada e sem placa NVIDIA, rodando o lote de verdade com o Claude falso; e um 4º vídeo cancelado no meio da geração de verdade, conferindo que não sobra arquivo quebrado. Usa o Whisper de verdade quando consegue baixar o modelo.
- Novo `docs/TESTES-1.6.0.md` com a tabela de resultados e o que conferir no seu PC.
- `testes/test_telas.py`: o caminho inteiro pela tela (selecionar 3 vídeos → Preparar lote → Começar → resumo → Revisar → Tentar de novo), a pergunta "Continuar o lote de onde parou?" e se as janelas novas cabem em 1366×768.
- `testes/test_telas.py`: teste novo que clica na lista de verdade (caixinha, Ctrl, Shift, Selecionar todos, Limpar) e confere o botão laranja do lote.

## [1.5.1] - 2026-11-17

Versão de **correções** nos Shorts.

### Legenda adiantada no silêncio
- **Problema:** às vezes o vídeo estava em silêncio e a legenda da próxima fala já aparecia, bem antes da hora.
- **Causas e consertos** (`app/shorts/legendas.py`):
  - o Whisper às vezes marca o começo de uma palavra muito antes de ela ser falada (em geral a primeira depois de um silêncio). Agora uma palavra não pode durar mais que o razoável para o tamanho dela (mínimo 0,6 s; mais letras, mais tempo): se passar, o começo vai para perto do fim;
  - palavra que o Claude acrescentou na legenda corrigida e o Whisper não tinha ouvido era espalhada pelo silêncio inteiro antes da fala. Agora ela fica colada na fala que vem depois (0,35 s por palavra);
  - trecho que o Claude reescreveu e que tinha uma pausa no meio (mais de 0,6 s) era espalhado por cima da pausa. Agora as palavras são repartidas só pelo tempo em que há fala.
- **Para os Shorts que já existem:** gere de novo (**3 Gerar Shorts → SIM**, ou botão direito no Short → Renderizar de novo). Não precisa transcrever de novo nem chamar o Claude. Short com legenda **revisada à mão** mantém os tempos da sua revisão: nesse caso, botão direito no Short → Voltar ao original, ou acerte o tempo da linha com duplo clique.

### Título dos Shorts sem o nome do vídeo no final
- **Problema:** desde a 1.5.0 os títulos vinham com o nome do vídeo/live colado no fim (o pedido automático passou a informar o nome da live e a regra dizia "se for série, cite o episódio").
- O pedido ao Claude (o automático e o de copiar e colar) e as diretrizes do canal agora dizem: título **só sobre o que acontece no corte**, sem o nome do vídeo, da live, do episódio nem do canal.
- **Segurança:** se mesmo assim o título vier terminando com o nome do vídeo depois de " - ", " | ", ":", "#" ou entre parênteses, o Studio tira sozinho ao receber os cortes. Nome que faz parte da frase ("Explodi a bike no Bully") não é mexido.
- **Shorts já gerados:** a tela de **Publicar** já mostra o título limpo. O título que aparece dentro do vídeo e o nome do arquivo só mudam se você pedir os cortes de novo.

### Testes
- Testes novos para os três casos da legenda e para a limpeza dos títulos.

## [1.5.0] - 2026-11-16

Versão de **publicação e interface nova**: o Studio ganhou o visual cinza e laranja com barra lateral, o editor de Shorts virou "duplo clique e botão direito", dá para excluir projetos pelo app (sempre para a Lixeira), o Claude do seu PC escolhe os cortes, edita o vídeo longo e **agenda no YouTube** com um clique, e o vídeo longo perdeu o gancho e ganhou o **outro** no final.

### Interface nova (cinza + laranja)
- **Todas as cores num arquivo só:** `app/interface/tema.py`. Fundo `#1F1E1D`, painéis `#2B2A28`, bordas `#3A3936`, texto `#ECEAE4`, texto secundário `#A8A49B`, laranja `#D97757` (botão principal, tela ativa, barra de progresso), laranja do mouse `#E08A6D`, verde `#7FB069` (sucesso) e vermelho `#D9534F` (só excluir e erro). As cores que estavam espalhadas em 12 arquivos agora vêm do tema.
- **Barra lateral** no lugar das abas: **Início · Shorts · Vídeos longos · Publicação · Configurações** (atalhos `Ctrl+1` a `Ctrl+5`). O Studio lembra a última tela aberta.
- **Início:** mostra o que está pendente: vídeos para transcrever (inclusive os que estão na pasta `videos` e ainda não viraram projeto), Shorts para fazer/revisar/publicar, vídeos longos esperando revisão e os próximos agendamentos. Clicar num item leva para a tela certa com o projeto já selecionado.
- **Cartões de projeto** com **miniatura** do vídeo (gerada sozinha com o ffmpeg, arquivo `miniatura.png` no projeto), nome, quantos Shorts, quantos publicados e o status.
- **Uma ação principal por tela, em laranja:** ao lado da lista fica o projeto selecionado com um único botão laranja que faz o **próximo passo** (ex.: "Gerar os Shorts"). Os outros passos ficam em botões discretos. Duplo clique no projeto faz o próximo passo.
- **Configurações** virou uma tela (antes era o botão "Menu"): pasta de trabalho, legenda e Shorts, músicas e efeitos, atualizações e ajuda. "Marcar câmera e gameplay" foi para lá.
- **Abre sempre maximizada**, no monitor onde estava da última vez. `F11` = tela cheia sem bordas; `Esc` sai da tela cheia. Se o monitor de antes não existir mais, abre no principal.
- **Arrastar e soltar:** arraste um ou vários vídeos para a janela e cada um vira um projeto (o Studio já abre a transcrição). Também tem o botão **"+ Adicionar vídeo"** no Início. Usa a biblioteca nova `tkinterdnd2`; se ela faltar, o resto funciona normal.
- **A transcrição aceita vários vídeos de uma vez** (um depois do outro, na mesma janela). Se você disser "não" para um vídeo, ele pula para o próximo em vez de fechar.
- **Estados vazios explicando o próximo passo** (ex.: "Nenhum vídeo ainda. Arraste um vídeo para esta janela ou clique em Adicionar vídeo.").
- **Notificações discretas no canto** (`app/interface/notificacao.py`) no lugar de algumas janelas de aviso que travavam a tela (ex.: "Limpar projeto" e "Colar edicao.json" quando dá tudo certo).
- Pasta nova `outro\` na pasta de trabalho, com `LEIA-ME.txt` (usada pelos vídeos longos), e pasta `publicar\` (pacotes de postagem).

### Editor de Shorts: duplo clique, botão direito e atalhos
- **Sumiram as fileiras de botões.** Embaixo ficam só **Salvar**, **Renderizar** e **Publicar** (laranja). O resto está no botão direito e nos atalhos.
- **Duplo clique** numa linha da legenda edita o texto ali mesmo (**Enter** salva, **Esc** cancela). Duplo clique no **Início** ou no **Fim** edita o tempo (ex.: `12:03.5`); o app não deixa o tempo invadir a linha de cima ou de baixo. Duplo clique em **Quem fala** abre a lista de pessoas.
- **Botão direito numa linha:** ▶ Ouvir este trecho · Assistir este trecho (vídeo) · ✏ Editar texto · Editar tempo › · 🗣 Trocar quem fala › (lista de pessoas, com ✓ em quem está) · 🔇 Censurar palavra › (as palavras da linha, com ✓ nas censuradas) · Sempre censurar (pôr na lista) › · ➕ Inserir linha abaixo · 🗑 Excluir linha · Desfazer.
- **Botão direito na caixa da linha:** censurar / tirar a censura da palavra clicada, ou pôr na lista.
- **Inserir linha:** cria uma linha nova logo abaixo, no espaço até a próxima fala (se não tiver espaço, divide o finalzinho da linha de cima), já abrindo para você digitar. Esc cancela e a linha some.
- **Botão direito na música:** Ouvir · Trocar · Sortear outra do clima · Volume · Excluir (também pelo botão "Opções da música ▾"). **Num efeito:** ouvir sozinho, ouvir o trecho com o efeito, trocar, volume, mudar o tempo, excluir. Duplo clique num efeito toca ele; `Delete` exclui.
- **Botão direito no Short da lista:** Abrir (assistir) · Renderizar de novo · Publicar · Abrir pasta · Voltar ao original · **Excluir este Short** (vai para a Lixeira, sai da lista de publicação e o corte não é gerado de novo; a transcrição e os outros Shorts ficam). Duplo clique no Short = assistir.
- **Atalhos:** `Ctrl+S` salvar, `Ctrl+Z` desfazer, `Espaço` tocar/parar o áudio da linha (dentro do Studio, sem abrir o player), `Delete` excluir linha, `F2` (ou `Enter`) editar. Os atalhos não atrapalham quando você está digitando.
- **Dica discreta no rodapé** nas 5 primeiras vezes que o editor abre.
- O editor abre num tamanho que cabe em telas de 1366×768.
- "Possível erro de português" agora aparece em amarelo (vermelho fica só para erro e excluir).
- **Lixeira:** agora usa a biblioteca `send2trash` (a função antiga do Windows fica de reserva). Se não conseguir mandar para a Lixeira, o arquivo **fica**: nada é apagado de vez.

### Excluir projetos e vídeos pelo app
- **Botão direito num projeto** (telas Shorts e Vídeos longos) abre o menu com os passos do projeto e **🗑 Excluir...**. Também dá para apertar `Delete` ou o botão "Excluir..." ao lado da lista.
- A janela de confirmação oferece:
  - **Só os Shorts gerados** (mantém transcrição, cortes e edições; dá para gerar de novo). Na tela de vídeos longos: **Só o episódio gerado**;
  - **Projeto inteiro** (Shorts, episódio, transcrição, cortes e edições; o vídeo original fica);
  - **Projeto + vídeo original**, com aviso em **vermelho** mostrando o caminho do vídeo, e uma segunda confirmação.
- Mostra **quanto espaço vai liberar** em cada opção.
- Avisa se o vídeo original está dentro da pasta do projeto (aí ele vai junto com "Projeto inteiro").
- **Seleção múltipla:** `Ctrl` + clique ou `Shift` + clique para escolher vários projetos e excluir todos de uma vez.
- **Sempre vai para a Lixeira** (biblioteca `send2trash`), nunca apaga de vez. Se não der (vídeo aberto no player), o app avisa em português e não apaga nada.
- **Início:** botão direito num vídeo da pasta `videos` que ainda não virou projeto: Transcrever · Mostrar na pasta · Excluir vídeo (Lixeira).
- O botão antigo "Limpar projeto (depois de postar)" deu lugar ao **Excluir...** (a opção "Só os Shorts gerados" / "Só o episódio" faz o papel da limpeza).

### Publicação no YouTube pelo Claude no seu computador
- A janela antiga de copiar textos para o YouTube, TikTok e Instagram deu lugar à publicação pelo **Claude no seu PC**, que agenda pelo **YouTube Studio no seu Chrome**.
- **Dois jeitos** (Configurações → Claude): **Claude Code + Claude in Chrome** (o Studio abre o `claude --chrome` já com o pedido e ele agenda sozinho) ou **Cowork / app do Claude** (o Studio copia o pedido e abre o app; você cola e envia). O padrão é **Automático**: Claude Code se estiver instalado, senão Cowork. Botão **"Testar: achar o Claude neste computador"**.
- **Tela de revisão antes de publicar:** título (com contador até 100 caracteres), data e hora (horário de Brasília, mostra o dia da semana), descrição, tags, playlist (lembra a última) e thumb (vídeo longo). **Nada é publicado sem o clique em "Confirmar e publicar".** O app não deixa confirmar com título vazio ou grande demais, data que já passou ou dois Shorts no mesmo dia.
- **Horário automático dos Shorts:** **12:00 de Brasília**, **um por dia**, no dia **depois do último Short já agendado** (nunca com menos de 1 hora de antecedência). Vídeo longo: você escolhe; a sugestão vem do `config.json` (`publicar_longo_hora`, padrão 18:00, e `publicar_longo_daqui_a_dias`, padrão 1).
- **Botões de publicar:** "Publicar" no editor e no botão direito do Short; **"5 Publicar os Shorts prontos"** (todos os prontos do vídeo); **"Publicar todos os Shorts prontos"** na tela Publicação (todos os vídeos, um por dia).
- **Pacote de postagem** em `publicar\<data> <título>\`: o MP4 final (ligado ao original, sem gastar disco, quando dá; senão copiado), `thumb.png`, `dados.txt` (título, descrição, tags, playlist, data e hora) e `dados.json`. Botão direito na fila → **"Copiar pedido para o Claude"**.
- **Fila de publicação** em `configuracoes\fila_publicacao.json` (pasta de trabalho), com a situação de cada vídeo: na fila · com o Claude · agendado · no ar · erro, e o link do YouTube. Sobrevive a fechar o app: ao abrir, o Studio confere e continua de onde parou. Gravação segura (arquivo temporário + troca), com versão e migração automática (cópia `.bak.json`).
- **O Studio sabe quando o Claude terminou:** o pedido manda o Claude gravar `resultado.json` no pacote (`{"status": "agendado", "link": ...}`). O Studio confere a cada poucos segundos e avisa no canto ("Agendado: ... qua 18/11 às 12:00"). Sem resposta em 12 horas, o item vira erro com a explicação. Passou do horário, vira "no ar".
- **Tela Publicação:** a fila com cores por situação, o motivo do erro embaixo e o botão direito: abrir no YouTube, abrir o pacote, assistir, mostrar na pasta, copiar pedido, mandar de novo, marcar como agendado (cola o link) ou publicado, tirar da fila (avisa que isso não cancela no YouTube).
- Quando um Short é agendado, o projeto marca como **publicado** (a coluna "Publicados" da lista). O vídeo longo agendado vira o **link do vídeo completo** dos Shorts, se ainda não tiver um.
- **Um Short conta como publicado quando saiu nas redes ativas** (`"redes"` no `config.json`, padrão só `["youtube"]`). Antes precisava estar marcado nas 3 redes.
- O pedido de cortes ao Claude agora pede textos **só para o YouTube** (título até 100 caracteres, descrição com `{link}`, tags). O `textos_para_postar.txt` não tem mais TikTok e Instagram.
- **Excluir avisa** se algum vídeo do projeto ainda está na fila e não saiu.
- Guia novo: **`docs/PUBLICAR.md`** (o que instalar, como funciona a fila, o que fazer quando dá erro).

### Pedir cortes e edição ao Claude com um clique
- **"Gerar cortes com o Claude"** (Shorts) e **"Editar com o Claude"** (vídeo longo): o Studio manda a transcrição + as diretrizes do canal + o formato do arquivo para o **Claude Code do seu PC** (modo sem janela, `claude -p`, com a sua assinatura) e recebe o JSON sozinho. **Sem copiar e colar.**
- **Janela de progresso** com barra, o que está acontecendo, o tempo passando e o botão **Cancelar** (fecha o Claude na hora; nada muda no projeto). O Studio continua usável enquanto isso.
- **Erro de rede:** tenta de novo sozinho, **até 3 vezes** (com uma pausa entre as tentativas).
- **Live longa demais para um pedido só:** a transcrição é dividida em partes (sem cortar fala no meio) e as respostas são juntadas. Cortes repetidos na emenda entre partes: fica o de nota maior. No vídeo longo, no fim vai um pedido curto com o resumo dos capítulos para o título, a descrição e as tags.
- **Confere o JSON que voltou** (tempos dentro do vídeo, fim depois do início, Short de 5 s a 3 min, título até 100 caracteres...). Se vier quebrado, **pede de novo uma vez**, explicando o erro; se vier errado de novo, avisa em português e não muda nada.
- O arquivo anterior **não se perde**: vira `cortes_anterior.json` / `edicao_anterior.json`. Se já existir, o Studio pergunta antes de pedir de novo.
- **Sem o Claude Code instalado,** os botões fazem do jeito antigo (copiam o pedido para colar no Claude). O jeito antigo também está no botão direito do projeto: "Copiar pedido de cortes" / "Copiar pedido de edição".
- O aviso de custo do plano não entrou: ele era para o caminho da API paga da Anthropic, e o Studio usa o Claude Code com a sua assinatura (sem custo por pedido).
- Configurações novas (opcionais) no `config.json`: `modelo_claude` (vazio = o padrão do Claude Code) e `claude_limite_caracteres` (tamanho de cada parte da transcrição; padrão 250 mil caracteres).

### Vídeos longos: sem gancho, com intro e outro
- **Sem gancho inicial:** o episódio começa normal, do começo, **mantendo a intro**. A "abertura" (cold open) saiu do vídeo longo (nos Shorts ela continua).
- **`edicao.json` versão 2** (formato novo): `{"versao": 2, "remover": [{"inicio", "fim", "motivo"}], "capitulos": [{"tempo", "titulo"}], "titulo", "descricao", "tags", ...}`. Os projetos antigos são **convertidos sozinhos** na primeira vez que abrem, com cópia de segurança `edicao.bak.json` (a abertura antiga é descartada).
- **Pedido ao Claude no estilo programa de TV:** sem picotar, cortes só onde realmente não acontece nada (espera, menu, tela parada, papo sem nada), manter a intro, sem gancho. As diretrizes do canal foram atualizadas.
- **Transições suaves:** cada emenda (onde saiu um trecho) ganha um fade curto (`episodio_fade_emenda` no `config.json`, padrão 0,2 s; 0 = corte seco). Trecho muito curto não ganha fade, para não piscar.
- **Outro padrão no final de todo vídeo longo:**
  - pasta nova **`outro\`** na pasta de trabalho, com `LEIA-ME.txt`; você coloca lá o seu outro (ex.: `outro.mp4`). Se tiver mais de um, vale o primeiro em ordem alfabética;
  - no render, o Studio junta o outro no final com uma **transição curta (xfade no vídeo + acrossfade no áudio)**, de 0,6 s (`outro_transicao` no `config.json`);
  - se a **resolução, o FPS ou o áudio** do outro forem diferentes, ele é **convertido na hora** para combinar com o episódio. Outro sem áudio ganha silêncio;
  - opção por vídeo **"Incluir o outro no final"** (ligada por padrão), na revisão. Pasta vazia: avisa e gera sem outro;
  - **dica no editor:** o outro precisa ter de **5 a 20 segundos** para dar para pôr a tela final do YouTube (o Studio avisa se estiver fora disso);
  - a duração do outro conta nos capítulos (a regra "capítulo a menos de 10 s do fim" agora olha o vídeo com o outro).
- **Tela de revisão nova:**
  - **linha do tempo** do vídeo inteiro com os trechos que saem (laranja), os que você mandou manter (cinza) e os capítulos; clicar num trecho acha ele na lista;
  - **botão direito** num trecho (na lista ou na linha do tempo): ▶ Ouvir o trecho que sai (abre o primeiro minuto do trecho no player) · ▶ Ouvir a emenda (como fica) · **Manter este trecho** · **Remover este trecho**. Duplo clique = ouvir o trecho que sai;
  - os capítulos vão para a descrição;
  - embaixo: Gerar prévia, **Mais opções ▾** (ouvir emenda, pedir de novo ao Claude, colar edicao.json, abrir pasta), **Publicar** e **Gerar episódio** (laranja). Cabe em telas de 1366×768.
- **Publicar o vídeo longo** igual aos Shorts: botão **Publicar** (na revisão, no botão direito do projeto e no passo "4 Publicar o episódio"), revisão, horário (sugestão do `config.json`), fila. A descrição já vai com os capítulos (no tempo do episódio editado). Depois de agendado, o projeto mostra "✓ Publicado" e o link vira o "link do vídeo completo" dos Shorts.

### Testes, instalador e documentação
- **Testes novos** (`testes/test_1_5_0.py`, `testes/test_ponta_a_ponta_longo.py` e mais telas em `testes/test_telas.py`): próximo dia livre às 12:00 de Brasília, fila (situações e retomada depois de fechar o app), pacote de postagem, envio ao Claude Code e ao Cowork (com respostas falsas, sem publicar nada), Lixeira, exclusão, edição da legenda (inserir, excluir, mudar o tempo), Claude sem janela (tentativas, cancelar, JSON quebrado, partes), migração do `edicao.json`, outro com resolução/FPS/áudio diferentes (vídeo e outro de amostra gerados com o ffmpeg) e um teste que confere se tudo cabe numa tela de **1366×768**. Resultado em `docs/TESTES-1.5.0.md`.
- Para caber em 1366×768: a lista de projetos encolhe, "Abrir pasta" e "Excluir" ficam lado a lado e o link do vídeo completo virou um texto clicável no cartão do projeto.
- **Instalador:** leva a pasta nova `publicacao\`, o guia `PUBLICAR.md` e as bibliotecas novas (`tkinterdnd2` e `Send2Trash`, pelo `requirements.txt`); o teste do instalador agora abre também os módulos novos. As pastas `outro\` e `publicar\` ficam na pasta de trabalho e o Studio cria sozinho ao abrir.
- **Bibliotecas do plano que não entraram:** `keyring` e o cliente do Google. Com a API do YouTube fora, o Studio não guarda nenhuma chave nem senha.
- **Docs:** `COMO USAR.md` reescrito (barra lateral, tabela de botão direito e atalhos, excluir, publicar, pasta `outro\`, edição do vídeo longo com o Claude), `PUBLICAR.md` novo, `README.md` (mapa "quero mudar X → abra Y" com os arquivos novos) e as diretrizes do canal (vídeo longo sem gancho).
- `app/versao.py` → **1.5.0**.

### Documentação
- Novo `docs/DIAGNOSTICO-1.5.0.md`: como o app está hoje (interface, pedidos ao Claude, publicação, vídeos longos, botões do editor), riscos e a ordem sugerida para a versão 1.5.0.

## [1.4.0] - 2026-11-16

Versão de **edição de áudio e falantes**: cada pessoa tem nome e cor, o Claude escolhe só os cortes que valem a pena (sem número fixo), a música combina com o clima do corte e entram efeitos sonoros. Tudo pode ser ligado, trocado ou excluído Short por Short no editor, sem refazer a transcrição nem chamar o Claude de novo.

### Falantes com nome e cor
- **Regra nova:** fala sem dono = **FamosoZora, em branco**. A regra antiga "quem fala mais no Short fica branco" deixou de existir (antes, se um amigo falasse mais, ele ficava branco e você ciano).
- **Cadastro de pessoas** (`pessoas.json`), que vale para todos os projetos: *Menu → Pessoas e cores da legenda*. Dá para criar, renomear, mudar a cor, excluir e escolher quem é a pessoa **padrão** (a que fica com as falas sem dono). A pessoa padrão não pode ser excluída.
  - O cadastro que vem com o programa fica em `app\padrao\pessoas.json`; o deste PC, em `%LOCALAPPDATA%\FamosoZora Studio\configuracoes\pessoas.json`.
  - Ao renomear uma pessoa, o nome também muda nos projetos que já usavam o nome antigo.
- **Editor de legendas com abas:** "Legenda" e "Falantes".
  - **Falantes:** cada voz que o detector achou no Short, com **▶ ouvir** uma amostra da voz, a escolha da pessoa (do cadastro ou "+ nova pessoa...") e o botão de cor.
  - **Legenda:** coluna nova "Quem fala" e a escolha **"Quem fala nesta linha"**, para corrigir quando o detector erra. A caixa da linha fica na cor da pessoa (prévia da cor).
  - **Aviso de contraste:** cor escura demais (ex.: azul-escuro) mostra "difícil de ler com a borda preta".
  - O **Desfazer** agora vale para tudo do Short (texto, censura, falantes e edição).
- **Mostrar nome de quem fala** (opcional, por Short, desligado por padrão): uma etiqueta pequena com o nome, na cor da pessoa, acima da legenda, só quando quem fala não é a pessoa padrão. Entra e sai com um fade curto.
- As vozes são ligadas **Short por Short** (arquivo `falantes.json` do projeto), porque o detector de vozes roda em cada corte separado e não reconhece a mesma voz entre Shorts.
- A abertura (cold open), quando fica fora do corte, ganha vozes próprias ("Voz 1 (abertura)"), sem se misturar com as do corte.
- Saiu do `config.json` a opção `cores_falantes` (a ordem de cores). As cores agora vêm do cadastro de pessoas. `cor_por_falante` continua ligando/desligando o detector de vozes.

### Shorts sem número obrigatório
- O pedido ao Claude agora diz: **gere só os cortes que valem a pena** (chamativos e/ou engraçados). Pode ser 0, 3 ou 15: qualidade acima de quantidade. O resumo das diretrizes continua indo junto. (Na 1.3.0 já não havia número fixo no código; o pedido só não falava de quantidade.)
- Cada corte passa a trazer:
  - `"clima"`: `engracado`, `epico`, `tenso`, `emocionante`, `calmo` ou `caotico` (escolhe a música);
  - `"motivo"`: 1 frase dizendo por que o trecho prende;
  - `"nota"`: de 1 a 10, a força do corte.
- **Editor de legendas:** a lista de Shorts fica ordenada pela nota (os mais fortes em cima, com `[8]` na frente) e o topo mostra nota, clima e "por que prende". O número do arquivo (`01`, `02`...) não muda.
- **Máximo de Shorts por vídeo** (*Menu → Máximo de Shorts por vídeo...*, ou `"maximo_shorts"` no `config.json`). Vazio = sem limite. É só um teto: se o Claude mandar mais, o Studio gera os de nota mais alta e avisa quantos ficaram de fora.
- **0 cortes não é erro:** aparece "Nenhum trecho forte o bastante nesse vídeo" (antes a lista dizia "Tudo postado!").
- **`cortes.json` versão 3**, com migração automática: um arquivo antigo (lista solta ou versão 2) ganha `"versao": 3` e a cópia de segurança `cortes.bak.json` (a primeira cópia nunca é apagada). Os campos antigos não mudam; os novos são opcionais.
- As DIRETRIZES DO CANAL ganharam a regra 8 (quantidade, clima, motivo e nota).

### Música tema conforme o clima
- A pasta de músicas agora tem **uma subpasta por clima**: `engracado\`, `epico\`, `tenso\`, `emocionante\`, `calmo\`, `caotico\` e `geral\` (serve para qualquer clima). Um `LEIA-ME.txt` explica onde pôr cada uma.
- **Migração automática:** as músicas soltas (de antes da 1.4.0) são **copiadas** para `geral\`, sem apagar nada. As duas trilhas que vêm com o programa já estão em `musicas\geral\`.
- No render, cada Short usa uma música da pasta do **clima do corte**. Pasta vazia → usa `geral\`. Nenhuma música → o Short sai **sem música** e a janela avisa.
- **Não repete** a mesma música em Shorts seguidos do mesmo projeto e, se der, usa todas as do clima antes de repetir. O sorteio é sempre o mesmo para o mesmo projeto: renderizar de novo não troca a música.
- O campo `"musica"` do corte (ou do `config.json`) continua valendo para pedir uma música pelo nome; `"nenhuma"` deixa sem música.
- **Mixagem:**
  - **Emenda sem pulo:** música menor que o Short agora repete com **crossfade** de 1,5 s (antes repetia "seca"). Música muito curta (menos de 4 s) só repete.
  - **Ducking mais forte:** a música abaixa bem mais quando alguém fala. Nos testes com voz normal, ela abaixava ~3 dB na 1.3.0 e agora abaixa ~9 dB, voltando sozinha depois da fala. Ajustável no `config.json`: `ducking_limiar` (0.015) e `ducking_forca` (10).
  - Volume baixo por padrão (`volume_musica`), fade-in e fade-out curtos, e a música sobe no final (INSCREVA-SE), como antes.
  - Tudo roda no processador: não precisa de placa de vídeo. Nos testes, a mixagem não aumentou o tempo de render de forma perceptível.
- *Menu*: "Músicas de fundo (por clima)" e o novo "Efeitos sonoros" abrem as pastas.
- O `.gitignore` deixou de ignorar os `.wav` de `musicas\` e `efeitos\`: eles agora vão para o GitHub no Push.

### Efeitos sonoros (SFX) e troca de música
- Pasta nova **`efeitos\`**, por categoria: `risada\`, `impacto\`, `falha\`, `suspense\`, `vitoria\`, `transicao\` (pode criar outras). Começa vazia, com um `LEIA-ME.txt` explicando onde pôr os arquivos. *Menu → Efeitos sonoros* abre a pasta. O Studio **não baixa nada da internet**: só usa o que você colocar (sem direitos autorais / licenciado), para não tomar Content ID.
- O pedido ao Claude manda **só as categorias que têm arquivo**. O Claude pode sugerir, por corte, `"sons": [{"tempo": "00:12:15.4", "categoria": "impacto", "motivo": "tomou o soco"}]`.
- **Regras para o Claude** (no pedido e nas DIRETRIZES, regra 9): efeito só quando combina com o momento, nada de som em todo segundo (sem cara de edição frenética), no máximo ~3 por Short e nunca em cima de uma fala.
- **Troca de música num momento-chave** (ex.: virada épica): `{"tempo": "...", "tipo": "musica", "clima": "epico"}`, no máximo 1 por Short. A música nova entra com crossfade.
- **No render:** o Studio escolhe um arquivo da categoria (sem repetir no mesmo Short, se der), põe no tempo certo (o tempo do vídeo original vira o tempo do Short, contando a abertura) e mistura com a voz e a música, com volume próprio e limitador para não estourar.
- Categoria sem arquivo, tempo inválido ou fora do Short: o efeito é ignorado com aviso, sem erro.
- `config.json`: `maximo_efeitos` (3) e `volume_efeitos` (0.8).

### Editor: aba "Áudio e edição"
Na mesma janela de revisar legendas, uma aba nova para a música e os efeitos de cada Short:
- **Interruptores** "Música ligada" e "Efeitos ligados", para comparar rápido com e sem.
- **Música tema:** nome do arquivo e clima do corte, ▶ Ouvir, 🔄 Trocar... (lista das músicas, começando pelas do clima), 🎲 Sortear outra do clima, 🗑 Excluir (Short sem música), controle de volume e "Tirar a troca de música".
- **Efeitos sonoros:** uma linha por efeito (tempo, categoria, arquivo, volume e motivo do Claude), com ▶ Efeito sozinho, ▶ Trecho com o efeito (prévia de ~5 s com a fala, a música e o efeito, sem renderizar o vídeo), ✏ Tempo, 🔄 Trocar arquivo, 🔊 Volume, 🗑 Excluir e "+ Adicionar efeito" (no tempo da linha selecionada na aba Legenda).
- **Avisos:** efeito em cima de uma fala fica em vermelho ("pode cobrir a voz"), e aparece um aviso se passar do máximo de efeitos.
- **Restaurar sugestão do Claude** volta a música e os efeitos ao que o Claude sugeriu (dá para desfazer).
- Salvar, Desfazer e "Renderizar de novo só este Short" valem para tudo. O que você muda vai para `edicao_shorts\NN_edicao.json`; a sugestão do Claude fica guardada à parte. Se a edição ficar igual à sugestão, nenhum arquivo de edição é guardado.
- Shorts gerados antes da 1.4.0: a sugestão é montada na hora em que você abre o Short, do mesmo jeito que o render faria.
- A janela ficou um pouco mais alta (1180 × 780).

### Edição por Short (base para música e efeitos)
- Pasta nova no projeto, `edicao_shorts\`: `NN_sugestao.json` (o que saiu da geração, sugestão do Claude) e `NN_edicao.json` (o que você mudou no editor). Fica separada do `edicao.json` do vídeo longo.
- Se você pedir cortes novos e o Short 03 virar outro trecho, a edição antiga é ignorada em vez de ir para o lugar errado.

### Instalador e documentação
- `build/montar_app.ps1` agora copia `musicas\` **com as subpastas** e a pasta nova `efeitos\` para o app instalado, cria todas as subpastas de clima e de categoria e para com erro se as músicas não forem copiadas. O teste de módulos do build também abre `biblioteca`, `audio_short` e o editor.
- Instalador: na atualização, as músicas e os efeitos **que vêm com o programa** são trocados inteiros (a pasta antiga, sem subpastas, não fica misturada). As suas músicas e efeitos, em `%LOCALAPPDATA%`, não são mexidos.
- `docs/COMO USAR.md`: como cadastrar pessoas e cores, as abas Falantes e Áudio e edição, como organizar as pastas de músicas por clima e de efeitos, e os ajustes novos do `config.json`.
- `README.md`: o mapa "quero mudar X → abra o arquivo Y" com os arquivos novos.
- `docs/DIAGNOSTICO-1.4.0.md` (Fase 0) e `docs/TESTES-1.4.0.md` (tabela de resultados).

### Testes
- **83 testes passando** (tabela completa em `docs/TESTES-1.4.0.md`).
- `testes/test_1_4_0.py`: pessoas e cores, contraste, legenda com nome, migração do `cortes.json`, 0 cortes, teto de Shorts, música por clima (com pasta vazia e sem nenhuma música), não repetir música, limite de efeitos, tempo do efeito no Short, edição por Short (salvar, desfazer, restaurar).
- `testes/test_ponta_a_ponta_audio.py` (novo, roda no Windows e no Linux): vídeo de amostra de 20 s e sons de teste gerados com o ffmpeg. Gera o Short, nomeia um falante, troca a música, adiciona e exclui um efeito e renderiza de novo só este Short. Mede no áudio o ducking, o efeito no tempo certo e se estoura, e confere a cor da legenda no vídeo.
- O teste das telas agora também aperta os botões dos painéis Falantes e Áudio e edição e da janela Pessoas e cores.
- **Erros achados e corrigidos pelos testes:**
  - a música curta parava no meio do Short (o crossfade precisava abrir o arquivo uma vez por repetição);
  - o nome de quem fala ficava em cima da legenda quando ela quebrava em duas linhas.

## [1.3.0] - 2026-11-14

Versão grande: a janela ganhou **duas abas** (Shorts e Vídeos longos / Lives), um **editor de legendas** com censura, o botão **Limpar projeto** e o **aviso de atualização automático**. O código foi reorganizado para ficar fácil de achar as coisas, vários erros escondidos foram consertados e agora existem **testes automáticos**.

> **Ao atualizar:** as suas configurações (vocabulário, correções, marcação da câmera) e músicas saem da pasta de trabalho e passam a ficar junto do programa. O Studio copia sozinho na primeira abertura; não precisa fazer nada.

### Duas abas: Shorts e Vídeos longos / Lives
- A janela principal agora tem **duas abas**, cada uma com a sua lista de projetos e os seus passos:
  - **Shorts:** 1 Transcrever → 2 Pedir cortes ao Claude → 3 Gerar Shorts → 4 Revisar legendas → 5 Publicar, mais "Marcar câmera e gameplay".
  - **Vídeos longos / Lives:** 1 Juntar vídeos (partes da live) → 2 Transcrever a live → 3 Editar vídeo longo, mais "Colar edicao.json". O antigo passo 5 virou o passo 3 desta aba.
- Cada aba mostra só as colunas que interessam: a de Shorts mostra cortes, Shorts e postados; a de Vídeos longos mostra a edição do Claude e o episódio.
- O que vale para o programa inteiro saiu das abas e foi para o botão **Menu**, no topo: novidades, procurar atualização, pasta de trabalho, configurações, vocabulário, correções, músicas, diretrizes, guia e placa NVIDIA.

### Editor de legendas (passo 4 da aba Shorts)
Fluxo novo: gerar o Short → **revisar as legendas** → renderizar a versão final.
- Botão novo **"4 Revisar legendas"**. Abre a lista de Shorts do projeto e, ao escolher um, a legenda em linhas, com início, fim e texto.
- **Editar:** selecione a linha, mude o texto na caixa de baixo e aperte Enter.
  - Com a mesma quantidade de palavras, cada palavra mantém o seu tempo.
  - Com quantidade diferente, o tempo da linha é repartido entre as palavras novas.
- **Amarelo:** palavras que o Claude marcou como incertas (`[[ ]]`). **Sublinhado:** possível erro de português (corretor ortográfico em português; os nomes do vocabulário do canal não contam como erro).
- **Ouvir trecho:** corta do vídeo original só o trecho daquela linha e abre no player. Duplo clique na linha faz o mesmo.
- **Salvar**, **Desfazer** (volta uma mudança por vez) e **Voltar ao original**.
- **Renderizar de novo só este Short:** refaz apenas aquele Short com a legenda revisada, sem refazer a transcrição nem chamar o Claude.
- A legenda original nunca é perdida. Ficam na pasta do projeto: `legendas\NN_original.json` (como saiu da geração) e `legendas\NN_editada.json` (a sua revisão).
- Shorts gerados antes desta versão não têm a legenda guardada: é só renderizar de novo uma vez.
- **Correções viram sugestão:** ao salvar, o Studio mostra as palavras que você trocou à mão e pergunta se quer gravar no `correcoes.txt`, para o erro não se repetir. Só grava se você disser SIM.

### Censura (por Short, desligada por padrão)
As diretrizes do canal permitem palavrão, então nada é censurado sozinho. A censura é uma escolha sua em cada Short.
- **Censurar palavra:** no editor, clique na palavra e no botão. Ela vira `p***` na legenda, só naquele Short.
- **Lista de censura** (`censura.txt`, uma palavra ou expressão por linha): vale só nos Shorts em que você marcar "Censurar as palavras da lista".
- **Adicionar sempre à lista:** grava a palavra selecionada no `censura.txt`.
- **Áudio (opcional):** `"censura_audio"` no `config.json`. O padrão é `"nenhum"` (só a legenda muda). Com `"silencio"`, a palavra é calada; com `"bip"`, entra um bip no lugar.

### Aviso de atualização automático
- Ao abrir, o Studio procura sozinho, **em segundo plano** (a tela não trava), se existe versão nova no GitHub.
- Se tiver, aparece uma janela com o número da versão, as novidades e os botões **"Atualizar agora"** (baixa o instalador, abre e fecha o Studio para instalar) e **"Depois"**.
- Sem internet, ou se o GitHub não responder, não aparece nada: só fica registrado no log.
- **Importante:** com o repositório **privado**, o GitHub não deixa o app consultar as versões, e o aviso não aparece. Ele passa a funcionar quando o repositório for **público**.
- **Modo desenvolvedor** (pasta do GitHub): em vez do instalador, o Studio confere se a `main` do GitHub tem código novo, feito em outro PC, e oferece baixar (Pull). Também avisa quando há alterações suas que ainda não foram para o GitHub (sem Commit ou sem Push).
- Opção no Menu: **"Verificar atualizações ao abrir"** (ligada por padrão; vale só para o PC onde for mudada).
- O botão **Menu → Procurar atualização** usa a mesma consulta e sempre responde.

### Editar o código de qualquer PC (de mesa ou notebook)
- O **`Studio (modo desenvolvedor).bat`** agora prepara tudo sozinho, em qualquer PC:
  1. confere se o Python 3.12 existe (se não, explica o que fazer e abre a página de download);
  2. cria a pasta `.venv` e instala as bibliotecas, **só quando o `requirements` muda** (nas outras vezes abre em poucos segundos);
  3. baixa o ffmpeg para a pasta `bin`, o mesmo do instalador;
  4. com placa NVIDIA, baixa as bibliotecas dela; sem placa (notebook), tudo funciona no processador;
  5. abre o Studio.
- **Sincronização segura:** no modo desenvolvedor, **antes de abrir** a janela o Studio confere o GitHub:
  - tem código novo, feito em outro PC? Pergunta se quer baixar e já abre com ele;
  - tem alterações suas que ainda não foram para o GitHub? Avisa para fazer Commit e Push.
- O `README.md` ganhou a seção **"Configurar em outro PC"**, passo a passo, com a regra de ouro: antes de mexer, Fetch/Pull; depois de mexer, Commit + Push.
- Nada no código depende de um PC específico: não há caminhos fixos como `F:\...`. A pasta de trabalho é escolhida em cada PC.

### Testes automáticos
- Pasta nova **`testes/`**, com `pytest`:
  - **testes rápidos** (menos de 1 segundo): tempos, versões, pastas, correções, censura, `cortes.json` v2, duração do Short, legendas editadas, edição do vídeo longo, capítulos e limpeza;
  - **de ponta a ponta**: um vídeo de amostra de 20 s, com a voz do Windows falando, passa por transcrever → cortes → Short → editar a legenda → renderizar de novo, no processador (como no notebook);
  - **botão a botão**: aperta cada botão das duas abas, das janelas e do Menu, e falha se algum der erro.
- Nenhum teste usa os seus vídeos ou a sua pasta de trabalho. A tabela de resultados está em `docs\TESTES-1.3.0.md`.
- As últimas funções grandes (montar a legenda, montar o comando do ffmpeg e transcrever) foram divididas em partes menores, protegidas pelos testes.

### Limpar projeto
- Botão novo **"Limpar projeto (depois de postar)"**, nas duas abas.
- Manda para a **Lixeira do Windows** o que pesa: os Shorts, o episódio, as versões antigas e os temporários. Dá para restaurar pela Lixeira.
- **Guarda o resumo** (poucos KB): cortes, edição, transcrição, legendas revisadas, textos para postar e o que já foi marcado como postado. O projeto continua na lista como "Projeto limpo".
- Avisa antes se algum Short ainda não está marcado como postado ou se existe um episódio gerado.
- Também dá para mandar o projeto inteiro para a Lixeira, inclusive o resumo.
- O vídeo original nunca é tocado.

### Código reorganizado
- A pasta `app\` agora é dividida por assunto:
  - `interface\`: tudo que é tela;
  - `shorts\`: como os Shorts são montados;
  - `videos_longos\`: episódio editado e juntar vídeos;
  - `nucleo\`: a base usada por todos (pastas, ffmpeg, Whisper, transcrição).
- O arquivo da janela principal, que tinha 960 linhas e 4 janelas, virou 6 arquivos menores, um por janela.
- O gerador de Shorts virou 4 arquivos: legendas, montagem, textos e o "maestro".
- As funções grandes dos Shorts e do episódio foram quebradas em funções menores, com nomes que dizem o que fazem.
- O programa agora abre pelo `main.py`. O atalho é trocado sozinho ao instalar a versão nova.
- O `README.md` ganhou um mapa: "quero mudar X → abra o arquivo Y".
- Código padronizado com `black` (formatação) e `ruff` (aponta erros), configurados no `pyproject.toml`.
- Os Shorts não mudaram: o mesmo Short do Bully 11 sai com a imagem idêntica à de antes.

### Configurações fora da pasta de trabalho
- A **pasta de trabalho agora é descartável**: tem só os vídeos e os projetos em produção. Depois de postar, pode limpar.
- **Configurações e músicas ficam junto do programa, no GitHub** (`app\padrao\` e `musicas\`): vocabulário, correções, marcação de câmera e `config.json`. Mudou num PC, fez Commit + Push, chegou no outro.
- No **app instalado**, o que for mudado pelo app fica em `%LOCALAPPDATA%\FamosoZora Studio\configuracoes` (e `\musicas`) e vale **junto** com o que vem do GitHub. As configurações que estavam na pasta de trabalho são aproveitadas sozinhas na primeira abertura.

### Consertos
- **`cortes.json` com erro agora avisa.** Antes, um arquivo quebrado virava "0 cortes" sem mensagem nenhuma. Agora a lista mostra o problema e o gerador para com uma mensagem clara.
- **Placa NVIDIA de volta.** O instalador passava a levar sempre o ffmpeg mais novo do dia, que deixou de aceitar drivers NVIDIA um pouco mais antigos, e o app caía para o processador sem avisar. Agora o ffmpeg é travado na versão 8.1, que funciona com esses drivers, e o app **avisa** quando acha a placa mas não consegue usá-la.
- **Legenda temporária com nome por Short:** gerar dois Shorts do mesmo projeto ao mesmo tempo não mistura mais as legendas.
- **Versões das bibliotecas travadas** (`requirements.txt`). Antes, cada instalador pegava a versão mais nova do dia, e uma atualização de fora podia quebrar o app.
- **Marcar câmera** não salva mais imagens dentro da pasta do programa (elas podiam ir para o GitHub sem querer). Agora vão para `%LOCALAPPDATA%\FamosoZora Studio\marcar_camera`.
- **Arquivos `.json` à prova de queda:** se o PC desligar no meio da gravação, o arquivo antigo continua inteiro (vale para os "Postado", o `edicao.json` e o `config.json`).
- **Arquivo de log:** os erros agora ficam registrados em `%LOCALAPPDATA%\FamosoZora Studio\logs\studio.log`.
- **Transcrever** avisa quando já existe um projeto com o mesmo nome feito de outro vídeo, em vez de substituir calado.
- O download dos modelos de voz não trava mais para sempre com internet ruim (limite de 60 s).
- **Conexão com o GitHub mais confiável:** o Python às vezes recusava o certificado do GitHub ("certificate verify failed"), dependendo do servidor. Agora os downloads do app conferem o certificado do mesmo jeito que o Windows (biblioteca `truststore`).
- Mensagens que citavam botões que não existem mais foram corrigidas.
- O `.gitignore` agora cobre logs, caches, imagens geradas e arquivos de senha.
- O relatório `docs\DIAGNOSTICO-1.3.0.md` lista tudo o que foi encontrado. Ele fica só no GitHub, não vai no instalador.

## [1.2.0] - 2026-11-12

Novidade grande: o Studio agora também edita o **vídeo longo**. A live bruta vira um episódio editado, estilo programa de TV, pronto pra postar toda semana.

### Passo 5: Editar vídeo longo
- Botão novo **"5 Editar vídeo longo"** e coluna nova **Episódio** na lista (`-` = não editado, `revisar` = o Claude já mandou a edição, `ok` = episódio gerado).
- **Pedido de edição pro Claude** (no mesmo estilo do "Pedir cortes"): vai com a pasta do projeto, o resumo das diretrizes e os critérios de corte. O Claude lê o `transcricao_para_claude.txt` direto da pasta (a transcrição não vai colada no pedido) e salva o `edicao.json`.
  - **Sai:** espera antes do jogo, intro, menus e carregamentos longos, pausas e papo com o jogo parado.
  - **Fica:** tudo em que você está jogando, inclusive conversa e piada durante o jogo. Das tentativas repetidas da mesma missão, ficam a primeira, a que deu certo e as que tiveram reação boa.
  - Nenhum corte menor que 30 s, todo corte em fim de frase, e "trecho sem fala não é trecho morto".
- Botão **"Colar edicao.json"**: quando a conversa com o Claude não tem acesso ao PC, copie o JSON que ele mandar e clique aqui. O Studio lê da área de transferência, confere e salva (o anterior vira `edicao_anterior.json`).
- **Janela de revisão** (obrigatória, porque o Claude só vê a transcrição, não a tela):
  - no topo, a duração original → a duração final;
  - a lista do que vai **sair**, com início, fim, duração e motivo;
  - uma caixinha em cada corte para desmarcar (o trecho desmarcado fica no episódio);
  - aviso nos cortes com menos de 30 s;
  - **Ouvir emenda**: gera em segundos um clipe de 10 s (5 s antes do corte + 5 s depois, já emendados) e abre no player;
  - **Gerar prévia (10 min)**: renderiza só os primeiros 10 minutos e mostra a velocidade e a estimativa de tempo do episódio inteiro;
  - **Gerar episódio**.
- O resultado vai para `<pasta do projeto>\episodio\`:
  - o `.mp4` do episódio (com o título do episódio no nome);
  - o `textos_episodio.txt`, com título, descrição e capítulos em português e em inglês, as 3 opções de título, a ideia da miniatura e as tags.
  - Os temporários ficam em `episodio\_temp` e são apagados no fim. Ao gerar de novo, o episódio anterior vai para `episodio\antigos\<data>`.

### Como o episódio é montado
- **Emendas limpas**: cada trecho que fica é recodificado com corte exato, quadro a quadro. O áudio de cada ponta ganha um fade de 15 ms, que tira o estalo. Depois tudo é juntado sem recodificar de novo, e o áudio vira AAC uma vez só, no final. Corte seco (hard cut), sem transição chamativa.
- **Bordas no silêncio**: o começo e o fim de cada corte vão sozinhos para o meio da pausa entre palavras mais próxima (até 2 s), usando o tempo de cada palavra da transcrição.
- **Abertura**: o melhor momento (15 a 30 s) passa antes do episódio, com um fade curto para preto.
- **Capítulos**: o Claude informa os tempos do vídeo original e o Studio converte para o tempo do episódio editado (soma a abertura e os trechos que ficaram). As regras do YouTube são aplicadas sozinhas: o primeiro capítulo é sempre 0:00, cada um tem 10 s ou mais, e o Studio avisa se ficarem menos de 3. Os capítulos também vão gravados dentro do `.mp4`.
- Sai em 16:9, no enquadramento e na resolução originais da gravação (o mesmo fps também).
- **Velocidade**: usa a placa NVIDIA (NVENC) se ela funcionar e, se não, o processador (x264, `veryfast`). O progresso aparece na janela preta, com o tempo que falta.

### Configurações novas (`config.json`)
Entram como padrão. O `config.json` da pasta de trabalho não é reescrito, e a câmera marcada continua igual.
- `episodio_preset`: velocidade do x264 (`veryfast`).
- `episodio_crf`: qualidade (`20`).
- `episodio_ajuste_silencio`: até quantos segundos a borda do corte pode andar até a pausa (`2.0`; `0` desliga).
- `episodio_usar_abertura` (`true`) e `episodio_fade_preto` (`0.35` s).

### Outras mudanças
- `edicao.json` (versão 1): os cortes desmarcados na revisão ficam salvos com `"ativo": false`. Cortes sobrepostos são juntados, tempos fora do vídeo dão erro claro e um JSON com erro de formatação dá uma mensagem amigável (com linha e coluna).
- Módulos novos: `app\editar_episodio.py` (renderização) e `app\pedido_edicao.py` (pedido, validação, silêncio e capítulos). O teste do instalador agora também abre esses dois módulos.
- Os Shorts não mudaram: `gerar_shorts.py` e `transcrever.py` não foram alterados.

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
- Painel com os 4 passos: **Transcrever → Pedir cortes ao Claude → Gerar Shorts → Publicar**.
- Janela **Publicar**: copia título, descrição e tags do YouTube e as legendas do TikTok e do Instagram e marca "Postado" em cada rede.
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

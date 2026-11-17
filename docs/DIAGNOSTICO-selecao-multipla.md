# Diagnóstico: gerar Shorts de vários vídeos de uma vez (Fase 0 da versão 1.6.0)

Este arquivo explica como o Studio está hoje (versão 1.5.1), por que não dá para gerar os Shorts de vários
vídeos de uma vez e o que eu sugiro fazer. Nesta fase eu **só li o código**: não mudei nada no programa.

---

## 1. Versão e biblioteca de interface

- **Versão atual:** `1.5.1` (em `app/versao.py`).
- **Versão nova:** `1.6.0` (recurso novo = sobe o número do meio).
- **Biblioteca de interface:** **tkinter** puro, com os widgets `ttk` (o tema cinza e laranja fica em
  `app/interface/tema.py`). Não é CustomTkinter nem PySide. Arrastar e soltar usa a `tkinterdnd2`.
- A lista de projetos da tela **Shorts** é um `ttk.Treeview` (uma tabela) montado em
  `app/interface/aba_base.py`, usado pela `app/interface/aba_shorts.py`.

---

## 2. Por que hoje não dá para gerar de vários vídeos

Encontrei três coisas:

1. **A lista JÁ aceita selecionar vários.** O `Treeview` foi criado com `selectmode="extended"`, então
   `Ctrl` + clique e `Shift` + clique já marcam várias linhas. Só que isso não aparece (não tem caixinha,
   contador nem botão "Selecionar todos"), e por isso parece que é seleção única.
2. **Mas todos os botões só olham o PRIMEIRO selecionado.** O botão laranja, "Transcrever", "Gerar cortes
   com o Claude" e "Gerar Shorts" usam a função `selecionado()`, que pega só a primeira linha marcada.
   A única coisa que hoje usa os vários selecionados é o **Excluir** (botão direito → "Excluir 3 projetos").
3. **A Fase 5B da v1.5.0 não foi feita.** Procurei no código, no `CHANGELOG.md` e nos documentos e não
   existe nada de "lote" (nem pela metade). Na 1.5.0, a Fase 5 virou "gerar cortes com o Claude num
   clique" e a parte de vários vídeos ficou de fora. O que existe parecido:
   - a **transcrição** aceita vários vídeos de uma vez (arrastando para a janela ou em "+ Adicionar vídeo");
   - o resto (cortes e Shorts) é sempre um vídeo por vez.

Resumo: **não tem botão que não funciona; o recurso simplesmente não existe.** Não há código de lote para
reaproveitar, mas há muita coisa pronta que o lote pode chamar (ver a seção 3).

---

## 3. O caminho de um vídeo hoje, etapa por etapa

| Etapa | Quem faz | Como roda hoje | Dá para chamar sem clicar em nada? |
|---|---|---|---|
| **1. Transcrever** | `app/nucleo/transcrever.py` → `transcrever_video(video)` | Outro processo, numa **janela preta** (console), aberta por `rodar_script("nucleo.transcrever", video)` | **Quase.** A função `pasta_do_projeto()` faz duas perguntas no console com `input()`: "esse projeto foi feito de OUTRO vídeo, continuar?" e "já foi transcrito, transcrever de novo?". Preciso de uma opção "sem perguntas". |
| **2. Marcar câmera** | `app/interface/marcar_camera.py` (janela com o quadro do vídeo) | Janela própria, sempre com cliques | **Não** (é visual de propósito). Precisa ir para o começo do lote. |
| **3. Pedir os cortes ao Claude** | `app/shorts/cortes_com_claude.py` → `gerar_cortes(...)` e `salvar_cortes(...)` | Linha separada dentro do Studio (`JanelaClaude`), usando o **Claude Code do PC** (`claude -p`, em `app/nucleo/claude_local.py`) | **Sim.** `gerar_cortes()` não abre janela nenhuma: recebe a pasta, devolve o `cortes.json` pronto e aceita "cancelar". Já tenta de novo sozinho até 3 vezes se der erro de rede. |
| **4. Gerar os Shorts** | `app/shorts/gerar_shorts.py` → `main()` | Outro processo, numa **janela preta**, com a pasta do projeto | **Quase.** Com a pasta passada, não pergunta nada. Mas o `main()` só lê a linha de comando e mostra o progresso com `print`. Para o lote, rodo ele como processo escondido e leio a saída ("[3/8] ...") para mostrar o progresso. |

Coisas boas que já existem e o lote aproveita:

- **Arquivo nunca fica quebrado:** os JSON são gravados num temporário e depois trocados (`gravar_json`);
  cada Short é renderizado como `_gerando_NN.mp4` e só ganha o nome certo quando termina. Se cancelar
  no meio, basta apagar o `_gerando_...` e o `temp_legenda_...`.
- **"Gerar só os que faltam":** o `gerar_shorts` pula os Shorts que já existem. Isso deixa retomar um
  lote parado no meio sem refazer nada.
- **Cada vídeo já é um projeto separado** (pasta própria em `shorts\`, com `projeto.json`,
  `transcricao.json`, `cortes.json` e `prontos\`). O lote não precisa misturar nada.
- **Mandar para a Lixeira:** `app/nucleo/limpeza.py` já usa o `send2trash` (biblioteca que já vai no
  instalador). Nenhuma biblioteca nova deve ser necessária.

---

## 4. O que abre janela ou pergunta no meio do caminho (vai para o começo do lote)

| Onde | Pergunta | Como fica no lote |
|---|---|---|
| Transcrever | "Já foi transcrito, transcrever de novo?" | O lote **só transcreve quem ainda não tem transcrição**. Não pergunta. |
| Transcrever | "Projeto com esse nome feito de OUTRO vídeo, continuar?" | Raro. Mostro um aviso na janela "Preparar lote" e o vídeo fica de fora até você resolver. |
| Gerar cortes | "Esse vídeo já tem cortes. Pedir de novo?" | O lote **usa os cortes que já existem**; só pede ao Claude quem não tem. |
| Gerar Shorts | "Câmera não marcada, gerar com fundo desfocado?" | Resolvido na "Preparar lote": marcar ali ou usar a mesma área para todos. |
| Gerar Shorts | "Já existem Shorts: refazer todos / só os que faltam / cancelar" | Escolha por vídeo na "Preparar lote": **Pular** ou **Gerar de novo** (os antigos vão para a **Lixeira**). |
| Gerar cortes | Sem Claude Code no PC → copia o pedido para colar | Conferido antes de começar (ver seção 5). |

### Um ponto importante sobre a área da câmera

Hoje a área da câmera **não é por vídeo**: é uma só, guardada no `configuracoes\config.json`
(`camera_area` e `gameplay_area`) e vale para todos os vídeos. O plano pede "vídeo que já tem área salva
usa a salva". Minha proposta:

- guardar a área **também no `projeto.json`** de cada vídeo (quando for marcada pelo lote ou pelo
  "Marcar câmera" com um projeto selecionado);
- ao gerar, o vídeo usa **a área dele**; se não tiver, usa a **área geral** do `config.json` (como hoje).
  Assim nada muda para os projetos antigos;
- na "Preparar lote", vídeo sem área própria aparece como "usa a área geral" (se existir) ou "falta
  marcar". Você pode marcar só para ele ou usar a mesma para todos.

Isso é uma mudança pequena no `gerar_shorts.py` (hoje ele lê a área uma vez só, do `config.json`).

---

## 5. Como o app pede os cortes ao Claude hoje

- **Jeito principal (automático):** o Studio chama o **Claude Code do seu PC** com `claude -p`
  (`app/nucleo/claude_local.py`). Manda o pedido e a transcrição (dividida em partes se a live for longa),
  recebe o JSON, confere se os tempos fazem sentido e salva o `cortes.json`. Usa a sua assinatura do
  Claude, sem chave de API. **Isso funciona no lote sem nenhuma pergunta.**
- **Jeito antigo (copiar e colar):** só é usado quando o Studio **não acha o Claude Code** no PC. Esse não
  dá para automatizar.

No lote:

- antes de começar, a "Preparar lote" confere se o Claude Code existe e está logado;
- se **não existir** e algum vídeo ainda precisar de cortes, mostro o aviso: "O Claude Code não está
  instalado neste PC. Os vídeos que já têm cortes serão feitos; os outros vão só ser transcritos."
  Você pode continuar assim ou cancelar e instalar o Claude Code;
- se o Claude der erro num vídeo (sem internet, limite da assinatura...), aquele vídeo fica com ❌ e o
  lote segue para o próximo, como o plano pede.

---

## 6. Resto de Buffer ou Cloudflare no código

- **No programa (pasta `app\`): não tem nada.** A única palavra "buffer" é `np.frombuffer` em
  `app/nucleo/video.py`, que é uma função de leitura de áudio e não tem nada a ver com o serviço Buffer.
- **Nos textos antigos ainda aparecem**, como histórico:
  - `CHANGELOG.md` (notas das versões 1.3.0 a 1.5.0, que contam quando o Buffer saiu);
  - `docs/DIAGNOSTICO-1.3.0.md`, `docs/DIAGNOSTICO-1.5.0.md` e `docs/TESTES-1.3.0.md`.
- **Minha sugestão:** deixar como está, porque são registros do passado (o `CHANGELOG.md` conta a história
  das versões). Não apago nada sem você aprovar. Se preferir, eu tiro dos três documentos antigos.

---

## 7. Como vou montar o lote (proposta)

- **Um "motor do lote" novo** (`app/shorts/lote.py`), sem janelas, que sabe a lista de vídeos e a etapa de
  cada um e grava tudo em `configuracoes\lote.json` (com número de versão) a cada passo. Ele roda numa
  linha separada, então a janela do Studio não trava.
- **Transcrever e gerar Shorts continuam em processos separados** (como hoje), mas **escondidos** e sem
  perguntas. Isso é bom porque o Whisper usa muita memória: quando o processo termina, a memória volta.
  O lote lê o que eles escrevem para mostrar o progresso.
- **Os cortes** são pedidos direto com a `gerar_cortes()` que já existe.
- **Pausar:** termina a etapa atual e espera. **Cancelar:** pede confirmação, para o processo, apaga os
  arquivos temporários (`_gerando_...`, `temp_legenda_...`) e guarda o estado. Os Shorts que já ficaram
  prontos continuam valendo.
- **Fechou o app ou o PC desligou:** ao abrir, o Studio vê o `lote.json` sem terminar e pergunta
  "Continuar o lote de onde parou?". Como o `gerar_shorts` pula os Shorts prontos, nada é refeito.
- **Uma janela nova "Preparar lote"** e **uma tela do lote** (com a lista, a barra geral, o tempo
  estimado e os botões), na pasta `app/interface/`.
- **Só um lote por vez:** o botão fica desligado enquanto um lote roda, e o `lote.json` diz se já tem um
  em andamento.

---

## 8. Riscos

1. **Transcrição no notebook (sem NVIDIA) é lenta.** Uma live de 2 horas pode levar mais de uma hora só
   para transcrever. O aviso "o lote vai demorar mais" ajuda, e o tempo estimado aparece na tela.
2. **Limite da assinatura do Claude.** Com muitos vídeos seguidos, o Claude Code pode bater no limite de
   uso. O vídeo fica com ❌ e o botão "Tentar de novo só este" resolve depois.
3. **Mudar a área da câmera para "por vídeo"** mexe no `gerar_shorts.py`, que é o coração dos Shorts.
   Vou fazer com cuidado (sem área própria = exatamente igual a hoje) e com testes.
4. **Eu não consigo abrir a janela aqui.** O ambiente onde eu trabalho é Linux e não tem o tkinter nem
   placa de vídeo. Consigo testar todo o motor do lote (com o Claude falso e vídeos de amostra feitos com
   o ffmpeg), mas **a parte visual (1366×768, arrastar para mudar a ordem, notebook sem NVIDIA) você vai
   precisar conferir no seu PC**. Vou deixar um roteiro curto de teste manual.
   - Hoje os testes rodam assim aqui: **124 passam**; 1 falha só porque falta o `send2trash` neste
     ambiente e o `test_telas.py` não abre por falta do tkinter. No seu PC eles funcionam.
5. **"Gerar de novo" vai para a Lixeira.** Hoje o "refazer todos" manda os Shorts antigos para a pasta
   `antigos` dentro do projeto. No lote vou usar a **Lixeira** como o plano pede. Pergunta: quer que o
   botão normal (um vídeo só) também passe a usar a Lixeira, para ficar igual?

---

## 9. Ordem sugerida

1. **Fase 1 – Selecionar vários:** caixinha (coluna ☐/☑ na tabela), contador, "Selecionar todos",
   "Limpar seleção", coluna de estado (não transcrito · transcrito · com cortes · com Shorts) e o botão
   laranja "Gerar Shorts dos selecionados (N)".
2. **Fase 3 antes da 2, por dentro:** primeiro o **motor do lote** e o `lote.json` (é a parte mais
   arriscada e a que dá para testar bem), depois a tela do lote.
3. **Fase 2 – Preparar lote:** área da câmera por vídeo, Pular/Gerar de novo, ordem, aviso de GPU.
4. **Fase 4 – Resumo e notificação.**
5. **Fase 5 – Testes** (unitários com Claude falso + ponta a ponta com 3 vídeos de 20 s).
6. **Fase 6 – Fechamento** (versão, CHANGELOG, COMO USAR, instalador).

Os commits continuam um por fase, na ordem do plano.

---

## 10. O que preciso que você decida

1. **Área da câmera por vídeo** (seção 4): pode guardar no `projeto.json` de cada vídeo, usando a área
   geral quando o vídeo não tiver a dele?
2. **Sem Claude Code no PC** (seção 5): está bom "faz o que der e avisa no começo"?
3. **Buffer nos documentos antigos** (seção 6): deixo como histórico ou tiro?
4. **Lixeira também no botão de um vídeo só** (risco 5): sim ou não?
5. **Nome da branch:** o ambiente onde eu trabalho só me deixa enviar para a branch
   `claude/blissful-ptolemy-gnl0n3`. Posso fazer todo o trabalho nela (é ela que vai aparecer no GitHub
   Desktop) e no fim te passo o passo a passo para juntar na `main`? Se você quiser muito o nome `v1.6.0`,
   dá para renomear no GitHub Desktop depois.

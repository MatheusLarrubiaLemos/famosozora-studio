# Diagnóstico do FamosoZora Studio (Fase 0 da versão 1.5.0)

Feito em 16/11/2026, a partir da **1.4.0** (`app/versao.py` = `"1.4.0"`, confere com o plano).
Nesta fase **nada do código foi alterado**: só li o código e escrevi este relatório.

> **Sobre a branch:** o plano pede a branch `v1.5.0`. Neste ambiente do Claude Code na nuvem eu só posso
> enviar para a branch `claude/famosozora-studio-v1-5-0-33yvt0`. Vou trabalhar nela (é a "v1.5.0" na prática).
> No fim, você junta na `main` pelo GitHub Desktop (ou eu abro um pull request, se você pedir).

---

## 1. Biblioteca de interface

**Hoje:** `tkinter` + `ttk` (tema `clam`), que já vem com o Python. Nada de CustomTkinter nem PySide.

| Onde | O quê |
|---|---|
| `app/interface/janela_principal.py` | Janela principal: topo com "Menu" e duas abas (`ttk.Notebook`): Shorts e Vídeos longos/Lives. Tamanho fixo 1120×720. |
| `app/interface/aba_base.py` | Lista de projetos (`ttk.Treeview`) + coluna de botões à direita ("PASSO A PASSO 1…5"). |
| `app/interface/utilidades.py` | As 3 cores: fundo `#14141f`, texto `#ffffff`, destaque amarelo `#ffd400`. |
| Espalhado em 12 arquivos | **105 lugares** com cor escrita direto no código (`#232336`, `#14141f`, `#c8c8d8`...). |

### Dá para fazer o visual novo (Fase 3) com tkinter?

**Sim.** Recomendo **ficar com tkinter/ttk** e criar o `app/interface/tema.py`.

| Opção | Prós | Contras | Tamanho do trabalho |
|---|---|---|---|
| **Ficar no tkinter/ttk** (recomendado) | Já funciona; os testes de tela (`testes/test_telas.py`) continuam valendo; instalador não cresce; o `Treeview` (lista da legenda, lista de projetos) já tem duplo clique e botão direito. | Cantos arredondados e sombras só "imitando"; dá trabalho deixar bonito, mas dá. | **Médio**: `tema.py` + trocar as 105 cores + barra lateral + cartões. |
| CustomTkinter | Botões e campos arredondados prontos, modo escuro fácil. | **Não tem lista/tabela** (`Treeview`): teria que misturar com ttk mesmo assim; mais uma biblioteca; o visual misturado fica estranho. | Médio-grande. |
| PySide6 (Qt) | O visual mais bonito e moderno; arrastar e soltar, notificações e tela cheia muito fáceis. | **Reescrever toda a interface** (~3.000 linhas em 14 arquivos) e todos os testes de tela; instalador cresce ~100 MB; mais risco de quebrar coisas que hoje funcionam. | **Grande** (sozinho seria uma versão inteira). |

Itens da Fase 3 que precisam de algo a mais no tkinter:
- **Arrastar e soltar** vídeo na janela: o tkinter não faz sozinho. Uso a biblioteca `tkinterdnd2` (pequena, funciona no Windows). Se ela falhar ao carregar, o app abre normal, só sem arrastar.
- **Tela cheia:** `state("zoomed")` ao abrir e `F11` com `attributes("-fullscreen")`. Funciona no tkinter.
- **Notificações no canto:** uma janelinha sem borda que some sozinha depois de alguns segundos. Dá para fazer.
- **Miniatura nos cartões:** gerar um `.png` com o ffmpeg (que o app já usa) e mostrar com `tk.PhotoImage`. Sem biblioteca nova.

## 2. Como o app pede os cortes ao Claude hoje

**Copiar e colar.** Não existe chave da API nem chamada automática.

| Botão | O que acontece |
|---|---|
| Shorts → **"2 Pedir cortes ao Claude"** (`aba_shorts.py`, texto em `shorts/pedido_cortes.py`) | Copia um pedido pronto para a área de transferência. Você cola na conversa com o Claude. O pedido manda o Claude **ler a transcrição na pasta e salvar o `cortes.json` lá**, ou seja, você usa um Claude que tem acesso aos arquivos do PC. |
| Vídeos longos → **"3 Editar vídeo longo"** (`janela_principal.py` → `pedir_edicao`, texto em `videos_longos/pedido_edicao.py`) | Igual: copia o pedido; o Claude lê `transcricao_para_claude.txt` e salva o `edicao.json`. |
| **"Colar edicao.json"** | Plano B: você copia o JSON da resposta e o app lê da área de transferência, valida e salva. |

O que dá para **reaproveitar** na Fase 5: os textos dos pedidos, a validação (`extrair_json`, `normalizar`, `erro_json_amigavel`) e a leitura do `cortes.json` (`shorts/cortes.py`). Falta só a parte que "manda e recebe sozinho".

## 3. Buffer e a aba de vídeos longos hoje

### Buffer
**Não usa a API.** A janela "5 Publicar (Buffer)" (`interface/janela_publicar.py`):
- botão **"Abrir o Buffer"** (abre `publish.buffer.com` no navegador);
- para cada Short: título/descrição de **YouTube, TikTok e Instagram** com botões de copiar, "Mostrar na pasta", "Assistir";
- você marca à mão o que já postou (fica no `prontos\publicacao.json`).

⚠ **Achado:** um Short só conta como "postado" quando está marcado nas **três** redes (`nucleo/projetos.py`). Como agora você publica **só no YouTube**, os Shorts nunca apareceriam como "todos postados". Na Fase 1 isso passa a olhar só as redes ligadas (por enquanto, só YouTube).

### Aba "Vídeos longos / Lives"
1. **Juntar vídeos** (partes da live, script PowerShell);
2. **Transcrever a live**;
3. **Editar vídeo longo**: pede ao Claude o `edicao.json` (o que **sai**, capítulos, título, descrição, tags, **abertura**), abre a revisão (`interface/janela_edicao.py`: lista de cortes, "Ouvir emenda", "Gerar prévia (10 min)", "Gerar episódio") e renderiza com `videos_longos/editar_episodio.py` (corte exato, fade curto no áudio de cada emenda).
4. Já gera o arquivo de textos do episódio com título, descrição e capítulos no formato do YouTube.

⚠ **Achado importante para a Fase 6:**
- O vídeo longo **hoje tem gancho**: o campo `"abertura"` (cold open de 15 a 30 s, com fade para preto) entra **antes** do episódio. A Fase 6 tira isso.
- **Já existe** o arquivo com o que sai: `edicao.json` com `"cortes"` (= o "remover" do plano), `"capitulos"`, `"titulo"`, `"descricao"`, `"tags"`. O plano pede um arquivo **novo**, `edicao_longo.json`, com `"remover"`. **Proposta:** em vez de criar um segundo arquivo, **subir o `edicao.json` para a versão 2** (sem `abertura`, `cortes` renomeado para `remover`, com migração automática + backup `.bak.json`, como pede a regra 3). Assim os projetos que já existem continuam funcionando e não ficam dois arquivos parecidos. *(Preciso que você aprove; ver pergunta 3.)*
- **Outro no final:** não existe nada hoje. Tudo novo.

## 4. Botões do editor de Shorts que viram menu (Fase 2)

Tudo na janela "Revisar legendas" (`interface/editor_legendas.py`):

| Onde | Botões hoje | Vira |
|---|---|---|
| Aba **Legenda**, linha 1 (`editor_legendas.py`, ~linha 160) | Aplicar linha (Enter) · Ouvir trecho · Censurar palavra · Tirar censura · Adicionar sempre à lista | Duplo clique (editar) + botão direito na linha |
| Aba **Legenda**, "Quem fala nesta linha" (caixa de escolha) | — | Botão direito → "Trocar quem fala ›" |
| Aba **Legenda**, duplo clique na linha | Hoje **toca o trecho** | Passa a **editar** (o ▶ Ouvir vai para o menu e para a tecla `Espaço`) |
| Embaixo (`_montar_botoes_de_baixo`) | Salvar · Desfazer · Voltar ao original · Assistir o Short · Renderizar de novo só este Short | Ficam **Salvar, Renderizar, Publicar**; o resto vai para o menu / atalhos (`Ctrl+Z`) |
| Aba **Áudio e edição** (`interface/painel_audio.py`, linhas ~64–116) | Música: ligar, ouvir, trocar, sortear, excluir, "Tirar a troca", "Restaurar sugestão do Claude". Efeitos: ouvir, ouvir trecho, mudar tempo, trocar, volume, excluir, adicionar | Botão direito na música / no efeito: Ouvir · Trocar · Volume · Excluir |
| Lista de Shorts à esquerda | — | Botão direito: Abrir · Renderizar de novo · Publicar · Abrir pasta · Excluir |
| Aba **Falantes** (`interface/painel_falantes.py`) | ▶ ouvir + escolha da pessoa por voz | Fica como está (já é simples) |

Nada disso precisa de biblioteca nova: o `Treeview` do tkinter já aceita duplo clique e botão direito.

## 5. O que deste plano a 1.4.0 já tem (regra 6: reaproveitar)

| Item do plano | Situação na 1.4.0 | O que falta |
|---|---|---|
| Mandar para a Lixeira | ✅ `nucleo/limpeza.py` usa a Lixeira do Windows direto (sem biblioteca) | Usar `send2trash` como pede o plano (funciona igual e dá para testar fora do Windows); a função atual fica de reserva. |
| Limpar projeto | ✅ "Limpar projeto (depois de postar)": SIM = só a mídia, NÃO = projeto inteiro | As 3 opções da Fase 4, tamanho, seleção múltipla, aviso da fila. |
| Desfazer no editor | ✅ vale para tudo do Short | Só o atalho `Ctrl+Z`. |
| Ouvir trecho | ✅ | Ir para o menu / `Espaço`. |
| Capítulos, título, descrição, tags do vídeo longo | ✅ no `edicao.json` | Levar para a publicação. |
| Textos de cada Short (título, descrição) | ✅ `publicacao.json` | Levar para a publicação. |
| Validação de JSON do Claude | ✅ | Pedir de novo 1 vez se vier quebrado. |
| Fade nas emendas do vídeo longo | ✅ (15 ms no áudio) | Fade um pouco maior (estilo TV) e xfade do outro. |
| `keyring`, Google API, cliente R2, `tkinterdnd2`, `send2trash` | ❌ | Entram no `requirements.txt` e no instalador. |
| `.gitignore` com segredos | ⚠ tem `ajustes.json`, `.env`, `*token*` | Acrescentar `*.credenciais*`, `client_secret*.json`, `fila_publicacao.json`. |

## 6. Riscos

1. **Auditoria do YouTube:** projeto novo do Google sobe vídeo **travado como privado** até passar na auditoria (pode levar semanas). Por isso o "pacote + Claude no navegador" é o caminho padrão dos vídeos longos no começo. ✅ já previsto no plano.
2. **API do Buffer:** a API nova (GraphQL) é recente e os detalhes (nomes dos campos, limites do plano grátis) podem mudar. Vou conferir a documentação atual na Fase 1 e deixar tudo testado com respostas falsas. O teste de verdade é o manual guiado com você.
3. **Cloudflare R2:** o link público do balde fica aberto enquanto o Short não sai. O nome do arquivo vai ter um código aleatório e o app apaga depois de publicado. O risco é baixo, mas existe.
4. **Não consigo abrir janelas aqui:** a máquina onde eu trabalho é Linux, **sem tkinter e sem pytest instalados**. Vou tentar instalar para rodar os testes; se não der, os testes de tela (e a conferência em 1366×768 e no notebook) ficam para você rodar no Windows, com um roteiro meu.
5. **Fase 3 mexe em quase todos os arquivos de tela**: é onde mais pode quebrar. Por isso sugiro fazer **antes** da Fase 2 (ver ordem abaixo) e rodar os testes de tela a cada passo.
6. **Tirar o gancho do vídeo longo** muda o formato do `edicao.json`: precisa de migração com backup (regra 3).
7. **Custo da API da Anthropic** (se escolher o caminho 1 na Fase 5): live longa = transcrição grande = pedido mais caro. Vou mostrar o custo aproximado antes de mandar, como pede o plano.
8. **Tamanho do instalador:** as bibliotecas do Google somam alguns MB; nada grave.

## 7. Ordem que eu sugiro

| # | Fase | Por quê |
|---|---|---|
| 1 | **Fase 3 – Interface nova** (tema, barra lateral, tela cheia) | Todas as outras fases criam telas novas. Se o tema e a barra lateral vierem antes, as telas novas já nascem no visual novo e eu não faço o trabalho duas vezes. |
| 2 | **Fase 2 – Duplo clique e botão direito** | Usa o tema novo; é a base do "botão direito → Publicar / Excluir". |
| 3 | **Fase 4 – Excluir** | Pequena; usa os menus da Fase 2. |
| 4 | **Fase 1 – Publicação** | A maior. Depende das suas contas (Buffer, Cloudflare, Google). Enquanto você cria as contas, eu adianto as outras fases. |
| 5 | **Fase 5 – Claude com um clique** | Depende da sua resposta sobre a chave da API. |
| 6 | **Fase 6 – Vídeos longos** (sem gancho, outro, publicar) | Usa as Fases 1 e 5. |
| 7 | **Fases 7 e 8 – Testes e fechamento** | |

Se você preferir **seguir a ordem do plano** (1 → 8), também funciona: só vou mexer de novo nas telas da Fase 1 quando chegar a Fase 3.

---

## 8. Perguntas para você (antes de eu seguir)

1. **Fase 5:** você tem **chave da API da Anthropic** (paga por uso, separada da assinatura) ou prefere usar o **Claude Code instalado no PC** (`claude -p`, usa a sua assinatura)?
   *Minha sugestão:* Claude Code, se ele já estiver instalado aí, porque não tem custo extra e ele consegue ler a transcrição sozinho na pasta. Posso deixar os dois, com a escolha nas Configurações.
2. **Fase 1:** você já criou a **conta na Cloudflare** (com o balde R2) e o **projeto no Google Cloud**? Se não, eu faço o código com testes falsos e o `docs/PUBLICAR.md` ensina a criar.
3. **Fase 6:** posso **reaproveitar o `edicao.json`** (versão 2, com migração) em vez de criar o `edicao_longo.json` novo?
4. **Interface:** aprova **ficar no tkinter** (com `tkinterdnd2` para arrastar e soltar), em vez de migrar para PySide6?
5. **Ordem:** aprova a ordem 3 → 2 → 4 → 1 → 5 → 6 → 7 → 8, ou prefere 1 → 8 como no plano?

**Parei aqui e estou esperando a sua aprovação.**

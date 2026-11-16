# Novidades do FamosoZora Studio (patch notes)

Os números de versão seguem o padrão **MAIOR.MENOR.CORREÇÃO**:

- **MAIOR**: muda o jeito de usar (ex.: virou app instalável).
- **MENOR**: recurso novo.
- **CORREÇÃO**: conserto de erro ou um ajuste pequeno.

Toda versão nova aparece aqui com todas as mudanças. O GitHub também gera o instalador sozinho, em *Releases*.

## [1.5.0] - em andamento

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

### Publicação no YouTube pelo Claude no seu computador (sem Buffer)
- **Saiu o Buffer.** A janela antiga de copiar textos para o Buffer, TikTok e Instagram deu lugar à publicação pelo **Claude no seu PC**, que agenda pelo **YouTube Studio no seu Chrome**.
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

### Documentação
- Novo `docs/DIAGNOSTICO-1.5.0.md`: como o app está hoje (interface, pedidos ao Claude, Buffer, vídeos longos, botões do editor), riscos e a ordem sugerida para a versão 1.5.0.

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
  - **Shorts:** 1 Transcrever → 2 Pedir cortes ao Claude → 3 Gerar Shorts → 4 Revisar legendas → 5 Publicar (Buffer), mais "Marcar câmera e gameplay".
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

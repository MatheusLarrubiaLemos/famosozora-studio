# Novidades do FamosoZora Studio (patch notes)

Os números de versão seguem o padrão **MAIOR.MENOR.CORREÇÃO**:

- **MAIOR**: muda o jeito de usar (ex.: virou app instalável).
- **MENOR**: recurso novo.
- **CORREÇÃO**: conserto de erro ou um ajuste pequeno.

Toda versão nova aparece aqui com todas as mudanças. O GitHub também gera o instalador sozinho, em *Releases*.

## [1.3.0] - em andamento

Versão de arrumação: o código foi reorganizado para ficar fácil de achar as coisas, e vários erros escondidos foram consertados. As próximas fases (abas, editor de legendas, aviso de atualização) entram nesta mesma versão.

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

### Limpar projeto
- Botão novo **"Limpar projeto (depois de postar)"**, nas duas abas.
- Manda para a **Lixeira do Windows** o que pesa: os Shorts, o episódio, as versões antigas e os temporários. Dá para restaurar pela Lixeira.
- **Guarda o resumo** (poucos KB): cortes, edição, transcrição, legendas revisadas, textos para postar e o que já foi marcado como postado. O projeto continua na lista como "Projeto limpo".
- Avisa antes se algum Short ainda não está marcado como postado ou se existe um episódio gerado.
- Também dá para mandar o projeto inteiro para a Lixeira, inclusive o resumo.
- O vídeo original nunca é tocado.

### Código reorganizado (Fase 1)
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

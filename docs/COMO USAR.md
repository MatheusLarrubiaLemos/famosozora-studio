# FamosoZora Studio — Como usar

Tudo para transformar a live em Shorts estilo **trailer**, postar no **YouTube, TikTok e Instagram** e editar o **vídeo longo** como um episódio de programa de TV, num painel só.

```
Vídeo longo ──► 1. Transcrever ──► 2. Claude escolhe os cortes ──► 3. Gerar Shorts ──► 4. Publicar (Buffer)
                      │
                      └──────────► 5. Editar vídeo longo (Claude escolhe o que sai ──► você revisa ──► episódio)
```

Os vídeos originais **nunca são alterados**: as ferramentas só leem os vídeos e criam arquivos novos.

---

## 1. Primeira vez (instalação)

1. No GitHub, abra **Releases** e baixe o `FamosoZora-Studio-Setup-X.Y.Z.exe` mais novo.
2. Abra o arquivo. Se o Windows avisar que protegeu o computador, clique em **Mais informações → Executar assim mesmo**.
3. Abra o **FamosoZora Studio** pelo atalho da Área de Trabalho.
4. Na primeira vez, ele pergunta qual vai ser a **pasta de trabalho** (onde ficam os vídeos e os Shorts):
   - **SIM** = `Documentos\FamosoZora`;
   - **NÃO** = escolher outra pasta, por exemplo `F:\CLAUDE\canal famosozora`.
5. Se o PC tiver placa NVIDIA, ele oferece ativar a aceleração. Vale a pena: a transcrição fica muito mais rápida.

---

## 2. O dia a dia: os passos

Abra o **FamosoZora Studio**. A lista mostra cada vídeo e em que passo ele está. A faixa embaixo da lista mostra o **próximo passo** do vídeo selecionado.

### Passo 1 — Transcrever vídeo novo
- Clique em **1 Transcrever vídeo novo** e escolha o vídeo, que normalmente fica na pasta `videos`.
- Uma janela preta mostra o progresso. Com placa de vídeo, 3h de vídeo levam uns 10 a 20 minutos.
- Isso gera, na pasta do vídeo dentro de `shorts`:
  - `legenda_video_completo.srt`: legenda do vídeo longo. Dá pra importar no CapCut.
  - `transcricao_para_claude.txt`: o texto que o Claude lê pra escolher os cortes.

> Se o vídeo estiver em partes, junte antes com **Juntar vídeos (partes)**.

### Passo 2 — Pedir cortes ao Claude
- Selecione o vídeo e clique em **2 Pedir cortes ao Claude**. O pedido já sai copiado.
- Cole (**Ctrl+V**) na conversa com o Claude e envie.
- O Claude lê a transcrição, escolhe os melhores momentos e salva o `cortes.json` na pasta do vídeo. Cada corte vem com:
  - **Abertura:** o momento mais forte do corte, mostrado logo no começo, como num trailer.
  - **Gancho:** uma frase grande na tela nos primeiros segundos.
  - **Legenda corrigida:** nomes, gírias e palavras que o Whisper errou.
  - **Textos de cada rede:** título, descrição e tags do YouTube, e as legendas do TikTok e do Instagram.

### Passo 3 — Gerar Shorts
- Clique em **3 Gerar Shorts**.
- Se o vídeo já tiver Shorts, ele pergunta:
  - **SIM:** refaz todos. Os atuais vão pra pasta `prontos\antigos`, nada é apagado.
  - **NÃO:** gera só os que faltam.
- Os Shorts ficam em `shorts\<nome do vídeo>\prontos`.

### Passo 4 — Publicar (Buffer)
- Clique em **4 Publicar (Buffer)**. Abre uma janela com a lista de Shorts e, pra cada um:
  - **Mostrar na pasta:** abre o Explorer com o vídeo selecionado, pra arrastar pro Buffer.
  - **Copiar título / descrição / tags:** textos do YouTube.
  - **Copiar legenda:** texto do TikTok e do Instagram.
  - **Postado:** marque quando postar em cada rede. O Studio guarda isso.
- No Buffer:
  1. Clique em **Abrir o Buffer** (publish.buffer.com) → **Criar post**.
  2. Marque **YouTube, TikTok e Instagram**.
  3. Arraste o vídeo.
  4. Personalize o texto de cada rede, colando os textos copiados no Studio.
  5. **Publicar agora** ou **Agendar**.

### Passo 5 — Editar vídeo longo
Transforma a live bruta (umas 3 horas) num episódio editado, sem as partes paradas. O vídeo precisa estar transcrito (passo 1).

1. **Pedir a edição ao Claude.** Selecione o vídeo e clique em **5 Editar vídeo longo**. Na primeira vez, o pedido de edição já sai copiado.
   - Cole (**Ctrl+V**) na conversa com o Claude e envie.
   - O Claude lê a transcrição direto da pasta do vídeo e salva o `edicao.json` lá.
   - **Se a conversa não tiver acesso ao PC:** o Claude manda o JSON na conversa. Copie tudo e clique em **Colar edicao.json** no Studio. Ele confere e salva.
2. **Revisar.** Clique em **5 Editar vídeo longo** de novo. Abre a janela de revisão:
   - no topo, a duração original → a duração do episódio;
   - a lista do que vai **SAIR**, com início, fim, duração e o motivo que o Claude deu;
   - **caixinha** em cada corte: clique nela (ou aperte Espaço) para desmarcar. O trecho desmarcado **fica** no episódio;
   - ⚠ nos cortes com menos de 30 s;
   - **Ouvir emenda:** selecione um corte e clique. Em poucos segundos abre um clipe de 10 s (5 s antes + 5 s depois do corte, já emendados). Use para conferir se a emenda ficou boa. Duplo clique no corte faz o mesmo;
   - **Gerar prévia (10 min):** gera só os primeiros 10 minutos do episódio e mostra quanto tempo o episódio inteiro vai levar.
   > O Claude só vê a transcrição, não a tela. Por isso a revisão é obrigatória: ouça as emendas dos cortes duvidosos antes de gerar.
3. **Gerar.** Clique em **Gerar episódio**. Uma janela preta mostra o progresso e o tempo que falta.
   - Sem placa NVIDIA, um episódio de 1h30 leva uns 35 a 40 minutos (depende do PC).
   - Se o vídeo já tiver episódio, o anterior vai para `episodio\antigos\<data>`. Nada é apagado.
4. **Postar.** Tudo fica em `shorts\<nome do vídeo>\episodio`:
   - o `.mp4` do episódio;
   - `textos_episodio.txt`: título, descrição **já com os capítulos**, a versão em inglês, as 3 opções de título, a ideia da miniatura e as tags.
   - No YouTube Studio, cole a descrição com os capítulos. A versão em inglês vai em **Idiomas → Adicionar idioma**.

**Como o episódio é montado:**

| Parte | O que acontece |
|---|---|
| **Abertura** | O melhor momento (15 a 30 s) passa antes de tudo, com um fade curto para preto. |
| **Episódio** | A live sem as partes que saíram. Corte seco, sem transição chamativa. |
| **Emendas** | Cada borda de corte vai sozinha para a pausa entre palavras mais próxima (até 2 s). O áudio ganha um fade de 15 ms, que tira o estalo. |
| **Capítulos** | O Studio converte os tempos para o episódio editado e segue as regras do YouTube: o primeiro é 0:00, cada um tem 10 s ou mais e são no mínimo 3. Também vão gravados dentro do `.mp4`. |
| **Formato** | 16:9, na mesma resolução e fps da gravação. |

> **Quero mudar um corte:** fale pro Claude (*"o corte das 01:06:37 começa 5 s depois"*), ou desmarque na revisão. Depois gere de novo.

> **Link do vídeo completo:** depois de publicar o vídeo longo, use **Link do vídeo completo...** no Studio. As descrições passam a apontar pra ele. Enquanto não tiver link, elas usam o link do canal.
> No YouTube Studio, também dá pra ligar cada Short ao vídeo completo pelo campo **Vídeo relacionado**.

---

## 3. Configurar o Buffer (uma vez só)

1. Crie uma conta grátis em **buffer.com**. O plano grátis conecta **3 canais** e guarda até **10 posts agendados por canal**.
2. Conecte os 3 canais:
   - **YouTube:** o canal FamosoZora.
   - **TikTok:** precisa ser **conta Business**. No app do TikTok: *Configurações e privacidade → Conta → Mudar para Conta Comercial*.
   - **Instagram:** precisa ser **conta profissional**, de Criador de conteúdo ou Comercial. No app: *Configurações → Tipo de conta e ferramentas → Mudar para conta profissional*.
3. Pronto. Agora o passo 4 funciona.

> O TikTok aceita vídeos de 3 segundos a 10 minutos, até 1 GB. Os Shorts gerados ficam bem abaixo disso.

---

## 4. Como cada Short é montado

| Parte | O que acontece |
|---|---|
| **Abertura** | Começa com a frase mais forte do corte (1 a 5 s), que se mistura suavemente no corte (*fade* de 0,45 s). |
| **Corte** | O trecho escolhido, com legenda palavra por palavra. A palavra falada fica cheia e um pouco maior, e **cada pessoa tem uma cor**: quem fala mais é branco. |
| **Final** | 3,5 s com o vídeo **borrando** aos poucos e o texto **VÍDEO COMPLETO NO CANAL / INSCREVA-SE / youtube.com/famosozora**. |
| **Música** | Trilha *idle* de fundo, baixinha. Ela **abaixa sozinha quando alguém fala** e sobe no final. |

**Formato:** câmera em cima (1080x600) e jogo embaixo (1080x1320). Pra marcar onde fica sua câmera, use **Marcar câmera e gameplay** no Studio. Se mudar a câmera de lugar no OBS, é só marcar de novo.

---

## 5. Legendas mais precisas

Três coisas trabalham juntas:

1. **Vocabulário** (`configuracoes\vocabulario.txt`, ou *Mais opções → Vocabulário*): nomes e termos do canal (Matheus, João, Pedro, Bully, FamosoZora...), um por linha. O Whisper passa a escrever esses nomes certo. **Adicione nomes novos sempre que aparecerem**: jogos, amigos, apelidos.
2. **Retranscrição dos cortes:** com placa de vídeo, cada corte é transcrito de novo com o modelo mais preciso (`large-v3`) antes de gerar. Na primeira vez ele baixa o modelo, uns 3 GB.
3. **Legenda corrigida pelo Claude:** o Claude escreve o texto certo de cada corte, e o gerador encaixa esse texto no tempo de cada palavra.
   - Partes entre `[[ ]]` são as que o Claude não teve certeza. Nelas, vale o que o áudio diz.

Correções que se repetem em todo vídeo vão em `configuracoes\correcoes.txt` (*Mais opções → Correções automáticas*), no formato `palavra errada = palavra certa`.

---

## 6. Músicas de fundo

- As músicas ficam em `shorts\musicas`. Já vêm duas trilhas *idle* (`idle_zora_01` e `idle_zora_02`) feitas do zero pelo Claude, **livres de direitos**.
- Pode colocar as suas (`.mp3`, `.m4a`, `.wav`). Use só música que você pode usar, como a **Biblioteca de áudio do YouTube Studio**.
- Por padrão, cada Short usa uma música diferente da pasta.
- Pra desligar a música, troque `"musica"` para `"nenhuma"` no `config.json`.

---

## 7. Ajustes (`config.json`)

Abra em **Mais opções → Configurações** no Studio (Bloco de Notas). Salve e gere de novo. Os ajustes de legenda, cor por pessoa e transição estão na seção 11.

| Ajuste | O que faz | Padrão |
|---|---|---|
| `layout` | `camera`, `desfocado` (vídeo inteiro com fundo borrado) ou `recorte` | `camera` |
| `palavras_por_legenda` | Quantas palavras aparecem por vez | `3` |
| `tamanho_legenda` / `posicao_legenda` | Tamanho da letra / distância até o pé da tela | `96` / `520` |
| `usar_abertura` | Liga ou desliga a abertura estilo trailer | `true` |
| `mostrar_texto_gancho` / `duracao_gancho` | Texto branco do gancho no começo (desligado) / quanto tempo fica na tela | `false` / `3.5` |
| `duracao_final` | Segundos do final com INSCREVA-SE (`0` desliga) | `3.5` |
| `final_linha_1/2/3` | Textos do final | `VÍDEO COMPLETO NO CANAL` / `INSCREVA-SE` / `youtube.com/famosozora` |
| `musica` | `aleatoria`, o nome de um arquivo da pasta `musicas` ou `nenhuma` | `aleatoria` |
| `volume_musica` / `volume_musica_final` | Volume da música durante o corte / no final | `0.18` / `0.55` |
| `retranscrever_cortes` | `auto` (só com placa de vídeo), `true` ou `false` | `auto` |
| `qualidade_crf` | Menor = mais qualidade e arquivo maior (18 a 23) | `20` |
| `codificar_na_gpu` | `auto` usa a placa NVIDIA (NVENC) pra montar o vídeo, que fica mais rápido e libera o processador; `false` usa só o processador | `auto` |
| `episodio_preset` | Velocidade do episódio sem NVIDIA: `superfast` (mais rápido, arquivo maior), `veryfast` ou `faster` (mais lento, arquivo menor) | `veryfast` |
| `episodio_crf` | Qualidade do episódio (menor = mais qualidade e arquivo maior) | `20` |
| `episodio_ajuste_silencio` | Até quantos segundos a borda do corte anda até a pausa mais próxima (`0` desliga) | `2.0` |
| `episodio_usar_abertura` / `episodio_fade_preto` | Liga a abertura do episódio / duração do fade para preto (s) | `true` / `0.35` |

---

## 8. Onde fica cada coisa

O programa e os seus arquivos ficam **separados**.

**Pasta de trabalho** (a que você escolheu, ex.: `F:\CLAUDE\canal famosozora`):

```
canal famosozora\
├─ videos\                     ← coloque aqui os vídeos longos
├─ configuracoes\              ← config.json, vocabulario.txt, correcoes.txt
└─ shorts\
   ├─ musicas\                 ← trilhas de fundo
   └─ <nome do vídeo>\
      ├─ transcricao_para_claude.txt, legenda_video_completo.srt
      ├─ cortes.json           ← escrito pelo Claude (Shorts)
      ├─ edicao.json           ← escrito pelo Claude (vídeo longo)
      ├─ prontos\              ← Shorts + textos_para_postar.txt
      └─ episodio\             ← episódio editado + textos_episodio.txt
```

**Programa** (instalado pelo `.exe`): fica em `%LOCALAPPDATA%\Programs\FamosoZora Studio`. Não precisa mexer lá.

**Código no GitHub** (só para quem desenvolve; no PC fica em `F:\CLAUDE\famosozora-studio`):

```
famosozora-studio\
├─ app\                        ← código do Studio (painel, transcrever, gerar_shorts...)
│  └─ padrao\                  ← configurações iniciais
├─ musicas\                    ← músicas que vêm com o app
├─ docs\                       ← este guia e as diretrizes do canal
├─ build\                      ← monta o instalador (usado pelo GitHub)
├─ CHANGELOG.md                ← novidades de cada versão
└─ Studio (modo desenvolvedor).bat
```

---

## 9. Problemas comuns

| Problema | Solução |
|---|---|
| Erro numa janela preta | Tire um print e mande pro Claude. |
| Quero saber se a placa de vídeo está sendo usada | Na janela preta aparece **"Usando a PLACA DE VIDEO"** (legenda) e **"Codificando na: PLACA DE VIDEO (NVENC)"** (vídeo). No Gerenciador de Tarefas → Desempenho → GPU, troque um dos gráficos de "3D" para **"Cuda"** e veja a **memória dedicada** subir. |
| Falta alguma coisa / deu erro estranho depois de atualizar | Instale de novo o `.exe` mais novo por cima (seus vídeos e Shorts não são apagados). |
| A parte de cima não mostra seu rosto | **Marcar câmera e gameplay** de novo, num vídeo em que o rosto apareça. |
| Uma palavra sempre sai errada | Coloque em `correcoes.txt` ou o nome em `vocabulario.txt`. |
| A emenda do episódio cortou uma fala | Desmarque o corte na revisão, ou peça pro Claude mudar o tempo dele. Use **Ouvir emenda** pra conferir. |
| O episódio está demorando muito | Use **Gerar prévia** pra ver a estimativa. Pra ficar mais rápido, troque `episodio_preset` para `superfast` no `config.json`. |
| Quero mudar o começo ou o fim de um corte | Fale pro Claude, por exemplo: *"começa o corte 3 dois segundos antes"*. Depois gere de novo com **SIM**. |
| O Buffer não deixa conectar o TikTok ou o Instagram | Mude a conta para Business ou profissional (seção 3). |

---

## 10. Usar em outro computador (app)

Desde a versão 1.0.0 o Studio é um **app instalável**:

- **Instalar:** no GitHub, em *Releases*, baixe o `FamosoZora-Studio-Setup-X.Y.Z.exe` e abra.
  - Se o Windows avisar que protegeu o computador: **Mais informações → Executar assim mesmo**.
- **Pasta de trabalho:** você escolhe na primeira vez. Para trocar: *Mais opções → Mudar pasta de trabalho*.
- **Placa NVIDIA:** o app pergunta na primeira vez. Também dá para fazer depois em *Mais opções → Ativar placa de vídeo NVIDIA*.
- **Novidades:** o botão **"Novidades da versão"** mostra tudo o que mudou.
- **Atualizar:** use o botão **"Procurar atualização"** e instale a versão nova por cima.
- **Vídeos e Shorts não vão pro GitHub.** Para gerar Shorts de um vídeo no outro computador, copie o vídeo para a pasta `videos` dele.

## 11. Ajustes do visual (config.json)

| Ajuste | O que faz |
|---|---|
| `tamanho_legenda` / `borda_legenda` | Tamanho da letra (96) e grossura da borda (4). |
| `cor_por_falante` | `true` = cada pessoa que fala ganha uma cor. Quem fala mais fica branco. |
| `cores_falantes` | Ordem das cores: `branco`, `ciano`, `rosa`, `verde`, `laranja`, `lilas`, `azul`, `vermelho`. |
| `sensibilidade_falantes` | 0,9 por padrão. Aumente se o app separar a mesma pessoa em duas cores; diminua se juntar pessoas diferentes. |
| `transicao` / `duracao_transicao` | Como a abertura passa pro corte: `fade` (padrão), `fadeblack`, `smoothleft`, `nenhuma`. Duração em segundos (0,45). |
| `mostrar_texto_gancho` | `false` (padrão) = sem texto do gancho no começo. `true` = mostra em branco, sem caixa. |

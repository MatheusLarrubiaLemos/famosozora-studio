# FamosoZora Studio — Como usar

Tudo para transformar um vídeo longo em Shorts estilo **trailer** e postar no **YouTube, TikTok e Instagram**, num painel só.

```
Vídeo longo ──► 1. Transcrever ──► 2. Claude escolhe os cortes ──► 3. Gerar Shorts ──► 4. Publicar (Buffer)
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

## 2. O dia a dia: 4 passos

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
      ├─ cortes.json           ← escrito pelo Claude
      └─ prontos\              ← Shorts + textos_para_postar.txt
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

# FamosoZora Studio — Como usar

Tudo para transformar um vídeo longo em Shorts estilo **trailer** e postar no **YouTube, TikTok e Instagram**, num painel só.

```
Vídeo longo ──► 1. Transcrever ──► 2. Claude escolhe os cortes ──► 3. Gerar Shorts ──► 4. Publicar (Buffer)
```

Os vídeos originais **nunca são alterados**: as ferramentas só leem os vídeos e criam arquivos novos.

---

## 1. Primeira vez (instalação)

1. Abra a pasta `F:\CLAUDE\canal famosozora\shorts`.
2. Dê dois cliques em **`0 - Instalar (so na primeira vez).bat`**.
   - Ele instala o ffmpeg, o Python 3.12 e o Whisper (o programa que transcreve). Com placa NVIDIA, também instala a aceleração por GPU.
   - Se ele instalar o Python e pedir, **feche a janela e rode de novo**.
3. No final ele cria o atalho **FamosoZora Studio** na Área de Trabalho.

> Também dá pra abrir o painel pelo arquivo **`FamosoZora Studio.bat`**, na pasta `canal famosozora`.

Pra atualizar depois, use o botão **Instalar / atualizar** dentro do Studio.

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
| **Abertura** | Começa com a frase mais forte do corte (1 a 5 s) e um *flash* branco antes do início. |
| **Gancho** | Frase grande numa caixa amarela nos primeiros 3,5 s. No formato com câmera, fica na divisa entre câmera e jogo. |
| **Corte** | O trecho escolhido, com legenda palavra por palavra (a palavra falada fica amarela). |
| **Final** | 3,5 s com o vídeo **borrando** aos poucos e o texto **VÍDEO COMPLETO NO CANAL / INSCREVA-SE / youtube.com/famosozora**. |
| **Música** | Trilha *idle* de fundo, baixinha. Ela **abaixa sozinha quando alguém fala** e sobe no final. |

**Formato:** câmera em cima (1080x600) e jogo embaixo (1080x1320). Pra marcar onde fica sua câmera, use **Marcar câmera e gameplay** no Studio. Se mudar a câmera de lugar no OBS, é só marcar de novo.

---

## 5. Legendas mais precisas

Três coisas trabalham juntas:

1. **Vocabulário** (`ferramentas\vocabulario.txt`): nomes e termos do canal (Matheus, João, Pedro, Bully, FamosoZora...), um por linha. O Whisper passa a escrever esses nomes certo. **Adicione nomes novos sempre que aparecerem**: jogos, amigos, apelidos.
2. **Retranscrição dos cortes:** com placa de vídeo, cada corte é transcrito de novo com o modelo mais preciso (`large-v3`) antes de gerar. Na primeira vez ele baixa o modelo, uns 3 GB.
3. **Legenda corrigida pelo Claude:** o Claude escreve o texto certo de cada corte, e o gerador encaixa esse texto no tempo de cada palavra.
   - Partes entre `[[ ]]` são as que o Claude não teve certeza. Nelas, vale o que o áudio diz.

Correções que se repetem em todo vídeo vão em `ferramentas\correcoes.txt`, no formato `palavra errada = palavra certa`.

---

## 6. Músicas de fundo

- As músicas ficam em `shorts\musicas`. Já vêm duas trilhas *idle* (`idle_zora_01` e `idle_zora_02`) feitas do zero pelo Claude, **livres de direitos**.
- Pode colocar as suas (`.mp3`, `.m4a`, `.wav`). Use só música que você pode usar, como a **Biblioteca de áudio do YouTube Studio**.
- Por padrão, cada Short usa uma música diferente da pasta.
- Pra desligar a música, troque `"musica"` para `"nenhuma"` no `config.json`.

---

## 7. Ajustes (`ferramentas\config.json`)

Abra pelo botão **Configurações** no Studio (Bloco de Notas). Salve e gere de novo.

| Ajuste | O que faz | Padrão |
|---|---|---|
| `layout` | `camera`, `desfocado` (vídeo inteiro com fundo borrado) ou `recorte` | `camera` |
| `palavras_por_legenda` | Quantas palavras aparecem por vez | `3` |
| `tamanho_legenda` / `posicao_legenda` | Tamanho da letra / distância até o pé da tela | `84` / `520` |
| `cor_destaque` | Cor da palavra falada: amarelo, verde, vermelho, azul, rosa, laranja, branco | `amarelo` |
| `usar_abertura` | Liga ou desliga a abertura estilo trailer | `true` |
| `duracao_gancho` / `tamanho_gancho` / `cor_gancho` | Tempo, tamanho e cor da caixa do gancho | `3.5` / `72` / `amarelo` |
| `duracao_final` | Segundos do final com INSCREVA-SE (`0` desliga) | `3.5` |
| `final_linha_1/2/3` | Textos do final | `VÍDEO COMPLETO NO CANAL` / `INSCREVA-SE` / `youtube.com/famosozora` |
| `musica` | `aleatoria`, o nome de um arquivo da pasta `musicas` ou `nenhuma` | `aleatoria` |
| `volume_musica` / `volume_musica_final` | Volume da música durante o corte / no final | `0.18` / `0.55` |
| `retranscrever_cortes` | `auto` (só com placa de vídeo), `true` ou `false` | `auto` |
| `qualidade_crf` | Menor = mais qualidade e arquivo maior (18 a 23) | `20` |
| `codificar_na_gpu` | `auto` usa a placa NVIDIA (NVENC) pra montar o vídeo, que fica mais rápido e libera o processador; `false` usa só o processador | `auto` |

---

## 8. Onde fica cada coisa

```
canal famosozora\   (pode ficar em qualquer pasta)
├─ FamosoZora Studio.bat        ← abre o painel
├─ videos\                      ← vídeos longos (+ Juntar Videos.bat)
└─ shorts\
   ├─ COMO USAR.md              ← este guia
   ├─ 0 - Instalar (so na primeira vez).bat
   ├─ musicas\                  ← trilhas de fundo
   ├─ ferramentas\              ← scripts, config.json, vocabulario.txt, correcoes.txt
   └─ <nome do vídeo>\
      ├─ transcricao_para_claude.txt, legenda_video_completo.srt
      ├─ cortes.json            ← escrito pelo Claude
      └─ prontos\               ← Shorts + textos_para_postar.txt
```

> Os arquivos `1 - Transcrever video.bat`, `2 - Gerar Shorts.bat` e `3 - Marcar camera e gameplay.bat` ainda funcionam, mas o Studio faz tudo isso.

---

## 9. Problemas comuns

| Problema | Solução |
|---|---|
| Erro numa janela preta | Tire um print e mande pro Claude. |
| Quero saber se a placa de vídeo está sendo usada | Na janela preta aparece **"Usando a PLACA DE VIDEO"** (legenda) e **"Codificando na: PLACA DE VIDEO (NVENC)"** (vídeo). No Gerenciador de Tarefas → Desempenho → GPU, troque um dos gráficos de "3D" para **"Cuda"** e veja a **memória dedicada** subir. |
| "Rode o instalador" | Botão **Instalar / atualizar** no Studio. |
| A parte de cima não mostra seu rosto | **Marcar câmera e gameplay** de novo, num vídeo em que o rosto apareça. |
| Uma palavra sempre sai errada | Coloque em `correcoes.txt` ou o nome em `vocabulario.txt`. |
| Quero mudar o começo ou o fim de um corte | Fale pro Claude, por exemplo: *"começa o corte 3 dois segundos antes"*. Depois gere de novo com **SIM**. |
| O Buffer não deixa conectar o TikTok ou o Instagram | Mude a conta para Business ou profissional (seção 3). |

---

## 10. Usar em outro computador (GitHub)

O programa está no GitHub (repositório privado), então funciona no PC e no notebook.

- **Instalar num computador novo:** GitHub Desktop → *File → Clone repository* → escolha o repositório → rode `shorts\0 - Instalar (so na primeira vez).bat`. Sem placa NVIDIA, a transcrição usa o processador (mais lenta).
- **Pegar a versão nova:** botão **Baixar atualização (GitHub)** no Studio, ou *Fetch origin → Pull origin* no GitHub Desktop.
- **Mandar mudanças deste computador** (ex.: marcou a câmera de novo, mexeu no `vocabulario.txt`): GitHub Desktop → *Commit to main* → *Push origin*.
- **Vídeos e Shorts não vão pro GitHub.** Cada computador tem os seus. Para gerar Shorts de um vídeo no outro computador, copie o vídeo pra pasta `videos\` dele (ou copie a pasta do vídeo inteira de dentro de `shorts\`).

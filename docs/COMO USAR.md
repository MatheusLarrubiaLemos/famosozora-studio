# FamosoZora Studio — Como usar

Tudo para transformar a live em Shorts estilo **trailer**, editar o **vídeo longo** como um episódio de programa de TV e **publicar no YouTube**, num painel só.

```
Shorts:         1 Transcrever ─► 2 Gerar cortes com o Claude ─► 3 Gerar Shorts ─► 4 Revisar ─► 5 Publicar
Vídeos longos:  1 Juntar as partes ─► 2 Transcrever ─► 3 Editar com o Claude e revisar ─► Gerar episódio ─► 4 Publicar
```

Os vídeos originais **nunca são alterados**: o Studio só lê os vídeos e cria arquivos novos. E **nada é publicado** sem você revisar e clicar em **Confirmar**.

---

## 1. Primeira vez (instalação)

1. No GitHub, abra **Releases** e baixe o `FamosoZora-Studio-Setup-X.Y.Z.exe` mais novo.
2. Abra o arquivo. Se o Windows avisar que protegeu o computador, clique em **Mais informações → Executar assim mesmo**.
3. Abra o **FamosoZora Studio** pelo atalho da Área de Trabalho.
4. Na primeira vez, ele pergunta qual vai ser a **pasta de trabalho**, onde ficam os vídeos e os projetos em produção:
   - **SIM** = `Documentos\FamosoZora`;
   - **NÃO** = escolher outra pasta.
5. Se o PC tiver placa NVIDIA, ele oferece ativar a aceleração. Vale a pena: a transcrição fica muito mais rápida.
6. Para publicar e para pedir cortes com um clique, veja **`PUBLICAR.md`** (Configurações → Ajuda → Guia: PUBLICAR no YouTube): o Studio usa o **Claude Code** e o **Claude in Chrome** do seu PC (ou o Cowork).

> A pasta de trabalho é **descartável**: depois de publicar, dá para excluir o que pesa (seção 6). As suas configurações (vocabulário, correções, marcação da câmera, músicas) **não** ficam nela.

---

## 2. A janela do Studio

- Abre **sempre maximizada**, no monitor onde estava da última vez. **F11** = tela cheia sem bordas; **Esc** sai da tela cheia.
- **Barra lateral** (à esquerda): **Início · Shorts · Vídeos longos · Publicação · Configurações**. Atalhos: `Ctrl+1` a `Ctrl+5`.
- **Início:** o que está pendente: vídeos para transcrever, Shorts para fazer/revisar/publicar, vídeos longos esperando revisão ou publicação e os próximos agendamentos. Clique num item para ir direto para ele.
- **Arrastar e soltar:** arraste um ou vários vídeos para a janela. Cada um vira um projeto e o Studio já começa a transcrever. Ou use **+ Adicionar vídeo** no Início.
- **Telas Shorts e Vídeos longos:** à esquerda, os **cartões** dos projetos (miniatura, nome, quantos Shorts, publicados e status). À direita, o projeto selecionado com **um botão laranja**: o próximo passo. Duplo clique no projeto faz o mesmo.
- **Avisos discretos** aparecem no canto de baixo ("Agendado: ... qua 18/11 às 12:00") e somem sozinhos.
- **Configurações:** pasta de trabalho, legenda e Shorts (pessoas e cores, máximo de Shorts, vocabulário, correções, marcar câmera, `config.json`), músicas e efeitos, **Claude** (como publicar), atualizações e ajuda.

### Botão direito e atalhos (em todo o Studio)

| Onde | Botão direito | Atalhos |
|---|---|---|
| Projeto (Shorts / Vídeos longos) | os passos do projeto, abrir pasta, **Excluir...** | `Delete` exclui; `Enter` faz o próximo passo; `Ctrl`/`Shift` + clique seleciona vários |
| Linha da legenda (editor) | ▶ Ouvir · Assistir · ✏ Editar texto · Editar tempo › · 🗣 Trocar quem fala › · 🔇 Censurar palavra › · Sempre censurar › · ➕ Inserir linha · 🗑 Excluir linha · Desfazer | duplo clique edita; `F2`/`Enter` editar; `Espaço` tocar/parar; `Delete` excluir linha; `Ctrl+S` salvar; `Ctrl+Z` desfazer |
| Música / efeito (editor, aba Áudio) | Ouvir · Trocar · Volume · Tempo · Excluir | duplo clique no efeito toca; `Delete` exclui |
| Short da lista (editor) | Abrir · Renderizar de novo · Publicar · Abrir pasta · Voltar ao original · Excluir | duplo clique assiste |
| Trecho do vídeo longo (revisão) | Ouvir o trecho que sai · Ouvir a emenda · Manter · Remover | `Espaço` manter/remover; duplo clique ouve |
| Item da fila (Publicação) | Abrir no YouTube · Abrir o pacote · Copiar pedido · Mandar de novo · Marcar como agendado/publicado · Tirar da fila | duplo clique abre o link; `Delete` tira da fila |
| Janela principal | — | `F11` tela cheia · `Esc` sai · `Ctrl+1..5` telas |

---

## 3. Shorts

### Passo 1 — Transcrever vídeo novo
- Arraste o vídeo para a janela, ou clique em **1 Transcrever vídeo novo** e escolha o vídeo (pode escolher vários).
- Uma janela preta mostra o progresso. Com placa de vídeo, 3h de vídeo levam uns 10 a 20 minutos.
- Isso gera, na pasta do vídeo dentro de `shorts`:
  - `legenda_video_completo.srt`: legenda do vídeo longo. Dá pra importar no CapCut.
  - `transcricao_para_claude.txt`: o texto que o Claude lê pra escolher os cortes.

> Se o vídeo estiver em partes, junte antes, na tela **Vídeos longos** (passo 1).

### Passo 2 — Gerar cortes com o Claude
- Selecione o vídeo e clique em **2 Gerar cortes com o Claude** (ou no botão laranja).
- O Studio manda a transcrição e as diretrizes do canal para o **Claude Code** do seu PC e recebe o `cortes.json` **sozinho**, sem copiar e colar. Uma janela mostra o progresso, com **Cancelar**.
  - Live muito longa: o Studio divide em partes e junta as respostas.
  - Erro de rede: tenta de novo sozinho até 3 vezes. Resposta quebrada: pede de novo uma vez. Se não der, avisa e não muda nada.
  - Já tinha cortes? O Studio pergunta antes, e os antigos vão para `cortes_anterior.json`.
  - **Sem o Claude Code instalado:** o botão copia o pedido (jeito antigo). Cole (**Ctrl+V**) na conversa com o Claude e envie; ele salva o `cortes.json` na pasta. Esse jeito também está no botão direito: **Copiar pedido de cortes**.
- O Claude escolhe **só os momentos que valem a pena** (chamativos e/ou engraçados). **Não tem número fixo:** pode vir 0, 3 ou 15 cortes. Se não vier nenhum, o Studio mostra "Nenhum trecho forte o bastante nesse vídeo".
- Para pôr um teto: *Configurações → Máximo de Shorts por vídeo...* (vazio = sem limite). É só um teto: se o Claude mandar mais, o Studio gera os de nota mais alta.
- Cada corte vem com:
  - **Clima** (engraçado, épico, tenso, emocionante, calmo ou caótico): escolhe a música (seção 10).
  - **Motivo** (por que o trecho prende) e **nota** de 1 a 10: aparecem no editor, e a lista fica ordenada pela nota.
  - **Sons** (opcional): efeitos sonoros e troca de música sugeridos pelo Claude (seção 10).
  - **Abertura:** o momento mais forte do corte, mostrado logo no começo, como num trailer.
  - **Legenda corrigida:** nomes, gírias e palavras que o Whisper errou.
  - **Textos do YouTube:** título (até 100 caracteres), descrição e tags.

### Passo 3 — Gerar Shorts
- Clique em **3 Gerar Shorts**.
- Se o vídeo já tiver Shorts, ele pergunta:
  - **SIM:** refaz todos. Os atuais vão pra pasta `prontos\antigos`, nada é apagado.
  - **NÃO:** gera só os que faltam.
- Os Shorts ficam em `shorts\<nome do vídeo>\prontos`.

### Passo 4 — Revisar os Shorts
Clique em **4 Revisar legendas**. À esquerda ficam os Shorts do projeto (os de nota mais alta em cima). Ao escolher um, o topo mostra a nota, o clima e por que o trecho prende, e embaixo há **três abas**: **Legenda**, **Falantes** e **Áudio e edição**. Embaixo de tudo ficam só três botões: **Salvar** (`Ctrl+S`), **Renderizar** e **Publicar** (laranja). O resto está no **botão direito** e nos atalhos.

**Aba Legenda:** a legenda em linhas, com início, fim, quem fala e o texto.

- **Corrigir o texto:** **duplo clique** na linha (ou `F2`), mude e aperte **Enter**. **Esc** cancela.
  - Com o mesmo número de palavras, cada palavra continua no seu tempo.
  - Com mais ou menos palavras, o tempo da linha é repartido entre elas.
- **Corrigir o tempo:** duplo clique no **Início** ou no **Fim** (ex.: `12:03.5`). O Studio não deixa invadir a linha de cima nem a de baixo.
- **Botão direito na linha:** ▶ Ouvir este trecho (toca o áudio dentro do Studio; `Espaço` toca e para) · Assistir este trecho (vídeo) · Editar texto · Editar tempo · **Trocar quem fala** (lista de pessoas ou "+ nova pessoa...") · **Censurar palavra** (as palavras da linha) · Sempre censurar (pôr na lista) · **Inserir linha abaixo** · **Excluir linha** (`Delete`) · Desfazer (`Ctrl+Z`).
- **Amarelo:** palavras que o Claude marcou como incertas. Confira essas primeiro.
- **Sublinhado / texto amarelo:** possível erro de português. Os nomes do vocabulário do canal não contam. O corretor só aponta: gíria como "véi" também aparece, e tudo bem.
- A caixa embaixo da lista mostra a linha selecionada na **cor da pessoa** (a cor da legenda no vídeo).
- **Renderizar:** refaz apenas esse Short com a sua revisão (salva antes). Não refaz a transcrição nem chama o Claude.
- Ao salvar, o Studio mostra as palavras que você trocou e pergunta se quer gravar no `correcoes.txt`, para o erro não se repetir nos próximos vídeos.

> A legenda original nunca se perde: ficam `legendas\NN_original.json` (como saiu) e `legendas\NN_editada.json` (a sua revisão) na pasta do vídeo. **Botão direito no Short → Voltar ao original** descarta a revisão.

**Botão direito no Short da lista:** Abrir (assistir) · Renderizar de novo · Publicar · Abrir pasta · Voltar ao original · **Excluir este Short** (vai para a Lixeira, sai da lista de publicação e o corte não é gerado de novo).

**Aba Falantes (nome e cor de quem fala).** Regra: fala sem dono = **FamosoZora, em branco**.
- Cada voz que o detector achou no Short aparece numa linha: **▶ ouvir** toca uma amostra da voz; ao lado, escolha a pessoa (ou "+ nova pessoa...") e clique em **cor** para mudar a cor dela.
- **"Mostrar nome de quem fala no vídeo"** (desligado por padrão): põe o nome pequeno, na cor da pessoa, acima da legenda, só quando quem fala não é o FamosoZora.
- Se aparecer "⚠ cor escura: difícil de ler", escolha uma cor mais clara (a legenda tem borda preta).
- As vozes são ligadas **Short por Short**: o detector analisa cada corte separado, então a "Voz 1" de um Short pode ser outra pessoa no seguinte.

**Cadastro de pessoas** (*Configurações → Pessoas e cores da legenda*, ou o botão **Pessoas e cores...** na aba Falantes): vale para todos os projetos. Dá para criar, renomear, mudar a cor, **Tornar padrão** (quem fica com as falas sem dono) e excluir. A pessoa padrão não pode ser excluída; as falas de quem você excluir voltam para ela. Renomear também troca o nome nos projetos.

**Aba Áudio e edição (música e efeitos deste Short).**
- **Música ligada / Efeitos ligados:** interruptores para comparar rápido com e sem.
- **Música tema:** botão direito no nome da música (ou **Opções da música ▾**): ▶ Ouvir · 🔄 Trocar... · 🎲 Sortear outra do clima · 🔊 Volume · 🗑 Excluir (Short sem música). O volume também tem a barra. Botão direito na linha da troca: "Tirar a troca de música".
- **Efeitos sonoros:** um por linha, com tempo, categoria, arquivo, volume e o motivo do Claude. Botão direito num efeito: ▶ Ouvir sozinho · ▶ Ouvir o trecho com o efeito (uns 5 s com a fala, a música e o efeito) · Trocar arquivo · Volume · Mudar o tempo · Excluir. **+ Adicionar efeito** põe um efeito no tempo da linha selecionada na aba Legenda.
- Efeito em **vermelho** = está em cima de uma fala e pode cobrir a voz.
- **Restaurar sugestão do Claude:** volta a música e os efeitos ao que o Claude sugeriu.

> O que você muda fica em `edicao_shorts\NN_edicao.json`, separado da sugestão do Claude (`NN_sugestao.json`), e as vozes ligadas ficam em `falantes.json`.

**Censura (por Short; desligada por padrão).** As diretrizes do canal permitem palavrão, então nada é censurado sozinho.
- **Botão direito na linha → Censurar palavra ›** e escolha a palavra (✓ = já censurada; clicar de novo tira). Ou botão direito em cima da palavra, na caixa da linha. Ela vira `p***` só neste Short.
- **"Censurar as palavras da lista (censura.txt) neste Short":** marque para censurar, neste Short, tudo o que está na lista.
- **Sempre censurar (pôr na lista):** grava a palavra no `censura.txt`.
- **No áudio:** por padrão só a legenda muda. Para calar a palavra ou pôr um bip, mude `censura_audio` no `config.json` (seção 11).

### Passo 5 — Publicar
- **Um Short:** botão **Publicar** no editor (ou botão direito no Short → Publicar).
- **Todos os prontos deste vídeo:** **5 Publicar os Shorts prontos**. **Todos de todos os vídeos:** tela **Publicação → Publicar todos os Shorts prontos**.
- O horário é automático: **12:00 (Brasília)**, **um por dia**, no dia depois do último Short já agendado.
- Abre a **revisão**: título (até 100 caracteres), data e hora, descrição, tags e playlist. Confira e clique em **Confirmar e publicar**.
- O Studio monta o **pacote** (`publicar\<data> <título>\`) e manda o pedido para o **Claude no seu PC**, que agenda pelo **YouTube Studio** no seu Chrome. Acompanhe na tela **Publicação**. Detalhes, o que instalar e o que fazer quando dá erro: **`PUBLICAR.md`**.

> **Link do vídeo completo:** clique no texto 🔗 "Link do vídeo completo" no cartão do projeto (ou botão direito → Link do vídeo completo...). As descrições passam a apontar pra ele. Quando o vídeo longo é agendado pelo Studio, o link entra sozinho.
> No YouTube Studio, também dá pra ligar cada Short ao vídeo completo pelo campo **Vídeo relacionado**.

---

## 4. Vídeos longos

Transforma a live bruta (umas 3 horas) num episódio editado, **estilo programa de TV**: sem as partes paradas, **sem gancho** (começa normal, com a intro) e com o seu **outro** no final.

### Passo 1 — Juntar vídeos (partes da live)
Se a live ficou em várias partes, junte numa só. Arraste os arquivos para a lista, acerte a ordem e clique em **JUNTAR**. Os originais não são tocados.

### Passo 2 — Transcrever a live
O mesmo passo 1 dos Shorts: uma transcrição serve para os Shorts e para o episódio.

### Passo 3 — Editar com o Claude e revisar
1. **Editar com o Claude.** Selecione o vídeo e clique no botão laranja (ou **3 Editar com o Claude / revisar**). O Studio manda a transcrição para o Claude Code e recebe o `edicao.json` sozinho (com progresso, Cancelar, novas tentativas e conferência, como nos cortes). O Claude marca só o que **realmente não tem nada acontecendo** (espera, menu, tela parada, papo sem nada), os capítulos, o título, a descrição e as tags.
   - **Sem o Claude Code:** o pedido sai copiado (jeito antigo). Se a conversa não tiver acesso ao PC, copie o JSON que o Claude mandar e use **Colar edicao.json** (botão direito no projeto ou *Mais opções* na revisão).
2. **Revisar.** Abre a janela de revisão:
   - no topo, a duração original → a duração do episódio;
   - a **linha do tempo** do vídeo inteiro: em **laranja** o que sai, em **cinza** o que você mandou manter, e os **capítulos**. Clique num trecho para achar na lista;
   - a lista do que vai **SAIR**, com início, fim, duração e o motivo que o Claude deu; **caixinha** (ou `Espaço`) para manter/remover;
   - **botão direito** num trecho (na lista ou na linha do tempo): ▶ **Ouvir o trecho que sai** (abre o primeiro minuto dele) · ▶ **Ouvir a emenda** (5 s antes + 5 s depois, já emendados) · **Manter este trecho** · **Remover este trecho**;
   - ⚠ nos trechos com menos de 30 s;
   - **Incluir o outro no final** (ligado por padrão) e a situação da pasta `outro\` (seção 5);
   - **Gerar prévia (10 min):** gera só os primeiros 10 minutos e mostra quanto tempo o episódio inteiro vai levar;
   - **Mais opções ▾:** ouvir emenda, pedir de novo ao Claude, colar edicao.json, abrir a pasta do episódio.
   > O Claude só vê a transcrição, não a tela. Por isso a revisão é obrigatória: ouça os trechos duvidosos antes de gerar.
3. **Gerar.** Clique em **Gerar episódio** (laranja). Uma janela preta mostra o progresso e o tempo que falta.
   - Um episódio de 1h30 leva uns 25 a 40 minutos, conforme o PC.
   - Se o vídeo já tiver episódio, o anterior vai para `episodio\antigos\<data>`. Nada é apagado.
   - Tudo fica em `shorts\<nome do vídeo>\episodio`: o `.mp4` e o `textos_episodio.txt` (título, descrição **com os capítulos**, inglês, 3 opções de título, ideia da miniatura e tags).

### Passo 4 — Publicar o episódio
Botão **Publicar** (na revisão, no botão laranja ou no botão direito do projeto). Abre a mesma revisão dos Shorts, com a descrição **já com os capítulos**, as tags, a sugestão de horário (padrão: amanhã às 18:00, ajustável) e **Escolher thumb...** (senão vai um quadro do vídeo). Depois de agendado, o projeto mostra "✓ Publicado".

**Como o episódio é montado:**

| Parte | O que acontece |
|---|---|
| **Começo** | **Sem gancho:** começa do começo, com a intro. |
| **Episódio** | A live sem as partes que saíram. |
| **Emendas** | Cada borda vai sozinha para a pausa entre palavras mais próxima (até 2 s), e cada emenda tem uma **transição curta** (fade de 0,2 s). |
| **Outro** | O seu outro (pasta `outro\`) entra no final com uma transição de 0,6 s (xfade + acrossfade), já convertido para a resolução, o FPS e o áudio do episódio. |
| **Capítulos** | O Studio converte os tempos para o episódio editado e segue as regras do YouTube: o primeiro é 0:00, cada um tem 10 s ou mais e são no mínimo 3. Também vão gravados dentro do `.mp4`. |
| **Formato** | 16:9, na mesma resolução e fps da gravação. |

> **Quero mudar um trecho:** fale pro Claude (*"o trecho das 01:06:37 começa 5 s depois"*), ou mande manter na revisão. Depois gere de novo.

---

## 5. O outro (final padrão dos vídeos longos)

- Abra a pasta **`outro\`** da pasta de trabalho (*Configurações → Pasta do outro*, ou **Pasta do outro** na revisão) e coloque lá o seu outro, por exemplo `outro.mp4`. O `LEIA-ME.txt` explica tudo.
- Ele precisa ter de **5 a 20 segundos** para dar para pôr a **tela final do YouTube** (vídeos e botão de inscrever). O Studio avisa se estiver fora disso.
- Pode ser de qualquer resolução, FPS ou áudio (ou sem áudio): o Studio converte na hora.
- Mais de um vídeo na pasta: vale o primeiro em ordem alfabética.
- Pasta vazia: o episódio sai sem outro, com aviso. Para um vídeo não ter outro, desligue **Incluir o outro no final** na revisão.

---

## 6. Excluir projetos e vídeos

**Botão direito no projeto → Excluir...** (ou `Delete`, ou o botão **🗑 Excluir...**). Para vários de uma vez, selecione com `Ctrl` + clique ou `Shift` + clique.

| Opção | O que vai para a Lixeira |
|---|---|
| **Só os Shorts gerados** (tela Shorts) | os `.mp4` dos Shorts, as versões antigas e os temporários. Ficam a transcrição, os cortes e as edições (dá para gerar de novo). |
| **Só o episódio gerado** (tela Vídeos longos) | o `.mp4` do episódio e as versões antigas. Ficam a transcrição e a edição. |
| **Projeto inteiro** | a pasta do projeto toda. O vídeo original fica. |
| **Projeto + vídeo original** | a pasta e o vídeo original (aviso em **vermelho** e uma segunda confirmação). |

- A janela mostra **quanto espaço vai liberar**.
- Avisa se algum vídeo ainda está na **fila de publicação** e não saiu.
- **Sempre vai para a Lixeira do Windows**, nunca é apagado de vez. Para desfazer: abra a Lixeira, botão direito no arquivo → **Restaurar**.
- No **Início**, botão direito num vídeo da pasta `videos` que ainda não virou projeto: Transcrever · Mostrar na pasta · Excluir vídeo.

---

## 7. Atualizações

- Ao abrir, o Studio procura sozinho, em segundo plano, se tem versão nova no GitHub.
- Se tiver, aparece uma janela com o número da versão e as novidades:
  - **Atualizar agora:** baixa o instalador, abre e fecha o Studio para instalar. Seus vídeos, projetos e configurações não são apagados.
  - **Depois:** fecha o aviso. Ele aparece de novo na próxima abertura.
- Sem internet, não aparece nada.
- Para não procurar ao abrir: *Configurações → Verificar atualizações ao abrir* (desmarque).
- Para procurar na hora: *Configurações → Procurar atualização*.

---

## 8. Como cada Short é montado

| Parte | O que acontece |
|---|---|
| **Abertura** | Começa com a frase mais forte do corte (1 a 5 s), que se mistura suavemente no corte (*fade* de 0,45 s). |
| **Corte** | O trecho escolhido, com legenda palavra por palavra. A palavra falada fica cheia e um pouco maior, e **cada pessoa tem a sua cor** (cadastro de pessoas). Fala sem dono = FamosoZora, branco. |
| **Final** | 3,5 s com o vídeo **borrando** aos poucos e o texto **VÍDEO COMPLETO NO CANAL / INSCREVA-SE / youtube.com/famosozora**. |
| **Música** | Música do **clima do corte**, baixinha. Ela **abaixa sozinha quando alguém fala** e sobe no final. Se for menor que o Short, repete com crossfade. |
| **Efeitos** | Os efeitos sonoros sugeridos pelo Claude (no máximo 3), cada um no seu tempo e com o seu volume. |

**Formato:** câmera em cima (1080x600) e jogo embaixo (1080x1320). Pra marcar onde fica sua câmera, use *Configurações → Marcar câmera e gameplay*. Se mudar a câmera de lugar no OBS, é só marcar de novo.

---

## 9. Legendas mais precisas

Quatro coisas trabalham juntas:

1. **Vocabulário** (*Configurações → Vocabulário*): nomes e termos do canal (Matheus, João, Pedro, Bully, FamosoZora...), um por linha. O Whisper passa a escrever esses nomes certo, e o corretor deixa de marcá-los como erro. **Adicione nomes novos sempre que aparecerem**: jogos, amigos, apelidos.
2. **Retranscrição dos cortes:** com placa de vídeo, cada corte é transcrito de novo com o modelo mais preciso (`large-v3`) antes de gerar. Na primeira vez ele baixa o modelo, uns 3 GB.
3. **Legenda corrigida pelo Claude:** o Claude escreve o texto certo de cada corte, e o gerador encaixa esse texto no tempo de cada palavra. Partes entre `[[ ]]` são as que o Claude não teve certeza: nelas vale o que o áudio diz, e no editor elas aparecem em amarelo.
4. **A sua revisão** no passo 4 dos Shorts.

Correções que se repetem em todo vídeo vão em *Configurações → Correções automáticas*, no formato `palavra errada = palavra certa`. O editor de legendas também oferece gravar ali as palavras que você corrigiu.

---

## 10. Músicas e efeitos sonoros

O Studio **só usa o áudio que você colocar nas pastas**. Ele não baixa nada da internet. Use só música e efeito que você pode usar (sem direitos autorais ou licenciado, como a **Biblioteca de áudio do YouTube Studio**), para não tomar Content ID.

**Músicas por clima** (*Configurações → Músicas de fundo (por clima)*): uma subpasta por clima do corte.

```
musicas\
├─ engracado\    ├─ epico\    ├─ tenso\
├─ emocionante\  ├─ calmo\    ├─ caotico\
└─ geral\        ← serve para qualquer clima (as duas trilhas idle do canal já estão aqui)
```

- Cada Short usa uma música da pasta do clima dele. Pasta vazia → usa `geral\`. Nenhuma música → o Short sai sem música e o Studio avisa.
- Não repete a mesma música em Shorts seguidos e, se der, usa todas do clima antes de repetir.
- Músicas soltas de antes da 1.4.0 foram **copiadas** para `geral\` (nada foi apagado).
- Para desligar a música de todos os Shorts, troque `"musica"` para `"nenhuma"` no `config.json`. Para um Short só, use a aba **Áudio e edição**.

**Efeitos sonoros** (*Configurações → Efeitos sonoros*): uma subpasta por categoria. O nome da pasta é o que o Claude vê.

```
efeitos\
├─ risada\   ├─ impacto\   ├─ falha\
└─ suspense\ ├─ vitoria\   └─ transicao\     (pode criar outras, ex.: explosao\)
```

- Começa vazia. Prefira efeitos curtos (até uns 3 s), em `.wav`, `.mp3` ou `.m4a`.
- O pedido ao Claude só manda as categorias que **têm arquivo**. O Claude põe efeito só quando combina com o momento: no máximo ~3 por Short e nunca em cima de uma fala.
- O Claude também pode sugerir **trocar a música** num momento-chave (ex.: uma virada épica).

**Para valer em todos os seus PCs:** coloque as músicas e os efeitos nas pastas `musicas\` e `efeitos\` **da pasta do GitHub** e faça Commit + Push. O que você põe pelas *Configurações* no app instalado vale só naquele PC.

---

## 11. Ajustes (`config.json`)

Abra em *Configurações → Configurações avançadas (config.json)* (Bloco de Notas). Salve e gere de novo.

**Shorts**

| Ajuste | O que faz | Padrão |
|---|---|---|
| `layout` | `camera`, `desfocado` (vídeo inteiro com fundo borrado) ou `recorte` | `camera` |
| `palavras_por_legenda` | Quantas palavras aparecem por vez | `3` |
| `tamanho_legenda` / `borda_legenda` | Tamanho da letra / grossura da borda | `96` / `4` |
| `posicao_legenda` | Distância da legenda até o pé da tela | `520` |
| `cor_por_falante` | `true` = o Studio separa as vozes de cada Short, para cada pessoa ter a sua cor (nome e cor vêm do cadastro de pessoas) | `true` |
| `sensibilidade_falantes` | Aumente se o app separar a mesma pessoa em duas vozes; diminua se juntar pessoas diferentes | `0.9` |
| `maximo_shorts` | Teto de Shorts por vídeo (`null` = sem limite). Também em *Configurações → Máximo de Shorts por vídeo...* | `null` |
| `usar_abertura` | Liga ou desliga a abertura estilo trailer | `true` |
| `transicao` / `duracao_transicao` | Como a abertura passa pro corte: `fade`, `fadeblack`, `smoothleft`, `nenhuma` / duração em segundos | `fade` / `0.45` |
| `mostrar_texto_gancho` / `duracao_gancho` | Texto branco do gancho no começo / quanto tempo fica na tela | `false` / `3.5` |
| `duracao_final` | Segundos do final com INSCREVA-SE (`0` desliga) | `3.5` |
| `final_linha_1/2/3` | Textos do final | `VÍDEO COMPLETO NO CANAL` / `INSCREVA-SE` / `youtube.com/famosozora` |
| `musica` | `aleatoria`, o nome de uma música ou `nenhuma` | `aleatoria` |
| `volume_musica` / `volume_musica_final` | Volume da música durante o corte / no final (cada Short pode ter o seu volume no editor) | `0.18` / `0.55` |
| `ducking_forca` / `ducking_limiar` | Quanto a música abaixa quando alguém fala (maior = abaixa mais) / a partir de que volume de fala (menor = abaixa mais cedo) | `10` / `0.015` |
| `maximo_efeitos` / `volume_efeitos` | Máximo de efeitos sonoros por Short / volume padrão dos efeitos | `3` / `0.8` |
| `censura_audio` | O que acontece no áudio das palavras censuradas: `nenhum` (só a legenda muda), `silencio` ou `bip` | `nenhum` |
| `retranscrever_cortes` | `auto` (só com placa de vídeo), `true` ou `false` | `auto` |
| `qualidade_crf` | Menor = mais qualidade e arquivo maior (18 a 23) | `20` |

**Vídeo longo e geral**

| Ajuste | O que faz | Padrão |
|---|---|---|
| `codificar_na_gpu` | `auto` usa a placa NVIDIA pra montar os vídeos (mais rápido); `false` usa só o processador | `auto` |
| `episodio_preset` | Velocidade do episódio no processador: `superfast` (mais rápido, arquivo maior), `veryfast` ou `faster` (mais lento, arquivo menor) | `veryfast` |
| `episodio_crf` | Qualidade do episódio (menor = mais qualidade e arquivo maior) | `20` |
| `episodio_ajuste_silencio` | Até quantos segundos a borda do corte anda até a pausa mais próxima (`0` desliga) | `2.0` |
| `episodio_fade_emenda` | Transição curta em cada emenda do episódio, em segundos (`0` = corte seco) | `0.2` |
| `outro_transicao` | Transição entre o fim do episódio e o outro, em segundos | `0.6` |
| `redes` | Onde você publica (um Short conta como publicado quando saiu em todas) | `["youtube"]` |
| `publicar_shorts_hora` | Horário dos Shorts (Brasília), um por dia | `12:00` |
| `publicar_longo_hora` / `publicar_longo_daqui_a_dias` | Sugestão de horário para o vídeo longo | `18:00` / `1` |
| `modelo_claude` | Modelo do Claude para cortes e edição (vazio = o padrão do Claude Code) | vazio |
| `claude_limite_caracteres` | Tamanho de cada parte da transcrição mandada ao Claude | `250000` |

---

## 12. Onde fica cada coisa

**Pasta de trabalho** (a que você escolheu). É descartável: só material de produção.

```
<pasta de trabalho>\
├─ videos\                     ← vídeos longos (juntados pelo Studio, se quiser)
├─ outro\                      ← o seu outro (final dos vídeos longos) + LEIA-ME.txt
├─ publicar\                   ← pacotes de postagem (vídeo, thumb, dados) e os pedidos ao Claude
├─ configuracoes\fila_publicacao.json  ← a fila de publicação
└─ shorts\
   └─ <nome do vídeo>\
      ├─ transcricao_para_claude.txt, legenda_video_completo.srt
      ├─ cortes.json           ← escrito pelo Claude (Shorts); cortes_anterior.json = o pedido anterior
      ├─ falantes.json         ← quem é cada voz, em cada Short
      ├─ edicao.json           ← escrito pelo Claude (vídeo longo, versão 2); edicao.bak.json = cópia do formato antigo
      ├─ legendas\             ← legenda original e revisada de cada Short
      ├─ edicao_shorts\        ← música e efeitos de cada Short (sugestão do Claude e a sua edição)
      ├─ prontos\              ← Shorts + textos_para_postar.txt
      └─ episodio\             ← episódio editado + textos_episodio.txt
```

**Configurações, pessoas, músicas e efeitos:** vêm junto com o programa (o vocabulário, as correções, o cadastro de pessoas, a marcação da câmera, as trilhas e os efeitos do canal). O que você mudar pelas *Configurações* fica neste PC, em `%LOCALAPPDATA%\FamosoZora Studio\configuracoes`, `\musicas` e `\efeitos`, e vale junto com o que veio no programa. Até a 1.2.0 elas ficavam na pasta de trabalho; na primeira abertura da 1.3.0 o Studio copia sozinho.

**Programa** (instalado pelo `.exe`): `%LOCALAPPDATA%\Programs\FamosoZora Studio`. Não precisa mexer lá.

**Registro de erros (log):** `%LOCALAPPDATA%\FamosoZora Studio\logs\studio.log`. Útil para mandar pro Claude quando algo der errado.

**Código no GitHub:** veja o `README.md` do repositório. Ele tem o mapa "quero mudar X → abra o arquivo Y" e o passo a passo para editar o código em outro PC.

---

## 13. Problemas comuns

| Problema | Solução |
|---|---|
| Erro numa janela preta | Tire um print e mande pro Claude. Se precisar de mais detalhes, mande também o `studio.log` (seção 12). |
| Quero saber se a placa de vídeo está sendo usada | Na janela preta aparece **"Usando a PLACA DE VIDEO"** (legenda) e **"Codificando na: PLACA DE VIDEO (NVENC)"** (vídeo). |
| Aparece "Achei uma placa NVIDIA, mas ela não aceitou montar o vídeo" | O driver da NVIDIA está antigo. Funciona assim mesmo, pelo processador; atualizar o driver deixa mais rápido. |
| Falta alguma coisa / deu erro estranho depois de atualizar | Instale de novo o `.exe` mais novo por cima (seus vídeos e projetos não são apagados). |
| A parte de cima do Short não mostra seu rosto | **Marcar câmera e gameplay** de novo, num vídeo em que o rosto apareça. |
| Uma palavra sempre sai errada | Corrija no editor de legendas e aceite gravar no `correcoes.txt`, ou coloque o nome no vocabulário. |
| A lista diz que o `cortes.json` está com erro | O arquivo veio quebrado. Peça pro Claude conferir e salvar de novo. |
| A emenda do episódio cortou uma fala | Mande manter o trecho na revisão (botão direito → Manter), ou peça pro Claude mudar o tempo dele. Use **Ouvir a emenda** pra conferir. |
| O episódio está demorando muito | Use **Gerar prévia** pra ver a estimativa. Pra ficar mais rápido, troque `episodio_preset` para `superfast` no `config.json`. |
| Quero mudar o começo ou o fim de um corte | Fale pro Claude, por exemplo: *"começa o corte 3 dois segundos antes"*. Depois gere de novo com **SIM**. |
| Excluí sem querer | Abra a **Lixeira** do Windows, clique com o botão direito no arquivo e em **Restaurar**. |
| Publicar deu erro / o Claude não respondeu | Veja a tela **Publicação** (o motivo aparece embaixo) e o `PUBLICAR.md`. |
| "Não achei o Claude Code neste computador" | Instale o Claude Code, ou mude para **Cowork** em *Configurações → Claude*. Os cortes e a edição caem no jeito antigo (copiar e colar). |
| O episódio saiu sem o outro | A pasta `outro\` está vazia ou "Incluir o outro no final" está desligado na revisão. |

---

## 14. Usar em outro computador

- **Instalar:** no GitHub, em *Releases*, baixe o `FamosoZora-Studio-Setup-X.Y.Z.exe` e abra.
  - Se o Windows avisar que protegeu o computador: **Mais informações → Executar assim mesmo**.
- **Pasta de trabalho:** você escolhe na primeira vez. Para trocar: *Configurações → Mudar pasta de trabalho*. Ela pode ser diferente em cada PC.
- **Placa NVIDIA:** o app pergunta na primeira vez. Também dá para fazer depois em *Configurações → Ativar placa de vídeo NVIDIA*. Sem placa (no notebook, por exemplo), tudo funciona pelo processador, só mais devagar.
- **Vídeos e projetos não vão pro GitHub.** Para trabalhar num vídeo no outro computador, copie o vídeo para lá.
- **Para editar o código** no outro computador, siga a seção "Configurar em outro PC" do `README.md`.

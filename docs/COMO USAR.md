# FamosoZora Studio — Como usar

Tudo para transformar a live em Shorts estilo **trailer**, postar no **YouTube, TikTok e Instagram** e editar o **vídeo longo** como um episódio de programa de TV, num painel só.

A janela tem **duas abas**, uma para cada tipo de vídeo:

```
Aba Shorts:          1 Transcrever ─► 2 Claude escolhe os cortes ─► 3 Gerar Shorts ─► 4 Revisar legendas ─► 5 Publicar (Buffer)

Aba Vídeos longos:   1 Juntar as partes ─► 2 Transcrever a live ─► 3 Editar vídeo longo (o Claude escolhe o que sai,
                                                                     você revisa e o Studio gera o episódio)
```

Os vídeos originais **nunca são alterados**: o Studio só lê os vídeos e cria arquivos novos.

---

## 1. Primeira vez (instalação)

1. No GitHub, abra **Releases** e baixe o `FamosoZora-Studio-Setup-X.Y.Z.exe` mais novo.
2. Abra o arquivo. Se o Windows avisar que protegeu o computador, clique em **Mais informações → Executar assim mesmo**.
3. Abra o **FamosoZora Studio** pelo atalho da Área de Trabalho.
4. Na primeira vez, ele pergunta qual vai ser a **pasta de trabalho**, onde ficam os vídeos e os projetos em produção:
   - **SIM** = `Documentos\FamosoZora`;
   - **NÃO** = escolher outra pasta.
5. Se o PC tiver placa NVIDIA, ele oferece ativar a aceleração. Vale a pena: a transcrição fica muito mais rápida.

> A pasta de trabalho é **descartável**: depois de postar, dá para limpar (seção 5). As suas configurações (vocabulário, correções, marcação da câmera, músicas) **não** ficam nela.

---

## 2. A janela do Studio

- **Abas Shorts e Vídeos longos / Lives:** cada uma tem a lista de vídeos, os botões dos passos e, embaixo da lista, a faixa com o **próximo passo** do vídeo selecionado.
- **Botão Menu** (no topo, à direita): o que vale para o programa inteiro.
  - Novidades da versão, Procurar atualização e "Verificar atualizações ao abrir";
  - Abrir e Mudar pasta de trabalho;
  - Configurações (`config.json`), Vocabulário, Correções automáticas e Músicas de fundo;
  - Diretrizes do canal e este guia;
  - Ativar placa de vídeo NVIDIA.

---

## 3. Aba Shorts

### Passo 1 — Transcrever vídeo novo
- Clique em **1 Transcrever vídeo novo** e escolha o vídeo.
- Uma janela preta mostra o progresso. Com placa de vídeo, 3h de vídeo levam uns 10 a 20 minutos.
- Isso gera, na pasta do vídeo dentro de `shorts`:
  - `legenda_video_completo.srt`: legenda do vídeo longo. Dá pra importar no CapCut.
  - `transcricao_para_claude.txt`: o texto que o Claude lê pra escolher os cortes.

> Se o vídeo estiver em partes, junte antes, na aba **Vídeos longos / Lives** (passo 1).

### Passo 2 — Pedir cortes ao Claude
- Selecione o vídeo e clique em **2 Pedir cortes ao Claude**. O pedido já sai copiado.
- Cole (**Ctrl+V**) na conversa com o Claude e envie.
- O Claude lê a transcrição, escolhe os melhores momentos e salva o `cortes.json` na pasta do vídeo. Cada corte vem com:
  - **Abertura:** o momento mais forte do corte, mostrado logo no começo, como num trailer.
  - **Legenda corrigida:** nomes, gírias e palavras que o Whisper errou.
  - **Textos de cada rede:** título, descrição e tags do YouTube, e as legendas do TikTok e do Instagram.

### Passo 3 — Gerar Shorts
- Clique em **3 Gerar Shorts**.
- Se o vídeo já tiver Shorts, ele pergunta:
  - **SIM:** refaz todos. Os atuais vão pra pasta `prontos\antigos`, nada é apagado.
  - **NÃO:** gera só os que faltam.
- Os Shorts ficam em `shorts\<nome do vídeo>\prontos`.

### Passo 4 — Revisar legendas
Antes de postar, confira a legenda de cada Short. Clique em **4 Revisar legendas**: à esquerda ficam os Shorts do projeto e, ao escolher um, a legenda aparece em linhas, com início, fim e texto.

- **Corrigir:** selecione a linha, mude o texto na caixa de baixo e aperte **Enter**.
  - Com o mesmo número de palavras, cada palavra continua no seu tempo.
  - Com mais ou menos palavras, o tempo da linha é repartido entre elas.
- **Amarelo:** palavras que o Claude marcou como incertas. Confira essas primeiro.
- **Sublinhado vermelho:** possível erro de português. Os nomes do vocabulário do canal não contam. O corretor só aponta: gíria como "véi" também aparece sublinhada, e tudo bem.
- **Ouvir trecho:** abre no player só o pedaço do vídeo daquela linha. Duplo clique na linha faz o mesmo.
- **Salvar**, **Desfazer** (volta uma mudança por vez) e **Voltar ao original**.
- **Renderizar de novo só este Short:** refaz apenas esse Short com a legenda revisada. Não refaz a transcrição nem chama o Claude. Depois, **Assistir o Short** para conferir.
- Ao salvar, o Studio mostra as palavras que você trocou e pergunta se quer gravar no `correcoes.txt`, para o erro não se repetir nos próximos vídeos.

> A legenda original nunca se perde: ficam `legendas\NN_original.json` (como saiu) e `legendas\NN_editada.json` (a sua revisão) na pasta do vídeo.
> Shorts gerados antes da versão 1.3.0 não têm a legenda guardada: clique uma vez em "Renderizar de novo só este Short".

**Censura (por Short; desligada por padrão).** As diretrizes do canal permitem palavrão, então nada é censurado sozinho.
- **Censurar palavra:** clique em cima da palavra, na caixa da linha, e no botão. Ela vira `p***` só neste Short. **Tirar censura** desfaz.
- **"Censurar as palavras da lista (censura.txt) neste Short":** marque para censurar, neste Short, tudo o que está na lista.
- **Adicionar sempre à lista:** grava a palavra no `censura.txt`.
- **No áudio:** por padrão só a legenda muda. Para calar a palavra ou pôr um bip, mude `censura_audio` no `config.json` (seção 11).

### Passo 5 — Publicar (Buffer)
- Clique em **5 Publicar (Buffer)**. Abre uma janela com a lista de Shorts e, pra cada um:
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

> **Link do vídeo completo:** depois de publicar o vídeo longo, use **Link do vídeo completo...** na aba Shorts. As descrições passam a apontar pra ele. Enquanto não tiver link, elas usam o link do canal.
> No YouTube Studio, também dá pra ligar cada Short ao vídeo completo pelo campo **Vídeo relacionado**.

**Outro botão da aba:** **Marcar câmera e gameplay** (seção 8).

---

## 4. Aba Vídeos longos / Lives

Transforma a live bruta (umas 3 horas) num episódio editado, sem as partes paradas.

### Passo 1 — Juntar vídeos (partes da live)
Se a live ficou em várias partes, junte numa só. Arraste os arquivos para a lista, acerte a ordem e clique em **JUNTAR**. Os originais não são tocados.

### Passo 2 — Transcrever a live
O mesmo passo 1 da aba Shorts: uma transcrição serve para os Shorts e para o episódio.

### Passo 3 — Editar vídeo longo
1. **Pedir a edição ao Claude.** Selecione o vídeo e clique em **3 Editar vídeo longo**. Na primeira vez, o pedido de edição já sai copiado.
   - Cole (**Ctrl+V**) na conversa com o Claude e envie.
   - O Claude lê a transcrição direto da pasta do vídeo e salva o `edicao.json` lá.
   - **Se a conversa não tiver acesso ao PC:** o Claude manda o JSON na conversa. Copie tudo e clique em **Colar edicao.json**. O Studio confere e salva.
2. **Revisar.** Clique em **3 Editar vídeo longo** de novo. Abre a janela de revisão:
   - no topo, a duração original → a duração do episódio;
   - a lista do que vai **SAIR**, com início, fim, duração e o motivo que o Claude deu;
   - **caixinha** em cada corte: clique nela (ou aperte Espaço) para desmarcar. O trecho desmarcado **fica** no episódio;
   - ⚠ nos cortes com menos de 30 s;
   - **Ouvir emenda:** selecione um corte e clique. Em poucos segundos abre um clipe de 10 s (5 s antes + 5 s depois do corte, já emendados). Duplo clique no corte faz o mesmo;
   - **Gerar prévia (10 min):** gera só os primeiros 10 minutos do episódio e mostra quanto tempo o episódio inteiro vai levar.
   > O Claude só vê a transcrição, não a tela. Por isso a revisão é obrigatória: ouça as emendas dos cortes duvidosos antes de gerar.
3. **Gerar.** Clique em **Gerar episódio**. Uma janela preta mostra o progresso e o tempo que falta.
   - Um episódio de 1h30 leva uns 25 a 40 minutos, conforme o PC.
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

---

## 5. Limpar projeto (depois de postar)

A pasta de trabalho guarda só material de produção. Depois de postar, clique em **Limpar projeto (depois de postar)**, em qualquer uma das abas.

- **SIM:** manda para a **Lixeira do Windows** o que pesa: os Shorts, o episódio, as versões antigas e os temporários. **Guarda o resumo** (poucos KB): cortes, edição, transcrição, legendas revisadas, textos para postar e o que já foi marcado como postado. O vídeo continua na lista como "Projeto limpo".
- **NÃO:** manda o projeto **inteiro** para a Lixeira, inclusive o resumo.
- **CANCELAR:** não faz nada.

O Studio avisa antes se algum Short ainda não está marcado como postado ou se existe episódio gerado. Dá para restaurar pela Lixeira. O vídeo original nunca é tocado.

---

## 6. Atualizações

- Ao abrir, o Studio procura sozinho, em segundo plano, se tem versão nova no GitHub.
- Se tiver, aparece uma janela com o número da versão e as novidades:
  - **Atualizar agora:** baixa o instalador, abre e fecha o Studio para instalar. Seus vídeos, projetos e configurações não são apagados.
  - **Depois:** fecha o aviso. Ele aparece de novo na próxima abertura.
- Sem internet, não aparece nada.
- Para não procurar ao abrir: **Menu → Verificar atualizações ao abrir** (desmarque).
- Para procurar na hora: **Menu → Procurar atualização**.

---

## 7. Configurar o Buffer (uma vez só)

1. Crie uma conta grátis em **buffer.com**. O plano grátis conecta **3 canais** e guarda até **10 posts agendados por canal**.
2. Conecte os 3 canais:
   - **YouTube:** o canal FamosoZora.
   - **TikTok:** precisa ser **conta Business**. No app do TikTok: *Configurações e privacidade → Conta → Mudar para Conta Comercial*.
   - **Instagram:** precisa ser **conta profissional**, de Criador de conteúdo ou Comercial. No app: *Configurações → Tipo de conta e ferramentas → Mudar para conta profissional*.
3. Pronto. Agora o passo 5 da aba Shorts funciona.

> O TikTok aceita vídeos de 3 segundos a 10 minutos, até 1 GB. Os Shorts gerados ficam bem abaixo disso.

---

## 8. Como cada Short é montado

| Parte | O que acontece |
|---|---|
| **Abertura** | Começa com a frase mais forte do corte (1 a 5 s), que se mistura suavemente no corte (*fade* de 0,45 s). |
| **Corte** | O trecho escolhido, com legenda palavra por palavra. A palavra falada fica cheia e um pouco maior, e **cada pessoa tem uma cor**: quem fala mais é branco. |
| **Final** | 3,5 s com o vídeo **borrando** aos poucos e o texto **VÍDEO COMPLETO NO CANAL / INSCREVA-SE / youtube.com/famosozora**. |
| **Música** | Trilha *idle* de fundo, baixinha. Ela **abaixa sozinha quando alguém fala** e sobe no final. |

**Formato:** câmera em cima (1080x600) e jogo embaixo (1080x1320). Pra marcar onde fica sua câmera, use **Marcar câmera e gameplay** na aba Shorts. Se mudar a câmera de lugar no OBS, é só marcar de novo.

---

## 9. Legendas mais precisas

Quatro coisas trabalham juntas:

1. **Vocabulário** (*Menu → Vocabulário*): nomes e termos do canal (Matheus, João, Pedro, Bully, FamosoZora...), um por linha. O Whisper passa a escrever esses nomes certo, e o corretor deixa de marcá-los como erro. **Adicione nomes novos sempre que aparecerem**: jogos, amigos, apelidos.
2. **Retranscrição dos cortes:** com placa de vídeo, cada corte é transcrito de novo com o modelo mais preciso (`large-v3`) antes de gerar. Na primeira vez ele baixa o modelo, uns 3 GB.
3. **Legenda corrigida pelo Claude:** o Claude escreve o texto certo de cada corte, e o gerador encaixa esse texto no tempo de cada palavra. Partes entre `[[ ]]` são as que o Claude não teve certeza: nelas vale o que o áudio diz, e no editor elas aparecem em amarelo.
4. **A sua revisão** no passo 4 da aba Shorts.

Correções que se repetem em todo vídeo vão em *Menu → Correções automáticas*, no formato `palavra errada = palavra certa`. O editor de legendas também oferece gravar ali as palavras que você corrigiu.

---

## 10. Músicas de fundo

- Já vêm duas trilhas *idle* (`idle_zora_01` e `idle_zora_02`) feitas do zero pelo Claude, **livres de direitos**.
- Para colocar as suas (`.mp3`, `.m4a`, `.wav`): *Menu → Músicas de fundo* e copie os arquivos para a pasta que abrir. Use só música que você pode usar, como a **Biblioteca de áudio do YouTube Studio**.
- Por padrão, cada Short usa uma música diferente.
- Pra desligar a música, troque `"musica"` para `"nenhuma"` no `config.json`.

---

## 11. Ajustes (`config.json`)

Abra em *Menu → Configurações* (Bloco de Notas). Salve e gere de novo.

**Shorts**

| Ajuste | O que faz | Padrão |
|---|---|---|
| `layout` | `camera`, `desfocado` (vídeo inteiro com fundo borrado) ou `recorte` | `camera` |
| `palavras_por_legenda` | Quantas palavras aparecem por vez | `3` |
| `tamanho_legenda` / `borda_legenda` | Tamanho da letra / grossura da borda | `96` / `4` |
| `posicao_legenda` | Distância da legenda até o pé da tela | `520` |
| `cor_por_falante` | `true` = cada pessoa que fala ganha uma cor. Quem fala mais fica branco | `true` |
| `cores_falantes` | Ordem das cores: `branco`, `ciano`, `rosa`, `verde`, `laranja`, `lilas`, `azul`, `vermelho` | as 5 primeiras |
| `sensibilidade_falantes` | Aumente se o app separar a mesma pessoa em duas cores; diminua se juntar pessoas diferentes | `0.9` |
| `usar_abertura` | Liga ou desliga a abertura estilo trailer | `true` |
| `transicao` / `duracao_transicao` | Como a abertura passa pro corte: `fade`, `fadeblack`, `smoothleft`, `nenhuma` / duração em segundos | `fade` / `0.45` |
| `mostrar_texto_gancho` / `duracao_gancho` | Texto branco do gancho no começo / quanto tempo fica na tela | `false` / `3.5` |
| `duracao_final` | Segundos do final com INSCREVA-SE (`0` desliga) | `3.5` |
| `final_linha_1/2/3` | Textos do final | `VÍDEO COMPLETO NO CANAL` / `INSCREVA-SE` / `youtube.com/famosozora` |
| `musica` | `aleatoria`, o nome de uma música ou `nenhuma` | `aleatoria` |
| `volume_musica` / `volume_musica_final` | Volume da música durante o corte / no final | `0.18` / `0.55` |
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
| `episodio_usar_abertura` / `episodio_fade_preto` | Liga a abertura do episódio / duração do fade para preto (s) | `true` / `0.35` |

---

## 12. Onde fica cada coisa

**Pasta de trabalho** (a que você escolheu). É descartável: só material de produção.

```
<pasta de trabalho>\
├─ videos\                     ← vídeos longos (juntados pelo Studio, se quiser)
└─ shorts\
   └─ <nome do vídeo>\
      ├─ transcricao_para_claude.txt, legenda_video_completo.srt
      ├─ cortes.json           ← escrito pelo Claude (Shorts)
      ├─ edicao.json           ← escrito pelo Claude (vídeo longo)
      ├─ legendas\             ← legenda original e revisada de cada Short
      ├─ prontos\              ← Shorts + textos_para_postar.txt
      └─ episodio\             ← episódio editado + textos_episodio.txt
```

**Configurações e músicas:** vêm junto com o programa (o vocabulário, as correções, a marcação da câmera e as trilhas do canal). O que você mudar pelo *Menu* fica neste PC, em `%LOCALAPPDATA%\FamosoZora Studio\configuracoes` e `\musicas`, e vale junto com o que veio no programa. Até a 1.2.0 elas ficavam na pasta de trabalho; na primeira abertura da 1.3.0 o Studio copia sozinho.

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
| A emenda do episódio cortou uma fala | Desmarque o corte na revisão, ou peça pro Claude mudar o tempo dele. Use **Ouvir emenda** pra conferir. |
| O episódio está demorando muito | Use **Gerar prévia** pra ver a estimativa. Pra ficar mais rápido, troque `episodio_preset` para `superfast` no `config.json`. |
| Quero mudar o começo ou o fim de um corte | Fale pro Claude, por exemplo: *"começa o corte 3 dois segundos antes"*. Depois gere de novo com **SIM**. |
| Apaguei sem querer ao limpar o projeto | Abra a **Lixeira** do Windows, clique com o botão direito no arquivo e em **Restaurar**. |
| O Buffer não deixa conectar o TikTok ou o Instagram | Mude a conta para Business ou profissional (seção 7). |

---

## 14. Usar em outro computador

- **Instalar:** no GitHub, em *Releases*, baixe o `FamosoZora-Studio-Setup-X.Y.Z.exe` e abra.
  - Se o Windows avisar que protegeu o computador: **Mais informações → Executar assim mesmo**.
- **Pasta de trabalho:** você escolhe na primeira vez. Para trocar: *Menu → Mudar pasta de trabalho*. Ela pode ser diferente em cada PC.
- **Placa NVIDIA:** o app pergunta na primeira vez. Também dá para fazer depois em *Menu → Ativar placa de vídeo NVIDIA*. Sem placa (no notebook, por exemplo), tudo funciona pelo processador, só mais devagar.
- **Vídeos e projetos não vão pro GitHub.** Para trabalhar num vídeo no outro computador, copie o vídeo para lá.
- **Para editar o código** no outro computador, siga a seção "Configurar em outro PC" do `README.md`.

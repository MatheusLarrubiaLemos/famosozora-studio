# Diagnóstico do FamosoZora Studio (Fase 0 da versão 1.4.0)

Feito em 15/11/2026, na branch `v1.4.0`, a partir da **1.3.0** (`app/versao.py` = `"1.3.0"`, confere com o plano).
Nesta fase **nada do código foi alterado**: só li o código e escrevi este relatório.

---

## 1. Cores por falante: como funciona hoje

| Peça | Onde | O que faz |
|---|---|---|
| Quem fala | `app/shorts/falantes.py` | Um "detector de vozes" (sherpa-onnx) roda **em cada corte separado** e devolve trechos `(início, fim, número)`. Cada palavra da legenda ganha `"s": 0`, `"s": 1`... (o número do falante). |
| Lista de cores | `config.json` → `"cores_falantes": ["branco","ciano","rosa","verde","laranja"]` | Nomes de cor. A tabela de nomes → cor fica em `app/shorts/legendas.py` (`CORES`). |
| Quem ganha qual cor | `legendas.py` → `cores_por_falante()` | Conta as palavras de cada falante **naquele Short**: quem fala mais fica com a 1ª cor (branco), o 2º com ciano etc. |
| Liga/desliga | `config.json` → `"cor_por_falante": true` | Desligado = não roda o detector e tudo sai branco. |

**Problemas que isso traz (e que a Fase 1 resolve):**

1. Se um amigo fala mais que você num Short, **ele** fica branco e você fica ciano.
2. O número do falante **não vale entre Shorts**: o `falante_0` do Short 1 pode ser o Pedro, e o `falante_0` do Short 2 pode ser você. O detector roda corte por corte e não "lembra" vozes.
3. A abertura (cold open), quando fica fora do corte, é detectada **separada**: o `falante_1` da abertura pode não ser o mesmo `falante_1` do corte.

## 2. Número de Shorts: onde está fixado

**Em nenhum lugar.** Procurei no pedido ao Claude (`app/interface/aba_shorts.py`, botão "2 Pedir cortes ao Claude"), no `config.json`, em `gerar_shorts.py` e nas `DIRETRIZES DO CANAL.md`: não há número fixo nem mínimo. Hoje o pedido simplesmente não fala em quantidade, e o Claude escolhe "uns quantos" por costume.

Então a Fase 2 é **acrescentar** a regra "só o que vale a pena (pode ser 0)" e o teto opcional; não tem número para tirar.

**Achado:** se o `cortes.json` vier com 0 cortes, hoje a lista de projetos diz *"Tudo postado! Pode limpar o projeto."* (errado) e o Gerar Shorts termina com "0 criado(s)". A Fase 2 troca isso pela mensagem "Nenhum trecho forte o bastante nesse vídeo".

## 3. Música: como entra hoje no ffmpeg

Arquivo: `app/shorts/montagem.py`.

| Item | Como está hoje |
|---|---|
| Escolha | `escolher_musica()`: `config.json` `"musica": "aleatoria"` (padrão), o nome de uma música, ou `"nenhuma"`. O corte também pode trazer `"musica"` no `cortes.json`. No modo aleatório, embaralha as músicas com o nome do projeto e usa uma por Short em sequência (**já não repete em Shorts seguidos** se houver mais de uma). |
| Onde procura | `listar_musicas()` em `nucleo/comum.py`: `musicas\` do programa + `%LOCALAPPDATA%\FamosoZora Studio\musicas` (app instalado). **Só a pasta raiz**, sem subpastas. |
| Loop | `-stream_loop -1` na entrada: repete a música **sem crossfade** (pode dar um "pulo" na emenda). |
| Corte | `atrim=0:<duração do Short>`. |
| Volume | `volume_musica` 0.18 durante o corte, sobe para `volume_musica_final` 0.55 no final (INSCREVA-SE), em 0.8 s. |
| Fade | entra em 1.0 s, sai em 1.2 s. |
| Ducking | **Já existe**: `sidechaincompress` (threshold 0.05, ratio 5, attack 20 ms, release 500 ms) usando a voz como "chave". |
| Mistura final | `amix` (sem normalizar) + `alimiter` 0.97 (evita estourar). |

## 4. O que deste plano a 1.3.0 já tem

| Item do plano | Situação na 1.3.0 | O que falta |
|---|---|---|
| Ducking com `sidechaincompress` | ✅ pronto | Só ajustar (ver risco 5). |
| Fade-in / fade-out da música | ✅ pronto | — |
| Volume baixo ajustável | ✅ global (`volume_musica`) | Volume **por Short** no editor. |
| Não repetir música em Shorts seguidos | ✅ no modo aleatório | Manter isso dentro de cada pasta de clima. |
| Loop da música | ⚠ repete, mas sem crossfade | Crossfade na emenda. |
| Música por corte no `cortes.json` | ✅ campo `"musica"` | Campo `"clima"` e subpastas. |
| Editor de legendas com Salvar / Desfazer / Voltar ao original / Renderizar só este Short / Ouvir trecho | ✅ pronto (`interface/editor_legendas.py`) | Painel Falantes e seção "Áudio e edição" entram **nessa mesma janela**. |
| Padrão "original + editado" por Short | ✅ `legendas\NN_original.json` + `NN_editada.json` | Mesmo padrão para música e efeitos. |
| Cores por falante | ⚠ por ordem de quem fala mais | Cadastro de pessoas, FamosoZora sempre branco. |
| Efeitos sonoros | ❌ não existe | Tudo. |
| Pasta de efeitos | ❌ não existe | Tudo. |
| `clima`, `motivo`, `nota` nos cortes | ❌ | Tudo. |
| Máximo de Shorts | ❌ | Tudo. |

## 5. Ajustes que proponho ao plano (por causa do código real)

### 5.1 Onde ficam `pessoas.json`, músicas e efeitos ⚠ (preciso da sua decisão)

O plano fala em `configuracoes\pessoas.json`, `shorts\musicas\` e `shorts\efeitos\` **na pasta de trabalho**. Mas desde a 1.3.0 a pasta de trabalho é **descartável** (dá para limpar depois de postar) e as configurações e músicas **saíram dela**:

- configurações: `app\padrao\` (GitHub) + `%LOCALAPPDATA%\FamosoZora Studio\configuracoes` (este PC);
- músicas: `musicas\` (GitHub) + `%LOCALAPPDATA%\FamosoZora Studio\musicas` (este PC);
- a antiga `shorts\musicas\` da pasta de trabalho só é lida uma vez, para copiar o que tinha.

**Proposta:** seguir o padrão da 1.3.0:

| Arquivo | Vem com o programa (GitHub) | Deste PC |
|---|---|---|
| `pessoas.json` | `app\padrao\pessoas.json` | `%LOCALAPPDATA%\FamosoZora Studio\configuracoes\pessoas.json` |
| Músicas por clima | `musicas\<clima>\` | `%LOCALAPPDATA%\FamosoZora Studio\musicas\<clima>\` |
| Efeitos | `efeitos\<categoria>\` | `%LOCALAPPDATA%\FamosoZora Studio\efeitos\<categoria>\` |

Assim, se você limpar a pasta de trabalho, não perde o cadastro de pessoas nem a biblioteca de sons. No modo desenvolvedor, como hoje, vale só a pasta do GitHub. **Não mexo na pasta `canal famosozora`.** (Se mesmo assim você quiser tudo na pasta de trabalho, me diga.)

### 5.2 Nome do arquivo `edicao.json` ⚠ (conflito)

Já existe um `edicao.json` na pasta do projeto: é o plano do **vídeo longo** (passo "Editar vídeo longo"). Um segundo arquivo com o mesmo nome ia confundir. **Proposta:** seguir o padrão das legendas, por Short:

```
<projeto>\edicao_shorts\01_sugestao.json   ← o que o Claude sugeriu, já com os arquivos escolhidos (não muda)
<projeto>\edicao_shorts\01_edicao.json     ← o que você mudou no editor (só existe se você mexeu)
```

"Restaurar sugestão do Claude" = apagar o `01_edicao.json` (igual ao "Voltar ao original" das legendas).

### 5.3 Quem fala: por Short, não por projeto

Como o número do falante não vale entre Shorts (item 1.2), o `falantes.json` do projeto guarda a ligação **por Short**:

```json
{ "versao": 1,
  "shorts": { "01": {"0": "FamosoZora", "1": "Pedro"},
              "02": {"0": "Pedro"} } }
```

Falante sem ligação = FamosoZora (branco). Para facilitar, quando você ligar uma voz a uma pessoa, o editor oferece "usar essa pessoa também nos outros Shorts onde ela aparecer"... **não** dá para fazer isso automaticamente (o detector não reconhece a voz entre cortes), então fica manual e rápido: uma lista por Short.

**Troca de falante numa linha:** o plano sugere `"falantes_linha": {"7": "Pedro"}` (pelo número da linha). O problema: o número da linha muda quando você edita o texto (as linhas se refazem). **Proposta:** gravar a pessoa **na própria palavra** da legenda editada (`"pessoa": "Pedro"` em cada palavra daquela linha, no `NN_editada.json`). Fica firme mesmo editando o texto, e "Voltar ao original" desfaz.

### 5.4 Abertura (cold open) e falantes

Quando a abertura está fora do corte, ela é detectada à parte e seus números de falante podem colidir com os do corte. **Proposta:** os falantes da abertura ganham números próprios (`a0`, `a1`...) para aparecerem separados no painel, em vez de se misturarem.

## 6. Formato novo do `cortes.json` (versão 3)

Hoje ele aceita dois formatos: uma lista `[...]` (versão 1) ou `{"versao": 2, "cortes": [...], "correcoes": {...}}` (versão 2, a que os testes da 1.3.0 usam). Por isso o formato novo é a **versão 3**.

```json
{
  "versao": 3,
  "cortes": [
    {
      "titulo": "...", "inicio": "00:12:03", "fim": "00:12:48",
      "abertura": {"inicio": "...", "fim": "..."},
      "legenda": "...", "descricao": "...", "hashtags": [...],
      "clima": "engracado",
      "motivo": "Ele erra o pulo três vezes e xinga o jogo.",
      "nota": 8,
      "sons": [
        {"tempo": "00:12:15.4", "categoria": "impacto", "motivo": "tomou o soco"},
        {"tempo": "00:12:40.0", "tipo": "musica", "clima": "epico", "motivo": "virada"}
      ]
    }
  ],
  "correcoes": {}
}
```

- `tempo` dos sons no **tempo do vídeo original** (igual a `inicio`/`fim`, que é como o Claude lê a transcrição). O app converte para o tempo do Short; no editor você vê o tempo do Short.
- Todos os campos novos são **opcionais**: sem `clima` → pasta `geral\`; sem `nota` → 5; sem `sons` → sem efeitos.
- **Migração automática:** ao abrir um `cortes.json` antigo, o app guarda `cortes.bak.json` e grava a versão 3 (põe `"versao": 3` e transforma a lista solta em `{"cortes": [...]}`). Os campos que já existiam não mudam. Shorts já gerados continuam valendo.
- **Ordem por nota:** a lista do editor mostra os Shorts ordenados pela nota, mas os **números dos arquivos não mudam** (o `01`, `02`... continua sendo a posição no `cortes.json`), para não quebrar legendas já revisadas.
- **Máximo de Shorts:** se o Claude mandar mais que o teto, o app gera os de nota mais alta e avisa quantos ficaram de fora.

## 7. Formato do `NN_edicao.json` (por Short)

```json
{
  "versao": 1,
  "corte": {"inicio": 723.0, "fim": 768.0},
  "musica": {"ligada": true, "arquivo": "epico/tema1.mp3", "volume": 0.18},
  "trocas_musica": [{"tempo": 30.1, "arquivo": "epico/virada.mp3"}],
  "efeitos_ligados": true,
  "efeitos": [
    {"tempo": 12.4, "categoria": "impacto", "arquivo": "impacto/soco.wav", "volume": 0.8, "motivo": "tomou o soco"}
  ],
  "mostrar_nome_falante": false
}
```

- `arquivo` é sempre relativo à pasta de músicas/efeitos (funciona em outro PC).
- `corte` guarda o início e fim: se você pedir cortes novos ao Claude e o Short 03 virar outro trecho, o app percebe e **ignora** a edição antiga (em vez de pôr efeitos no lugar errado).
- `tempo` aqui é o **tempo do Short** (o que você vê ao assistir).
- Arquivo que sumiu da pasta → aviso no editor e o Short sai sem aquele som (não dá erro).

## 8. Riscos

| # | Risco | Tamanho | Como lidar |
|---|---|---|---|
| 1 | **Tempo de render a mais** com a mixagem. | Pequeno | Áudio é muito leve perto do vídeo. Estimo **+1 a 3 s por Short** com 3 efeitos + crossfade. Vou medir na Fase 6. |
| 2 | **Ouvir prévia** ("ouvir o trecho com o efeito") precisa montar o áudio. | Pequeno | Prévia só de áudio, ~5 s em volta do efeito, sem refazer o vídeo: fica pronta em ~1 s. |
| 3 | Detector de vozes erra (junta duas pessoas ou separa uma em duas). | Médio | Por isso a troca de falante por linha e o ▶ amostra. |
| 4 | Música curta com crossfade no loop em músicas muito curtas (< 4 s). | Pequeno | Sem crossfade nesses casos (só repete). |
| 5 | Efeito alto em cima da voz. O ducking atual abaixa só a **música**, não os efeitos. | Médio | Efeitos com volume próprio e limite (`alimiter`); a regra "não cobrir a fala" vai no pedido ao Claude, e o editor avisa se o efeito cair em cima de uma fala. |
| 6 | Claude inventar categoria que não existe na pasta. | Pequeno | O pedido manda só as categorias que **têm arquivo**; categoria desconhecida é ignorada com aviso. |
| 7 | Arquivos de áudio com formato estranho (mono, 44.1 kHz, 8 bits). | Pequeno | Tudo passa por `aresample=48000` + estéreo antes de misturar (já é assim com a música). |
| 8 | **Contraste da cor**: cor escura some com a borda preta. | Pequeno | Calcular o brilho da cor: abaixo do limite, aviso "difícil de ler" no editor. |
| 9 | `build/montar_app.ps1` copia `musicas\*` **sem** `-Recurse`: as subpastas de clima iriam vazias para o app instalado. | **Alto se esquecer** | Corrigir na Fase 7 (copiar `musicas\` e `efeitos\` inteiras). |
| 10 | Testes na sua máquina: aqui no ambiente do Claude não tem placa NVIDIA (bom: testa o caminho do processador), mas **também não tem a janela (tkinter)** para testar a interface clicando. | Médio | Testo a lógica do editor sem janela e o render de ponta a ponta aqui; o teste **de ouvido** e o teste no notebook ficam com você, com um roteiro curto que eu escrevo. |
| 11 | Shorts antigos (gerados antes da 1.4.0) não têm `NN_sugestao.json`. | Pequeno | Ao abrir no editor, o app monta a sugestão a partir do `cortes.json` na hora. |

## 9. Ordem de trabalho (sem mudança no plano)

Fase 1 Falantes → Fase 2 Cortes sem número → Fase 3 Música por clima → Fase 4 Efeitos → Fase 5 Editor → Fase 6 Testes → Fase 7 Fechamento. Um commit por fase.

## 10. O que preciso que você aprove

1. **Local dos arquivos** (item 5.1): `pessoas.json`, músicas e efeitos no padrão da 1.3.0 (programa + `%LOCALAPPDATA%`), e **não** na pasta de trabalho.
2. **Nome do arquivo de edição** (item 5.2): `edicao_shorts\NN_edicao.json` em vez de `edicao.json` (que já é do vídeo longo).
3. **Falantes por Short** e troca de falante gravada na palavra (item 5.3).
4. Formatos dos itens 6 e 7.

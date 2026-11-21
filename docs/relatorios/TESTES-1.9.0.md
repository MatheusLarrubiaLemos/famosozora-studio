# Testes da versão 1.9.0 (Auto-Edit + editor de vídeo embutido)

Feitos no ambiente de desenvolvimento: **Linux, sem placa NVIDIA, 4 núcleos** (parecido com o notebook), com as
telas numa tela virtual (`xvfb-run`). O que só dá para conferir no seu PC está marcado como **"conferir no PC"**.

## Resultado por função

| Função | Funcionou? | Observação |
|---|---|---|
| Versão leve (proxy 540p, quadro-chave 0,5 s) | sim | x264 sem placa; com NVIDIA usa NVENC (conferir no PC) |
| Som: volume, onda, fala | sim | o VAD do faster-whisper entra quando a biblioteca existe (no app, sempre) |
| Imagem só na área do jogo (câmera de fora) | sim | na amostra, a câmera mexendo não virou "ação"; sem marcar a câmera, virou (teste mostra a diferença) |
| Tela congelada, tela preta, trocas de cena | sim | amostra: 3 trocas certas, preto e congelado nos lugares certos |
| Claude olhando as cenas (mosaicos) | sim, com Claude de mentira | **conferir no PC** se o `claude -p --tools Read` lê os mosaicos com a sua conta |
| Claude lendo a conversa (papo fora, introdução) | sim, com Claude de mentira | idem |
| Decidir os cortes (regras da predefinição) | sim | margens, mínimo, juntar, nunca cortar palavra, ímã na troca de cena, acelerar |
| Mesma entrada + mesma predefinição = mesmo resultado | sim | teste compara o JSON inteiro |
| Mudar a predefinição sem analisar de novo | sim | `sugerir()` usa os sinais guardados (instantâneo) |
| Analisar de novo mantendo os cortes manuais | sim | |
| Desfazer / refazer sem limite | sim | |
| edicao.json v2 → v3 com cópia `.bak.json` | sim | Pedir de novo ao Claude não apaga os trechos |
| Capítulos recalculados depois dos cortes e acelerações | sim | |
| Introdução protegida (pede confirmação) | sim | |
| Episódio com corte e trecho acelerado (ffmpeg de verdade) | sim | duração e áudio batem com a conta |
| Episódio: continuar de onde parou | sim | só refaz os trechos que faltam |
| Short com pedaço cortado por dentro (ffmpeg de verdade) | sim | 10 s − 3 s = 7 s |
| Legenda do Short acompanhando os cortes | sim | palavras do pedaço cortado somem; cor por falante vai junto |
| Editor: abrir, player mpv embutido, 4x, prévia do resultado | sim (Linux) | na prévia em 4x, pulou o corte de 30 s a 110 s sozinho. **Conferir no PC (Windows)** |
| Editor: prévia vertical do Short | sim (Linux) | câmera em cima, jogo embaixo |
| Editor: atalhos (I/O/X, C, R, J/K/L, N/Enter/Backspace, Ctrl+Z...) | sim | teste tecla a tecla |
| Editor: salva sozinho em até 1 s; `edicao.anterior.json` | sim | |
| Editor sem o player (sem `libmpv-2.dll`) | sim | mostra as miniaturas e avisa |
| Editor numa tela de 1366x768 | sim | a janela se ajusta ao tamanho da tela |
| Analisar várias lives de uma vez | sim (tela) | usa o mesmo jeito escondido do lote |
| Configurações → Cortes automáticos (salvar, erro, voltar ao padrão) | sim | |
| Exportar XML (Premiere/DaVinci) e um arquivo por trecho | sim | abrir o XML no Premiere/DaVinci: **conferir no PC** |
| Descrição padrão do canal (issues #7 e #8) | sim | |
| Instalador com `autoedit`, `editor`, `python-mpv` e `libmpv-2.dll` | **conferir no GitHub Actions** | só roda no Windows |
| Testes antigos | sim | `test_lote_de_3_videos_de_ponta_a_ponta` e `test_publicacao_seleciona_varios_de_uma_vez` já falhavam **antes** desta versão neste ambiente Linux (não mudaram) |

Totais aqui: **198 testes rápidos passam**; nos lentos (telas e ffmpeg), passam todos, menos os 2 que já falhavam antes.

## Tempo da análise

Medido num vídeo de **10 min, 1080p, 60 fps** (gerado com o ffmpeg), **sem placa NVIDIA, 4 núcleos** (como o notebook):

| Etapa | 10 min | 3 h (estimado, ×18) |
|---|---|---|
| 1. Versão leve (proxy, x264) | 1 min 55 s | ~34 min |
| 2. Som (volume, onda) | 2 s | ~45 s |
| 3. Imagem (movimento, congelado, preto, trocas) | 10 s | ~3 min |
| 4. Miniaturas da timeline | 4 s | ~1 min |
| **Total sem o Claude** | **~2 min 10 s** | **~39 min** |
| 5 e 6. Claude (cenas + conversa) | — | ~25 s por mosaico em dúvida + a leitura da conversa (estimado; conferir no PC) |

- A parte mais pesada é a **versão leve**: ela lê a live inteira em 1080p. **No PC de mesa (NVENC)** deve ficar várias
  vezes mais rápida (conferir no PC). As outras etapas leem a versão leve, por isso são rápidas.
- É uma vez só por live: depois tudo fica em `analise\`, e mudar a predefinição é instantâneo.
- Um vídeo real com mais movimento e áudio de verdade pode demorar um pouco mais que a amostra.


## Teste manual guiado com você (falta)
1. Abra uma live real em **Editar** → **Analisar a live** (20 min de live servem). Anote o tempo de cada etapa (aparece no
   fim e fica em `analise\analise.json`).
2. Assista em **Prévia do resultado** em 4x. Confira se a voz está entendível e se os pulos estão certos.
3. Aceite e recuse algumas sugestões, corte uma parte com I/O/X e gere o episódio.
4. Num Short: **✂ Ajustar corte**, corte um respiro, **Renderizar este Short** e confira se a legenda acompanhou.
5. Repita o passo 1 no notebook (sem NVIDIA) e com a janela em 1366x768.

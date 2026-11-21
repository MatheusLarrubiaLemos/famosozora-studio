# Diagnóstico para a versão 1.9.0 (Auto-Edit + editor de vídeo embutido)

Este documento é a **Fase 0** do megaplano. O plano foi escrito para a "1.7.0", mas o Studio já estava na **1.8.0**
quando o trabalho começou. Por isso a versão nova se chama **1.9.0** (o dono aprovou).

## 1. Biblioteca de interface e player de vídeo

- A tela é **Tkinter** (vem junto com o Python; o app instalado leva o Python inteiro). Não é PySide6.
- **Escolha: mpv (opção A)**, pela biblioteca `python-mpv` (arquivo único, `mpv.py`), que carrega o `libmpv-2.dll`.
  - Funciona dentro de uma janela Tkinter: o mpv recebe o "número da janela" (`wid = quadro.winfo_id()`) e desenha
    dentro dela. Não precisa trocar de biblioteca de interface.
  - Velocidade até 4x com a voz normal (sem voz de esquilo): o filtro `scaletempo2` do mpv já vem ligado.
  - Pula para qualquer ponto rápido (com o proxy, Fase 1A).
  - Também mostra a **prévia vertical** do Short (câmera em cima, jogo embaixo) com o mesmo filtro do render.
- **Opção B (QMediaPlayer do PySide6): descartada.** Exigiria refazer a tela inteira em outra biblioteca (umas 8.000
  linhas de tela), além de somar uns 150 MB ao instalador.
- **Precisa entrar no build:** `python-mpv` (no `requirements.txt`) e o `libmpv-2.dll` (~100 MB, da compilação de
  shinchiro no GitHub, a mesma usada pela maioria dos players de Windows). O `build/montar_app.ps1` baixa e coloca em
  `bin\`. O `build/preparar_dev.ps1` faz o mesmo no modo desenvolvedor.
- **Sem o `libmpv-2.dll`** (por exemplo, se o download falhar), o editor abre do mesmo jeito: em vez do vídeo, mostra
  a miniatura do ponto atual. Dá para cortar, mas não para assistir. Ele avisa isso.
- **Migrar de biblioteca: não precisa.**

## 2. Como está hoje (o que o Auto-Edit reaproveita)

| Item | Situação |
|---|---|
| Transcrição | `transcricao.json` com tempo **por palavra** (`{i, f, p}`). O Whisper já passa pelo VAD Silero (do faster-whisper) antes de transcrever. |
| `camera_area` | Fica no `config.json` (**uma só para o canal**), junto com `gameplay_area` (opcional). Desde a 1.9.0, um projeto pode ter a sua (`camera_area`/`gameplay_area` no `projeto.json`); sem ela, vale a do canal. |
| Juntar vídeos | `videos_longos/juntar_videos_gui.ps1` (sem mudança). |
| Outro padrão | `videos_longos/outro.py`: entra no último trecho com transição. Já funciona. |
| Introdução de episódio (6B da v1.5.0) | **Não existia.** Entra na 1.9.0: o Claude acha a introdução lendo a conversa, e o editor protege. |
| `edicao_longo.json` | **Nunca existiu.** O que existe é o `edicao.json` **versão 2** (o Claude marca `remover`, `manter`, `capitulos`, título...). A 1.9.0 passa para a **versão 3** (junta os campos do plano: `trechos`, `marcadores`, `introducao`, `predefinicao`...), com migração automática e cópia `edicao.bak.json`. |
| Cortes de pausa da 1.8.0 | `videos_longos/pausas.py`. **O Auto-Edit absorve:** quando a live foi analisada, valem as sugestões do Auto-Edit (silêncio, sem jogo, sem ação), e o corte de pausas antigo fica desligado para não cortar duas vezes. Live não analisada continua como na 1.8.0. |
| Revisão do vídeo longo | `interface/janela_edicao.py`, só com a lista dos cortes do Claude, sem vídeo. Continua existindo. O editor novo é o botão **"Editar"**. |
| Render do episódio | `videos_longos/editar_episodio.py` já corta do **original**, com corte exato (recodifica), fades e 2 trechos ao mesmo tempo. A 1.9.0 acrescenta: **continuar de onde parou**, acelerar trechos, crossfade da predefinição e "exportar para outro editor". |
| Editor de Shorts | `interface/editor_legendas.py` (legenda, falantes, áudio). Legendas: palavras no tempo do vídeo original, convertidas para o tempo do Short (`legendas.relativas`). A 1.9.0 acrescenta "Ajustar corte" e a conversão "tempo original → tempo final" quando o Short tem cortes dentro dele. |

## 3. Como o app chama o Claude

- **`claude -p`** (Claude Code do PC, com a sua assinatura), não a API: `nucleo/claude_local.py`, com o pedido pela
  entrada do programa, sem ferramentas (`--tools ""`).
- **Imagens (Fase 1D):** num pedido não interativo o Claude Code só lê arquivo se tiver a ferramenta `Read`. O
  Studio passa a chamar, só para as cenas, `--tools Read --allowedTools Read --add-dir <pasta dos mosaicos>`, e o
  Claude lê os `.jpg` dos mosaicos (a ferramenta Read do Claude Code aceita PNG/JPG). **Ainda falta confirmar no seu
  PC:** este ambiente de desenvolvimento não tem a sua conta. Se não funcionar, a análise roda sem essa etapa e avisa.
- Custo: é a sua assinatura, sem cobrança por uso. O Studio mostra a estimativa de tempo antes.

## 4. Licenças das bibliotecas novas

| Biblioteca | Licença | Observação |
|---|---|---|
| `python-mpv` | GPL-2.0+ ou LGPL-2.1+ (à escolha) | Um arquivo só. |
| `libmpv-2.dll` (mpv) | GPL (compilação com tudo ligado) | O código do Studio é público no GitHub, então distribuir junto não tem problema. |
| VAD | O Silero VAD **atual é MIT** (as versões antigas eram CC BY-NC). | **Não entra biblioteca nova:** o faster-whisper (MIT) já traz o Silero VAD em ONNX, e o Studio usa esse para reforçar a fala. |
| PySceneDetect | BSD-3, mas precisa do OpenCV (~90 MB) | **Não usado.** As trocas de cena são medidas pela mesma leitura da imagem que mede o movimento (diferença entre quadros), sem mais uma passada no vídeo. Dá o mesmo resultado prático e o instalador não engorda. |
| `freezedetect` do ffmpeg | já vem no ffmpeg | A "tela congelada" é calculada na mesma passada do movimento (é o mesmo cálculo que o `freezedetect` faz). |

## 5. Velocidade (medida)

Medido numa amostra gerada com o ffmpeg (este ambiente é Linux, **sem placa NVIDIA**, parecido com o notebook):

| Etapa | 10 min de vídeo 1080p | 3 h (estimado) |
|---|---|---|
| Som (volume + onda) | ver tabela no fim (Fase 7) | |
| Imagem (movimento, congelado, preto, trocas) | ver tabela no fim (Fase 7) | |
| Proxy 540p (x264 veryfast) | ver tabela no fim (Fase 7) | |
| Miniaturas da timeline | ver tabela no fim (Fase 7) | |

Os números reais estão no relatório final (`docs/relatorios/TESTES-1.9.0.md`). **No PC de mesa** o proxy usa NVENC e
fica bem mais rápido. A conta é feita uma vez só por live: depois tudo fica guardado em `<projeto>\analise\`.

**Teste no seu PC:** abra uma live, clique em **Editar** → "Analisar a live". A janela mostra quanto tempo cada etapa
levou, e o `studio.log` registra.

## 6. Riscos e ordem

1. **Player embutido no Windows** (maior risco): o mpv dentro do Tkinter funciona no Windows, mas só dá para
   conferir no seu PC. Mitigação: o editor funciona sem o mpv (miniaturas) e o erro vai para o log.
2. **`libmpv-2.dll` no build:** é um download a mais no GitHub Actions. Se falhar, o build avisa e o app sai sem o
   player (não quebra o resto).
3. **Claude lendo imagens:** depende do Claude Code do PC. Mitigação: etapa opcional, com aviso.
4. **Lives de 3 h:** o proxy e as medidas leem o vídeo inteiro uma vez (alguns minutos). Tudo fica em cache e é
   retomado se o app fechar.
5. **Ordem seguida:** motor de análise e regras (testáveis sem tela) → formato `edicao.json` v3 → editor → vídeo
   longo → Shorts → exportar → testes → documentação.

# Testes da versão 1.6.0 (gerar Shorts de vários vídeos de uma vez)

Rodados em 17/11/2026, num Linux **sem placa NVIDIA** (como o notebook), com a tela virtual em **1366×768**:

```
python -m pytest -m "lento or not lento"
166 passaram, 1 pulado (test_do_video_ao_short_revisado: usa a voz e a Lixeira do Windows, só roda no Windows)
```

- O **Claude** foi sempre **falso** nos testes (respostas prontas): nenhum pedido foi para a sua assinatura.
- O **Whisper** de verdade não pôde ser baixado aqui (o servidor do modelo está bloqueado neste ambiente). O teste de
  ponta a ponta usa o Whisper de verdade quando consegue baixar o modelo (no seu PC) e, se não conseguir, faz uma
  transcrição falsa. **Todo o resto rodou de verdade**: ffmpeg, geração dos Shorts, Lixeira, `lote.json`, cancelar.
- **Nada foi publicado.**

## Tabela de resultados

| Função | Funcionou? | Observação |
|---|---|---|
| Clique simples seleciona só um | sim | teste de regra e teste clicando na lista de verdade. |
| `Ctrl` + clique (um a um) | sim | marca e desmarca sem tirar os outros. |
| `Shift` + clique (intervalo) | sim | para cima e para baixo; a "âncora" fica no primeiro clique. `Ctrl` + `Shift` soma o intervalo. |
| Caixinha em cada linha | sim | marca/desmarca só aquele vídeo; duplo clique nela não dispara o próximo passo. |
| Selecionar todos / Limpar seleção / caixinha do cabeçalho | sim | depois do "Limpar", a lista não volta a marcar o primeiro sozinha. |
| Contador "3 vídeos selecionados" | sim | 0, 1 e vários. |
| Coluna "Etapa" | sim | não transcrito · transcrito · com cortes · com Shorts. |
| Botão laranja "Gerar Shorts dos selecionados (N)" | sim | aparece com 2 ou mais; com 1, o botão continua o de sempre. |
| Preparar lote: o que vai ser feito em cada vídeo | sim | "transcrever → cortes com o Claude → gerar Shorts", "cortes com o Claude → gerar Shorts" ou "(pulado)". |
| Preparar lote: Pular / Gerar de novo / aplicar a todos | sim | quem já tem Shorts começa como Pular. |
| Preparar lote: ordem (Subir/Descer e arrastar) | sim | Subir/Descer testados por teste; arrastar com o mouse **precisa ser conferido no seu PC** (ver abaixo). |
| Preparar lote: avisos | sim | sem NVIDIA (apareceu aqui), câmera marcada/não marcada, sem Claude Code (Começar desligado). |
| Montagem do lote na ordem escolhida | sim | |
| Cada vídeo no seu projeto (nada se mistura) | sim | cada um com a sua pasta, o seu `cortes.json` e os seus Shorts; o vídeo que já tinha cortes manteve os dele. |
| Pular vídeo com erro e seguir | sim | o erro fica guardado e aparece em português. |
| "Tentar de novo só este" | sim | só o vídeo com erro roda de novo, e só a etapa que faltava. |
| Gerar de novo → Lixeira | sim | os Shorts antigos foram para a Lixeira (de verdade no ponta a ponta); se a Lixeira falhar, o vídeo fica com erro e nada é apagado. |
| Pausar e Continuar | sim | pausa entre uma etapa e outra. |
| Cancelar no meio sem arquivo quebrado | sim | **de verdade**: cancelado no meio da geração de um Short, não sobrou `_gerando_...` nem `temp_legenda_...`, e os Shorts que já estavam prontos abrem inteiros no ffmpeg. |
| Cancelar para o processo na hora | sim | um processo de 30 s parou em menos de 1 s (inclusive os que ele abriu, como o ffmpeg). |
| Salvar e retomar o `lote.json` | sim | app fechado no meio: o vídeo que estava pela metade volta para a fila e o que estava pronto não é refeito. |
| Fechar o Studio com lote rodando | sim | pergunta antes, para a etapa atual direitinho e, ao abrir, pergunta "Continuar o lote de onde parou?". |
| Responder "não" para continuar | sim | o lote fica como cancelado e não pergunta de novo. |
| Não deixar dois lotes ao mesmo tempo | sim | |
| Migração do `lote.json` antigo | sim | formato sem versão vira versão 1, com cópia em `lote.bak.json`. |
| Vídeo sem nenhum corte bom | sim | fica "pronto" com 0 Shorts e o aviso "O Claude não achou nenhum corte bom". |
| Erros técnicos em português | sim | ex.: "403 Forbidden" vira "Não consegui baixar o modelo do Whisper (sem internet?)...". |
| Tempo estimado | sim | "calculando o tempo que falta..." no começo, depois "falta ~10 min". |
| Resumo no fim | sim | "Lote pronto: 2 Shorts de 2 vídeo(s)", tempo, erros; o primeiro com erro já vem selecionado. |
| Revisar (abre o editor de Shorts do projeto) | sim | |
| Notificação no canto | sim | "Lote pronto: 14 Shorts de 3 vídeos", mesmo com a tela do lote fechada. |
| **Ponta a ponta: 3 vídeos de 20 s** | sim | vídeo sem transcrição, vídeo sem cortes e vídeo que já tinha Shorts ("Gerar de novo"), sem área da câmera marcada (saiu com o fundo desfocado), sem NVIDIA (codificou no processador). 1 min 30 s ao todo. |
| Telas em 1366×768 | sim | Shorts, Preparar lote e tela do lote cabem (teste automático e prints conferidos por mim). |
| Notebook sem NVIDIA | sim | o ambiente de teste não tem NVIDIA: aviso aparece e tudo roda no processador. |
| Testes antigos (1.3.0 a 1.5.1) | sim | todos continuam passando. |

## Problemas que os testes acharam (e já foram consertados)

1. **A tela Shorts ficou larga demais para 1366×768** com a coluna nova: as colunas foram estreitadas.
2. **Transcrição repetida à toa:** um projeto com transcrição mas sem o arquivo de texto para o Claude seria transcrito
   de novo mesmo já tendo cortes. Agora só transcreve se ainda for pedir os cortes.
3. **Mensagem técnica:** "A transcrição falhou. 403 Forbidden" virou uma explicação do que fazer.
4. **A tela podia travar por alguns segundos:** a memória de uma janela já fechada às vezes era limpa pela linha do lote
   e o tkinter reclamava. Agora, enquanto o lote roda, essa limpeza é feita pela linha da tela.

## Para conferir no seu PC (eu não consigo daqui)

1. **Arrastar para mudar a ordem** na janela Preparar lote (com o mouse de verdade).
2. **Um lote real** com 2 vídeos curtos: o Whisper de verdade (com a placa de vídeo no PC de mesa) e o Claude de verdade.
3. **No notebook:** o aviso "o lote vai demorar mais" aparece e o lote termina.
4. **Fechar o Studio no meio** de um lote e abrir de novo: deve perguntar "Continuar o lote de onde parou?".
5. **Rodar os testes no Windows** (no modo desenvolvedor): `python -m pytest -m "lento or not lento"`.

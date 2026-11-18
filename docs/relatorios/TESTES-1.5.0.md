# Testes da versão 1.5.0

Rodados em 16/11/2026, num Linux sem placa NVIDIA (como o notebook), com a tela virtual em **1366×768**:

```
python -m pytest -m "lento or not lento"
127 passaram, 1 pulado (test_do_video_ao_short_revisado: usa a voz e a Lixeira do Windows, só roda no Windows)
```

Além disso, **81 botões** das telas foram apertados um por um pelo teste de telas, e **nenhum deu erro**.

Nada foi publicado nos testes: o Claude Code, o Cowork e o navegador foram trocados por versões **falsas** que só anotam o que fariam.

## Tabela de resultados

| Função | Funcionou? | Observação |
|---|---|---|
| Próximo dia livre às 12:00 de Brasília | sim | 7 casos: nada agendado, faltando menos de 1 h para o meio-dia, depois do meio-dia, dias seguidos, depois do último agendado, agendamento antigo, virada de ano. |
| Vários Shorts, um por dia | sim | 3 Shorts → 3 dias seguidos; a revisão não deixa 2 Shorts no mesmo dia. |
| Fila de publicação: situações | sim | na fila → com o Claude → agendado (com link) → no ar; erro do Claude; sem resposta em 12 h vira erro. |
| Fila: retomada depois de fechar o app | sim | a fila é lida de novo do arquivo e continua igual; gravação segura (arquivo temporário + troca). |
| Fila: migração e arquivo estragado | sim | formato sem versão vira versão 1 com `.bak.json`; arquivo quebrado vira `.estragado.json` e a fila recomeça. |
| Pacote de postagem | sim | vídeo (ligado ou copiado), `dados.txt`, `dados.json` e o pedido com "AGENDAR", "NUNCA publique" e `resultado.json`. |
| Revisão antes de publicar | sim | título de 120 caracteres é barrado; com título certo vai para a fila e o "Claude Code" (falso) recebe `--chrome`. |
| Claude Code x Cowork | sim | Automático escolhe o Claude Code se ele existir; senão copia o pedido e abre o Claude; Claude Code escolhido e não instalado = erro em português. |
| O Studio sabe quando o Claude terminou | sim | `resultado.json` no pacote → "agendado" e o Short fica marcado como publicado no projeto. |
| Publicar o vídeo longo | sim | descrição já com os capítulos (0:00, 1:15, 1:02:05) e as tags. |
| Excluir: o que cada opção leva | sim | só Shorts / só episódio / projeto inteiro / projeto + vídeo original. |
| Excluir vai para a Lixeira | sim | se a Lixeira falhar, o arquivo **fica** (nada é apagado de vez). |
| Excluir vários (Ctrl+clique) | sim | 2 projetos de uma vez, pelo botão direito. |
| Excluir um Short | sim | vai para a Lixeira, sai da publicação e o corte não volta no "Gerar Shorts". |
| Editor: duplo clique no texto | sim | Enter grava, Esc cancela. |
| Editor: mudar o tempo | sim | tempo que invade a linha vizinha é recusado com aviso. |
| Editor: inserir e excluir linha | sim | a linha nova fica separada; Ctrl+Z traz de volta a excluída. |
| Editor: botão direito, atalhos e menus | sim | todos os itens do menu da linha, da caixa, do Short, da música e dos efeitos; F2 abre a edição. |
| Claude sem janela (`claude -p`) | sim | testado com um programa falso: resposta certa, erro do Claude e **Cancelar** (fecha na hora). |
| Tentar de novo até 3 vezes | sim | 2 falhas e acerta na 3ª; 3 falhas = aviso "Tentei 3 vezes". |
| JSON quebrado: pede de novo uma vez | sim | na 2ª vez quebrada, avisa e não muda nada. |
| Live dividida em partes | sim | nenhuma fala perdida nem repetida; cortes repetidos na emenda ficam com a maior nota; vídeo longo pede o resumo no fim. |
| Gerar cortes / editar com um clique (tela) | sim | salva `cortes.json` e `edicao.json`, guarda o anterior; sem Claude Code cai no copiar e colar. |
| `edicao.json` versão 2 e migração | sim | formato antigo vira o novo com `edicao.bak.json`; o gancho sai. |
| Emendas com transição, sem gancho | sim | fade só nas emendas; trecho muito curto sem fade; 0 desliga. |
| **Outro com resolução, FPS e áudio diferentes** | sim | ponta a ponta com ffmpeg: vídeo 1280×720/30 fps + outro 640×360/25 fps **sem áudio** → episódio 1280×720/30 fps, áudio até o fim, duração certa (20 − 4 + 6 − 0,6 s), laranja do outro no último segundo, capítulos dentro do `.mp4`. |
| Outro desligado / pasta vazia | sim | episódio sem outro e o aviso aparece. |
| Tela de 1366×768 | sim | todas as telas e janelas cabem (descontando a barra de tarefas). Precisou compactar a tela de Shorts e o editor. |
| Sem placa NVIDIA | sim | tudo rodou no processador. |
| Testes antigos (1.3.0 e 1.4.0) | sim | continuam passando. |

## Teste manual guiado (para fazer no Windows, comigo)

O que os testes automáticos **não** conseguem fazer, porque precisam do seu PC de verdade:

1. **Abrir o Studio:** confira se abre maximizado, se a barra lateral aparece e se o F11 funciona.
2. **Arrastar um vídeo curto** para a janela: tem que abrir a janela preta da transcrição.
3. **Configurações → Claude → Testar:** tem que aparecer `✓ Claude Code: ...`.
4. **Gerar cortes com o Claude** num vídeo curto: acompanhe a barra; confira se o `cortes.json` apareceu.
5. **Publicar 1 Short de teste:** na revisão, troque a data para daqui a **uma semana** e o título para "TESTE - apagar". Confirme.
   - Acompanhe o Claude Code agendando no YouTube Studio.
   - Confira na tela **Publicação** se aparece "✓ agendado" com o link.
   - **Apague o vídeo no YouTube Studio** e, no Studio, botão direito → **Tirar da fila**.
6. **Outro:** coloque um `outro.mp4` de 10 s na pasta `outro\` e gere a **prévia** e depois o episódio de um vídeo curto.
7. **Excluir** um projeto de teste com "Só os Shorts gerados" e confira na **Lixeira**.

Se algo der errado, tire um print e me mande junto com o `studio.log` (`%LOCALAPPDATA%\FamosoZora Studio\logs\studio.log`).

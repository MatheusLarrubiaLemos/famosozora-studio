# Testes da versão 1.4.0 (Fase 6)

Feitos em 16/11/2026, num computador **sem placa de vídeo NVIDIA** (Linux, tudo no processador, como no notebook).

**Resultado: 83 testes passaram, 0 falharam.** 1 foi pulado: o de ponta a ponta da 1.3.0, que usa a voz e a Lixeira do Windows e só roda no Windows.

Como rodar (na pasta do repositório):

| Comando | O que roda | Tempo |
|---|---|---|
| `python -m pytest` | testes rápidos | ~1 s |
| `python -m pytest -m lento` | telas (botão por botão) e ponta a ponta | ~2 min |

## Tabela de resultados

| Função | Funcionou? | Observação |
|---|---|---|
| **Fase 1: falantes** | | |
| Cadastro padrão (`pessoas.json`) só com FamosoZora branco | sim | `test_cadastro_padrao_tem_so_o_famosozora_branco` |
| Falante sem nome = FamosoZora (branco) | sim | Também quando o detector de vozes está desligado. |
| Voz ligada a uma pessoa e troca de quem fala na linha | sim | Pessoa excluída volta para a padrão. |
| Pessoa padrão não pode ser excluída; dá para escolher outra padrão | sim | |
| Renomear pessoa troca o nome nos projetos | sim | `falantes.json` e legendas editadas. |
| Aviso de contraste (cor escura) | sim | Azul-escuro e preto avisam; branco e ciano não. |
| Legenda na cor da pessoa e nome só para quem não é o FamosoZora | sim | Conferido no arquivo `.ass` e **no vídeo** (pixels ciano na legenda do Pedro). |
| Nome acima da legenda quando ela quebra em 2 linhas | sim | **Erro achado e corrigido no teste:** a etiqueta ficava em cima do texto; agora é uma linha da própria legenda. |
| Painel Falantes e janela Pessoas e cores (todos os botões) | sim | `test_painel_falantes_e_janela_de_pessoas` |
| **Fase 2: cortes sem número** | | |
| Migração do `cortes.json` (lista, sem versão e versão 2 → 3) com `cortes.bak.json` | sim | O primeiro backup nunca é apagado; arquivo já na versão 3 não é regravado. |
| 0 cortes sem erro | sim | "Nenhum trecho forte o bastante nesse vídeo" no Gerar e na lista de projetos. |
| Máximo de Shorts é só teto (fica com as notas mais altas) | sim | Vazio ou 0 = sem limite. |
| Pedido ao Claude sem número fixo, com clima, motivo e nota | sim | O teto só aparece se estiver configurado. |
| **Fase 3: música por clima** | | |
| Música da pasta do clima; pasta vazia → `geral` | sim | |
| Sem nenhuma música → Short sem música e aviso | sim | |
| Não repete música em Shorts seguidos (e usa todas antes de repetir) | sim | Sorteio sempre igual para o mesmo projeto. |
| Músicas soltas copiadas para `geral\` sem apagar | sim | |
| Música curta repete com crossfade | sim | **Erro achado e corrigido no teste:** do primeiro jeito a música parava em 10 s; agora o arquivo entra uma vez por repetição. |
| Ducking (a música abaixa na fala) | sim | Música −39 dB sem fala → −51 dB com fala (12 dB a menos). Na 1.3.0, com voz normal, eram só ~3 dB: o ducking ficou mais forte. |
| **Fase 4: efeitos** | | |
| Tempo do vídeo original → tempo do Short (com e sem abertura) | sim | |
| Máximo de 3 efeitos, categoria inexistente ignorada com aviso | sim | |
| Efeito no tempo certo no vídeo | sim | Agudos −66 dB antes → −17 dB no instante do efeito (6,5 s). |
| Troca de música num momento-chave | sim | Entra com crossfade. |
| Pedido manda só as categorias que têm arquivo | sim | |
| Não estoura | sim | Pico −4,5 dBFS (limite: −0,1). |
| **Fase 5: editor** | | |
| `NN_edicao.json`: salvar, desfazer e restaurar a sugestão | sim | Edição igual à sugestão não grava arquivo. |
| Edição de outro trecho (cortes refeitos) é ignorada | sim | |
| Aba Áudio e edição: todos os botões | sim | `test_audio_e_edicao_de_um_short` |
| Prévia "Trecho com o efeito" | sim | 5 s de áudio, com o efeito em 2 s. |
| Short antigo (antes da 1.4.0) ganha a sugestão ao abrir no editor | sim | |
| **Ponta a ponta** | | |
| Gerar → nomear falante → trocar música → adicionar e excluir efeito → renderizar de novo só este Short | sim | `test_ponta_a_ponta_audio.py`: vídeo de 20 s e sons gerados com o ffmpeg (tons e ruído, nada baixado). A sugestão do Claude fica intacta. |
| Mixagem no processador, sem NVIDIA | sim | Tudo rodou em x264 + filtros de áudio na CPU. |
| Tempo de render a mais com música e efeitos | sim | 25 s com música + efeitos contra 24 s sem (Short de 17,5 s). |
| **Ainda falta com você** | | |
| Conferir **de ouvido** num Short de verdade | — | A medição mostra o ducking funcionando, mas o ouvido decide. Veja o roteiro abaixo. |
| Testar no **notebook** (Windows, sem NVIDIA) | — | Aqui foi Linux sem NVIDIA; falta o seu Windows. |

## Roteiro para você testar no notebook (uns 10 minutos)

1. Coloque 2 ou 3 músicas em *Menu → Músicas de fundo (por clima)*, em `epico\` e `engracado\`, e 1 ou 2 efeitos em *Menu → Efeitos sonoros*, em `impacto\`.
2. Num vídeo já transcrito, clique em **2 Pedir cortes ao Claude** e confira se o pedido fala em clima, nota e "sons".
3. Gere os Shorts. Na janela preta, confira as linhas `musica: epico/...` e `efeitos sonoros: N`.
4. Abra **4 Revisar legendas**:
   - aba **Falantes**: ▶ ouvir cada voz e ligue a voz do amigo a uma pessoa nova;
   - aba **Áudio e edição**: troque a música, mexa no volume, ▶ Trecho com o efeito, exclua um efeito.
5. Clique em **Renderizar de novo só este Short** e assista. Confira:
   - a sua fala fica clara com a música;
   - os efeitos não estouram nem cobrem a fala;
   - a legenda do amigo sai na cor dele.

Se a música abaixar demais ou de menos, ajuste no `config.json`: `ducking_forca` (padrão 10) e `ducking_limiar` (padrão 0.015).

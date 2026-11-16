# Publicar no YouTube pelo Studio (passo a passo)

O Studio **não publica sozinho na internet**. Ele monta tudo (vídeo, thumb, título, descrição, tags, data e hora) e pede para o **Claude no seu computador** agendar o vídeo no **YouTube Studio**, usando o seu Chrome, do jeito que você já fazia à mão.

Nada vai para o YouTube sem você **revisar e clicar em "Confirmar e publicar"**.

---

## 1. O que precisa ter (uma vez só)

Você escolhe um dos dois jeitos em **Configurações → Claude**. O padrão é **Automático**: o Studio usa o Claude Code se ele estiver instalado e, se não estiver, o Cowork.

### Jeito A: Claude Code + Claude in Chrome (sozinho, recomendado)
1. **Claude Code** instalado no PC (o programa `claude` do terminal). Instale pelo site oficial do Claude Code e entre com a sua conta (`claude` no terminal, uma vez).
2. **Claude in Chrome**: a extensão do Claude instalada no **Chrome** e conectada à sua conta. *(Você já tem.)*
3. No Chrome, **entre no YouTube Studio** com a conta do canal FamosoZora.
4. No Studio: **Configurações → Claude → "Testar: achar o Claude neste computador"**. Tem que aparecer `✓ Claude Code: ...`.

Quando você publica, o Studio abre uma **janela preta com o Claude Code** já com o pedido. Ele usa o Chrome para subir e agendar cada vídeo. Deixe a janela e o Chrome abertos e **aprove o que ele pedir** (na primeira vez ele pede permissão para mexer no Chrome e gravar arquivos).

### Jeito B: Cowork / app do Claude (copiar e colar)
1. **App do Claude** para computador, com o **Cowork**.
2. **Claude in Chrome** conectado (o Cowork também usa o Chrome).
3. Quando você publica, o Studio **copia o pedido** e abre o app do Claude. Abra o Cowork, **cole (Ctrl+V) e envie**.
   - Dê ao Cowork acesso à pasta de trabalho (a pasta `publicar\` fica dentro dela), para ele achar os vídeos e gravar o `resultado.json`.

---

## 2. Publicar Shorts

- **Um Short:** no editor (Revisar os Shorts), botão laranja **Publicar** (ou botão direito no Short → Publicar).
- **Todos os Shorts prontos de um vídeo:** tela Shorts → **"5 Publicar os Shorts prontos"** (ou botão direito no projeto → Publicar).
- **Todos os Shorts prontos de todos os vídeos:** tela **Publicação → "Publicar todos os Shorts prontos"**.

O horário é automático: **12:00 (horário de Brasília)**, **um Short por dia**, começando no dia **depois do último Short que já está na fila**. (Ex.: se já tem Shorts agendados até quinta, o próximo vai para sexta.) Se faltar menos de 1 hora para o meio-dia de hoje, começa amanhã.

> O Studio só conhece o que está na fila dele. Se você agendou algum Short **por fora** (direto no YouTube), ajuste a data na tela de revisão.

## 3. A tela de revisão

Antes de qualquer coisa ir para o YouTube, aparece a revisão com cada vídeo:

| Campo | O que fazer |
|---|---|
| **Título** | Até 100 caracteres (o contador fica vermelho se passar). Sem `<` nem `>`. |
| **Data e hora** | `dia/mês/ano hora:minuto`, horário de Brasília. Do lado aparece o dia da semana. |
| **Descrição** | Já vem com o link do vídeo completo (o que você colocou em "Link do vídeo completo..."). |
| **Tags** | Separadas por vírgula. |
| **Playlist** | Opcional. O Studio lembra a última que você usou. |
| **Thumb** | Shorts: o YouTube não deixa trocar pelo computador (fica um quadro do vídeo). Vídeo longo: "Escolher thumb..." (senão vai um quadro do vídeo). |

Clique em **Confirmar e publicar**. O Studio:
1. põe os vídeos na **fila de publicação**;
2. monta um **pacote** para cada vídeo em `publicar\<data> <título>\` (o MP4, `thumb.png`, `dados.txt`, `dados.json`);
3. manda o **pedido** para o Claude (Jeito A ou B).

## 4. A tela Publicação (a fila)

| Situação | Quer dizer |
|---|---|
| na fila | Confirmado, ainda não foi para o Claude. |
| com o Claude... | O pedido foi para o Claude; esperando ele terminar. |
| ✓ agendado | O Claude agendou no YouTube Studio (aparece o link). |
| ✓ no ar | Passou do horário: o vídeo já está publicado. |
| ⚠ erro | Deu errado. Clique no item para ver o motivo embaixo. |

Como o Studio sabe que deu certo? Quando termina cada vídeo, o Claude grava um arquivo **`resultado.json`** na pasta do pacote. O Studio confere sozinho a cada poucos segundos e avisa no canto da tela ("Agendado: ... qua 18/11 às 12:00"). Pode fechar o Studio: quando abrir de novo, ele confere e continua de onde parou.

**Botão direito num item da fila:** Abrir no YouTube · Abrir o pacote · Assistir o vídeo · Mostrar na pasta · **Copiar pedido para o Claude** · **Mandar para o Claude de novo** · Marcar como agendado (se você fez à mão) · Marcar como publicado · Tirar da fila.

## 5. Quando dá erro

| Problema | O que fazer |
|---|---|
| "Não achei o Claude Code neste computador" | Instale o Claude Code, ou mude para **Cowork** em Configurações → Claude. |
| "o Claude não respondeu" (depois de 12 horas) | O Claude não gravou o `resultado.json`. Confira no YouTube Studio se o vídeo foi agendado. Se foi: botão direito → **Marcar como agendado** (cole o link). Se não: **Mandar para o Claude de novo**. |
| O Claude diz que não está logado | Entre no YouTube Studio pelo Chrome com a conta do canal e mande de novo. |
| "Não consegui montar o pacote" | Falta espaço no disco ou o vídeo sumiu. Libere espaço e mande de novo pela tela Publicação. |
| Saiu dois Shorts no mesmo dia | A revisão não deixa; se aconteceu por fora, apague um no YouTube Studio. |

## 6. Bom saber

- **Tirar da fila não cancela no YouTube.** Se o vídeo já foi agendado, apague o agendamento no YouTube Studio.
- O vídeo no pacote é uma **"ligação"** para o arquivo original (não ocupa espaço de novo) quando os dois estão no mesmo disco. Se não der, o Studio faz uma cópia.
- O pedido de cada envio fica salvo em `publicar\pedido_<data>.txt`.
- **API oficial do YouTube:** não foi usada nesta versão (você preferiu publicar pelo Claude no PC). Ela exigiria um projeto no Google Cloud e uma auditoria do YouTube que pode levar semanas; sem a auditoria, todo vídeo enviado pela API fica travado como privado.

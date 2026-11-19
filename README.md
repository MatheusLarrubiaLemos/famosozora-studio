# FamosoZora Studio

App para Windows que transforma as lives do canal [FamosoZora](https://www.youtube.com/@famosozora) em Shorts e em episódios editados, e publica no YouTube. O fluxo:

1. Transcreve o vídeo com o Whisper.
2. O Claude (o Claude Code do seu PC) escolhe os cortes e edita o vídeo longo com um clique, seguindo as [diretrizes do canal](docs/DIRETRIZES%20DO%20CANAL.md).
3. O app gera os Shorts (gancho, legenda colorida por pessoa, música, efeitos e final "Inscreva-se") e o episódio (sem gancho, com transições suaves e o outro no final).
4. Você revisa e o Claude agenda no YouTube Studio pelo seu Chrome ([docs/PUBLICAR.md](docs/PUBLICAR.md)).

## Instalar (qualquer PC com Windows 10/11)

1. Abra **[Releases](../../releases/latest)** e baixe o `FamosoZora-Studio-Setup-X.Y.Z.exe`.
2. Abra o arquivo. Se aparecer "O Windows protegeu o computador", clique em **Mais informações → Executar assim mesmo**.
3. Pronto: abra o **FamosoZora Studio** pelo atalho da Área de Trabalho.

Não precisa instalar Python, ffmpeg nem nada mais. Com placa NVIDIA, o app oferece ativar a aceleração; sem ela, tudo funciona no processador.

**Atualizar:** baixe o instalador da versão nova e instale por cima. Seus vídeos e Shorts não são apagados.

## Novidades

Veja o [CHANGELOG.md](CHANGELOG.md) (patch notes, com o número da versão e todas as mudanças).

## Para quem mexe no código

### Mapa do projeto

```
app/
├─ main.py              abre o programa
├─ versao.py            número da versão
├─ interface/           tudo que é tela
├─ shorts/              como os Shorts são montados
├─ videos_longos/       episódio editado e juntar vídeos
├─ nucleo/              base usada por todo mundo (pastas, ffmpeg, Whisper, transcrição, Claude sem janela)
├─ publicacao/          publicar no YouTube: fila, horário, pacote e o pedido ao Claude
└─ padrao/              configurações do canal (config.json, pessoas.json, vocabulario.txt, correcoes.txt, censura.txt)
musicas/                músicas de fundo dos Shorts, uma subpasta por clima (engracado, epico... e geral)
efeitos/                efeitos sonoros dos Shorts, uma subpasta por categoria (risada, impacto...)
docs/                   guias (COMO USAR.md, PUBLICAR.md) e DIRETRIZES DO CANAL.md
└─ relatorios/          relatórios antigos de diagnóstico e de testes de cada versão (só no GitHub)
build/                  monta o instalador (montar_app.ps1 + instalador.iss)
CHANGELOG.md            patch notes de cada versão
testes/                 testes automáticos (pytest)
```

### Quero mudar X → abra o arquivo Y

| Quero mudar... | Abra |
|---|---|
| As cores, as fontes e os estilos de TODAS as telas | `app/interface/tema.py` |
| A barra lateral, tela cheia, arrastar e soltar | `app/interface/janela_principal.py` |
| A tela Início (pendências) | `app/interface/pagina_inicio.py` |
| A tela Configurações | `app/interface/pagina_configuracoes.py` |
| A tela Publicação (a fila) | `app/interface/pagina_publicacao.py` |
| Os menus de botão direito (o jeito de montar) | `app/interface/menus.py` |
| As notificações do canto da tela | `app/interface/notificacao.py` |
| Os botões, as colunas e o botão direito da tela Shorts | `app/interface/aba_shorts.py` |
| Os botões, as colunas e o botão direito da tela Vídeos longos | `app/interface/aba_videos_longos.py` |
| Os cartões de projeto e o botão laranja do próximo passo (igual nas duas telas) | `app/interface/aba_base.py` |
| Selecionar vários vídeos (caixinha, Ctrl, Shift, "Selecionar todos") | `app/nucleo/selecao.py` (a regra) e `app/interface/aba_base.py` (a lista) |
| Gerar os Shorts de vários vídeos de uma vez (o lote: etapas, `lote.json`, pausar, cancelar, retomar) | `app/shorts/lote.py` |
| A janela Preparar lote (ordem, Pular / Gerar de novo, avisos) | `app/interface/janela_preparar_lote.py` |
| A tela do lote e o resumo do fim | `app/interface/janela_lote.py` |
| A janela Excluir (as 3 opções) | `app/interface/janela_excluir.py` |
| A janela do aviso de atualização | `app/interface/aviso_atualizacao.py` |
| O "🐞 Reportar bug" (botão direito em qualquer tela): a janela e o que vai junto no relato | `app/interface/reportar_bug.py` (a janela) e `app/nucleo/relato_bug.py` (monta o relato sem dados pessoais) |
| Janelas que abrem uma vez só (clicar de novo traz a aberta para a frente) | `app/interface/utilidades.py` (`janela_ja_aberta` e `lembrar_janela`) |
| Como o app procura versão nova (GitHub e git) | `app/nucleo/atualizacao.py` |
| O que cada opção de Excluir manda para a Lixeira | `app/nucleo/limpeza.py` |
| As miniaturas dos cartões | `app/nucleo/miniatura.py` |
| O editor de legendas (tela de revisão) | `app/interface/editor_legendas.py` |
| Como a legenda editada é guardada e dividida em linhas | `app/shorts/revisao.py` |
| A censura (máscara `p***`, lista, bip) | `app/shorts/censura.py` |
| O corretor ortográfico | `app/nucleo/ortografia.py` |
| A janela de revisão antes de publicar | `app/interface/janela_publicar.py` |
| A fila de publicação (situações, retomada) | `app/publicacao/fila.py` |
| O horário automático (12:00 de Brasília, um por dia) | `app/publicacao/horario.py` |
| O pacote de postagem e o pedido ao Claude | `app/publicacao/pacote.py` |
| Como o Studio acha e chama o Claude Code / Cowork | `app/publicacao/claude_pc.py` |
| Título, descrição e horário que aparecem na revisão | `app/publicacao/rascunhos.py` |
| Pedir ao Claude sem janela (tentativas, partes ao mesmo tempo, JSON) | `app/nucleo/claude_local.py` e a janela `app/interface/janela_claude.py` |
| Gerar cortes com o Claude (juntar partes, salvar) | `app/shorts/cortes_com_claude.py` |
| Editar o vídeo longo com o Claude | `app/videos_longos/edicao_com_claude.py` |
| O outro no final do vídeo longo | `app/videos_longos/outro.py` |
| A janela de revisão do vídeo longo | `app/interface/janela_edicao.py` |
| A tela de marcar câmera e gameplay | `app/interface/marcar_camera.py` |
| Cores das telas, abrir pastas e arquivos | `app/interface/utilidades.py` |
| O visual da legenda (tamanho, cor, palavra em destaque) | `app/shorts/legendas.py` |
| Abertura, final "INSCREVA-SE", mixagem (música, ducking, efeitos) e qualidade do Short | `app/shorts/montagem.py` |
| Os textos para postar (YouTube) | `app/shorts/textos.py` |
| A ordem em que o Short é gerado | `app/shorts/gerar_shorts.py` |
| Quem fala em cada parte do corte (detector de vozes) | `app/shorts/falantes.py` |
| O cadastro de pessoas, as cores e a regra "sem dono = FamosoZora" | `app/shorts/pessoas.py` |
| O painel Falantes e a janela Pessoas e cores | `app/interface/painel_falantes.py` e `app/interface/janela_pessoas.py` |
| A aba Áudio e edição do editor (música e efeitos de um Short) | `app/interface/painel_audio.py` |
| O pedido de cortes ao Claude (quantidade, clima, nota, sons) | `app/shorts/pedido_cortes.py` |
| O formato do `cortes.json` (versão, migração, teto de Shorts) | `app/shorts/cortes.py` |
| As pastas de músicas e efeitos e a escolha da música por clima | `app/shorts/biblioteca.py` |
| A sugestão de música e efeitos de cada Short e a prévia de áudio | `app/shorts/audio_short.py` |
| Onde fica a edição de cada Short (`edicao_shorts\NN_edicao.json`) | `app/shorts/edicao.py` |
| O pedido de edição do vídeo longo e as regras do `edicao.json` | `app/videos_longos/pedido_edicao.py` |
| Como o episódio é renderizado (emendas, outro, prévia, capítulos) | `app/videos_longos/editar_episodio.py` |
| A janela de juntar vídeos | `app/videos_longos/juntar_videos_gui.ps1` |
| A transcrição (Whisper) | `app/nucleo/transcrever.py` e `app/nucleo/whisper.py` |
| Onde ficam as pastas e os valores padrão do `config.json` | `app/nucleo/comum.py` |
| Comandos do ffmpeg e o teste da placa NVIDIA | `app/nucleo/video.py` |
| Em que passo cada projeto está (lista da janela) | `app/nucleo/projetos.py` |
| O vocabulário, as correções e a marcação de câmera do canal | `app/padrao/` |
| O que vai no instalador | `build/montar_app.ps1` e `build/instalador.iss` |
| O que o `.bat` de desenvolvedor prepara | `build/preparar_dev.ps1` |

### Onde ficam as configurações

- **Na pasta do GitHub (modo desenvolvedor):** em `app/padrao/`, `musicas/` e `efeitos/`. O que você mudar ali (vocabulário, correções, pessoas e cores, marcação de câmera, música ou efeito novo) vai para o GitHub no **Commit + Push** e chega aos outros PCs.
- **No app instalado:** as do GitHub vêm dentro do app. O que for mudado pelo app fica só naquele PC, em `%LOCALAPPDATA%\FamosoZora Studio\configuracoes`, `\musicas` e `\efeitos`, e vale junto com as do GitHub.
- **A pasta de trabalho é descartável:** tem só vídeos e projetos em produção. Depois de publicar, pode excluir o que pesa (botão direito → Excluir).

### Configurar em outro PC (por exemplo, o notebook)

O GitHub é a versão oficial do código. Cada PC tem uma cópia, e o GitHub Desktop leva as mudanças de um para o outro.

1. **Instale o GitHub Desktop:** baixe em [desktop.github.com](https://desktop.github.com), instale e entre com a sua conta do GitHub.
2. **Instale o Python 3.12:** baixe em [python.org](https://www.python.org/downloads/release/python-31210/) o "Windows installer (64-bit)". Na primeira tela do instalador, **marque "Add python.exe to PATH"** e clique em "Install Now".
3. **Clone o repositório:** no GitHub Desktop, *File → Clone repository*, escolha `famosozora-studio` e uma pasta (por exemplo, `C:\FamosoZora\famosozora-studio`). Clique em *Clone*.
4. **Abra o `Studio (modo desenvolvedor).bat`** dessa pasta, com dois cliques. Na primeira vez ele prepara tudo sozinho (leva alguns minutos e precisa de internet):
   - cria a pasta `.venv` e instala as bibliotecas;
   - baixa o ffmpeg para a pasta `bin`;
   - se o PC tiver placa NVIDIA, baixa as bibliotecas dela. Sem placa, tudo funciona no processador, só mais devagar.
5. Na primeira abertura, o Studio pergunta qual vai ser a **pasta de trabalho** deste PC. Ela pode ser diferente em cada PC.

Nas próximas vezes, o `.bat` só confere o que mudou e abre em poucos segundos.

**Regra de ouro (para não dar conflito entre os PCs):**
- **Antes de mexer:** no GitHub Desktop, *Fetch origin* e depois *Pull origin*. O Studio também confere sozinho ao abrir e pergunta se quer baixar o código novo.
- **Depois de mexer:** *Commit* e depois *Push origin*. O Studio avisa ao abrir se ficou alguma coisa sem enviar.

### Dia a dia

- **Testar sem instalar:** abra o `Studio (modo desenvolvedor).bat`. Ele prepara o que faltar e abre o Studio.
- **Reinstalar as bibliotecas:** rode o `.bat` com a palavra `instalar` (ou *Configurações → Atualizar dependências*).
- **Rodar os testes:** `.venv\Scripts\python -m pytest` (rápidos) e `.venv\Scripts\python -m pytest -m lento` (vídeo de amostra do começo ao fim e botão a botão). Os relatórios de testes de cada versão estão em `docs/relatorios/`.
- **Formatar e conferir o código:** `python -m black app` e `python -m ruff check app` (configurados no `pyproject.toml`; instale com `pip install -r requirements-dev.txt`).
- **Lançar uma versão:**
  1. Aumente o número em `app/versao.py`.
  2. Escreva a seção da versão no `CHANGELOG.md`.
  3. Faça **Commit** e **Push**.
- O GitHub Actions (`.github/workflows/build.yml`) roda os testes e, se todos passarem, monta o instalador e publica o Release sozinho. Se algum teste falhar, a versão não sai (veja o erro na aba *Actions*).
- Vídeos e Shorts **nunca** ficam aqui: eles ficam na pasta de trabalho, que é escolhida no Studio.

# FamosoZora Studio

App para Windows que transforma os vídeos longos do canal [FamosoZora](https://www.youtube.com/@famosozora) em Shorts prontos para YouTube, TikTok e Instagram. O fluxo tem quatro passos:

1. Transcreve o vídeo com o Whisper.
2. O Claude escolhe os cortes, seguindo as [diretrizes do canal](docs/DIRETRIZES%20DO%20CANAL.md).
3. O app gera os Shorts com gancho, transição suave, legenda colorida por pessoa que fala, música e final "Inscreva-se".
4. Ajuda a postar pelo Buffer.

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
├─ nucleo/              base usada por todo mundo (pastas, ffmpeg, Whisper, transcrição)
└─ padrao/              configurações do canal (config.json, vocabulario.txt, correcoes.txt, censura.txt)
musicas/                músicas de fundo dos Shorts
docs/                   guia (COMO USAR.md), DIRETRIZES DO CANAL.md e os relatórios
build/                  monta o instalador (montar_app.ps1 + instalador.iss)
CHANGELOG.md            patch notes de cada versão
```

### Quero mudar X → abra o arquivo Y

| Quero mudar... | Abra |
|---|---|
| O topo da janela e o botão Menu | `app/interface/janela_principal.py` |
| Os botões e as colunas da aba Shorts | `app/interface/aba_shorts.py` |
| Os botões e as colunas da aba Vídeos longos / Lives | `app/interface/aba_videos_longos.py` |
| A lista de projetos e a faixa "próximo passo" (igual nas duas abas) | `app/interface/aba_base.py` |
| A janela do aviso de atualização | `app/interface/aviso_atualizacao.py` |
| Como o app procura versão nova (GitHub e git) | `app/nucleo/atualizacao.py` |
| O que o "Limpar projeto" apaga e o que guarda | `app/nucleo/limpeza.py` |
| O editor de legendas (tela de revisão) | `app/interface/editor_legendas.py` |
| Como a legenda editada é guardada e dividida em linhas | `app/shorts/revisao.py` |
| A censura (máscara `p***`, lista, bip) | `app/shorts/censura.py` |
| O corretor ortográfico | `app/nucleo/ortografia.py` |
| A janela Publicar (copiar textos, marcar postado) | `app/interface/janela_publicar.py` |
| A janela de revisão do vídeo longo | `app/interface/janela_edicao.py` |
| A tela de marcar câmera e gameplay | `app/interface/marcar_camera.py` |
| Cores das telas, abrir pastas e arquivos | `app/interface/utilidades.py` |
| O visual da legenda (tamanho, cor, palavra em destaque) | `app/shorts/legendas.py` |
| Abertura, final "INSCREVA-SE", música e qualidade do Short | `app/shorts/montagem.py` |
| Os textos para postar (YouTube, TikTok, Instagram) | `app/shorts/textos.py` |
| A ordem em que o Short é gerado | `app/shorts/gerar_shorts.py` |
| As cores por pessoa que fala | `app/shorts/falantes.py` |
| O pedido de edição do vídeo longo e as regras do `edicao.json` | `app/videos_longos/pedido_edicao.py` |
| Como o episódio é renderizado (emendas, prévia, capítulos) | `app/videos_longos/editar_episodio.py` |
| A janela de juntar vídeos | `app/videos_longos/juntar_videos_gui.ps1` |
| A transcrição (Whisper) | `app/nucleo/transcrever.py` e `app/nucleo/whisper.py` |
| Onde ficam as pastas e os valores padrão do `config.json` | `app/nucleo/comum.py` |
| Comandos do ffmpeg e o teste da placa NVIDIA | `app/nucleo/video.py` |
| Em que passo cada projeto está (lista da janela) | `app/nucleo/projetos.py` |
| O vocabulário, as correções e a marcação de câmera do canal | `app/padrao/` |
| O que vai no instalador | `build/montar_app.ps1` e `build/instalador.iss` |
| O que o `.bat` de desenvolvedor prepara | `build/preparar_dev.ps1` |

### Onde ficam as configurações

- **Na pasta do GitHub (modo desenvolvedor):** em `app/padrao/` e `musicas/`. O que você mudar ali (vocabulário, correções, marcação de câmera, música nova) vai para o GitHub no **Commit + Push** e chega aos outros PCs.
- **No app instalado:** as do GitHub vêm dentro do app. O que for mudado pelo app fica só naquele PC, em `%LOCALAPPDATA%\FamosoZora Studio\configuracoes`, e vale junto com as do GitHub.
- **A pasta de trabalho é descartável:** tem só vídeos e projetos em produção. Depois de postar, pode limpar.

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
- **Reinstalar as bibliotecas:** rode o `.bat` com a palavra `instalar` (ou *Menu → Atualizar dependências*).
- **Formatar e conferir o código:** `python -m black app` e `python -m ruff check app` (configurados no `pyproject.toml`; instale com `pip install -r requirements-dev.txt`).
- **Lançar uma versão:**
  1. Aumente o número em `app/versao.py`.
  2. Escreva a seção da versão no `CHANGELOG.md`.
  3. Faça **Commit** e **Push**.
- O GitHub Actions (`.github/workflows/build.yml`) monta o instalador e publica o Release sozinho.
- Vídeos e Shorts **nunca** ficam aqui: eles ficam na pasta de trabalho, que é escolhida no Studio.

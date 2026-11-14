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

### Onde ficam as configurações

- **Na pasta do GitHub (modo desenvolvedor):** em `app/padrao/` e `musicas/`. O que você mudar ali (vocabulário, correções, marcação de câmera, música nova) vai para o GitHub no **Commit + Push** e chega aos outros PCs.
- **No app instalado:** as do GitHub vêm dentro do app. O que for mudado pelo app fica só naquele PC, em `%LOCALAPPDATA%\FamosoZora Studio\configuracoes`, e vale junto com as do GitHub.
- **A pasta de trabalho é descartável:** tem só vídeos e projetos em produção. Depois de postar, pode limpar.

### Dia a dia

- **Testar sem instalar:** abra o `Studio (modo desenvolvedor).bat`. Na primeira vez, ele prepara o Python numa pasta `.venv`.
- **Formatar e conferir o código:** `python -m black app` e `python -m ruff check app` (configurados no `pyproject.toml`; instale com `pip install -r requirements-dev.txt`).
- **Lançar uma versão:**
  1. Aumente o número em `app/versao.py`.
  2. Escreva a seção da versão no `CHANGELOG.md`.
  3. Faça **Commit** e **Push**.
- O GitHub Actions (`.github/workflows/build.yml`) monta o instalador e publica o Release sozinho.
- Vídeos e Shorts **nunca** ficam aqui: eles ficam na pasta de trabalho, que é escolhida no Studio.

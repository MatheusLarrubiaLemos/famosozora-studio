# Pacote de postagem: uma pasta publicar\pacotes\<nome do video>\ com tudo o que o Claude precisa para agendar o video
# no YouTube Studio pelo seu Chrome:
#   - o MP4 final (ligacao direta ao arquivo quando da, para nao ocupar espaco de novo; senao, uma copia)
#   - thumb.png (um quadro do video)
#   - dados.txt (titulo, descricao, tags, playlist, data e hora) e dados.json (o mesmo, para programas)
#   - pedido.txt: o pedido pronto para o Claude
# Quando termina, o Claude grava resultado.json no pacote: {"status": "agendado", "link": "https://youtu.be/..."}
# Depois que o video entra no ar, o pacote nao serve mais: 7 dias depois ele vai para a Lixeira sozinho
# ("publicar_limpar_pacotes_dias" no config.json; 0 = nunca), e o Excluir do projeto leva os pacotes dele.
# (O video do pacote e uma LIGACAO do mesmo arquivo do Short: sem apagar o pacote, o espaco nao era liberado.)
# Desde a 1.11.3 a pasta publicar\ fica so com duas coisas: "ENVIAR ESTES VIDEOS" (os videos do envio juntos, para
# voce arrastar de uma vez) e "pacotes" (um pacote por video + os pedidos: e onde o Claude grava o resultado.json).
# Os pacotes antigos (direto em publicar\) continuam valendo: a fila guarda o caminho de cada um.
import json
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from nucleo.comum import PASTA_PUBLICAR, nome_seguro
from publicacao.horario import agora, em_brasilia, texto_horario

LIMITE_TITULO = 100  # o YouTube nao aceita titulo maior que isso
LIMITE_DESCRICAO = 5000
DIAS_PARA_LIMPAR = 7  # o pacote de um video que ja esta no ar ha mais que isso vai para a Lixeira sozinho


def problemas_do_item(item: dict) -> list:
    """O que impede de publicar (em portugues simples). Lista vazia = pode publicar."""
    erros = []
    titulo = (item.get("titulo") or "").strip()
    if not titulo:
        erros.append("o título está vazio")
    elif len(titulo) > LIMITE_TITULO:
        erros.append(f"o título tem {len(titulo)} caracteres (o YouTube aceita até {LIMITE_TITULO})")
    if "<" in titulo or ">" in titulo:
        erros.append("o título não pode ter < nem > (o YouTube recusa)")
    if len(item.get("descricao") or "") > LIMITE_DESCRICAO:
        erros.append(f"a descrição passou de {LIMITE_DESCRICAO} caracteres")
    if not Path(item.get("video") or "").is_file():
        erros.append(f"o vídeo não foi encontrado: {item.get('video')}")
    return erros


def pasta_do_pacote(item: dict) -> Path:
    base = nome_seguro(f"{em_brasilia(item['horario']).strftime('%Y-%m-%d %H%M')} {item['titulo']}", 90)
    return pasta_pacotes() / base


def pasta_pacotes() -> Path:
    """publicar\\pacotes: um pacote por video e os pedidos (o "recibo" de cada envio; voce nao precisa abrir)."""
    return PASTA_PUBLICAR / "pacotes"


def ligar_ou_copiar(origem: Path, destino: Path, progresso=None):
    """Poe o video no pacote. Primeiro tenta uma "ligacao" (o mesmo arquivo em dois lugares, sem gastar disco);
    se o Windows nao deixar (outro disco, por exemplo), copia em pedacos, avisando o progresso (0 a 1)."""
    if destino.exists():
        if destino.stat().st_size == origem.stat().st_size:
            return
        destino.unlink()
    try:
        os.link(origem, destino)
        return
    except OSError:
        pass
    total = max(1, origem.stat().st_size)
    feito = 0
    with open(origem, "rb") as a, open(destino, "wb") as b:
        while True:
            pedaco = a.read(8 * 1024 * 1024)
            if not pedaco:
                break
            b.write(pedaco)
            feito += len(pedaco)
            if progresso:
                progresso(feito / total)
    shutil.copystat(origem, destino)


def texto_dados(item: dict) -> str:
    """O dados.txt: tudo o que vai no YouTube Studio, facil de ler e copiar."""
    linhas = [
        f"TIPO: {'Short' if item['tipo'] == 'short' else 'Vídeo longo'}",
        f"DATA E HORA (Brasília): {texto_horario(item['horario'], com_ano=True)}",
        f"ARQUIVO: {Path(item.get('video_pacote') or item['video']).name}",
        "",
        "TÍTULO:",
        item["titulo"],
        "",
        "DESCRIÇÃO:",
        item.get("descricao") or "",
        "",
        "TAGS:",
        ", ".join(item.get("tags") or []),
    ]
    if item.get("playlist"):
        linhas += ["", "PLAYLIST:", item["playlist"]]
    if item.get("titulo_en") or item.get("descricao_en"):
        linhas += [
            "",
            "INGLÊS (YouTube Studio > Idiomas):",
            item.get("titulo_en") or "",
            item.get("descricao_en") or "",
        ]
    return "\n".join(linhas) + "\n"


def montar_pacote(item: dict, progresso=None) -> Path:
    """Cria (ou atualiza) a pasta do pacote. Devolve a pasta. Da OSError se nao conseguir."""
    from nucleo.miniatura import tirar_quadro
    from nucleo.video import duracao_video

    pasta = Path(item.get("pacote") or pasta_do_pacote(item))
    pasta.mkdir(parents=True, exist_ok=True)
    video = Path(item["video"])
    destino = pasta / video.name
    ligar_ou_copiar(video, destino, progresso)
    item["video_pacote"] = str(destino)
    thumb = pasta / "thumb.png"
    if item.get("thumb") and Path(item["thumb"]).is_file():
        shutil.copy2(item["thumb"], thumb)
    elif not thumb.exists():
        try:
            dur = duracao_video(video)
        except (SystemExit, Exception):
            dur = 0
        largura, altura = (720, 1280) if item["tipo"] == "short" else (1280, 720)
        tirar_quadro(video, thumb, dur / 3 if dur else 1.0, largura, altura)
    (pasta / "dados.txt").write_text(texto_dados(item), encoding="utf-8")
    dados = {k: item.get(k) for k in ("tipo", "titulo", "descricao", "tags", "playlist", "horario", "titulo_en",
                                      "descricao_en")}  # fmt: skip
    dados["arquivo"] = destino.name
    (pasta / "dados.json").write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    (pasta / "resultado.json").unlink(missing_ok=True)  # mandando de novo: o resultado antigo nao vale
    item["pacote"] = str(pasta)
    return pasta


def texto_pedido(itens: list) -> str:
    """O pedido para o Claude agendar os videos no YouTube Studio (pelo Chrome, com o Claude in Chrome)."""
    partes = [
        "Claude, agende estes vídeos no meu canal do YouTube (FamosoZora) pelo YouTube Studio, usando o Chrome "
        "(Claude in Chrome). Eu já estou logado no canal.",
        "",
        "COMO VAMOS FAZER (o upload é comigo; a ferramenta de upload do Claude in Chrome só aceita até ~10 MB):",
        "A. NÃO tente enviar nenhum arquivo de vídeo. Abra https://studio.youtube.com e clique em Criar > Enviar "
        f'vídeos. Depois ABRA PARA MIM a pasta com os vídeos, rodando o comando: explorer.exe "{pasta_enviar()}" '
        "(o explorer.exe sempre termina com código 1: isso é normal, não é erro; não rode de novo; se você não "
        "conseguir rodar comandos no meu PC, pule: o Studio já deixou a pasta aberta). Aí me diga aqui "
        "no terminal: 'Abri a pasta: selecione todos (Ctrl+A) e arraste para a janela de envio do YouTube'. Eu "
        "arrasto e respondo 'pronto' quando todos estiverem enviados. ESPERE o meu 'pronto'.",
        "B. Depois, em Conteúdo, os vídeos aparecem como rascunho/privado, com o NOME DO ARQUIVO (sem o .mp4) como "
        "título. Para CADA vídeo da lista abaixo, um por um, abra o rascunho que tem o nome do arquivo dele e:",
        "1. Confira se é o vídeo certo (nome do arquivo e duração). Se não achar, avise e siga para o próximo.",
        "2. Preencha o título, a descrição e as tags EXATAMENTE como estão (as tags ficam em 'Mostrar mais').",
        "3. Público: 'Não, não é conteúdo para crianças'.",
        "4. Se tiver playlist, coloque na playlist (crie se não existir).",
        "5. Se tiver título e descrição em inglês, adicione em 'Idiomas' depois de salvar (se der).",
        "6. Se tiver thumb.png e não for Short, envie como miniatura (a imagem é pequena: essa você pode enviar).",
        "7. Em Visibilidade, escolha AGENDAR, com a data e a hora indicadas (fuso: Horário de Brasília). "
        "NUNCA publique como público na hora.",
        "8. Quando terminar o vídeo, grave um arquivo resultado.json DENTRO da pasta do pacote dele, assim: "
        '{"status": "agendado", "link": "https://youtu.be/CODIGO"}',
        '   Se não conseguir, grave: {"status": "erro", "motivo": "o que aconteceu"} e siga para o próximo.',
        "",
        "Os vídeos:",
    ]
    for k, item in enumerate(itens, 1):
        pacote = Path(item["pacote"])
        partes += [
            "",
            f"===== VÍDEO {k} de {len(itens)}: {'SHORT' if item['tipo'] == 'short' else 'VÍDEO LONGO'} =====",
            f"Pasta do pacote: {pacote}",
            f"Arquivo (o rascunho no YouTube tem este nome, sem o .mp4): {nome_para_enviar(item)}",
            f"Agendar para: {texto_horario(item['horario'], com_ano=True)} (Brasília)",
            f"Título: {item['titulo']}",
            "Descrição:",
            item.get("descricao") or "(vazia)",
            f"Tags: {', '.join(item.get('tags') or []) or '(nenhuma)'}",
        ]
        if item.get("playlist"):
            partes.append(f"Playlist: {item['playlist']}")
        if item.get("titulo_en"):
            partes.append(f"Título em inglês: {item['titulo_en']}")
        if item.get("descricao_en"):
            partes += ["Descrição em inglês:", item["descricao_en"]]
        partes.append("(os mesmos dados estão em dados.txt dentro da pasta do pacote)")
    partes += ["", "No fim, me diga em português quais deram certo e quais não."]
    return "\n".join(partes)


def pasta_enviar() -> Path:
    """publicar\\ENVIAR ESTES VIDEOS: todos os videos de um envio juntos (voce seleciona todos e arrasta de uma vez).
    Ate a 1.11.2 se chamava "_para_enviar" (sumia no meio dos pacotes)."""
    return PASTA_PUBLICAR / "ENVIAR ESTES VIDEOS"


PASTA_ENVIAR_ANTIGA = "_para_enviar"


def nome_para_enviar(item: dict) -> str:
    """O nome do video na pasta ENVIAR ESTES VIDEOS (o YouTube usa esse nome como titulo do rascunho)."""
    return item.get("nome_envio") or Path(item.get("video_pacote") or item["video"]).name


def juntar_para_enviar(itens: list) -> Path:
    """Poe os videos deste envio juntos em publicar\\ENVIAR ESTES VIDEOS (ligacao do mesmo arquivo: nao gasta disco),
    para voce selecionar todos e arrastar para o YouTube Studio de uma vez. O envio anterior vai para a Lixeira.
    Nomes repetidos ganham (2), (3)... Grava em cada item o nome usado ("nome_envio")."""
    from nucleo.limpeza import mandar_para_lixeira

    destino = pasta_enviar()
    antigas = [p for p in (destino, PASTA_PUBLICAR / PASTA_ENVIAR_ANTIGA) if p.exists()]
    if antigas:
        mandar_para_lixeira(antigas)
    destino.mkdir(parents=True, exist_ok=True)
    usados = set()
    for item in itens:
        origem = Path(item.get("video_pacote") or item["video"])
        nome, k = origem.name, 2
        while nome.lower() in usados:
            nome, k = f"{origem.stem} ({k}){origem.suffix}", k + 1
        usados.add(nome.lower())
        ligar_ou_copiar(origem, destino / nome)
        item["nome_envio"] = nome
    return destino


def gravar_pedido(itens: list) -> Path:
    """Grava o pedido em publicar\\pacotes\\pedido_<data>.txt (o Claude Code le esse arquivo). Devolve o arquivo.
    Os pedidos antigos soltos em publicar\\ vao para pacotes\\ junto (a pasta publicar\\ fica so com 2 pastas)."""
    from datetime import datetime

    destino = pasta_pacotes()
    destino.mkdir(parents=True, exist_ok=True)
    for antigo in PASTA_PUBLICAR.glob("pedido_*.txt"):
        try:
            if not (destino / antigo.name).exists():
                antigo.replace(destino / antigo.name)
        except OSError:
            pass  # aberto em outro programa: fica onde esta, sem problema
    arq = destino / f"pedido_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
    arq.write_text(texto_pedido(itens), encoding="utf-8")
    return arq


# ------------------------------------------------------------------ limpar pacotes de videos que ja estao no ar
def pasta_segura(item: dict):
    """A pasta do pacote do item, so se ela existe e fica DENTRO de publicar\\ (nunca mexe em outra pasta)."""
    caminho = item.get("pacote")
    if not caminho:
        return None
    pasta = Path(caminho)
    try:
        if pasta.is_dir() and PASTA_PUBLICAR.resolve() in pasta.resolve().parents:
            return pasta
    except OSError:
        pass
    return None


def pacotes_para_limpar(itens: list, dias=DIAS_PARA_LIMPAR, referencia=None) -> list:
    """[(id, pasta)] dos videos que ja estao no ar ha 'dias' dias ou mais e ainda tem o pacote."""
    try:
        dias = float(dias)
    except (TypeError, ValueError):
        dias = DIAS_PARA_LIMPAR
    if dias <= 0:
        return []
    ref = em_brasilia(referencia) if referencia else agora()
    pares = []
    for item in itens:
        if item.get("status") != "publicado":
            continue
        try:
            no_ar = em_brasilia(item["horario"])
        except (KeyError, TypeError, ValueError):
            continue
        pasta = pasta_segura(item)
        if pasta and ref - no_ar >= timedelta(days=dias):
            pares.append((item["id"], pasta))
    return pares


def pacotes_dos_videos(itens: list, caminhos) -> list:
    """[(id, pasta)] dos pacotes de videos JA PUBLICADOS cujo video e um destes caminhos ou esta dentro de uma
    destas pastas. O Excluir leva esses pacotes junto (os que ainda vao sair ficam: o Studio so avisa)."""
    caminhos = [Path(c) for c in caminhos]
    pares = []
    for item in itens:
        if item.get("status") != "publicado":
            continue
        video = Path(item.get("video") or "")
        if not any(video == c or c in video.parents for c in caminhos):
            continue
        pasta = pasta_segura(item)
        if pasta:
            pares.append((item["id"], pasta))
    return pares


def liberado_se_apagar(pasta: Path) -> int:
    """Quanto apagar o pacote libera de verdade: so o que nao esta ligado a outro arquivo (o video do pacote,
    enquanto o Short existir, nao libera nada)."""
    total = 0
    for f in pasta.rglob("*"):
        try:
            if f.is_file():
                st = f.stat()
                if st.st_nlink <= 1:
                    total += st.st_size
        except OSError:
            pass
    return total


def mandar_pacotes_para_lixeira(pares: list) -> list:
    """Manda cada pacote para a Lixeira (da para restaurar). Devolve [(id, deu_certo, bytes liberados)].
    Nao mexe na fila: quem chama anota com marcar_pacotes_limpos (na linha da tela)."""
    from nucleo.limpeza import mandar_para_lixeira

    resultado = []
    for id_, pasta in pares:
        livre = liberado_se_apagar(pasta)
        ok = mandar_para_lixeira([pasta])
        resultado.append((id_, ok, livre if ok else 0))
    return resultado


def marcar_pacotes_limpos(ids: list):
    """Anota na fila que o pacote desses itens foi para a Lixeira (o menu deixa de oferecer "Abrir o pacote")."""
    from publicacao import fila

    quando = datetime.now().isoformat(timespec="seconds")
    for id_ in ids:
        fila.atualizar(id_, pacote="", video_pacote="", pacote_limpo_em=quando)

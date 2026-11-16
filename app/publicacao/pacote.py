# Pacote de postagem: uma pasta publicar\<nome do video>\ com tudo o que o Claude precisa para agendar o video
# no YouTube Studio pelo seu Chrome:
#   - o MP4 final (ligacao direta ao arquivo quando da, para nao ocupar espaco de novo; senao, uma copia)
#   - thumb.png (um quadro do video)
#   - dados.txt (titulo, descricao, tags, playlist, data e hora) e dados.json (o mesmo, para programas)
#   - pedido.txt: o pedido pronto para o Claude
# Quando termina, o Claude grava resultado.json no pacote: {"status": "agendado", "link": "https://youtu.be/..."}
import json
import os
import shutil
from pathlib import Path

from nucleo.comum import PASTA_PUBLICAR, nome_seguro
from publicacao.horario import em_brasilia, texto_horario

LIMITE_TITULO = 100  # o YouTube nao aceita titulo maior que isso
LIMITE_DESCRICAO = 5000


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
    return PASTA_PUBLICAR / base


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
        "Para CADA vídeo abaixo:",
        "1. Abra https://studio.youtube.com e clique em Criar > Enviar vídeos.",
        "2. Envie o arquivo de vídeo que está na pasta do pacote.",
        "3. Preencha o título, a descrição e as tags EXATAMENTE como estão (as tags ficam em 'Mostrar mais').",
        "4. Público: 'Não, não é conteúdo para crianças'.",
        "5. Se tiver playlist, coloque na playlist (crie se não existir).",
        "6. Se tiver título e descrição em inglês, adicione em 'Idiomas' depois de salvar (se der).",
        "7. Se tiver thumb.png e não for Short, envie como miniatura.",
        "8. Em Visibilidade, escolha AGENDAR, com a data e a hora indicadas (fuso: Horário de Brasília). "
        "NUNCA publique como público na hora.",
        "9. Quando terminar, grave um arquivo resultado.json DENTRO da pasta do pacote, assim: "
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
            f"Arquivo: {pacote / Path(item.get('video_pacote') or item['video']).name}",
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


def gravar_pedido(itens: list) -> Path:
    """Grava o pedido em publicar\\pedido_<data>.txt (o Claude Code le esse arquivo). Devolve o arquivo."""
    from datetime import datetime

    PASTA_PUBLICAR.mkdir(parents=True, exist_ok=True)
    arq = PASTA_PUBLICAR / f"pedido_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
    arq.write_text(texto_pedido(itens), encoding="utf-8")
    return arq

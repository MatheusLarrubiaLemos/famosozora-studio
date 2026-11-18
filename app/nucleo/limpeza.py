# Limpar projeto: depois de postar, manda para a Lixeira a midia pesada do projeto (Shorts, episodio,
# versoes antigas e temporarios) e guarda um resumo pequeno (cortes, edicao, textos e o que foi postado).
# Excluir pelo app (botao direito > Excluir): so os Shorts, so o episodio, o projeto inteiro, ou o projeto
# junto com o video original.
# Nada e apagado de vez: tudo vai para a Lixeira do Windows, de onde da para restaurar.
import os
import time
from datetime import datetime
from pathlib import Path

from nucleo.comum import EXTENSOES_VIDEO, gravar_json, ler_json


def _tamanho(caminho: Path) -> int:
    """Tamanho em bytes de um arquivo ou de uma pasta inteira."""
    if caminho.is_file():
        return caminho.stat().st_size
    return sum(f.stat().st_size for f in caminho.rglob("*") if f.is_file())


def midia_do_projeto(pasta: Path) -> list:
    """O que pesa no projeto: [(caminho, bytes)]. O resumo (arquivos .json e .txt) fica de fora."""
    itens = []
    for sub in ("prontos", "episodio"):
        base = pasta / sub
        if not base.exists():
            continue
        for f in base.iterdir():
            if f.is_dir() and f.name in ("antigos", "_temp"):
                itens.append(f)
            elif f.is_file() and f.suffix.lower() in EXTENSOES_VIDEO:
                itens.append(f)
    return [(f, _tamanho(f)) for f in itens]


# o que cada opcao da janela "Excluir" manda para a Lixeira
MODOS = {
    "shorts": "Só os Shorts gerados",
    "episodio": "Só o episódio gerado",
    "projeto": "Projeto inteiro",
    "tudo": "Projeto + vídeo original",
}


def _gerados(base: Path) -> list:
    """Videos gerados de uma pasta (prontos ou episodio), as versoes antigas e os temporarios."""
    if not base.exists():
        return []
    return [f for f in base.iterdir()
            if (f.is_dir() and f.name in ("antigos", "_temp")) or (f.is_file() and f.suffix.lower() in EXTENSOES_VIDEO)]  # fmt: skip


def video_original(pasta: Path):
    """O video que deu origem ao projeto (se ainda existe)."""
    caminho = (ler_json(pasta / "projeto.json", {}) or {}).get("video")
    video = Path(caminho) if caminho else None
    return video if video and video.is_file() else None


def itens_para_excluir(pasta: Path, modo: str) -> list:
    """Arquivos e pastas que a opcao 'modo' manda para a Lixeira."""
    if modo == "shorts":
        return _gerados(pasta / "prontos")
    if modo == "episodio":
        return _gerados(pasta / "episodio")
    if modo == "projeto":
        return [pasta] if pasta.exists() else []
    if modo == "tudo":
        video = video_original(pasta)
        return ([pasta] if pasta.exists() else []) + ([video] if video else [])
    raise ValueError(f"opção de exclusão desconhecida: {modo}")


def tamanho_dos_itens(itens) -> int:
    total = 0
    for f in itens:
        try:
            total += _tamanho(Path(f))
        except OSError:
            pass
    return total


def excluir_projeto(pasta: Path, modo: str) -> int:
    """Manda para a Lixeira o que a opcao 'modo' escolhe. Devolve os bytes liberados."""
    itens = itens_para_excluir(pasta, modo)
    total = tamanho_dos_itens(itens)
    if not mandar_para_lixeira(itens):
        raise OSError(f'Não consegui mandar "{pasta.name}" para a Lixeira. Algum vídeo dele está aberto no player? '
                      "Feche e tente de novo.")  # fmt: skip
    return total


def tamanho_txt(n_bytes: int) -> str:
    if n_bytes >= 1_000_000_000:
        return f"{n_bytes / 1_000_000_000:.1f} GB".replace(".", ",")
    if 0 < n_bytes < 1_000_000:
        return "menos de 1 MB"
    return f"{n_bytes / 1_000_000:.0f} MB"


# Esperas (em segundos) entre as tentativas de mandar para a Lixeira. No Windows, logo depois de um video
# ser gerado, tocado ou mostrado no Explorer, algum programa (o proprio Explorer fazendo a miniatura, o
# antivirus, o indexador de busca) ainda segura o arquivo por um instante. Antes o Studio desistia na
# primeira falha e era preciso clicar em Excluir 2 ou 3 vezes; agora ele tenta de novo sozinho.
ESPERAS_LIXEIRA = (0.3, 0.7, 1.5)


def mandar_para_lixeira(caminhos) -> bool:
    """Manda arquivos e pastas para a Lixeira (da para restaurar). NUNCA apaga de vez. Devolve True se deu certo.
    Usa a biblioteca send2trash; se ela faltar, usa a funcao do proprio Windows.
    Manda um item por vez (um arquivo preso nao impede os outros de irem) e, se sobrar algum, espera um
    pouco e tenta de novo (ate 4 vezes no total)."""
    pendentes = [str(Path(c).resolve()) for c in caminhos if Path(c).exists()]
    for espera in (*ESPERAS_LIXEIRA, None):
        if not pendentes:
            return True
        _tentar_lixeira(pendentes)
        pendentes = _ainda_existem(pendentes)
        if pendentes and espera is not None:
            time.sleep(espera)
    return not pendentes


def _tentar_lixeira(caminhos: list):
    """Uma tentativa: manda cada item para a Lixeira, sem parar se algum falhar."""
    try:
        from send2trash import send2trash
    except ImportError:
        send2trash = None
    for c in caminhos:
        try:
            if send2trash is not None:
                send2trash(c)
            else:
                _lixeira_do_windows([c])
        except Exception:
            pass  # fica para a proxima tentativa


def _ainda_existem(caminhos: list) -> list:
    """O que ainda nao sumiu. O Windows as vezes demora um instante para tirar o item da pasta."""
    restantes = [c for c in caminhos if Path(c).exists()]
    for _ in range(5):
        if not restantes:
            break
        time.sleep(0.05)
        restantes = [c for c in restantes if Path(c).exists()]
    return restantes


def _lixeira_do_windows(caminhos: list) -> bool:
    """Reserva: a Lixeira pela funcao do Windows (SHFileOperation), sem biblioteca."""
    if os.name != "nt":
        raise OSError("A Lixeira so existe no Windows.")
    import ctypes
    from ctypes import wintypes

    class OperacaoDeArquivo(ctypes.Structure):  # SHFILEOPSTRUCTW do Windows
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("wFunc", wintypes.UINT),
            ("pFrom", wintypes.LPCWSTR),
            ("pTo", wintypes.LPCWSTR),
            ("fFlags", ctypes.c_ushort),
            ("fAnyOperationsAborted", wintypes.BOOL),
            ("hNameMappings", ctypes.c_void_p),
            ("lpszProgressTitle", wintypes.LPCWSTR),
        ]

    apagar = 3  # FO_DELETE
    # permitir desfazer (Lixeira) + sem perguntar + sem janela de erro + sem janela de progresso
    opcoes = 0x0040 | 0x0010 | 0x0400 | 0x0004
    op = OperacaoDeArquivo(None, apagar, "\0".join(caminhos) + "\0\0", None, opcoes, False, None, None)
    resultado = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    return resultado == 0 and not op.fAnyOperationsAborted


def limpar_midia(pasta: Path) -> int:
    """Manda a midia do projeto para a Lixeira e anota no projeto.json. Devolve os bytes liberados."""
    itens = midia_do_projeto(pasta)
    if not mandar_para_lixeira([f for f, _ in itens]):
        raise OSError("O Windows nao conseguiu mandar tudo para a Lixeira (algum video esta aberto no player?).")
    projeto = ler_json(pasta / "projeto.json", {}) or {}
    projeto["limpo_em"] = datetime.now().isoformat(timespec="seconds")
    gravar_json(pasta / "projeto.json", projeto)
    return sum(t for _, t in itens)


def excluir_short(pasta: Path, n: int, arquivo: str):
    """Exclui um Short: o .mp4 vai para a Lixeira, sai da lista de publicacao e o corte fica marcado como
    descartado (para o "Gerar Shorts" nao fazer ele de novo). A transcricao e os outros cortes ficam."""
    from shorts.cortes import descartar_corte

    mp4 = pasta / "prontos" / arquivo
    if mp4.exists() and not mandar_para_lixeira([mp4]):
        raise OSError("O Windows não conseguiu mandar o Short para a Lixeira (ele está aberto no player?).")
    arq = pasta / "prontos" / "publicacao.json"
    pub = ler_json(arq, None)
    if isinstance(pub, dict) and isinstance(pub.get("shorts"), list):
        pub["shorts"] = [s for s in pub["shorts"] if s.get("n") != n]
        gravar_json(arq, pub)
    descartar_corte(pasta, n)


def apagar_projeto(pasta: Path):
    """Manda a pasta inteira do projeto para a Lixeira (inclusive o resumo)."""
    if not mandar_para_lixeira([pasta]):
        raise OSError("O Windows nao conseguiu mandar o projeto para a Lixeira (algum arquivo esta aberto?).")

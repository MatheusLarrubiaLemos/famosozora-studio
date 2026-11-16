# Limpar projeto: depois de postar, manda para a Lixeira a midia pesada do projeto (Shorts, episodio,
# versoes antigas e temporarios) e guarda um resumo pequeno (cortes, edicao, textos e o que foi postado).
# Nada e apagado de vez: tudo vai para a Lixeira do Windows, de onde da para restaurar.
import os
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


def tamanho_txt(n_bytes: int) -> str:
    if n_bytes >= 1_000_000_000:
        return f"{n_bytes / 1_000_000_000:.1f} GB".replace(".", ",")
    return f"{n_bytes / 1_000_000:.0f} MB"


def mandar_para_lixeira(caminhos) -> bool:
    """Manda arquivos e pastas para a Lixeira (da para restaurar). NUNCA apaga de vez. Devolve True se deu certo.
    Usa a biblioteca send2trash; se ela faltar, usa a funcao do proprio Windows."""
    caminhos = [str(Path(c).resolve()) for c in caminhos if Path(c).exists()]
    if not caminhos:
        return True
    try:
        from send2trash import send2trash
    except ImportError:
        return _lixeira_do_windows(caminhos)
    try:
        send2trash(caminhos)
    except Exception:
        return False
    return not any(Path(c).exists() for c in caminhos)


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

# FamosoZora Studio: um painel so pra todo o processo dos Shorts e do video longo.
#   1 Transcrever -> 2 Pedir cortes ao Claude -> 3 Gerar Shorts -> 4 Publicar (Buffer)
#   5 Editar video longo (edicao.json do Claude -> revisao -> episodio)
import os
import shutil
import subprocess
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from comum import (APP_INSTALADO, CANAL_URL, DADOS_APP, FERRAMENTAS, PASTA_APP, PASTA_CANAL, PASTA_CONFIG,
                   PASTA_MUSICAS, PASTA_SHORTS, PASTA_VIDEOS, REPO_URL, VERSAO, carregar_config, gravar_json,
                   ler_ajustes, ler_json, pasta_trabalho_padrao, preparar_pasta_trabalho, salvar_ajustes, tempo_txt)

BUFFER_URL = "https://publish.buffer.com"
REDES = [("youtube", "YouTube"), ("tiktok", "TikTok"), ("instagram", "Instagram")]
IGNORAR = {"ferramentas", "musicas", "__pycache__"}


def primeiro_existente(*caminhos):
    for c in caminhos:
        if Path(c).exists():
            return Path(c)
    return Path(caminhos[0])


# app instalado: tudo na raiz do programa; pasta do GitHub: guias em docs\
ARQ_GUIA = primeiro_existente(PASTA_APP / "COMO USAR.md", PASTA_APP / "docs" / "COMO USAR.md")
ARQ_NOVIDADES = PASTA_APP / "CHANGELOG.md"
ARQ_DIRETRIZES = primeiro_existente(PASTA_APP / "DIRETRIZES DO CANAL.md", PASTA_APP / "docs" / "DIRETRIZES DO CANAL.md")
BAT_DEV = PASTA_APP / "Studio (modo desenvolvedor).bat"


def tem_nvidia() -> bool:
    return bool(shutil.which("nvidia-smi")) or Path(r"C:\Windows\System32\nvidia-smi.exe").exists()


def gpu_baixada() -> bool:
    return any((DADOS_APP / "gpu" / "nvidia").glob("*/bin/*.dll"))

PY = Path(sys.executable)
PY_CONSOLE = PY.with_name("python.exe") if PY.name.lower() == "pythonw.exe" else PY
PY_JANELA = PY.with_name("pythonw.exe") if PY.with_name("pythonw.exe").exists() else PY

COR_FUNDO = "#14141f"
COR_TEXTO = "#ffffff"
COR_DESTAQUE = "#ffd400"


def achar_git():
    """git do PATH ou o que vem junto com o GitHub Desktop."""
    g = shutil.which("git")
    if g:
        return g
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "GitHubDesktop"
    achados = sorted(base.glob("app-*/resources/app/git/cmd/git.exe"))
    return str(achados[-1]) if achados else None


# ------------------------------------------------------------------ utilidades
def abrir(caminho):
    caminho = str(caminho)
    if not hasattr(os, "startfile"):
        print("ABRIR:", caminho)
        return
    try:
        os.startfile(caminho)
    except OSError:
        # sem programa associado (ex.: .md ou .json): abre no Bloco de Notas
        subprocess.Popen(["notepad.exe", caminho])


def abrir_texto(caminho):
    if os.name == "nt":
        subprocess.Popen(["notepad.exe", str(caminho)])
    else:
        print("ABRIR TEXTO:", caminho)


def mostrar_na_pasta(arquivo: Path):
    if os.name == "nt":
        subprocess.Popen(f'explorer /select,"{arquivo}"')
    else:
        print("MOSTRAR:", arquivo)


def rodar_script(script: str, *args, console=True):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", HF_HUB_DISABLE_SYMLINKS_WARNING="1")
    if console:
        flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        cmd = [str(PY_CONSOLE), str(FERRAMENTAS / script), *map(str, args), "--pausar"]
        return subprocess.Popen(cmd, creationflags=flags, env=env, cwd=str(FERRAMENTAS))
    cmd = [str(PY_JANELA), str(FERRAMENTAS / script), *map(str, args)]
    return subprocess.Popen(cmd, env=env, cwd=str(FERRAMENTAS))


def info_projeto(p: Path) -> dict:
    cortes = ler_json(p / "cortes.json", None)
    lista = (cortes.get("cortes", []) if isinstance(cortes, dict) else cortes) if cortes else []
    prontos = p / "prontos"
    mp4 = [f for f in prontos.glob("*.mp4") if not f.name.startswith("_")] if prontos.exists() else []
    pub = ler_json(prontos / "publicacao.json", {}) or {}
    shorts_pub = pub.get("shorts", [])
    postados = sum(1 for s in shorts_pub if all(s.get("postado", {}).get(r) for r, _ in REDES))
    info = {
        "pasta": p, "nome": p.name,
        "transcrito": (p / "transcricao.json").exists(),
        "n_cortes": len(lista), "tem_cortes": cortes is not None,
        "n_shorts": len(mp4), "postados": postados, "n_pub": len(shorts_pub),
        "projeto": ler_json(p / "projeto.json", {}) or {},
        "episodio": estado_episodio(p),
    }
    if not info["transcrito"]:
        passo = "Transcrever o vídeo (passo 1)."
    elif not info["tem_cortes"]:
        passo = "Pedir os cortes ao Claude (passo 2)."
    elif info["n_shorts"] < info["n_cortes"]:
        passo = "Gerar os Shorts (passo 3)."
    elif info["postados"] < info["n_shorts"]:
        passo = "Publicar no YouTube, TikTok e Instagram pelo Buffer (passo 4)."
    else:
        passo = "Tudo postado! Bora pro próximo vídeo."
    info["passo"] = passo
    return info


def estado_episodio(p: Path) -> str:
    """'-' sem edicao.json, 'revisar' com edicao.json e sem episodio, 'ok' com o episodio gerado."""
    ep = p / "episodio"
    if ep.exists() and any(not f.name.startswith("_") for f in ep.glob("*.mp4")):
        return "ok"
    return "revisar" if (p / "edicao.json").exists() else "-"


def listar_projetos():
    if not PASTA_SHORTS.exists():
        return []
    pastas = [p for p in PASTA_SHORTS.iterdir()
              if p.is_dir() and p.name not in IGNORAR
              and ((p / "projeto.json").exists() or (p / "transcricao.json").exists())]
    pastas.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [info_projeto(p) for p in pastas]


# ------------------------------------------------------------------ janela principal
class Studio:
    def __init__(self):
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        self.raiz = tk.Tk()
        self.raiz.title(f"FamosoZora Studio {VERSAO}")
        self.raiz.geometry("1120x700")
        self.raiz.minsize(940, 560)
        self.raiz.configure(bg=COR_FUNDO)
        estilo = ttk.Style()
        try:
            estilo.theme_use("clam")
        except Exception:
            pass
        estilo.configure("Treeview", rowheight=30, font=("Segoe UI", 10))
        estilo.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        estilo.configure("Passo.TButton", font=("Segoe UI", 11, "bold"), padding=(10, 9))
        estilo.configure("Extra.TButton", font=("Segoe UI", 10), padding=(8, 5))
        estilo.configure("Sec.TLabel", background=COR_FUNDO, foreground="#9a9ab0", font=("Segoe UI", 9, "bold"))

        topo = tk.Frame(self.raiz, bg=COR_FUNDO)
        topo.pack(fill="x", padx=18, pady=(14, 6))
        tk.Label(topo, text="FamosoZora Studio", bg=COR_FUNDO, fg=COR_DESTAQUE,
                 font=("Segoe UI", 20, "bold")).pack(side="left")
        tk.Label(topo, text="   do vídeo longo aos Shorts, num lugar só", bg=COR_FUNDO, fg="#c8c8d8",
                 font=("Segoe UI", 11)).pack(side="left", pady=(8, 0))
        tk.Label(topo, text=f"versão {VERSAO}", bg=COR_FUNDO, fg="#7a7a90",
                 font=("Segoe UI", 10)).pack(side="right", pady=(8, 0))

        corpo = tk.Frame(self.raiz, bg=COR_FUNDO)
        corpo.pack(fill="both", expand=True, padx=18, pady=6)

        esq = tk.Frame(corpo, bg=COR_FUNDO)
        esq.pack(side="left", fill="both", expand=True)
        colunas = ("transcricao", "cortes", "shorts", "postados", "episodio")
        self.tree = ttk.Treeview(esq, columns=colunas, show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="Vídeo")
        self.tree.column("#0", width=380, anchor="w")
        for col, txt, w in [("transcricao", "Transcrição", 100), ("cortes", "Cortes", 80),
                            ("shorts", "Shorts", 80), ("postados", "Postados", 90), ("episodio", "Episódio", 90)]:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.atualizar_passo())
        self.tree.bind("<Double-1>", lambda e: self.abrir_pasta())

        self.lbl_passo = tk.Label(esq, text="", bg="#232336", fg=COR_TEXTO, anchor="w", justify="left",
                                  font=("Segoe UI", 11), padx=12, pady=10)
        self.lbl_passo.pack(fill="x", pady=(8, 0))

        dir_ = tk.Frame(corpo, bg=COR_FUNDO)
        dir_.pack(side="right", fill="y", padx=(16, 0))

        def secao(txt):
            ttk.Label(dir_, text=txt, style="Sec.TLabel").pack(anchor="w", pady=(10, 3))

        def botao(txt, cmd, estilo_="Extra.TButton"):
            b = ttk.Button(dir_, text=txt, command=cmd, style=estilo_, width=30)
            b.pack(fill="x", pady=2)
            return b

        secao("PASSO A PASSO")
        botao("1   Transcrever vídeo novo", self.transcrever, "Passo.TButton")
        botao("2   Pedir cortes ao Claude", self.pedir_cortes, "Passo.TButton")
        botao("3   Gerar Shorts", self.gerar, "Passo.TButton")
        botao("4   Publicar (Buffer)", self.publicar, "Passo.TButton")
        botao("5   Editar vídeo longo", self.editar_longo, "Passo.TButton")
        secao("PROJETO SELECIONADO")
        botao("Colar edicao.json", self.colar_edicao)
        botao("Link do vídeo completo...", self.definir_link)
        botao("Abrir pasta do projeto", self.abrir_pasta)
        secao("FERRAMENTAS")
        botao("Marcar câmera e gameplay", lambda: rodar_script("marcar_camera.py", console=False))
        botao("Juntar vídeos (partes)", self.juntar)
        botao(f"Novidades da versão {VERSAO}", self.novidades)
        botao("Procurar atualização", self.atualizar_github)

        mais = ttk.Menubutton(dir_, text="Mais opções  ▾", width=30)
        menu = tk.Menu(mais, tearoff=0, font=("Segoe UI", 10))
        menu.add_command(label="Músicas de fundo", command=lambda: self.abrir_pasta_segura(PASTA_MUSICAS))
        menu.add_command(label="Configurações (config.json)", command=lambda: abrir_texto(PASTA_CONFIG / "config.json"))
        menu.add_command(label="Vocabulário (nomes do canal)", command=lambda: abrir_texto(PASTA_CONFIG / "vocabulario.txt"))
        menu.add_command(label="Correções automáticas", command=lambda: abrir_texto(PASTA_CONFIG / "correcoes.txt"))
        menu.add_command(label="Diretrizes do canal (o que o Claude segue)", command=lambda: abrir(ARQ_DIRETRIZES))
        menu.add_command(label="Guia: COMO USAR", command=lambda: abrir(ARQ_GUIA))
        menu.add_separator()
        menu.add_command(label="Abrir pasta de trabalho", command=lambda: self.abrir_pasta_segura(PASTA_CANAL))
        menu.add_command(label="Mudar pasta de trabalho...", command=self.mudar_pasta_trabalho)
        if APP_INSTALADO:
            menu.add_command(label="Ativar placa de vídeo NVIDIA", command=self.instalar)
        else:
            menu.add_command(label="Atualizar dependências (modo desenvolvedor)", command=self.instalar)
        mais["menu"] = menu
        mais.pack(fill="x", pady=(8, 2))

        self.atualizar()
        self.raiz.after(4000, self.auto_atualizar)
        self.raiz.after(600, self.boas_vindas)

    # ---------------------------------------------------------- lista
    def atualizar(self, forcar=True):
        sel = self.selecionado()
        nome_sel = sel["nome"] if sel else None
        novos = {i["nome"]: i for i in listar_projetos()}
        assinatura = [(n, i["transcrito"], i["n_cortes"], i["n_shorts"], i["postados"], i["n_pub"], i["passo"],
                       i["projeto"].get("link_video_completo"), i["episodio"]) for n, i in novos.items()]
        if not forcar and assinatura == getattr(self, "_assinatura", None):
            return
        self._assinatura = assinatura
        self.projetos = novos
        self.tree.delete(*self.tree.get_children())
        for nome, i in self.projetos.items():
            self.tree.insert("", "end", iid=nome, text="  " + nome, values=(
                "ok" if i["transcrito"] else "-",
                i["n_cortes"] if i["tem_cortes"] else "-",
                f"{i['n_shorts']}/{i['n_cortes']}" if i["tem_cortes"] else "-",
                f"{i['postados']}/{i['n_pub']}" if i["n_pub"] else "-",
                i["episodio"],
            ))
        if nome_sel in self.projetos:
            self.tree.selection_set(nome_sel)
        elif self.projetos:
            self.tree.selection_set(next(iter(self.projetos)))
        self.atualizar_passo()

    def auto_atualizar(self):
        try:
            self.atualizar(forcar=False)
        finally:
            self.raiz.after(4000, self.auto_atualizar)

    def selecionado(self):
        try:
            sel = self.tree.selection()
        except Exception:
            return None
        if not sel:
            return None
        return getattr(self, "projetos", {}).get(sel[0])

    def atualizar_passo(self):
        i = self.selecionado()
        if not i:
            self.lbl_passo.config(text="Nenhum vídeo ainda. Comece pelo passo 1: Transcrever vídeo novo.")
            return
        link = i["projeto"].get("link_video_completo") or "(ainda não definido: usa o link do canal)"
        ep = {"-": "ainda não editado (passo 5)", "revisar": "edicao.json pronto: revisar e gerar (passo 5)",
              "ok": "episódio gerado (pasta episodio)"}[i["episodio"]]
        self.lbl_passo.config(text=f"{i['nome']}\nPróximo passo: {i['passo']}\nLink do vídeo completo: {link}"
                                   f"\nVídeo longo: {ep}")

    def exigir(self):
        i = self.selecionado()
        if not i:
            messagebox.showinfo("FamosoZora Studio", "Selecione um vídeo na lista primeiro.")
        return i

    # ---------------------------------------------------------- passos
    def transcrever(self):
        rodar_script("transcrever.py")

    def pedir_cortes(self):
        i = self.exigir()
        if not i:
            return
        if not i["transcrito"]:
            messagebox.showinfo("Pedir cortes", "Esse vídeo ainda não foi transcrito. Faça o passo 1 antes.")
            return
        texto = (f'Claude, escolhe os cortes do projeto "{i["nome"]}".\n'
                 f'Pasta: {i["pasta"]}\n'
                 f'Siga as DIRETRIZES DO CANAL ({ARQ_DIRETRIZES}). Resumo:\n'
                 "- O vídeo é a versão bruta da live: escolha momentos em que estou JOGANDO "
                 "(nada de espera, menu, intro ou papo fora do jogo).\n"
                 "- O Short apresenta, o vídeo longo aprofunda: cada corte se entende sozinho, com começo, "
                 "meio e fim, sem picotar, e deixa vontade de ver o vídeo completo.\n"
                 "- Título honesto e chamativo, alinhado ao que acontece no corte (sem mentir). "
                 "Se for série, cite o episódio.\n"
                 "- Falas naturais, palavrão pode ficar. Pouca hashtag; o conteúdo é que vende.\n"
                 "- Inclua também título e descrição em inglês (youtube_titulo_en, youtube_descricao_en).\n"
                 "Legenda corrigida e textos pra YouTube, TikTok e Instagram. Salva o cortes.json na pasta.")
        self.copiar(texto)
        messagebox.showinfo("Pedir cortes ao Claude",
                            "Pedido copiado!\n\nAgora cole (Ctrl+V) na conversa com o Claude e envie.\n"
                            "Quando ele avisar que salvou o cortes.json, volte aqui e clique em 3 - Gerar Shorts.")

    def gerar(self):
        i = self.exigir()
        if not i:
            return
        if not i["tem_cortes"]:
            messagebox.showinfo("Gerar Shorts", "Esse vídeo ainda não tem cortes. Faça o passo 2 antes.")
            return
        cfg = carregar_config()
        if cfg.get("layout") == "camera" and not cfg.get("camera_area"):
            if not messagebox.askyesno("Câmera não marcada",
                                       "O formato com câmera em cima ainda não foi marcado.\n"
                                       "Quer gerar assim mesmo (com fundo desfocado)?"):
                return
        prontos = i["pasta"] / "prontos"
        existentes = [f for f in prontos.glob("*.mp4") if not f.name.startswith("_")] if prontos.exists() else []
        if existentes:
            r = messagebox.askyesnocancel(
                "Gerar Shorts",
                f"Já existem {len(existentes)} Shorts desse vídeo.\n\n"
                "SIM = refazer TODOS (os atuais vao para a pasta 'antigos')\n"
                "NÃO = gerar só os que faltam\n"
                "CANCELAR = não fazer nada")
            if r is None:
                return
            if r:
                destino = prontos / "antigos" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                destino.mkdir(parents=True, exist_ok=True)
                for f in existentes:
                    shutil.move(str(f), str(destino / f.name))
        rodar_script("gerar_shorts.py", i["pasta"])

    def publicar(self):
        i = self.exigir()
        if not i:
            return
        pub = ler_json(i["pasta"] / "prontos" / "publicacao.json", None)
        if not pub or not pub.get("shorts"):
            messagebox.showinfo("Publicar", "Esse vídeo ainda não tem Shorts gerados. Faça o passo 3 antes.")
            return
        JanelaPublicar(self, i)

    def editar_longo(self):
        i = self.exigir()
        if not i:
            return
        if not i["transcrito"]:
            messagebox.showinfo("Editar vídeo longo", "Esse vídeo ainda não foi transcrito. Faça o passo 1 antes.")
            return
        if not (i["pasta"] / "edicao.json").exists():
            self.pedir_edicao(i)
            return
        JanelaEdicao(self, i)

    def pedir_edicao(self, i, parent=None):
        from pedido_edicao import info_video, texto_pedido
        _, dur = info_video(i["pasta"])
        self.copiar(texto_pedido(i["nome"], i["pasta"], ARQ_DIRETRIZES, dur))
        messagebox.showinfo("Editar vídeo longo",
                            "Pedido de edição copiado!\n\nAgora cole (Ctrl+V) na conversa com o Claude e envie.\n"
                            "Quando ele avisar que salvou o edicao.json, selecione o vídeo e clique em "
                            "5 - Editar vídeo longo de novo para revisar.\n\n"
                            "Se a conversa não tiver acesso ao PC, copie o JSON que o Claude mandar e clique em "
                            "\"Colar edicao.json\".", parent=parent or self.raiz)

    def colar_edicao(self, i=None, parent=None):
        """Le o edicao.json da area de transferencia, valida e salva na pasta do projeto."""
        from pedido_edicao import erro_json_amigavel, extrair_json, info_video, normalizar
        i = i or self.exigir()
        if not i:
            return False
        parent = parent or self.raiz
        try:
            texto = self.raiz.clipboard_get()
        except tk.TclError:
            texto = ""
        if not texto.strip():
            messagebox.showinfo("Colar edicao.json", "A área de transferência está vazia.\n"
                                "Copie o JSON que o Claude mandou e clique aqui de novo.", parent=parent)
            return False
        try:
            bruto = extrair_json(texto)
        except Exception as e:
            messagebox.showerror("Colar edicao.json", erro_json_amigavel(e), parent=parent)
            return False
        _, dur = info_video(i["pasta"])
        dados, erros, avisos = normalizar(bruto, dur)
        if erros:
            messagebox.showerror("Colar edicao.json", "O edicao.json tem problemas e NÃO foi salvo:\n\n- "
                                 + "\n- ".join(erros[:12]) + "\n\nPeça pro Claude corrigir.", parent=parent)
            return False
        arq = i["pasta"] / "edicao.json"
        if arq.exists():
            if not messagebox.askyesno("Colar edicao.json", "Esse vídeo já tem um edicao.json.\n\n"
                                       "Substituir pelo que você copiou?\n(o atual vira edicao_anterior.json)",
                                       parent=parent):
                return False
            shutil.copy2(arq, i["pasta"] / "edicao_anterior.json")
        gravar_json(arq, dados)
        n = len(dados.get("cortes", []))
        msg = f"edicao.json salvo com {n} cortes e {len(dados.get('capitulos', []))} capítulos."
        if avisos:
            msg += "\n\nAvisos:\n- " + "\n- ".join(avisos[:10])
        messagebox.showinfo("Colar edicao.json", msg, parent=parent)
        self.atualizar()
        return True

    # ---------------------------------------------------------- extras
    def definir_link(self):
        i = self.exigir()
        if not i:
            return
        atual = i["projeto"].get("link_video_completo", "")
        link = simpledialog.askstring("Link do vídeo completo",
                                      "Cole o link do vídeo longo no YouTube\n(vai na descrição dos Shorts):",
                                      initialvalue=atual, parent=self.raiz)
        if link is None:
            return
        link = link.strip()
        if link and not link.startswith("http"):
            link = "https://" + link
        projeto = ler_json(i["pasta"] / "projeto.json", {}) or {}
        projeto["link_video_completo"] = link
        gravar_json(i["pasta"] / "projeto.json", projeto)
        self.atualizar()

    def abrir_pasta(self):
        i = self.exigir()
        if i:
            alvo = i["pasta"] / "prontos" if (i["pasta"] / "prontos").exists() else i["pasta"]
            abrir(alvo)

    def abrir_pasta_segura(self, pasta: Path):
        pasta.mkdir(parents=True, exist_ok=True)
        abrir(pasta)

    def juntar(self):
        ps1 = FERRAMENTAS / "juntar_videos_gui.ps1"
        if not ps1.exists():
            messagebox.showinfo("Juntar vídeos", f"Não achei {ps1}.")
            return
        PASTA_VIDEOS.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-STA",
                          "-WindowStyle", "Hidden", "-File", str(ps1)],
                         env=dict(os.environ, FAMOSOZORA_VIDEOS=str(PASTA_VIDEOS)))

    def instalar(self):
        if APP_INSTALADO:
            if not tem_nvidia() and not messagebox.askyesno(
                    "Placa de vídeo", "Não achei uma placa NVIDIA neste computador. Tentar ativar mesmo assim?"):
                return
            rodar_script("ativar_gpu.py")
            return
        if BAT_DEV.exists():
            subprocess.Popen(["cmd", "/c", "start", "", str(BAT_DEV), "instalar"], cwd=str(PASTA_APP))

    # ---------------------------------------------------------- app: versao, pasta, GPU
    def boas_vindas(self):
        ajustes = ler_ajustes()
        if not ajustes.get("pasta_trabalho"):
            usar = messagebox.askyesno(
                "Bem-vindo ao FamosoZora Studio",
                f"Seus vídeos, transcrições e Shorts vão ficar nesta pasta:\n\n{PASTA_CANAL}\n\n"
                "SIM = usar essa pasta\nNÃO = escolher outra (por exemplo, a pasta que você já usa)")
            if not usar and self.mudar_pasta_trabalho():
                return
            salvar_ajustes({"pasta_trabalho": str(PASTA_CANAL)})
            preparar_pasta_trabalho()
            self.atualizar()
        if ajustes.get("ultima_versao_vista") != VERSAO:
            salvar_ajustes({"ultima_versao_vista": VERSAO})
            if ajustes.get("ultima_versao_vista"):          # atualizou: mostra o que mudou
                self.novidades()
        if APP_INSTALADO and tem_nvidia() and not gpu_baixada() and not ajustes.get("perguntou_gpu"):
            salvar_ajustes({"perguntou_gpu": True})
            if messagebox.askyesno("Placa de vídeo NVIDIA encontrada",
                                   "Quer ativar a placa de vídeo para transcrever MUITO mais rápido?\n\n"
                                   "Vai baixar cerca de 1 GB (só uma vez)."):
                self.instalar()

    def novidades(self):
        JanelaTexto(self.raiz, f"Novidades - FamosoZora Studio {VERSAO}", ARQ_NOVIDADES)

    def mudar_pasta_trabalho(self):
        from tkinter import filedialog
        nova = filedialog.askdirectory(title="Escolha a pasta de trabalho (vídeos e Shorts)",
                                       initialdir=str(PASTA_CANAL))
        if not nova or Path(nova) == PASTA_CANAL:
            return False
        salvar_ajustes({"pasta_trabalho": str(Path(nova))})
        messagebox.showinfo("Pasta de trabalho", f"Pronto! A pasta agora é:\n{nova}\n\nO Studio vai reabrir.")
        subprocess.Popen([str(PY_JANELA), str(FERRAMENTAS / "painel.py")], cwd=str(FERRAMENTAS))
        self.raiz.destroy()
        return True

    def atualizar_github(self):
        if APP_INSTALADO:
            webbrowser.open(REPO_URL + "/releases/latest")
            messagebox.showinfo("Procurar atualização",
                                f"Você está na versão {VERSAO}.\n\nAbri a página do GitHub no navegador. Se lá tiver "
                                "uma versão maior, baixe o arquivo \"FamosoZora-Studio-Setup-....exe\" e instale "
                                "por cima (seus vídeos e Shorts não são apagados).")
            return
        git = achar_git()
        if not git:
            messagebox.showinfo("Atualizar", "Não achei o Git.\n\nAbra o GitHub Desktop e clique em "
                                "\"Fetch origin\" e depois em \"Pull origin\".")
            return
        if not (PASTA_APP / ".git").exists():
            messagebox.showinfo("Atualizar", "Esta pasta ainda não está ligada ao GitHub.\n"
                                "Abra o GitHub Desktop e adicione esta pasta como repositório.")
            return
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            r = subprocess.run([git, "-C", str(PASTA_APP), "pull", "--ff-only"], capture_output=True,
                               text=True, encoding="utf-8", errors="replace", timeout=180, creationflags=flags)
        except Exception as e:
            messagebox.showerror("Atualizar", f"Não consegui atualizar:\n{e}")
            return
        saida = (r.stdout + "\n" + r.stderr).strip()
        if r.returncode != 0:
            messagebox.showerror("Atualizar", "Não consegui atualizar pelo Studio.\n"
                                 "Use o GitHub Desktop: \"Fetch origin\" → \"Pull origin\".\n\n" + saida[-800:])
        elif "Already up to date" in saida or "Já está atualizado" in saida:
            messagebox.showinfo("Atualizar", "Você já está com a versão mais nova.")
        else:
            messagebox.showinfo("Atualizar", "Programa atualizado!\n\nFeche e abra o FamosoZora Studio de novo.\n"
                                "Se o Claude disse que mudou o instalador, clique em \"Instalar / atualizar\".")

    def copiar(self, texto: str):
        self.raiz.clipboard_clear()
        self.raiz.clipboard_append(texto)
        self.raiz.update()

    def rodar(self):
        self.raiz.mainloop()


# ------------------------------------------------------------------ janela de texto (novidades)
class JanelaTexto:
    def __init__(self, raiz, titulo: str, arquivo: Path):
        jan = tk.Toplevel(raiz)
        jan.title(titulo)
        jan.geometry("760x620")
        jan.configure(bg=COR_FUNDO)
        txt = tk.Text(jan, wrap="word", bg="#1c1c2b", fg=COR_TEXTO, insertbackground=COR_TEXTO,
                      font=("Segoe UI", 11), padx=16, pady=12, relief="flat")
        barra = ttk.Scrollbar(jan, command=txt.yview)
        txt.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        txt.pack(fill="both", expand=True)
        txt.tag_configure("h1", font=("Segoe UI", 16, "bold"), foreground=COR_DESTAQUE, spacing1=8, spacing3=6)
        txt.tag_configure("h2", font=("Segoe UI", 13, "bold"), foreground=COR_DESTAQUE, spacing1=10, spacing3=4)
        txt.tag_configure("h3", font=("Segoe UI", 11, "bold"), foreground="#c8c8ff", spacing1=6)
        try:
            linhas = arquivo.read_text(encoding="utf-8").splitlines()
        except Exception:
            linhas = [f"Não achei o arquivo {arquivo}."]
        for linha in linhas:
            limpa = linha.replace("**", "").replace("`", "")
            if limpa.startswith("### "):
                txt.insert("end", limpa[4:] + "\n", "h3")
            elif limpa.startswith("## "):
                txt.insert("end", limpa[3:] + "\n", "h2")
            elif limpa.startswith("# "):
                txt.insert("end", limpa[2:] + "\n", "h1")
            else:
                txt.insert("end", (("  •" + limpa[1:]) if limpa.startswith("- ") else limpa) + "\n")
        txt.configure(state="disabled")


# ------------------------------------------------------------------ janela de publicacao
class JanelaPublicar:
    def __init__(self, studio: Studio, info: dict):
        self.studio = studio
        self.pasta = info["pasta"]
        self.prontos = self.pasta / "prontos"
        self.arq = self.prontos / "publicacao.json"
        self.pub = ler_json(self.arq, {}) or {}
        self.link = (ler_json(self.pasta / "projeto.json", {}) or {}).get("link_video_completo") or CANAL_URL

        self.jan = tk.Toplevel(studio.raiz)
        self.jan.title(f"Publicar - {info['nome']}")
        self.jan.geometry("1060x640")
        self.jan.configure(bg=COR_FUNDO)

        topo = tk.Frame(self.jan, bg=COR_FUNDO)
        topo.pack(fill="x", padx=16, pady=(12, 4))
        tk.Label(topo, text="Publicar no YouTube, TikTok e Instagram", bg=COR_FUNDO, fg=COR_DESTAQUE,
                 font=("Segoe UI", 15, "bold")).pack(side="left")
        ttk.Button(topo, text="Abrir o Buffer", style="Passo.TButton",
                   command=lambda: webbrowser.open(BUFFER_URL)).pack(side="right")
        dica = ("No Buffer: Criar post → marque YouTube, TikTok e Instagram → arraste o vídeo "
                "('Mostrar na pasta') → personalize o texto de cada rede colando os textos abaixo → Agendar ou Publicar.")
        tk.Label(self.jan, text=dica, bg=COR_FUNDO, fg="#c8c8d8", font=("Segoe UI", 10), wraplength=1020,
                 justify="left").pack(fill="x", padx=16)

        corpo = tk.Frame(self.jan, bg=COR_FUNDO)
        corpo.pack(fill="both", expand=True, padx=16, pady=10)

        self.lista = tk.Listbox(corpo, width=46, font=("Segoe UI", 10), activestyle="none",
                                bg="#232336", fg=COR_TEXTO, selectbackground="#3a3a5a",
                                highlightthickness=0, borderwidth=0)
        self.lista.pack(side="left", fill="y")
        self.lista.bind("<<ListboxSelect>>", lambda e: self.mostrar())

        dir_ = tk.Frame(corpo, bg=COR_FUNDO)
        dir_.pack(side="left", fill="both", expand=True, padx=(14, 0))

        self.lbl_nome = tk.Label(dir_, text="", bg=COR_FUNDO, fg=COR_TEXTO, font=("Segoe UI", 12, "bold"),
                                 anchor="w", justify="left", wraplength=560)
        self.lbl_nome.pack(fill="x")
        linha = tk.Frame(dir_, bg=COR_FUNDO); linha.pack(fill="x", pady=(6, 8))
        ttk.Button(linha, text="Mostrar na pasta", style="Extra.TButton", command=self.na_pasta).pack(side="left")
        ttk.Button(linha, text="Assistir", style="Extra.TButton", command=self.assistir).pack(side="left", padx=6)

        self.vars = {}
        for rede, nome in REDES:
            quadro = tk.Frame(dir_, bg="#232336", padx=10, pady=8)
            quadro.pack(fill="x", pady=3)
            tk.Label(quadro, text=nome, bg="#232336", fg=COR_DESTAQUE, width=10, anchor="w",
                     font=("Segoe UI", 11, "bold")).pack(side="left")
            if rede == "youtube":
                for txt, campo in [("Copiar título", "titulo"), ("Copiar descrição", "descricao"), ("Copiar tags", "tags"),
                                   ("Título EN", "titulo_en"), ("Desc. EN", "descricao_en")]:
                    ttk.Button(quadro, text=txt, style="Extra.TButton",
                               command=lambda c=campo: self.copiar_youtube(c)).pack(side="left", padx=3)
            else:
                ttk.Button(quadro, text="Copiar legenda", style="Extra.TButton",
                           command=lambda r=rede: self.copiar_rede(r)).pack(side="left", padx=3)
            v = tk.BooleanVar()
            tk.Checkbutton(quadro, text="Postado", variable=v, bg="#232336", fg=COR_TEXTO, selectcolor="#14141f",
                           activebackground="#232336", activeforeground=COR_TEXTO, font=("Segoe UI", 10),
                           command=lambda r=rede: self.marcar(r)).pack(side="right")
            self.vars[rede] = v

        tk.Label(dir_, text="Prévia do texto (o que você copiar aparece aqui):", bg=COR_FUNDO, fg="#9a9ab0",
                 font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x", pady=(10, 2))
        self.txt = tk.Text(dir_, height=11, wrap="word", font=("Segoe UI", 10), bg="#0e0e16", fg=COR_TEXTO,
                           insertbackground=COR_TEXTO, relief="flat", padx=8, pady=6)
        self.txt.pack(fill="both", expand=True)

        self.preencher_lista()
        if self.shorts():
            self.lista.selection_set(0)
            self.mostrar()

    def shorts(self):
        return self.pub.get("shorts", [])

    def preencher_lista(self):
        sel = self.lista.curselection()
        self.lista.delete(0, "end")
        for s in self.shorts():
            p = s.get("postado", {})
            feito = sum(1 for r, _ in REDES if p.get(r))
            marca = "OK " if feito == len(REDES) else f"{feito}/3"
            self.lista.insert("end", f" [{marca}]  {s['arquivo']}")
        if sel:
            self.lista.selection_set(sel[0])

    def atual(self):
        sel = self.lista.curselection()
        return self.shorts()[sel[0]] if sel else None

    def mostrar(self):
        s = self.atual()
        if not s:
            return
        self.lbl_nome.config(text=f"{s['arquivo']}   ({s.get('duracao', '?')}s)")
        for rede, _ in REDES:
            self.vars[rede].set(bool(s.get("postado", {}).get(rede)))
        self.mostrar_texto(s["textos"]["youtube"]["titulo"])

    def preencher(self, t: str) -> str:
        return t.replace("{link}", self.link).replace("{canal}", CANAL_URL)

    def mostrar_texto(self, t: str):
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", t)

    def copiar(self, t: str):
        t = self.preencher(t)
        self.studio.copiar(t)
        self.mostrar_texto(t)

    def copiar_youtube(self, campo):
        s = self.atual()
        if s:
            v = s["textos"]["youtube"].get(campo, "")
            self.copiar(", ".join(v) if isinstance(v, list) else v)

    def copiar_rede(self, rede):
        s = self.atual()
        if s:
            self.copiar(s["textos"].get(rede, ""))

    def marcar(self, rede):
        s = self.atual()
        if not s:
            return
        s.setdefault("postado", {})[rede] = bool(self.vars[rede].get())
        gravar_json(self.arq, self.pub)
        self.preencher_lista()
        self.studio.atualizar()

    def arquivo(self):
        s = self.atual()
        return self.prontos / s["arquivo"] if s else None

    def na_pasta(self):
        a = self.arquivo()
        if a:
            mostrar_na_pasta(a)

    def assistir(self):
        a = self.arquivo()
        if a and a.exists():
            abrir(a)


# ------------------------------------------------------------------ janela de revisao do video longo
class JanelaEdicao:
    """Revisao do edicao.json: o que SAI, caixinha para desmarcar, ouvir emenda, previa e gerar."""

    def __init__(self, studio: Studio, info: dict):
        from pedido_edicao import carregar_palavras, fps_fracao, info_video
        self.studio = studio
        self.info = info
        self.pasta = info["pasta"]
        self.arq = self.pasta / "edicao.json"
        self.video, self.dur = info_video(self.pasta)
        self.fps = fps_fracao(self.video) if self.video.exists() else None
        self.palavras = carregar_palavras(self.pasta)

        self.jan = tk.Toplevel(studio.raiz)
        self.jan.title(f"Editar vídeo longo - {info['nome']}")
        self.jan.geometry("1120x680")
        self.jan.configure(bg=COR_FUNDO)

        topo = tk.Frame(self.jan, bg=COR_FUNDO)
        topo.pack(fill="x", padx=16, pady=(12, 2))
        tk.Label(topo, text="Revisar a edição do vídeo longo", bg=COR_FUNDO, fg=COR_DESTAQUE,
                 font=("Segoe UI", 15, "bold")).pack(side="left")
        self.lbl_dur = tk.Label(self.jan, text="", bg=COR_FUNDO, fg=COR_TEXTO, font=("Segoe UI", 13, "bold"),
                                anchor="w")
        self.lbl_dur.pack(fill="x", padx=16)
        self.lbl_info = tk.Label(self.jan, text="", bg=COR_FUNDO, fg="#c8c8d8", font=("Segoe UI", 10),
                                 anchor="w", justify="left", wraplength=1080)
        self.lbl_info.pack(fill="x", padx=16, pady=(2, 6))

        meio = tk.Frame(self.jan, bg=COR_FUNDO)
        meio.pack(fill="both", expand=True, padx=16)
        cols = ("sai", "inicio", "fim", "dur", "motivo", "aviso")
        self.tree = ttk.Treeview(meio, columns=cols, show="headings", selectmode="browse")
        for col, txt, w, anc in [("sai", "Sai?", 50, "center"), ("inicio", "Início", 90, "center"),
                                 ("fim", "Fim", 90, "center"), ("dur", "Duração", 80, "center"),
                                 ("motivo", "Motivo (o que sai)", 600, "w"), ("aviso", "Aviso", 150, "w")]:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor=anc, stretch=(col == "motivo"))
        barra = ttk.Scrollbar(meio, command=self.tree.yview)
        self.tree.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.tag_configure("off", foreground="#8a8aa0")
        self.tree.tag_configure("curto", foreground="#ffb347")
        self.tree.bind("<Button-1>", self.clique)
        self.tree.bind("<space>", lambda e: self.alternar())
        self.tree.bind("<Double-1>", lambda e: self.ouvir())
        tk.Label(self.jan, text="Clique na caixinha (ou aperte Espaço) para desmarcar um corte: o trecho desmarcado "
                 "FICA no episódio. Duplo clique = Ouvir emenda.", bg=COR_FUNDO, fg="#9a9ab0",
                 font=("Segoe UI", 9), anchor="w").pack(fill="x", padx=16, pady=(4, 0))

        bot = tk.Frame(self.jan, bg=COR_FUNDO)
        bot.pack(fill="x", padx=16, pady=10)
        ttk.Button(bot, text="Ouvir emenda", style="Extra.TButton", command=self.ouvir).pack(side="left")
        ttk.Button(bot, text="Gerar prévia (10 min)", style="Extra.TButton",
                   command=self.previa).pack(side="left", padx=6)
        ttk.Button(bot, text="Gerar episódio", style="Passo.TButton", command=self.gerar).pack(side="left", padx=6)
        ttk.Button(bot, text="Abrir pasta do episódio", style="Extra.TButton",
                   command=self.abrir_pasta_ep).pack(side="right")
        ttk.Button(bot, text="Colar edicao.json", style="Extra.TButton",
                   command=self.colar).pack(side="right", padx=6)
        ttk.Button(bot, text="Copiar pedido de novo", style="Extra.TButton",
                   command=lambda: self.studio.pedir_edicao(self.info, self.jan)).pack(side="right")

        self.carregar()

    # ------------------------------------------------------ dados
    def carregar(self):
        from pedido_edicao import ler_edicao
        self.dados, self.erros, self.avisos = ler_edicao(self.pasta, self.dur)
        self.mostrar()

    def mostrar(self):
        from pedido_edicao import CORTE_CURTO, capitulos_editados, montar_plano
        self.tree.delete(*self.tree.get_children())
        if self.erros or not self.dados:
            self.lbl_dur.config(text="O edicao.json tem problemas")
            self.lbl_info.config(text="- " + "\n- ".join(self.erros[:8]) + "\nPeça pro Claude corrigir "
                                 "(ou use \"Colar edicao.json\").", fg="#ff8080")
            return
        if not self.video.exists():
            self.lbl_dur.config(text="Não achei o vídeo original")
            self.lbl_info.config(text=str(self.video), fg="#ff8080")
            return
        self.plano = montar_plano(self.dados, self.dur, self.fps, self.palavras, carregar_config())
        for c in self.plano["cortes"]:
            curto = c["dur"] < CORTE_CURTO
            tags = ("off",) if not c["ativo"] else (("curto",) if curto else ())
            self.tree.insert("", "end", iid=str(c["n"]), tags=tags, values=(
                "☑" if c["ativo"] else "☐", tempo_txt(c["ini_aj"]), tempo_txt(c["fim_aj"]),
                f"{c['dur'] / 60:.0f} min" if c["dur"] >= 120 else f"{c['dur']:.0f} s",
                c["motivo"], "⚠ menos de 30 s" if curto else ""))
        sai = self.plano["dur_original"] - self.plano["dur_final"] + (
            self.plano["abertura"][1] / float(self.fps) if self.plano["abertura"] else 0)
        ativos = sum(1 for c in self.plano["cortes"] if c["ativo"])
        self.lbl_dur.config(text=f"Duração: {tempo_txt(self.plano['dur_original'])}  →  "
                                 f"{tempo_txt(self.plano['dur_final'])}      (sai {tempo_txt(sai)} em "
                                 f"{ativos} de {len(self.plano['cortes'])} cortes)")
        ab = self.plano["abertura"]
        linhas = []
        if ab:
            linhas.append(f"Abertura: {tempo_txt(ab[0] / float(self.fps))} → "
                          f"{tempo_txt((ab[0] + ab[1]) / float(self.fps))} ({ab[1] / float(self.fps):.0f} s), "
                          "com fade para preto antes do episódio.")
        else:
            linhas.append("Sem abertura.")
        caps, av_caps = capitulos_editados(self.dados, self.plano)
        linhas.append(f"Capítulos: {len(caps)}.  Título: {self.dados.get('titulo') or '(sem título)'}")
        for a in (self.avisos + av_caps)[:4]:
            linhas.append(f"⚠ {a}")
        self.lbl_info.config(text="\n".join(linhas), fg="#c8c8d8")

    def salvar(self):
        gravar_json(self.arq, self.dados)

    # ------------------------------------------------------ acoes
    def sel(self):
        s = self.tree.selection()
        return int(s[0]) if s else None

    def clique(self, ev):
        if self.tree.identify("region", ev.x, ev.y) == "cell" and self.tree.identify_column(ev.x) == "#1":
            linha = self.tree.identify_row(ev.y)
            if linha:
                self.tree.selection_set(linha)
                self.alternar()
                return "break"

    def alternar(self):
        n = self.sel()
        if not n or not self.dados:
            return
        c = self.dados["cortes"][n - 1]
        if c.get("ativo", True) is False:
            c.pop("ativo", None)
        else:
            c["ativo"] = False
        self.salvar()
        self.mostrar()
        self.tree.selection_set(str(n))
        self.tree.see(str(n))

    def pronto(self) -> bool:
        if self.erros or not self.dados or not self.video.exists():
            messagebox.showinfo("Editar vídeo longo", "Corrija o edicao.json primeiro.", parent=self.jan)
            return False
        return True

    def ouvir(self):
        n = self.sel()
        if not n:
            messagebox.showinfo("Ouvir emenda", "Selecione um corte na lista.", parent=self.jan)
            return
        if self.pronto():
            rodar_script("editar_episodio.py", self.pasta, "--emenda", n)

    def previa(self):
        if self.pronto():
            rodar_script("editar_episodio.py", self.pasta, "--previa", 600)

    def gerar(self):
        if not self.pronto():
            return
        ep = self.pasta / "episodio"
        existentes = [f for f in ep.glob("*.mp4") if not f.name.startswith("_")] if ep.exists() else []
        if existentes:
            if not messagebox.askyesno("Gerar episódio", "Esse vídeo já tem um episódio gerado.\n\n"
                                       "Gerar de novo? (o atual vai para a pasta episodio\\antigos)", parent=self.jan):
                return
            destino = ep / "antigos" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            destino.mkdir(parents=True, exist_ok=True)
            for f in existentes + [ep / "textos_episodio.txt", ep / "episodio.json"]:
                if f.exists():
                    shutil.move(str(f), str(destino / f.name))
        rodar_script("editar_episodio.py", self.pasta)
        self.studio.atualizar()

    def colar(self):
        if self.studio.colar_edicao(self.info, self.jan):
            self.carregar()

    def abrir_pasta_ep(self):
        ep = self.pasta / "episodio"
        abrir(ep if ep.exists() else self.pasta)


if __name__ == "__main__":
    try:
        if ler_ajustes().get("pasta_trabalho"):     # 1a vez: o Studio pergunta qual pasta usar
            preparar_pasta_trabalho()
        Studio().rodar()
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            messagebox.showerror("FamosoZora Studio - erro", f"{e}\n\nTire um print e mande pro Claude.")
        except Exception:
            pass

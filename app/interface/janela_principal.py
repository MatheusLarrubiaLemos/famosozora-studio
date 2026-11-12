# FamosoZora Studio: um painel so pra todo o processo dos Shorts e do video longo.
#   1 Transcrever -> 2 Pedir cortes ao Claude -> 3 Gerar Shorts -> 4 Publicar (Buffer)
#   5 Editar video longo (edicao.json do Claude -> revisao -> episodio)
import os
import shutil
import subprocess
import tkinter as tk
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from interface.janela_edicao import JanelaEdicao
from interface.janela_publicar import JanelaPublicar
from interface.janela_texto import JanelaTexto
from interface.utilidades import (
    ARQ_DIRETRIZES,
    ARQ_GUIA,
    ARQ_NOVIDADES,
    BAT_DEV,
    COR_DESTAQUE,
    COR_FUNDO,
    COR_TEXTO,
    PY_JANELA,
    abrir,
    abrir_texto,
    achar_git,
    gpu_baixada,
    rodar_script,
    tem_nvidia,
)
from nucleo.comum import (
    APP_INSTALADO,
    FERRAMENTAS,
    PASTA_APP,
    PASTA_CANAL,
    PASTA_CONFIG,
    PASTA_MUSICAS,
    PASTA_VIDEOS,
    REPO_URL,
    carregar_config,
    gravar_json,
    ler_ajustes,
    ler_json,
    preparar_pasta_trabalho,
    salvar_ajustes,
)
from nucleo.projetos import listar_projetos
from versao import VERSAO


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
        tk.Label(topo, text="FamosoZora Studio", bg=COR_FUNDO, fg=COR_DESTAQUE, font=("Segoe UI", 20, "bold")).pack(
            side="left"
        )
        tk.Label(
            topo, text="   do vídeo longo aos Shorts, num lugar só", bg=COR_FUNDO, fg="#c8c8d8", font=("Segoe UI", 11)
        ).pack(side="left", pady=(8, 0))
        tk.Label(topo, text=f"versão {VERSAO}", bg=COR_FUNDO, fg="#7a7a90", font=("Segoe UI", 10)).pack(
            side="right", pady=(8, 0)
        )

        corpo = tk.Frame(self.raiz, bg=COR_FUNDO)
        corpo.pack(fill="both", expand=True, padx=18, pady=6)

        esq = tk.Frame(corpo, bg=COR_FUNDO)
        esq.pack(side="left", fill="both", expand=True)
        colunas = ("transcricao", "cortes", "shorts", "postados", "episodio")
        self.tree = ttk.Treeview(esq, columns=colunas, show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="Vídeo")
        self.tree.column("#0", width=380, anchor="w")
        for col, txt, w in [
            ("transcricao", "Transcrição", 100),
            ("cortes", "Cortes", 80),
            ("shorts", "Shorts", 80),
            ("postados", "Postados", 90),
            ("episodio", "Episódio", 90),
        ]:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.atualizar_passo())
        self.tree.bind("<Double-1>", lambda e: self.abrir_pasta())

        self.lbl_passo = tk.Label(
            esq,
            text="",
            bg="#232336",
            fg=COR_TEXTO,
            anchor="w",
            justify="left",
            font=("Segoe UI", 11),
            padx=12,
            pady=10,
        )
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
        botao("Marcar câmera e gameplay", lambda: rodar_script("interface.marcar_camera", console=False))
        botao("Juntar vídeos (partes)", self.juntar)
        botao(f"Novidades da versão {VERSAO}", self.novidades)
        botao("Procurar atualização", self.atualizar_github)

        mais = ttk.Menubutton(dir_, text="Mais opções  ▾", width=30)
        menu = tk.Menu(mais, tearoff=0, font=("Segoe UI", 10))
        menu.add_command(label="Músicas de fundo", command=lambda: self.abrir_pasta_segura(PASTA_MUSICAS))
        menu.add_command(label="Configurações (config.json)", command=lambda: abrir_texto(PASTA_CONFIG / "config.json"))
        menu.add_command(
            label="Vocabulário (nomes do canal)", command=lambda: abrir_texto(PASTA_CONFIG / "vocabulario.txt")
        )
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
        assinatura = [
            (
                n,
                i["transcrito"],
                i["n_cortes"],
                i["n_shorts"],
                i["postados"],
                i["n_pub"],
                i["passo"],
                i["projeto"].get("link_video_completo"),
                i["episodio"],
            )
            for n, i in novos.items()
        ]
        if not forcar and assinatura == getattr(self, "_assinatura", None):
            return
        self._assinatura = assinatura
        self.projetos = novos
        self.tree.delete(*self.tree.get_children())
        for nome, i in self.projetos.items():
            self.tree.insert(
                "",
                "end",
                iid=nome,
                text="  " + nome,
                values=(
                    "ok" if i["transcrito"] else "-",
                    i["n_cortes"] if i["tem_cortes"] else "-",
                    f"{i['n_shorts']}/{i['n_cortes']}" if i["tem_cortes"] else "-",
                    f"{i['postados']}/{i['n_pub']}" if i["n_pub"] else "-",
                    i["episodio"],
                ),
            )
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
        ep = {
            "-": "ainda não editado (passo 5)",
            "revisar": "edicao.json pronto: revisar e gerar (passo 5)",
            "ok": "episódio gerado (pasta episodio)",
        }[i["episodio"]]
        self.lbl_passo.config(
            text=f"{i['nome']}\nPróximo passo: {i['passo']}\nLink do vídeo completo: {link}" f"\nVídeo longo: {ep}"
        )

    def exigir(self):
        i = self.selecionado()
        if not i:
            messagebox.showinfo("FamosoZora Studio", "Selecione um vídeo na lista primeiro.")
        return i

    # ---------------------------------------------------------- passos
    def transcrever(self):
        rodar_script("nucleo.transcrever")

    def pedir_cortes(self):
        i = self.exigir()
        if not i:
            return
        if not i["transcrito"]:
            messagebox.showinfo("Pedir cortes", "Esse vídeo ainda não foi transcrito. Faça o passo 1 antes.")
            return
        texto = (
            f'Claude, escolhe os cortes do projeto "{i["nome"]}".\n'
            f'Pasta: {i["pasta"]}\n'
            f"Siga as DIRETRIZES DO CANAL ({ARQ_DIRETRIZES}). Resumo:\n"
            "- O vídeo é a versão bruta da live: escolha momentos em que estou JOGANDO "
            "(nada de espera, menu, intro ou papo fora do jogo).\n"
            "- O Short apresenta, o vídeo longo aprofunda: cada corte se entende sozinho, com começo, "
            "meio e fim, sem picotar, e deixa vontade de ver o vídeo completo.\n"
            "- Título honesto e chamativo, alinhado ao que acontece no corte (sem mentir). "
            "Se for série, cite o episódio.\n"
            "- Falas naturais, palavrão pode ficar. Pouca hashtag; o conteúdo é que vende.\n"
            "- Inclua também título e descrição em inglês (youtube_titulo_en, youtube_descricao_en).\n"
            "Legenda corrigida e textos pra YouTube, TikTok e Instagram. Salva o cortes.json na pasta."
        )
        self.copiar(texto)
        messagebox.showinfo(
            "Pedir cortes ao Claude",
            "Pedido copiado!\n\nAgora cole (Ctrl+V) na conversa com o Claude e envie.\n"
            "Quando ele avisar que salvou o cortes.json, volte aqui e clique em 3 - Gerar Shorts.",
        )

    def gerar(self):
        i = self.exigir()
        if not i:
            return
        if not i["tem_cortes"]:
            messagebox.showinfo("Gerar Shorts", "Esse vídeo ainda não tem cortes. Faça o passo 2 antes.")
            return
        cfg = carregar_config()
        if cfg.get("layout") == "camera" and not cfg.get("camera_area"):
            if not messagebox.askyesno(
                "Câmera não marcada",
                "O formato com câmera em cima ainda não foi marcado.\n" "Quer gerar assim mesmo (com fundo desfocado)?",
            ):
                return
        prontos = i["pasta"] / "prontos"
        existentes = [f for f in prontos.glob("*.mp4") if not f.name.startswith("_")] if prontos.exists() else []
        if existentes:
            r = messagebox.askyesnocancel(
                "Gerar Shorts",
                f"Já existem {len(existentes)} Shorts desse vídeo.\n\n"
                "SIM = refazer TODOS (os atuais vao para a pasta 'antigos')\n"
                "NÃO = gerar só os que faltam\n"
                "CANCELAR = não fazer nada",
            )
            if r is None:
                return
            if r:
                destino = prontos / "antigos" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                destino.mkdir(parents=True, exist_ok=True)
                for f in existentes:
                    shutil.move(str(f), str(destino / f.name))
        rodar_script("shorts.gerar_shorts", i["pasta"])

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
        from videos_longos.pedido_edicao import info_video, texto_pedido

        _, dur = info_video(i["pasta"])
        self.copiar(texto_pedido(i["nome"], i["pasta"], ARQ_DIRETRIZES, dur))
        messagebox.showinfo(
            "Editar vídeo longo",
            "Pedido de edição copiado!\n\nAgora cole (Ctrl+V) na conversa com o Claude e envie.\n"
            "Quando ele avisar que salvou o edicao.json, selecione o vídeo e clique em "
            "5 - Editar vídeo longo de novo para revisar.\n\n"
            "Se a conversa não tiver acesso ao PC, copie o JSON que o Claude mandar e clique em "
            '"Colar edicao.json".',
            parent=parent or self.raiz,
        )

    def colar_edicao(self, i=None, parent=None):
        """Le o edicao.json da area de transferencia, valida e salva na pasta do projeto."""
        from videos_longos.pedido_edicao import erro_json_amigavel, extrair_json, info_video, normalizar

        i = i or self.exigir()
        if not i:
            return False
        parent = parent or self.raiz
        try:
            texto = self.raiz.clipboard_get()
        except tk.TclError:
            texto = ""
        if not texto.strip():
            messagebox.showinfo(
                "Colar edicao.json",
                "A área de transferência está vazia.\n" "Copie o JSON que o Claude mandou e clique aqui de novo.",
                parent=parent,
            )
            return False
        try:
            bruto = extrair_json(texto)
        except Exception as e:
            messagebox.showerror("Colar edicao.json", erro_json_amigavel(e), parent=parent)
            return False
        _, dur = info_video(i["pasta"])
        dados, erros, avisos = normalizar(bruto, dur)
        if erros:
            messagebox.showerror(
                "Colar edicao.json",
                "O edicao.json tem problemas e NÃO foi salvo:\n\n- "
                + "\n- ".join(erros[:12])
                + "\n\nPeça pro Claude corrigir.",
                parent=parent,
            )
            return False
        arq = i["pasta"] / "edicao.json"
        if arq.exists():
            if not messagebox.askyesno(
                "Colar edicao.json",
                "Esse vídeo já tem um edicao.json.\n\n"
                "Substituir pelo que você copiou?\n(o atual vira edicao_anterior.json)",
                parent=parent,
            ):
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
        link = simpledialog.askstring(
            "Link do vídeo completo",
            "Cole o link do vídeo longo no YouTube\n(vai na descrição dos Shorts):",
            initialvalue=atual,
            parent=self.raiz,
        )
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
        ps1 = FERRAMENTAS / "videos_longos" / "juntar_videos_gui.ps1"
        if not ps1.exists():
            messagebox.showinfo("Juntar vídeos", f"Não achei {ps1}.")
            return
        PASTA_VIDEOS.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-STA",
                "-WindowStyle",
                "Hidden",
                "-File",
                str(ps1),
            ],
            env=dict(os.environ, FAMOSOZORA_VIDEOS=str(PASTA_VIDEOS)),
        )

    def instalar(self):
        if APP_INSTALADO:
            if not tem_nvidia() and not messagebox.askyesno(
                "Placa de vídeo", "Não achei uma placa NVIDIA neste computador. Tentar ativar mesmo assim?"
            ):
                return
            rodar_script("nucleo.ativar_gpu")
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
                "SIM = usar essa pasta\nNÃO = escolher outra (por exemplo, a pasta que você já usa)",
            )
            if not usar and self.mudar_pasta_trabalho():
                return
            salvar_ajustes({"pasta_trabalho": str(PASTA_CANAL)})
            preparar_pasta_trabalho()
            self.atualizar()
        if ajustes.get("ultima_versao_vista") != VERSAO:
            salvar_ajustes({"ultima_versao_vista": VERSAO})
            if ajustes.get("ultima_versao_vista"):  # atualizou: mostra o que mudou
                self.novidades()
        if APP_INSTALADO and tem_nvidia() and not gpu_baixada() and not ajustes.get("perguntou_gpu"):
            salvar_ajustes({"perguntou_gpu": True})
            if messagebox.askyesno(
                "Placa de vídeo NVIDIA encontrada",
                "Quer ativar a placa de vídeo para transcrever MUITO mais rápido?\n\n"
                "Vai baixar cerca de 1 GB (só uma vez).",
            ):
                self.instalar()

    def novidades(self):
        JanelaTexto(self.raiz, f"Novidades - FamosoZora Studio {VERSAO}", ARQ_NOVIDADES)

    def mudar_pasta_trabalho(self):
        from tkinter import filedialog

        nova = filedialog.askdirectory(
            title="Escolha a pasta de trabalho (vídeos e Shorts)", initialdir=str(PASTA_CANAL)
        )
        if not nova or Path(nova) == PASTA_CANAL:
            return False
        salvar_ajustes({"pasta_trabalho": str(Path(nova))})
        messagebox.showinfo("Pasta de trabalho", f"Pronto! A pasta agora é:\n{nova}\n\nO Studio vai reabrir.")
        subprocess.Popen([str(PY_JANELA), str(FERRAMENTAS / "main.py")], cwd=str(FERRAMENTAS))
        self.raiz.destroy()
        return True

    def atualizar_github(self):
        if APP_INSTALADO:
            webbrowser.open(REPO_URL + "/releases/latest")
            messagebox.showinfo(
                "Procurar atualização",
                f"Você está na versão {VERSAO}.\n\nAbri a página do GitHub no navegador. Se lá tiver "
                'uma versão maior, baixe o arquivo "FamosoZora-Studio-Setup-....exe" e instale '
                "por cima (seus vídeos e Shorts não são apagados).",
            )
            return
        git = achar_git()
        if not git:
            messagebox.showinfo(
                "Atualizar",
                "Não achei o Git.\n\nAbra o GitHub Desktop e clique em " '"Fetch origin" e depois em "Pull origin".',
            )
            return
        if not (PASTA_APP / ".git").exists():
            messagebox.showinfo(
                "Atualizar",
                "Esta pasta ainda não está ligada ao GitHub.\n"
                "Abra o GitHub Desktop e adicione esta pasta como repositório.",
            )
            return
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            r = subprocess.run(
                [git, "-C", str(PASTA_APP), "pull", "--ff-only"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=180,
                creationflags=flags,
            )
        except Exception as e:
            messagebox.showerror("Atualizar", f"Não consegui atualizar:\n{e}")
            return
        saida = (r.stdout + "\n" + r.stderr).strip()
        if r.returncode != 0:
            messagebox.showerror(
                "Atualizar",
                "Não consegui atualizar pelo Studio.\n"
                'Use o GitHub Desktop: "Fetch origin" → "Pull origin".\n\n' + saida[-800:],
            )
        elif "Already up to date" in saida or "Já está atualizado" in saida:
            messagebox.showinfo("Atualizar", "Você já está com a versão mais nova.")
        else:
            messagebox.showinfo(
                "Atualizar",
                "Programa atualizado!\n\nFeche e abra o FamosoZora Studio de novo.\n"
                'Se o Claude disse que mudou o instalador, clique em "Instalar / atualizar".',
            )

    def copiar(self, texto: str):
        self.raiz.clipboard_clear()
        self.raiz.clipboard_append(texto)
        self.raiz.update()

    def rodar(self):
        self.raiz.mainloop()


def abrir_studio():
    """Abre a janela principal (chamado pelo main.py)."""
    try:
        if ler_ajustes().get("pasta_trabalho"):  # 1a vez: o Studio pergunta qual pasta usar
            preparar_pasta_trabalho()
        Studio().rodar()
    except Exception as e:
        import traceback

        traceback.print_exc()
        try:
            messagebox.showerror("FamosoZora Studio - erro", f"{e}\n\nTire um print e mande pro Claude.")
        except Exception:
            pass


if __name__ == "__main__":
    abrir_studio()

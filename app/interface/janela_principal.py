# Janela principal do FamosoZora Studio: o topo (titulo, versao e menu geral) e as duas abas,
#   Shorts               -> interface/aba_shorts.py
#   Videos longos/Lives  -> interface/aba_videos_longos.py
# O que vale para o programa inteiro (pasta de trabalho, atualizacao, configuracoes) fica no menu do topo.
import shutil
import subprocess
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, ttk

from interface.aba_shorts import AbaShorts
from interface.aba_videos_longos import AbaVideosLongos
from interface.aviso_atualizacao import AvisoAtualizacao, avisar_codigo_novo
from interface.janela_texto import JanelaTexto
from interface.utilidades import (
    ARQ_DIRETRIZES,
    ARQ_GUIA,
    ARQ_NOVIDADES,
    BAT_DEV,
    COR_DESTAQUE,
    COR_FUNDO,
    PY_JANELA,
    abrir,
    abrir_texto,
    achar_git,
    em_segundo_plano,
    gpu_baixada,
    rodar_script,
    tem_nvidia,
)
from nucleo.atualizacao import buscar_release, eh_mais_nova, situacao_git
from nucleo.comum import (
    APP_INSTALADO,
    FERRAMENTAS,
    PASTA_APP,
    PASTA_CANAL,
    PASTA_CONFIG,
    PASTA_MUSICAS,
    REPO_URL,
    gravar_json,
    ler_ajustes,
    preparar_pasta_trabalho,
    salvar_ajustes,
)
from nucleo.projetos import listar_projetos
from nucleo.registro import registrar
from versao import VERSAO


class Studio:
    def __init__(self):
        try:
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        self.raiz = tk.Tk()
        self.raiz.title(f"FamosoZora Studio {VERSAO}")
        self.raiz.geometry("1120x720")
        self.raiz.minsize(940, 580)
        self.raiz.configure(bg=COR_FUNDO)
        self._configurar_estilos()
        self._montar_topo()
        self._montar_abas()

        self._assinatura = None
        self.atualizar()
        self.raiz.after(4000, self.auto_atualizar)
        self.raiz.after(600, self.boas_vindas)
        # o modo desenvolvedor confere o GitHub antes de abrir (sincronizar_antes_de_abrir)
        if APP_INSTALADO and ler_ajustes().get("verificar_atualizacoes", True):
            self.raiz.after(2500, self.verificar_atualizacao)

    # ---------------------------------------------------------- montagem da janela
    def _configurar_estilos(self):
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
        estilo.configure("TNotebook", background=COR_FUNDO, borderwidth=0)
        estilo.configure("TNotebook.Tab", font=("Segoe UI", 11, "bold"), padding=(18, 8))
        estilo.map("TNotebook.Tab", background=[("selected", COR_DESTAQUE)], foreground=[("selected", "#14141f")])

    def _montar_topo(self):
        topo = tk.Frame(self.raiz, bg=COR_FUNDO)
        topo.pack(fill="x", padx=18, pady=(14, 6))
        tk.Label(topo, text="FamosoZora Studio", bg=COR_FUNDO, fg=COR_DESTAQUE, font=("Segoe UI", 20, "bold")).pack(
            side="left"
        )
        tk.Label(
            topo,
            text="   da live aos Shorts e ao episódio, num lugar só",
            bg=COR_FUNDO,
            fg="#c8c8d8",
            font=("Segoe UI", 11),
        ).pack(side="left", pady=(8, 0))

        geral = ttk.Menubutton(topo, text="Menu", width=8)
        geral["menu"] = self._montar_menu(geral)
        geral.pack(side="right", pady=(6, 0))
        tk.Label(topo, text=f"versão {VERSAO}", bg=COR_FUNDO, fg="#7a7a90", font=("Segoe UI", 10)).pack(
            side="right", padx=(0, 12), pady=(8, 0)
        )

    def _montar_menu(self, dono) -> tk.Menu:
        """Menu geral: tudo o que vale para o programa inteiro, e nao para um projeto."""
        menu = tk.Menu(dono, tearoff=0, font=("Segoe UI", 10))
        menu.add_command(label=f"Novidades da versão {VERSAO}", command=self.novidades)
        menu.add_command(label="Procurar atualização", command=self.atualizar_github)
        self.verificar_ao_abrir = tk.BooleanVar(value=ler_ajustes().get("verificar_atualizacoes", True))
        menu.add_checkbutton(
            label="Verificar atualizações ao abrir",
            variable=self.verificar_ao_abrir,
            command=lambda: salvar_ajustes({"verificar_atualizacoes": bool(self.verificar_ao_abrir.get())}),
        )
        menu.add_separator()
        menu.add_command(label="Abrir pasta de trabalho", command=lambda: self.abrir_pasta_segura(PASTA_CANAL))
        menu.add_command(label="Mudar pasta de trabalho...", command=self.mudar_pasta_trabalho)
        menu.add_separator()
        menu.add_command(label="Configurações (config.json)", command=lambda: abrir_texto(PASTA_CONFIG / "config.json"))
        menu.add_command(
            label="Vocabulário (nomes do canal)", command=lambda: abrir_texto(PASTA_CONFIG / "vocabulario.txt")
        )
        menu.add_command(label="Correções automáticas", command=lambda: abrir_texto(PASTA_CONFIG / "correcoes.txt"))
        menu.add_command(label="Músicas de fundo", command=lambda: self.abrir_pasta_segura(PASTA_MUSICAS))
        menu.add_separator()
        menu.add_command(label="Diretrizes do canal (o que o Claude segue)", command=lambda: abrir(ARQ_DIRETRIZES))
        menu.add_command(label="Guia: COMO USAR", command=lambda: abrir(ARQ_GUIA))
        menu.add_separator()
        if APP_INSTALADO:
            menu.add_command(label="Ativar placa de vídeo NVIDIA", command=self.instalar)
        else:
            menu.add_command(label="Atualizar dependências (modo desenvolvedor)", command=self.instalar)
        return menu

    def _montar_abas(self):
        self.abas = ttk.Notebook(self.raiz)
        self.abas.pack(fill="both", expand=True, padx=18, pady=(4, 14))
        self.aba_shorts = AbaShorts(self, self.abas)
        self.aba_longos = AbaVideosLongos(self, self.abas)
        self.abas.add(self.aba_shorts, text="  Shorts  ")
        self.abas.add(self.aba_longos, text="  Vídeos longos / Lives  ")

    # ---------------------------------------------------------- lista de projetos (igual nas duas abas)
    def atualizar(self, forcar=True):
        projetos = {i["nome"]: i for i in listar_projetos()}
        assinatura = [
            (n, i["transcrito"], i["n_cortes"], i["n_shorts"], i["postados"], i["n_pub"], i["passo"], i["passo_longo"],
             i["projeto"].get("link_video_completo"), i["episodio"], (i["pasta"] / "edicao.json").exists())
            for n, i in projetos.items()
        ]  # fmt: skip
        if not forcar and assinatura == self._assinatura:
            return
        self._assinatura = assinatura
        self.projetos = projetos
        self.aba_shorts.preencher(projetos)
        self.aba_longos.preencher(projetos)

    def auto_atualizar(self):
        try:
            self.atualizar(forcar=False)
        finally:
            self.raiz.after(4000, self.auto_atualizar)

    # ---------------------------------------------------------- video longo (tambem usado pela janela de revisao)
    def pedir_edicao(self, i, parent=None):
        from videos_longos.pedido_edicao import info_video, texto_pedido

        _, dur = info_video(i["pasta"])
        self.copiar(texto_pedido(i["nome"], i["pasta"], ARQ_DIRETRIZES, dur))
        messagebox.showinfo(
            "Editar vídeo longo",
            "Pedido de edição copiado!\n\nAgora cole (Ctrl+V) na conversa com o Claude e envie.\n"
            "Quando ele avisar que salvou o edicao.json, selecione o vídeo e clique em "
            "3 - Editar vídeo longo de novo para revisar.\n\n"
            "Se a conversa não tiver acesso ao PC, copie o JSON que o Claude mandar e clique em "
            '"Colar edicao.json".',
            parent=parent or self.raiz,
        )

    def colar_edicao(self, i, parent=None):
        """Le o edicao.json da area de transferencia, valida e salva na pasta do projeto."""
        from videos_longos.pedido_edicao import erro_json_amigavel, extrair_json, info_video, normalizar

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
                "A área de transferência está vazia.\nCopie o JSON que o Claude mandou e clique aqui de novo.",
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
        msg = f"edicao.json salvo com {len(dados.get('cortes', []))} cortes e {len(dados.get('capitulos', []))} capítulos."
        if avisos:
            msg += "\n\nAvisos:\n- " + "\n- ".join(avisos[:10])
        messagebox.showinfo("Colar edicao.json", msg, parent=parent)
        self.atualizar()
        return True

    # ---------------------------------------------------------- menu geral
    def abrir_pasta_segura(self, pasta: Path):
        pasta.mkdir(parents=True, exist_ok=True)
        abrir(pasta)

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

    def novidades(self):
        JanelaTexto(self.raiz, f"Novidades - FamosoZora Studio {VERSAO}", ARQ_NOVIDADES)

    def mudar_pasta_trabalho(self):
        from tkinter import filedialog

        nova = filedialog.askdirectory(
            title="Escolha a pasta de trabalho (vídeos e projetos)", initialdir=str(PASTA_CANAL)
        )
        if not nova or Path(nova) == PASTA_CANAL:
            return False
        salvar_ajustes({"pasta_trabalho": str(Path(nova))})
        messagebox.showinfo("Pasta de trabalho", f"Pronto! A pasta agora é:\n{nova}\n\nO Studio vai reabrir.")
        subprocess.Popen([str(PY_JANELA), str(FERRAMENTAS / "main.py")], cwd=str(FERRAMENTAS))
        self.raiz.destroy()
        return True

    def verificar_atualizacao(self, manual=False):
        """Procura versao nova em segundo plano (a tela nao trava). manual=True: veio do Menu, sempre responde."""

        if APP_INSTALADO:
            em_segundo_plano(self.raiz, buscar_release, lambda r: self._resultado_release(r, manual))
        else:
            em_segundo_plano(self.raiz, lambda: situacao_git(achar_git()), lambda s: self._resultado_git(s, manual))

    def _resultado_release(self, release, manual):
        if release and release["versao"] and eh_mais_nova(release["versao"], VERSAO):
            AvisoAtualizacao(self.raiz, release, self.raiz.destroy)
        elif manual and release:
            messagebox.showinfo("Procurar atualização", f"Você já está com a versão mais nova ({VERSAO}).")
        elif manual:
            webbrowser.open(REPO_URL + "/releases/latest")
            messagebox.showinfo(
                "Procurar atualização",
                f"Você está na versão {VERSAO}.\n\nNão consegui consultar o GitHub sozinho (sem internet, ou o "
                "repositório é privado). Abri a página no navegador: se lá tiver uma versão maior, baixe o "
                '"FamosoZora-Studio-Setup-....exe" e instale por cima.',
            )

    def _resultado_git(self, situacao, manual):
        if situacao and (situacao["atras"] or situacao["mudancas"] or situacao["a_frente"]):
            avisar_codigo_novo(self.raiz, situacao, self._baixar_e_avisar)
        elif manual and situacao:
            messagebox.showinfo("Atualizar", "Esta pasta já está igual ao GitHub. Nada para baixar.")
        elif manual:
            messagebox.showinfo(
                "Atualizar",
                "Não consegui falar com o GitHub por aqui (sem internet ou sem login).\n\n"
                'Use o GitHub Desktop: "Fetch origin" e depois "Pull origin".',
            )

    def _baixar_e_avisar(self):
        if baixar_codigo(self.raiz):
            messagebox.showinfo("Atualizar", "Código atualizado!\n\nFeche e abra o FamosoZora Studio de novo.")

    def atualizar_github(self):
        """Menu > Procurar atualizacao."""
        self.verificar_atualizacao(manual=True)

    # ---------------------------------------------------------- primeira abertura e avisos
    def boas_vindas(self):
        ajustes = ler_ajustes()
        if not ajustes.get("pasta_trabalho"):
            usar = messagebox.askyesno(
                "Bem-vindo ao FamosoZora Studio",
                f"Os vídeos e projetos em produção vão ficar nesta pasta:\n\n{PASTA_CANAL}\n\n"
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

    # ---------------------------------------------------------- utilidades
    def copiar(self, texto: str):
        self.raiz.clipboard_clear()
        self.raiz.clipboard_append(texto)
        self.raiz.update()

    def rodar(self):
        self.raiz.mainloop()


def baixar_codigo(parent=None) -> bool:
    """Modo desenvolvedor: git pull da main (so avanca, nunca mistura). Devolve True se baixou."""
    git = achar_git()
    if not git:
        messagebox.showinfo(
            "Atualizar",
            'Não achei o Git.\n\nAbra o GitHub Desktop e clique em "Fetch origin" e depois em "Pull origin".',
            parent=parent,
        )
        return False
    try:
        r = subprocess.run(
            [git, "-C", str(PASTA_APP), "pull", "--ff-only"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as e:
        messagebox.showerror("Atualizar", f"Não consegui atualizar:\n{e}", parent=parent)
        return False
    if r.returncode != 0:
        saida = (r.stdout + "\n" + r.stderr).strip()
        messagebox.showerror(
            "Atualizar",
            "Não consegui atualizar pelo Studio.\n"
            'Use o GitHub Desktop: "Fetch origin" → "Pull origin".\n\n' + saida[-800:],
            parent=parent,
        )
        return False
    return True


def sincronizar_antes_de_abrir():
    """Modo desenvolvedor: antes de abrir, confere se o GitHub tem codigo novo (de outro PC) ou se ha
    alteracoes daqui que ainda nao foram para o GitHub. Assim voce nao edita uma versao velha."""
    if APP_INSTALADO or not ler_ajustes().get("verificar_atualizacoes", True):
        return
    situacao = situacao_git(achar_git())
    if not situacao or not (situacao["atras"] or situacao["mudancas"] or situacao["a_frente"]):
        return
    raiz = tk.Tk()
    raiz.withdraw()
    baixou = []
    avisar_codigo_novo(raiz, situacao, lambda: baixou.append(baixar_codigo(raiz)))
    raiz.destroy()
    if any(baixou):  # o codigo mudou: abre o Studio de novo, ja com o codigo novo
        messagebox.showinfo("Atualizar", "Código novo baixado! O Studio vai abrir com ele.")
        subprocess.Popen([str(PY_JANELA), str(FERRAMENTAS / "main.py")], cwd=str(FERRAMENTAS))
        raise SystemExit(0)


def abrir_studio():
    """Abre a janela principal (chamado pelo main.py)."""
    try:
        sincronizar_antes_de_abrir()
        if ler_ajustes().get("pasta_trabalho"):  # 1a vez: o Studio pergunta qual pasta usar
            preparar_pasta_trabalho()
        Studio().rodar()
    except SystemExit:
        pass
    except Exception as e:
        import traceback

        traceback.print_exc()
        registrar("erro ao abrir o Studio", e)
        try:
            messagebox.showerror("FamosoZora Studio - erro", f"{e}\n\nTire um print e mande pro Claude.")
        except Exception:
            pass


if __name__ == "__main__":
    abrir_studio()

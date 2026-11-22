# Telas que abrem DENTRO da janela principal do Studio, no lugar das paginas (Inicio, Shorts...), em vez de janelas
# soltas do Windows. Desde a 1.9.2 toda "janela" do app e uma TelaInterna:
#   - nova_janela(pai) substitui tk.Toplevel(pai). Ela entende os mesmos comandos de janela (title, geometry,
#     protocol, lift, deiconify, focus_force...), entao o resto do codigo quase nao muda.
#   - em cima aparece a barra "← Voltar  |  titulo"; Voltar faz o mesmo que fechar a janela antes (pergunta se quer
#     salvar etc.). A barra lateral ganha "Abertas agora": clicar volta para a tela sem fechar.
#   - tela pequena (geometry com menos de 1000 de largura: Excluir, Reportar bug...) fica centralizada.
# Sem o Studio aberto (testes, marcar camera rodando sozinho) nova_janela devolve um tk.Toplevel normal.
import re
import tkinter as tk

from interface import tema

_studio = None  # o Studio aberto (janela_principal.Studio), anotado por registrar_studio
LARGURA_TELA_PEQUENA = 1000


def registrar_studio(studio):
    global _studio
    _studio = studio


def studio_aberto():
    try:
        if _studio is not None and _studio.raiz.winfo_exists():
            return _studio
    except tk.TclError:
        pass
    return None


def nova_janela(pai=None, **opcoes):
    """No lugar de tk.Toplevel(pai): uma tela dentro do Studio (ou uma janela normal, sem o Studio)."""
    st = studio_aberto()
    if st is None or not hasattr(st, "navegacao"):
        return tk.Toplevel(pai, **opcoes)
    return TelaInterna(st, **opcoes)


def tela_de(widget):
    """A TelaInterna onde o widget esta (ou None)."""
    w = widget
    while w is not None:
        if isinstance(w, TelaInterna):
            return w
        w = getattr(w, "master", None)
    return None


class TelaInterna(tk.Frame):
    """Um quadro que se comporta como janela (os comandos de janela que o app usa)."""

    def __init__(self, studio, **opcoes):
        opcoes.setdefault("bg", tema.FUNDO)
        super().__init__(studio.navegacao.area, **opcoes)
        self.studio = studio
        self.nav = studio.navegacao
        self._titulo = ""
        self._ao_fechar = None
        self.tamanho = None  # (largura, altura) se for tela pequena
        self._marcados = set()
        self.nav.abrir(self)
        self.after(50, self._marcar_filhos)

    # ------------------------------------------------ teclado e eventos como numa janela
    def _marcar_filhos(self):
        """Numa janela de verdade, uma tecla apertada em qualquer botao/caixa dentro dela chega tambem na janela
        (self.jan.bind("<Control-s>", ...)). Num quadro isso nao acontece sozinho: por isso cada widget de dentro
        ganha a "etiqueta" deste quadro (bindtags), logo antes da etiqueta da janela principal."""
        try:
            if not self.winfo_exists():
                return
            minha = str(self)
            pilha = list(self.winfo_children())
            while pilha:
                w = pilha.pop()
                pilha.extend(w.winfo_children())
                nome = str(w)
                if nome in self._marcados:
                    continue
                tags = list(w.bindtags())
                if minha not in tags:
                    pos = tags.index(".") if "." in tags else len(tags)
                    tags.insert(pos, minha)
                    w.bindtags(tuple(tags))
                self._marcados.add(nome)
            self.after(400, self._marcar_filhos)  # widgets criados depois (trocar de Short, abas...)
        except tk.TclError:
            pass

    # ------------------------------------------------ comandos de janela
    def title(self, texto=None):
        if texto is None:
            return self._titulo
        self._titulo = str(texto)
        self.nav.atualizar_barra()
        return ""

    wm_title = title

    def geometry(self, texto=None):
        if texto is None:
            return f"{self.winfo_width()}x{self.winfo_height()}"
        m = re.match(r"(\d+)x(\d+)", str(texto))
        if m:
            w, h = int(m.group(1)), int(m.group(2))
            self.tamanho = (w, h) if w < LARGURA_TELA_PEQUENA else None
            if self.nav.visivel is self:
                self.nav.mostrar(self)
        return ""

    wm_geometry = geometry

    def state(self, novo=None):
        if novo in ("withdrawn", "iconic"):
            self.nav.esconder(self)
        elif novo in ("normal", "zoomed"):
            self.nav.mostrar(self)
        return "normal"

    wm_state = state

    def protocol(self, nome=None, funcao=None):
        if nome == "WM_DELETE_WINDOW" and funcao is not None:
            self._ao_fechar = funcao
        return ""

    wm_protocol = protocol

    def _nada(self, *a, **k):
        return ""

    transient = grab_set = grab_release = resizable = minsize = maxsize = attributes = _nada
    iconphoto = iconbitmap = overrideredirect = wm_transient = wm_resizable = wm_minsize = wm_attributes = _nada

    def lift(self, *a):
        self.nav.mostrar(self)

    def deiconify(self):
        self.nav.mostrar(self)

    def focus_force(self):
        self.nav.mostrar(self)
        try:
            super().focus_force()
        except tk.TclError:
            pass

    def withdraw(self):
        self.nav.esconder(self)

    iconify = withdraw

    def pedir_fechar(self):
        """O "Voltar" / "✕": o mesmo que clicar no X da janela antes."""
        if self._ao_fechar:
            self._ao_fechar()
        else:
            self.destroy()

    def destroy(self):
        nav = self.nav
        super().destroy()
        nav.fechou(self)


class Navegacao:
    """Cuida de qual tela aparece: uma pagina do Studio ou uma TelaInterna."""

    def __init__(self, studio, conteudo: tk.Frame, lista_lateral: tk.Frame):
        self.studio = studio
        self.conteudo = conteudo
        self.abertas = []  # TelaInterna, da mais antiga para a mais nova
        self.visivel = None
        self.origem = {}  # tela -> o que estava na frente quando ela abriu (outra tela ou None = pagina)
        self.barra = tk.Frame(conteudo, bg=tema.PAINEL)
        self.btn_voltar = tk.Button(self.barra, text="←  Voltar", relief="flat", bd=0, cursor="hand2",
                                    bg=tema.PAINEL, fg=tema.TEXTO, activebackground=tema.BORDA,
                                    activeforeground=tema.TEXTO, font=(tema.FONTE, 10, "bold"), padx=14, pady=6,
                                    highlightthickness=0, command=self.voltar)  # fmt: skip
        self.btn_voltar.pack(side="left")
        self.lbl_titulo = tk.Label(self.barra, text="", bg=tema.PAINEL, fg=tema.TEXTO_2, font=(tema.FONTE, 10),
                                   anchor="w")  # fmt: skip
        self.lbl_titulo.pack(side="left", fill="x", expand=True, padx=8)
        self.area = tk.Frame(conteudo, bg=tema.FUNDO)
        self.lista = lista_lateral  # "Abertas agora" na barra lateral

    # ------------------------------------------------ abrir / mostrar / esconder
    def abrir(self, tela: TelaInterna):
        self.origem[tela] = self.visivel
        self.abertas.append(tela)
        self.mostrar(tela)

    def mostrar(self, tela: TelaInterna):
        if tela not in self.abertas:
            return
        if self.visivel is not None and self.visivel is not tela:
            self._tirar(self.visivel)
        self.studio.esconder_paginas()
        if not self.barra.winfo_ismapped():
            self.barra.pack(side="top", fill="x")
            self.area.pack(side="top", fill="both", expand=True)
        self._tirar(tela)
        if tela.tamanho:
            w, h = tela.tamanho
            tela.configure(highlightthickness=1, highlightbackground=tema.BORDA)
            tela.place(relx=0.5, rely=0.45, anchor="center", width=w, height=h)
        else:
            tela.pack(fill="both", expand=True)
        self.visivel = tela
        self.abertas.remove(tela)
        self.abertas.append(tela)
        self.atualizar_barra()
        try:
            tela.event_generate("<<TelaMostrada>>")
        except tk.TclError:
            pass

    def _tirar(self, tela):
        try:
            tela.pack_forget()
            tela.place_forget()
            tela.event_generate("<<TelaEscondida>>")
        except tk.TclError:
            pass

    def esconder(self, tela=None):
        """Some com a tela da frente (ela continua aberta em "Abertas agora") e volta para a pagina."""
        if tela is not None and tela is not self.visivel:
            return
        if self.visivel is not None:
            self._tirar(self.visivel)
        self.visivel = None
        self.barra.pack_forget()
        self.area.pack_forget()
        self.atualizar_barra()

    def voltar(self):
        if self.visivel is not None:
            self.visivel.pedir_fechar()

    def fechou(self, tela):
        try:
            self._fechou(tela)
        except tk.TclError:
            pass  # o Studio inteiro esta fechando

    def _fechou(self, tela):
        if tela in self.abertas:
            self.abertas.remove(tela)
        antes = self.origem.pop(tela, None)
        if self.visivel is tela:
            self.visivel = None
            if antes is not None and antes in self.abertas:
                self.mostrar(antes)
            else:
                self.esconder()
                self.studio.mostrar(self.studio.tela_atual or "inicio")
        self.atualizar_barra()

    # ------------------------------------------------ barra de cima e "Abertas agora"
    def atualizar_barra(self):
        try:
            if self.visivel is not None:
                self.lbl_titulo.configure(text=self.visivel.title())
            for w in self.lista.winfo_children():
                w.destroy()
            vivas = [t for t in self.abertas if t.winfo_exists()]
            if not vivas:
                self.lista.pack_forget()
                return
            self.lista.pack(fill="x", pady=(18, 0))
            tk.Label(self.lista, text="ABERTAS AGORA", bg=tema.PAINEL, fg=tema.TEXTO_2, font=tema.F_PEQUENA,
                     anchor="w").pack(fill="x", padx=20, pady=(0, 4))  # fmt: skip
            for t in vivas:
                linha = tk.Frame(self.lista, bg=tema.PAINEL)
                linha.pack(fill="x")
                ativo = t is self.visivel
                titulo = t.title() or "Tela"
                b = tk.Button(linha, text="  " + (titulo if len(titulo) <= 26 else titulo[:25] + "…"), anchor="w",
                              relief="flat", bd=0, cursor="hand2", bg=tema.BORDA if ativo else tema.PAINEL,
                              fg=tema.LARANJA if ativo else tema.TEXTO_2, activebackground=tema.BORDA,
                              activeforeground=tema.TEXTO, font=tema.F_PEQUENA, padx=14, pady=4,
                              highlightthickness=0, command=lambda t=t: self.mostrar(t))  # fmt: skip
                b.pack(side="left", fill="x", expand=True)
                x = tk.Button(linha, text="✕", relief="flat", bd=0, cursor="hand2", bg=tema.PAINEL, fg=tema.TEXTO_2,
                              activebackground=tema.BORDA, activeforeground=tema.TEXTO, font=tema.F_PEQUENA,
                              padx=8, highlightthickness=0, command=lambda t=t: self._fechar(t))  # fmt: skip
                x.pack(side="right")
        except tk.TclError:
            pass

    def _fechar(self, tela):
        if tela is not self.visivel:
            self.mostrar(tela)  # para ver o que esta fechando (e responder se perguntar algo)
        tela.pedir_fechar()


def janelas(studio) -> list:
    """Todas as "janelas" abertas: as telas internas e as janelas soltas que ainda existirem."""
    soltas = [w for w in studio.raiz.winfo_children() if isinstance(w, tk.Toplevel)]
    nav = getattr(studio, "navegacao", None)
    return soltas + ([t for t in nav.abertas if t.winfo_exists()] if nav else [])

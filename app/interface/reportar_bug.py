# "Reportar bug": botao direito em qualquer lugar do Studio (e em qualquer janela dele) tem "🐞 Reportar bug...".
# Abre uma janelinha para contar o que aconteceu; o Studio junta o contexto sozinho (nucleo/relato_bug.py),
# guarda o relato num arquivo e abre o navegador com a issue do GitHub ja preenchida (e so clicar em enviar).
# Tambem guarda a "trilha" (os ultimos cliques) e os erros que acontecem na tela, para irem junto no relato.
import tkinter as tk
import traceback
import webbrowser
from tkinter import messagebox, ttk

from interface import tema
from nucleo import relato_bug
from nucleo.registro import registrar

ITEM_DO_MENU = "🐞  Reportar bug..."
_estado = {"studio": None, "janela": None}


def iniciar(studio):
    """Liga o "Reportar bug" no app inteiro. Chamado uma vez, quando o Studio abre."""
    _estado["studio"] = studio
    raiz = studio.raiz
    # botao direito onde nao tem menu proprio (os menus proprios ja ganham o item no final: interface/menus.py)
    raiz.bind_all("<Button-3>", _menu_simples, add="+")
    if raiz.tk.call("tk", "windowingsystem") == "aqua":
        raiz.bind_all("<Button-2>", _menu_simples, add="+")
    raiz.bind_all("<ButtonRelease-1>", _anotar_clique, add="+")
    anterior = raiz.report_callback_exception

    def erro_na_tela(tipo, valor, tb):
        """Erro dentro de um botao/tela: vai para o registro e para o proximo relato de bug."""
        texto = "".join(traceback.format_exception(tipo, valor, tb))
        relato_bug.anotar_erro(texto)
        registrar("erro na tela", valor)
        anterior(tipo, valor, tb)

    raiz.report_callback_exception = erro_na_tela


def _texto_do_widget(w) -> str:
    for opcao in ("text", "label"):
        try:
            texto = str(w.cget(opcao)).strip()
        except (tk.TclError, AttributeError):
            continue
        if texto:
            return texto
    return ""


def _anotar_clique(evento):
    w = evento.widget
    if not isinstance(w, tk.Misc):
        return
    try:
        janela = w.winfo_toplevel().title()
        classe = w.winfo_class()
    except tk.TclError:
        return
    texto = _texto_do_widget(w)
    if isinstance(w, ttk.Treeview):
        sel = w.selection()
        if sel:
            texto = "lista: " + ", ".join(str(w.item(i, "text") or i) for i in sel[:5])
    elif isinstance(w, tk.Listbox):
        sel = w.curselection()
        if sel:
            texto = "lista: " + str(w.get(sel[0]))
    if texto:
        relato_bug.anotar(f'[{janela}] clicou em {classe} "{texto}"')


def _menu_simples(evento):
    from interface.menus import abrir_menu, montar_menu

    menu = montar_menu(evento.widget, [(ITEM_DO_MENU, lambda: abrir(evento.widget))])
    abrir_menu(evento, menu)


def item_do_menu(widget) -> tuple:
    """O item "Reportar bug" que entra no fim de todos os menus de botao direito."""
    return (ITEM_DO_MENU, lambda: abrir(widget))


# ---------------------------------------------------------------- contexto
def contexto(widget=None) -> dict:
    """O que estava na tela quando o bug aconteceu."""
    studio = _estado["studio"]
    dados = {}
    try:
        if widget is not None:
            dados["Janela onde clicou"] = widget.winfo_toplevel().title()
    except tk.TclError:
        pass
    if studio is None:
        return dados
    telas = {"inicio": "Início", "shorts": "Shorts", "longos": "Vídeos longos", "publicacao": "Publicação",
             "configuracoes": "Configurações"}  # fmt: skip
    atual = getattr(studio, "tela_atual", None)
    dados["Tela aberta"] = telas.get(atual, atual or "?")
    tela = getattr(studio, "telas", {}).get(atual)
    if tela is not None and hasattr(tela, "selecionados"):
        try:
            sel = tela.selecionados()
            dados["Vídeos selecionados"] = [f"{i['nome']} (etapa: {i.get('estado', '?')}, Shorts "
                                            f"{i.get('n_shorts', 0)}/{i.get('n_cortes', 0)}, publicados "
                                            f"{i.get('postados', 0)}/{i.get('n_pub', 0)})" for i in sel[:10]]  # fmt: skip
        except Exception:
            pass
    try:
        dados["Janelas abertas"] = [w.title() for w in studio.raiz.winfo_children()
                                    if isinstance(w, tk.Toplevel) and w.winfo_viewable()]  # fmt: skip
    except tk.TclError:
        pass
    try:
        dados["Lote rodando"] = "sim" if studio.lote_rodando() else "não"
    except Exception:
        pass
    dados["Projetos na lista"] = len(getattr(studio, "projetos", {}) or {})
    return dados


# ---------------------------------------------------------------- a janela
def abrir(widget=None):
    """Abre a janela "Reportar bug" (so uma de cada vez)."""
    studio = _estado["studio"]
    if studio is None:
        return None
    jan = _estado["janela"]
    if jan is not None:
        try:
            if jan.jan.winfo_exists():
                jan.jan.deiconify()
                jan.jan.lift()
                jan.jan.focus_force()
                return jan
        except tk.TclError:
            pass
    _estado["janela"] = JanelaReportarBug(studio, contexto(widget))
    return _estado["janela"]


class JanelaReportarBug:
    def __init__(self, studio, contexto_: dict):
        self.studio = studio
        self.contexto = contexto_
        self.jan = tk.Toplevel(studio.raiz)
        self.jan.title("Reportar bug")
        self.jan.configure(bg=tema.FUNDO)
        q = tk.Frame(self.jan, bg=tema.FUNDO, padx=22, pady=18)
        q.pack(fill="both", expand=True)
        tema.rotulo(q, "🐞 Reportar bug", "subtitulo").pack(fill="x")
        tema.rotulo(q, "Conte o que aconteceu e o que você esperava que acontecesse. A primeira linha vira o "
                    "título. O GitHub do Studio é público: confira o texto no navegador antes de enviar.", "secundario", wraplength=560).pack(fill="x", pady=(2, 8))  # fmt: skip
        self.texto = tk.Text(q, height=9, width=70, wrap="word", bg=tema.PAINEL, fg=tema.TEXTO,
                             insertbackground=tema.TEXTO, relief="flat", font=tema.F_TEXTO, padx=8, pady=6)  # fmt: skip
        self.texto.pack(fill="both", expand=True)
        self.texto.focus_set()
        resumo = ", ".join(f"{k}: {len(v) if isinstance(v, list) else v}" for k, v in self.contexto.items())
        tema.rotulo(q, "Vai junto, sozinho: versão, Windows, os últimos cliques, erros recentes e "
                    f"{resumo}.", "pequeno", wraplength=560).pack(fill="x", pady=(8, 0))  # fmt: skip
        self.com_log = tk.BooleanVar(value=True)
        ttk.Checkbutton(q, text="Incluir o fim do registro de erros (studio.log)", variable=self.com_log).pack(
            anchor="w", pady=(6, 0)
        )
        botoes = tk.Frame(q, bg=tema.FUNDO)
        botoes.pack(fill="x", pady=(14, 0))
        ttk.Button(botoes, text="Enviar (abre o GitHub)", style="Passo.TButton", command=self.enviar).pack(side="right")
        ttk.Button(botoes, text="Cancelar", style="Extra.TButton", command=self.jan.destroy).pack(side="right", padx=8)
        self.jan.bind("<Escape>", lambda e: self.jan.destroy())
        self.jan.transient(studio.raiz)

    def descricao(self) -> str:
        return self.texto.get("1.0", "end").strip()

    def enviar(self):
        descricao = self.descricao()
        if not descricao:
            messagebox.showinfo("Reportar bug", "Escreva o que aconteceu antes de enviar.", parent=self.jan)
            return None
        titulo = relato_bug.titulo_do_relato(descricao)
        arquivo = relato_bug.salvar(titulo, relato_bug.montar_texto(descricao, self.contexto, self.com_log.get()))
        url = relato_bug.endereco_que_cabe(descricao, self.contexto, self.com_log.get())
        try:
            webbrowser.open(url)
        except Exception as e:
            registrar("reportar bug: nao consegui abrir o navegador", e)
        self.jan.destroy()
        onde = f" (cópia salva em {arquivo})" if arquivo else ""
        self.studio.notificar("O navegador abriu com o bug preenchido: confira e clique em "
                              f"\"Create\" para enviar.{onde}", "ok", 8)  # fmt: skip
        return url

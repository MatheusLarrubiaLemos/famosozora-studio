# Tema do FamosoZora Studio: TODAS as cores, fontes e estilos da interface ficam aqui.
# Para mudar o visual do programa inteiro, mude so este arquivo (paleta cinza + laranja, estilo Claude).
import tkinter as tk
from tkinter import ttk

# ------------------------------------------------------------------ cores
FUNDO = "#1F1E1D"  # fundo da janela
PAINEL = "#2B2A28"  # paineis, barra lateral, cartoes
BORDA = "#3A3936"  # bordas e linhas divisorias
CAMPO = "#171615"  # caixas de texto (um pouco mais escuro que o fundo)
TEXTO = "#ECEAE4"  # texto principal
TEXTO_2 = "#A8A49B"  # texto secundario (dicas, legendas pequenas)
LARANJA = "#D97757"  # destaque: botao principal, aba ativa, barra de progresso
LARANJA_HOVER = "#E08A6D"  # laranja quando o mouse passa por cima
BOTAO = "#383633"  # botoes discretos
BOTAO_HOVER = "#46433F"  # botao discreto com o mouse em cima
LARANJA_ESCURO = "#4A3128"  # linha selecionada nas listas (laranja bem apagado)
VERDE = "#7FB069"  # sucesso
VERMELHO = "#D9534F"  # so para excluir e erro
AMARELO = "#E0B050"  # avisos (sem ser erro)
INCERTO = "#5C4A1A"  # fundo da palavra que o Claude marcou como incerta
TEXTO_ESCURO = "#1F1E1D"  # texto em cima do laranja

# ------------------------------------------------------------------ fontes
FONTE = "Segoe UI"
F_TEXTO = (FONTE, 10)
F_TEXTO_NEGRITO = (FONTE, 10, "bold")
F_PEQUENA = (FONTE, 9)
F_SECAO = (FONTE, 9, "bold")
F_SUBTITULO = (FONTE, 12, "bold")
F_TITULO = (FONTE, 18, "bold")
F_GRANDE = (FONTE, 13)

# ------------------------------------------------------------------ espacos
ESPACO = 16  # margem padrao
ESPACO_PEQUENO = 8


def aplicar(raiz: tk.Misc):
    """Aplica o tema nos estilos do ttk e nos menus. Chamar uma vez, logo depois de criar a janela principal."""
    estilo = ttk.Style(raiz)
    try:
        estilo.theme_use("clam")
    except tk.TclError:
        pass
    estilo.configure(".", background=FUNDO, foreground=TEXTO, font=F_TEXTO, bordercolor=BORDA,
                     darkcolor=PAINEL, lightcolor=PAINEL, troughcolor=CAMPO, fieldbackground=CAMPO,
                     selectbackground=LARANJA_ESCURO, selectforeground=TEXTO, focuscolor=LARANJA)  # fmt: skip
    # botoes: "Passo" = acao principal (laranja); "Extra" = discreto; "Perigo" = excluir
    estilo.configure("TButton", background=BOTAO, foreground=TEXTO, borderwidth=1, focusthickness=0,
                     padding=(10, 6), relief="flat")  # fmt: skip
    estilo.map("TButton", background=[("pressed", BORDA), ("active", BOTAO_HOVER)], bordercolor=[("focus", LARANJA)])
    estilo.configure("Extra.TButton", font=F_TEXTO, padding=(10, 5), background=BOTAO, foreground=TEXTO,
                     bordercolor=BOTAO, lightcolor=BOTAO, darkcolor=BOTAO)  # fmt: skip
    estilo.map("Extra.TButton", background=[("pressed", BORDA), ("active", BOTAO_HOVER)],
               bordercolor=[("active", BOTAO_HOVER)], lightcolor=[("active", BOTAO_HOVER)],
               darkcolor=[("active", BOTAO_HOVER)])  # fmt: skip
    estilo.configure("Passo.TButton", font=(FONTE, 11, "bold"), padding=(14, 9), background=LARANJA,
                     foreground=TEXTO_ESCURO, bordercolor=LARANJA, lightcolor=LARANJA, darkcolor=LARANJA)  # fmt: skip
    estilo.map(
        "Passo.TButton",
        lightcolor=[("active", LARANJA_HOVER)],
        darkcolor=[("active", LARANJA_HOVER)],
        bordercolor=[("active", LARANJA_HOVER)],
    )
    estilo.map("Passo.TButton", background=[("disabled", BORDA), ("pressed", LARANJA), ("active", LARANJA_HOVER)],
               foreground=[("disabled", TEXTO_2)])  # fmt: skip
    estilo.configure("Perigo.TButton", font=(FONTE, 11, "bold"), padding=(14, 9), background=VERMELHO,
                     foreground="#FFFFFF", bordercolor=VERMELHO)  # fmt: skip
    estilo.map("Perigo.TButton", background=[("active", "#E06A66")])
    # listas
    estilo.configure("Treeview", background=PAINEL, fieldbackground=PAINEL, foreground=TEXTO, rowheight=30,
                     font=F_TEXTO, borderwidth=0)  # fmt: skip
    estilo.map("Treeview", background=[("selected", LARANJA_ESCURO)], foreground=[("selected", TEXTO)])
    estilo.configure("Treeview.Heading", background=FUNDO, foreground=TEXTO_2, font=F_SECAO, relief="flat",
                     borderwidth=0, padding=(6, 6))  # fmt: skip
    estilo.map("Treeview.Heading", background=[("active", PAINEL)])
    estilo.configure("Cartoes.Treeview", rowheight=64, font=(FONTE, 11))
    estilo.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])  # sem a borda branca do clam
    # abas internas (ex.: Legenda / Falantes / Audio no editor)
    estilo.configure("TNotebook", background=FUNDO, borderwidth=0, tabmargins=(0, 0, 0, 0))
    estilo.configure("TNotebook.Tab", background=PAINEL, foreground=TEXTO_2, font=(FONTE, 10, "bold"),
                     padding=(16, 7), borderwidth=0)  # fmt: skip
    estilo.map("TNotebook.Tab", background=[("selected", LARANJA)], foreground=[("selected", TEXTO_ESCURO)])
    # textos
    estilo.configure("TLabel", background=FUNDO, foreground=TEXTO)
    estilo.configure("Sec.TLabel", background=FUNDO, foreground=TEXTO_2, font=F_SECAO)
    # campos
    estilo.configure("TEntry", fieldbackground=CAMPO, foreground=TEXTO, insertcolor=TEXTO, bordercolor=BORDA)
    estilo.configure("TCombobox", fieldbackground=CAMPO, background=PAINEL, foreground=TEXTO, arrowcolor=TEXTO,
                     bordercolor=BORDA)  # fmt: skip
    estilo.map("TCombobox", fieldbackground=[("readonly", CAMPO)], foreground=[("readonly", TEXTO)],
               selectbackground=[("readonly", CAMPO)])  # fmt: skip
    raiz.option_add("*TCombobox*Listbox.background", PAINEL)
    raiz.option_add("*TCombobox*Listbox.foreground", TEXTO)
    raiz.option_add("*TCombobox*Listbox.selectBackground", LARANJA)
    for tipo in ("TCheckbutton", "TRadiobutton"):
        estilo.configure(tipo, background=FUNDO, foreground=TEXTO, indicatorbackground=CAMPO,
                         indicatorforeground=TEXTO_ESCURO, upperbordercolor=BORDA, lowerbordercolor=BORDA)  # fmt: skip
    estilo.map("TCheckbutton", background=[("active", FUNDO)], indicatorbackground=[("selected", LARANJA)])
    estilo.map("TRadiobutton", background=[("active", FUNDO)], indicatorbackground=[("selected", LARANJA)])
    # barras
    for tipo in ("TScrollbar", "Vertical.TScrollbar", "Horizontal.TScrollbar"):
        estilo.configure(tipo, background=BOTAO, troughcolor=FUNDO, bordercolor=FUNDO, lightcolor=BOTAO,
                         darkcolor=BOTAO, arrowcolor=TEXTO_2, gripcount=0, arrowsize=12)  # fmt: skip
        estilo.map(tipo, background=[("active", BOTAO_HOVER), ("disabled", FUNDO)])
    estilo.configure("Horizontal.TScale", background=LARANJA, troughcolor=CAMPO)
    estilo.configure("Horizontal.TProgressbar", background=LARANJA, troughcolor=CAMPO, bordercolor=BORDA,
                     lightcolor=LARANJA, darkcolor=LARANJA)  # fmt: skip
    estilo.configure("TMenubutton", background=PAINEL, foreground=TEXTO)
    # menus (botao direito e o menu de cima)
    for chave, valor in (("background", PAINEL), ("foreground", TEXTO), ("activeBackground", LARANJA),
                         ("activeForeground", TEXTO_ESCURO), ("font", F_TEXTO), ("relief", "flat"),
                         ("borderWidth", 1), ("activeBorderWidth", 0), ("tearOff", 0)):  # fmt: skip
        raiz.option_add(f"*Menu.{chave}", valor)
    raiz.option_add("*Listbox.background", PAINEL)
    raiz.option_add("*Listbox.foreground", TEXTO)
    raiz.option_add("*Listbox.selectBackground", LARANJA_ESCURO)
    raiz.option_add("*Listbox.font", F_TEXTO)
    raiz.option_add("*Text.background", CAMPO)
    raiz.option_add("*Text.foreground", TEXTO)
    raiz.option_add("*Text.insertBackground", TEXTO)
    raiz.option_add("*Entry.background", CAMPO)
    raiz.option_add("*Entry.foreground", TEXTO)
    raiz.option_add("*Entry.insertBackground", TEXTO)
    raiz.option_add("*Toplevel.background", FUNDO)


def rotulo(pai, texto="", estilo="texto", cor=None, fundo=None, **k) -> tk.Label:
    """Um texto ja no tema. estilo: texto | secundario | secao | subtitulo | titulo | pequeno."""
    fontes = {"texto": F_TEXTO, "secundario": F_TEXTO, "secao": F_SECAO, "subtitulo": F_SUBTITULO,
              "titulo": F_TITULO, "pequeno": F_PEQUENA}  # fmt: skip
    padrao = TEXTO_2 if estilo in ("secundario", "secao", "pequeno") else TEXTO
    k.setdefault("anchor", "w")
    k.setdefault("justify", "left")
    return tk.Label(pai, text=texto, bg=fundo or FUNDO, fg=cor or padrao, font=fontes.get(estilo, F_TEXTO), **k)


def quadro(pai, fundo=None, **k) -> tk.Frame:
    return tk.Frame(pai, bg=fundo or FUNDO, **k)


def cartao(pai, **k) -> tk.Frame:
    """Painel com fundo um pouco mais claro e borda fina."""
    return tk.Frame(pai, bg=PAINEL, highlightbackground=BORDA, highlightthickness=1, **k)

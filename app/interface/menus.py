# Menus de botao direito (menu de contexto), iguais em todas as telas.
# Cada item e uma tupla:
#   ("texto", funcao)                      -> item normal
#   ("texto", funcao, "Ctrl+S")            -> item com o atalho escrito do lado
#   ("texto", [itens...])                  -> submenu (ex.: "Trocar quem fala ›")
#   ("texto", funcao, None, marcado)       -> item com marca (✓) quando marcado=True
#   None                                   -> linha separadora
# Item com funcao None aparece apagado (nao da para clicar).
# Todo menu de botao direito ganha no final o "🐞 Reportar bug..." (interface/reportar_bug.py).
import tkinter as tk

from interface import tema


def montar_menu(pai: tk.Misc, itens: list) -> tk.Menu:
    menu = tk.Menu(pai, tearoff=0, bg=tema.PAINEL, fg=tema.TEXTO, activebackground=tema.LARANJA,
                   activeforeground=tema.TEXTO_ESCURO, disabledforeground=tema.BORDA, font=tema.F_TEXTO,
                   relief="flat", bd=1)  # fmt: skip
    for item in itens:
        if item is None:
            menu.add_separator()
            continue
        texto, acao = item[0], item[1]
        atalho = item[2] if len(item) > 2 else None
        if isinstance(acao, list):
            menu.add_cascade(label=texto, menu=montar_menu(menu, acao))
        elif len(item) > 3:
            var = tk.BooleanVar(master=menu, value=bool(item[3]))
            menu.add_checkbutton(label=texto, variable=var, command=acao, accelerator=atalho or "",
                                 selectcolor=tema.LARANJA)  # fmt: skip
            menu._vars = getattr(menu, "_vars", []) + [var]  # guarda a variavel (senao o tkinter esquece)
        else:
            menu.add_command(label=texto, command=acao or (lambda: None), accelerator=atalho or "",
                             state="normal" if acao else "disabled")  # fmt: skip
    return menu


def abrir_menu(evento, menu: tk.Menu):
    """Mostra o menu onde o mouse esta."""
    try:
        menu.tk_popup(evento.x_root, evento.y_root)
    finally:
        menu.grab_release()


def ligar_botao_direito(widget: tk.Misc, construir):
    """Botao direito no widget abre o menu que construir(evento) devolver (ou nada, se devolver None).
    No Mac o botao direito e o Button-2; no Windows e no Linux, Button-3."""

    def ao_clicar(evento):
        from interface.reportar_bug import ITEM_DO_MENU, item_do_menu

        menu = construir(evento)
        if menu is None:
            menu = montar_menu(widget, [])
        fim = menu.index("end")
        if fim is None or menu.entrycget(fim, "label") != ITEM_DO_MENU:
            if fim is not None:
                menu.add_separator()
            texto, acao = item_do_menu(widget)
            menu.add_command(label=texto, command=acao)
        abrir_menu(evento, menu)
        return "break"

    for botao in ("<Button-3>", "<Button-2>" if widget.tk.call("tk", "windowingsystem") == "aqua" else None):
        if botao:
            widget.bind(botao, ao_clicar)


def todos_os_itens(menu: tk.Menu) -> list:
    """(rotulo, indice, menu) de todos os itens clicaveis, entrando nos submenus. Usado pelos testes."""
    achados = []
    fim = menu.index("end")
    for k in range(0 if fim is None else fim + 1):
        tipo = menu.type(k)
        if tipo == "cascade":
            achados += todos_os_itens(menu.nametowidget(menu.entrycget(k, "menu")))
        elif tipo in ("command", "checkbutton") and menu.entrycget(k, "state") != "disabled":
            achados.append((menu.entrycget(k, "label"), k, menu))
    return achados

# Janela "Pessoas e cores": o cadastro de quem aparece nos Shorts (nome e cor da legenda).
# Criar, renomear, mudar a cor, escolher a pessoa padrao (quem fica com as falas sem dono) e excluir.
# A pessoa padrao (FamosoZora) nao pode ser excluida.
import tkinter as tk
from tkinter import colorchooser, messagebox, simpledialog, ttk

from interface import tema
from interface.utilidades import COR_DESTAQUE, COR_FUNDO, COR_TEXTO
from shorts import pessoas

# cores sugeridas para pessoas novas (as mesmas da versao 1.3.0, sem amarelo)
CORES_SUGERIDAS = ["#8CE6FF", "#FF96C8", "#96FF9B", "#FFB46E", "#C8A0FF", "#5AB4FF", "#FF6464"]


def proxima_cor() -> str:
    usadas = {p["cor"] for p in pessoas.ler_pessoas()}
    return next((c for c in CORES_SUGERIDAS if c not in usadas), CORES_SUGERIDAS[0])


def escolher_cor(pai, atual: str):
    """Abre o seletor de cor. Devolve '#RRGGBB' ou None (cancelou)."""
    _, cor = colorchooser.askcolor(color=atual, parent=pai, title="Cor da legenda")
    return pessoas.cor_valida(cor) if cor else None


def aviso_de_contraste(cor: str) -> str:
    if pessoas.dificil_de_ler(cor):
        return "⚠ cor escura: difícil de ler com a borda preta da legenda"
    return ""


def nova_pessoa(pai):
    """Pergunta o nome e cria a pessoa (com uma cor sugerida). Devolve a pessoa ou None."""
    nome = simpledialog.askstring("Nova pessoa", "Nome de quem fala (aparece no vídeo, se ligado):", parent=pai)
    if not nome or not nome.strip():
        return None
    try:
        return pessoas.adicionar(nome.strip(), proxima_cor())
    except ValueError as e:
        messagebox.showinfo("Nova pessoa", str(e), parent=pai)
        return pessoas.achar(nome)


class JanelaPessoas:
    def __init__(self, pai, ao_mudar=None):
        self.ao_mudar = ao_mudar or (lambda: None)
        self.jan = tk.Toplevel(pai)
        self.jan.title("Pessoas e cores")
        self.jan.geometry("520x420")
        self.jan.configure(bg=COR_FUNDO)
        tk.Label(self.jan, text="Pessoas e cores da legenda", bg=COR_FUNDO, fg=COR_DESTAQUE,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=14, pady=(12, 0))  # fmt: skip
        tk.Label(
            self.jan, bg=COR_FUNDO, fg=tema.TEXTO_2, font=("Segoe UI", 9), justify="left", anchor="w",
            text="Vale para todos os projetos. A pessoa ★ padrão fica com as falas que não forem ligadas a ninguém.",
            wraplength=490,
        ).pack(fill="x", padx=14)  # fmt: skip
        self.lista = tk.Listbox(self.jan, font=("Segoe UI", 11), bg=tema.PAINEL, fg=COR_TEXTO, activestyle="none",
                                selectbackground=tema.LARANJA_ESCURO, selectforeground=tema.TEXTO, highlightthickness=0, exportselection=False)  # fmt: skip
        self.lista.pack(fill="both", expand=True, padx=14, pady=8)
        self.lista.bind("<<ListboxSelect>>", lambda e: self.mostrar_aviso())
        self.lbl_aviso = tk.Label(self.jan, text="", bg=COR_FUNDO, fg=tema.AMARELO, font=("Segoe UI", 9), anchor="w")
        self.lbl_aviso.pack(fill="x", padx=14)
        botoes = tk.Frame(self.jan, bg=COR_FUNDO)
        botoes.pack(fill="x", padx=14, pady=(4, 12))
        for texto, comando in [("+ Nova", self.nova), ("Renomear", self.renomear), ("Mudar cor", self.mudar_cor),
                               ("Tornar padrão", self.tornar_padrao), ("Excluir", self.excluir)]:  # fmt: skip
            ttk.Button(botoes, text=texto, style="Extra.TButton", command=comando).pack(side="left", padx=(0, 6))
        self.mostrar()

    def mostrar(self, selecionar: str | None = None):
        self.cadastro = pessoas.ler_pessoas()
        self.lista.delete(0, "end")
        for k, p in enumerate(self.cadastro):
            self.lista.insert("end", f"  ●  {p['nome']}{'   ★ padrão' if p['padrao'] else ''}   ({p['cor']})")
            self.lista.itemconfig(k, foreground=p["cor"])
            if selecionar and p["nome"].lower() == selecionar.lower():
                self.lista.selection_set(k)
        self.mostrar_aviso()

    def atual(self):
        sel = self.lista.curselection()
        return self.cadastro[sel[0]] if sel else None

    def mostrar_aviso(self):
        p = self.atual()
        self.lbl_aviso.config(text=aviso_de_contraste(p["cor"]) if p else "")

    def _pronto(self, nome=None):
        self.mostrar(nome)
        self.ao_mudar()

    def _exigir(self):
        p = self.atual()
        if not p:
            messagebox.showinfo("Pessoas", "Escolha uma pessoa na lista primeiro.", parent=self.jan)
        return p

    def nova(self):
        p = nova_pessoa(self.jan)
        if p:
            self._pronto(p["nome"])

    def renomear(self):
        p = self._exigir()
        if not p:
            return
        novo = simpledialog.askstring(
            "Renomear", f"Novo nome para {p['nome']}:", initialvalue=p["nome"], parent=self.jan
        )
        if not novo or novo.strip() == p["nome"]:
            return
        try:
            pessoas.renomear(p["nome"], novo)
        except ValueError as e:
            messagebox.showinfo("Renomear", str(e), parent=self.jan)
            return
        self._pronto(novo.strip())

    def mudar_cor(self):
        p = self._exigir()
        if not p:
            return
        cor = escolher_cor(self.jan, p["cor"])
        if cor:
            pessoas.mudar_cor(p["nome"], cor)
            self._pronto(p["nome"])

    def tornar_padrao(self):
        p = self._exigir()
        if p:
            pessoas.definir_padrao(p["nome"])
            self._pronto(p["nome"])

    def excluir(self):
        p = self._exigir()
        if not p:
            return
        if p["padrao"]:
            messagebox.showinfo("Excluir", f"{p['nome']} é a pessoa padrão e não pode ser excluída.", parent=self.jan)
            return
        if messagebox.askyesno(
            "Excluir", f"Excluir {p['nome']}?\nAs falas dessa pessoa voltam para a pessoa padrão.", parent=self.jan
        ):
            pessoas.excluir(p["nome"])
            self._pronto()

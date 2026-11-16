# Painel "Falantes" do editor de legendas: cada voz que o detector achou no Short,
# um botao para ouvir uma amostra dela, a escolha da pessoa (do cadastro ou "+ nova pessoa") e a cor.
# Tambem liga/desliga "Mostrar nome de quem fala" no video deste Short.
import tkinter as tk
from tkinter import ttk

from interface.janela_pessoas import JanelaPessoas, aviso_de_contraste, escolher_cor, nova_pessoa
from interface.utilidades import COR_FUNDO, COR_TEXTO
from shorts import pessoas

NOVA = "+ nova pessoa..."


def vozes_do_short(palavras: list) -> list:
    """[(voz, quantas palavras)] na ordem em que cada voz aparece."""
    conta = {}
    for w in palavras:
        if "s" in w:
            conta[str(w["s"])] = conta.get(str(w["s"]), 0) + 1
    return list(conta.items())


def trecho_de_amostra(palavras: list, voz: str, maximo: float = 6.0):
    """O maior pedaco seguido em que so essa voz fala: (inicio, fim) no video original, ou None."""
    melhor, atual = None, None
    for w in palavras:
        if str(w.get("s")) == voz:
            atual = [atual[0], w["f"]] if atual and w["i"] - atual[1] < 0.8 else [w["i"], w["f"]]
            if not melhor or atual[1] - atual[0] > melhor[1] - melhor[0]:
                melhor = list(atual)
        else:
            atual = None
    if not melhor:
        return None
    return max(0.0, melhor[0] - 0.2), min(melhor[1] + 0.2, melhor[0] + maximo)


def nome_da_voz(voz: str) -> str:
    return f"Voz {int(voz[1:]) + 1} (abertura)" if voz.startswith("a") else f"Voz {int(voz) + 1}"


class PainelFalantes:
    def __init__(self, pai, editor):
        self.editor = editor
        self.quadro = tk.Frame(pai, bg=COR_FUNDO)
        self.quadro.pack(fill="both", expand=True, padx=8, pady=8)
        topo = tk.Frame(self.quadro, bg=COR_FUNDO)
        topo.pack(fill="x")
        tk.Label(
            topo, bg=COR_FUNDO, fg="#c8c8d8", font=("Segoe UI", 10), justify="left", anchor="w", wraplength=640,
            text="Ligue cada voz a uma pessoa. Voz sem pessoa = a pessoa padrão (branco). "
            "Se o detector errar numa linha, troque na aba Legenda (\"Quem fala nesta linha\").",
        ).pack(side="left", fill="x", expand=True)  # fmt: skip
        ttk.Button(topo, text="Pessoas e cores...", style="Extra.TButton", command=self.abrir_cadastro).pack(
            side="right"
        )
        self.mostrar_nome = tk.BooleanVar(value=False)
        tk.Checkbutton(
            self.quadro, text="Mostrar nome de quem fala no vídeo (só quando não é a pessoa padrão)",
            variable=self.mostrar_nome, command=self.mudou_mostrar_nome, bg=COR_FUNDO, fg=COR_TEXTO,
            selectcolor="#14141f", activebackground=COR_FUNDO, activeforeground=COR_TEXTO, font=("Segoe UI", 10),
            anchor="w",
        ).pack(fill="x", pady=(8, 4))  # fmt: skip
        self.linhas = tk.Frame(self.quadro, bg=COR_FUNDO)
        self.linhas.pack(fill="both", expand=True)

    # ---------------------------------------------------------- desenhar
    def mostrar(self):
        for filho in self.linhas.winfo_children():
            filho.destroy()
        self.mostrar_nome.set(bool(self.editor.edicao.get("mostrar_nome_falante")))
        cadastro = pessoas.ler_pessoas()
        padrao = pessoas.pessoa_padrao(cadastro)
        vozes = vozes_do_short(self.editor.palavras)
        if not vozes:
            tk.Label(
                self.linhas, bg=COR_FUNDO, fg="#9a9ab0", font=("Segoe UI", 10), justify="left", anchor="w",
                text=f"Nenhuma voz separada neste Short: tudo sai como {padrao['nome']}.\n"
                "(o detector de vozes estava desligado ou não conseguiu separar). "
                "Você ainda pode trocar quem fala linha por linha, na aba Legenda.",
            ).pack(fill="x", pady=6)  # fmt: skip
            return
        nomes = [p["nome"] for p in cadastro]
        for voz, quantas in vozes:
            nome = self.editor.ligacoes.get(voz) or ""
            pessoa = pessoas.achar(nome, cadastro) or padrao
            linha = tk.Frame(self.linhas, bg=COR_FUNDO)
            linha.pack(fill="x", pady=3)
            tk.Label(linha, text=f"{nome_da_voz(voz)}  ·  {quantas} palavras", width=24, anchor="w", bg=COR_FUNDO,
                     fg=COR_TEXTO, font=("Segoe UI", 10)).pack(side="left")  # fmt: skip
            ttk.Button(linha, text="▶ ouvir", style="Extra.TButton", width=8,
                       command=lambda v=voz: self.ouvir(v)).pack(side="left", padx=4)  # fmt: skip
            escolha = ttk.Combobox(linha, values=nomes + [NOVA], state="readonly", width=18)
            escolha.set(pessoa["nome"])
            escolha.bind("<<ComboboxSelected>>", lambda e, v=voz, cb=escolha: self.escolheu(v, cb.get()))
            escolha.pack(side="left", padx=4)
            tk.Button(linha, text="  cor  ", bg=pessoa["cor"], fg="#000000", relief="flat",
                      command=lambda p=pessoa["nome"]: self.trocar_cor(p)).pack(side="left", padx=4)  # fmt: skip
            tk.Label(linha, text=aviso_de_contraste(pessoa["cor"]), bg=COR_FUNDO, fg="#ffb347",
                     font=("Segoe UI", 9)).pack(side="left", padx=4)  # fmt: skip

    # ---------------------------------------------------------- acoes
    def ouvir(self, voz: str):
        trecho = trecho_de_amostra(self.editor.palavras, voz)
        if trecho:
            self.editor.tocar_trecho(trecho[0], trecho[1], f"voz_{voz}")

    def escolheu(self, voz: str, nome: str):
        if nome == NOVA:
            p = nova_pessoa(self.editor.jan)
            if not p:
                self.mostrar()
                return
            nome = p["nome"]
        padrao = pessoas.pessoa_padrao()
        valor = "" if nome.lower() == padrao["nome"].lower() else nome

        def aplicar():
            if valor:
                self.editor.ligacoes[voz] = valor
            else:
                self.editor.ligacoes.pop(voz, None)

        self.editor.mudar(aplicar)

    def trocar_cor(self, nome: str):
        p = pessoas.achar(nome)
        cor = escolher_cor(self.editor.jan, p["cor"]) if p else None
        if cor:
            pessoas.mudar_cor(nome, cor)  # o cadastro vale para todos os projetos: grava na hora
            self.editor.redesenhar()

    def mudou_mostrar_nome(self):
        valor = self.mostrar_nome.get()
        self.editor.mudar(lambda: self.editor.edicao.update(mostrar_nome_falante=valor))

    def abrir_cadastro(self):
        JanelaPessoas(self.editor.jan, ao_mudar=self.editor.redesenhar)

# Configuracoes > "Cortes automaticos": as regras das predefinicoes "Longo (TV)" e "Short (dinamico)" do Auto-Edit,
# uma aba para cada, com "Salvar" e "Voltar ao padrao". Mudar uma regra aumenta a versao da predefinicao.
# As regras ficam em autoedit/predefinicoes.py (fabrica) e no predefinicoes_corte.json deste PC.
import tkinter as tk
from tkinter import messagebox, ttk

from autoedit import predefinicoes
from interface import tema
from interface.telas import nova_janela


class JanelaPredefinicoes:
    def __init__(self, studio):
        self.studio = studio
        self.jan = nova_janela(studio.raiz)
        self.jan.title("Cortes automáticos (predefinições)")
        self.jan.configure(bg=tema.FUNDO)
        self.jan.geometry("560x700")
        tk.Label(self.jan, text="Cortes automáticos", bg=tema.FUNDO, fg=tema.TEXTO, font=tema.F_SUBTITULO).pack(
            anchor="w", padx=14, pady=(12, 0))
        tk.Label(self.jan, text="As regras que o Auto-Edit usa para sugerir cortes. O mesmo vídeo com a mesma "
                 "predefinição dá sempre o mesmo resultado.\nNo editor, \"Analisar de novo com esta predefinição\" "
                 "aplica as regras novas sem perder os seus cortes.", bg=tema.FUNDO, fg=tema.TEXTO_2,
                 font=tema.F_PEQUENA, justify="left", wraplength=520).pack(anchor="w", padx=14, pady=(2, 8))  # fmt: skip
        self.abas = ttk.Notebook(self.jan)
        self.abas.pack(fill="both", expand=True, padx=14)
        self.campos = {}
        for tipo in predefinicoes.TIPOS:
            self._aba(tipo)
        tk.Label(self.jan, text="Longo (TV): segue as diretrizes do canal — pausas naturais durante o jogo ficam.",
                 bg=tema.FUNDO, fg=tema.AMARELO, font=tema.F_PEQUENA).pack(anchor="w", padx=14, pady=(6, 10))  # fmt: skip

    def _aba(self, tipo: str):
        regras = predefinicoes.da(tipo)
        aba = tk.Frame(self.abas, bg=tema.PAINEL)
        self.abas.add(aba, text=f"{regras['nome']} (v{regras['versao']})")
        vars_ = {}
        for k, (chave, texto, conv) in enumerate(predefinicoes.CAMPOS):
            tk.Label(aba, text=texto, bg=tema.PAINEL, fg=tema.TEXTO, font=tema.F_TEXTO, anchor="w").grid(
                row=k, column=0, sticky="w", padx=(12, 8), pady=2)
            if conv is bool:
                v = tk.BooleanVar(value=bool(regras.get(chave)))
                ttk.Checkbutton(aba, variable=v).grid(row=k, column=1, sticky="w")
            else:
                v = tk.StringVar(value=f"{regras.get(chave, 0):g}")
                ttk.Entry(aba, textvariable=v, width=8).grid(row=k, column=1, sticky="w")
            vars_[chave] = v
        self.campos[tipo] = vars_
        linha = tk.Frame(aba, bg=tema.PAINEL)
        linha.grid(row=len(predefinicoes.CAMPOS), column=0, columnspan=2, sticky="we", padx=12, pady=10)
        ttk.Button(linha, text="Salvar", style="Passo.TButton", command=lambda: self.salvar(tipo)).pack(side="left")
        ttk.Button(linha, text="Voltar ao padrão", style="Extra.TButton",
                   command=lambda: self.voltar(tipo)).pack(side="left", padx=8)  # fmt: skip

    def salvar(self, tipo: str):
        valores = {k: v.get() for k, v in self.campos[tipo].items()}
        limpo, erros = predefinicoes.validar(valores, tipo)
        if erros:
            messagebox.showerror("Cortes automáticos", "Arrume antes de salvar:\n\n- " + "\n- ".join(erros),
                                 parent=self.jan)  # fmt: skip
            return
        versao = predefinicoes.salvar(tipo, limpo)
        self._renomear(tipo, versao)
        self.studio.notificar(f"Predefinição salva (versão {versao}). No editor: \"Analisar de novo com esta "
                              "predefinição\".", "ok", 6)  # fmt: skip

    def voltar(self, tipo: str):
        if not messagebox.askyesno("Voltar ao padrão", "Voltar todas as regras desta predefinição para as de "
                                   "fábrica?", parent=self.jan):  # fmt: skip
            return
        versao = predefinicoes.voltar_ao_padrao(tipo)
        regras = predefinicoes.da(tipo)
        for chave, v in self.campos[tipo].items():
            v.set(bool(regras[chave]) if isinstance(v, tk.BooleanVar) else f"{regras[chave]:g}")
        self._renomear(tipo, versao)

    def _renomear(self, tipo: str, versao: int):
        k = predefinicoes.TIPOS.index(tipo)
        self.abas.tab(k, text=f"{predefinicoes.da(tipo)['nome']} (v{versao})")

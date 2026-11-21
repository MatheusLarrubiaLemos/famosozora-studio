# "Analisar os selecionados" (aba Videos longos com varios marcados): roda o Auto-Edit em cada live, uma depois
# da outra, escondido, com o progresso de cada uma e um botao Cancelar. A revisao continua sendo uma por uma, no
# editor ("Editar"). Usa o mesmo jeito de rodar escondido do lote de Shorts (shorts/lote.py).
import re
import threading
import tkinter as tk
from tkinter import ttk

from interface import tema
from nucleo.registro import registrar


class JanelaAnaliseLote:
    def __init__(self, studio, projetos: list, usar_claude: bool = True):
        self.studio = studio
        self.projetos = list(projetos)
        self.usar_claude = usar_claude
        self.cancelar = threading.Event()
        self.situacao = {str(p["pasta"]): "na fila" for p in self.projetos}
        self.pct = 0.0
        self.atual = None
        self.acabou = False
        self.jan = tk.Toplevel(studio.raiz)
        self.jan.title(f"Analisar {len(self.projetos)} live(s)")
        self.jan.configure(bg=tema.FUNDO)
        self.jan.geometry("640x380")
        self.jan.protocol("WM_DELETE_WINDOW", self.fechar)
        tk.Label(self.jan, text="Auto-Edit: analisando uma live depois da outra", bg=tema.FUNDO, fg=tema.TEXTO,
                 font=tema.F_SUBTITULO).pack(anchor="w", padx=14, pady=(12, 2))  # fmt: skip
        tk.Label(self.jan, text="Pode continuar usando o Studio. A revisão é depois, uma por uma, no botão \"Editar\".",
                 bg=tema.FUNDO, fg=tema.TEXTO_2, font=tema.F_PEQUENA).pack(anchor="w", padx=14)  # fmt: skip
        self.lista = ttk.Treeview(self.jan, columns=("live", "situacao"), show="headings", height=9)
        self.lista.heading("live", text="Live")
        self.lista.heading("situacao", text="Situação")
        self.lista.column("live", width=380)
        self.lista.column("situacao", width=200)
        self.lista.pack(fill="both", expand=True, padx=14, pady=8)
        for p in self.projetos:
            self.lista.insert("", "end", iid=str(p["pasta"]), values=(p["nome"], "na fila"))
        baixo = tk.Frame(self.jan, bg=tema.FUNDO)
        baixo.pack(fill="x", padx=14, pady=(0, 12))
        self.barra = ttk.Progressbar(baixo, length=360, maximum=100)
        self.barra.pack(side="left")
        self.btn = ttk.Button(baixo, text="Cancelar", style="Extra.TButton", command=self.parar)
        self.btn.pack(side="right")
        threading.Thread(target=self._rodar, daemon=True).start()
        self._mostrar()

    def _rodar(self):
        from shorts.lote import Cancelado, rodar_processo

        for p in self.projetos:
            if self.cancelar.is_set():
                break
            chave = str(p["pasta"])
            self.atual, self.pct = chave, 0.0
            self.situacao[chave] = "analisando..."

            def ao_ler(linha, chave=chave):
                m = re.match(r"\[(\d+)/(\d+)\]\s+(.*?)\s+([\d.]+)%", linha)
                if m:
                    k, n = int(m[1]), int(m[2])
                    self.pct = ((k - 1) + float(m[4]) / 100) / n * 100
                    self.situacao[chave] = f"etapa {k} de {n}"

            args = ["autoedit.analisar", chave] + ([] if self.usar_claude else ["--sem-claude"])
            try:
                codigo, ultimas = rodar_processo(args, self.cancelar, ao_ler)
                self.situacao[chave] = "✓ pronta para revisar" if codigo == 0 else "✗ deu erro (veja o studio.log)"
                if codigo != 0:
                    registrar(f"análise em lote falhou: {chave}\n" + "\n".join(ultimas[-15:]))
            except Cancelado:
                self.situacao[chave] = "cancelada"
                break
            except Exception as e:
                registrar("análise em lote", e)
                self.situacao[chave] = f"✗ {e}"
        for chave, s in self.situacao.items():
            if s == "na fila" and self.cancelar.is_set():
                self.situacao[chave] = "cancelada"
        self.acabou = True

    def _mostrar(self):
        try:
            for chave, s in self.situacao.items():
                self.lista.set(chave, "situacao", s)
            feitas = sum(1 for s in self.situacao.values() if s.startswith(("✓", "✗", "cancel")))
            total = max(1, len(self.projetos))
            self.barra.configure(value=(feitas + (self.pct / 100 if not self.acabou else 0)) / total * 100)
            if self.acabou:
                self.btn.configure(text="Fechar", command=self.fechar)
                self.studio.notificar("Análise das lives terminou. Abra cada uma em \"Editar\" para revisar.", "ok", 6)
                self.studio.atualizar()
                return
            self.jan.after(400, self._mostrar)
        except tk.TclError:
            pass  # janela fechada

    def parar(self):
        self.cancelar.set()
        self.btn.configure(text="Cancelando...")

    def fechar(self):
        if not self.acabou:
            self.cancelar.set()
        self.jan.destroy()

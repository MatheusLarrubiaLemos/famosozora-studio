# Janela do passo 4: copiar os textos de cada Short, abrir o Buffer e marcar o que ja foi postado.
import tkinter as tk
import webbrowser
from tkinter import ttk

from interface.utilidades import BUFFER_URL, COR_DESTAQUE, COR_FUNDO, COR_TEXTO, abrir, mostrar_na_pasta
from nucleo.comum import CANAL_URL, gravar_json, ler_json
from nucleo.projetos import REDES


class JanelaPublicar:
    def __init__(self, studio, info: dict):
        self.studio = studio
        self.pasta = info["pasta"]
        self.prontos = self.pasta / "prontos"
        self.arq = self.prontos / "publicacao.json"
        self.pub = ler_json(self.arq, {}) or {}
        self.link = (ler_json(self.pasta / "projeto.json", {}) or {}).get("link_video_completo") or CANAL_URL

        self.jan = tk.Toplevel(studio.raiz)
        self.jan.title(f"Publicar - {info['nome']}")
        self.jan.geometry("1060x640")
        self.jan.configure(bg=COR_FUNDO)

        topo = tk.Frame(self.jan, bg=COR_FUNDO)
        topo.pack(fill="x", padx=16, pady=(12, 4))
        tk.Label(
            topo,
            text="Publicar no YouTube, TikTok e Instagram",
            bg=COR_FUNDO,
            fg=COR_DESTAQUE,
            font=("Segoe UI", 15, "bold"),
        ).pack(side="left")
        ttk.Button(
            topo, text="Abrir o Buffer", style="Passo.TButton", command=lambda: webbrowser.open(BUFFER_URL)
        ).pack(side="right")
        dica = (
            "No Buffer: Criar post → marque YouTube, TikTok e Instagram → arraste o vídeo "
            "('Mostrar na pasta') → personalize o texto de cada rede colando os textos abaixo → Agendar ou Publicar."
        )
        tk.Label(
            self.jan, text=dica, bg=COR_FUNDO, fg="#c8c8d8", font=("Segoe UI", 10), wraplength=1020, justify="left"
        ).pack(fill="x", padx=16)

        corpo = tk.Frame(self.jan, bg=COR_FUNDO)
        corpo.pack(fill="both", expand=True, padx=16, pady=10)

        self.lista = tk.Listbox(
            corpo,
            width=46,
            font=("Segoe UI", 10),
            activestyle="none",
            bg="#232336",
            fg=COR_TEXTO,
            selectbackground="#3a3a5a",
            highlightthickness=0,
            borderwidth=0,
        )
        self.lista.pack(side="left", fill="y")
        self.lista.bind("<<ListboxSelect>>", lambda e: self.mostrar())

        dir_ = tk.Frame(corpo, bg=COR_FUNDO)
        dir_.pack(side="left", fill="both", expand=True, padx=(14, 0))

        self.lbl_nome = tk.Label(
            dir_,
            text="",
            bg=COR_FUNDO,
            fg=COR_TEXTO,
            font=("Segoe UI", 12, "bold"),
            anchor="w",
            justify="left",
            wraplength=560,
        )
        self.lbl_nome.pack(fill="x")
        linha = tk.Frame(dir_, bg=COR_FUNDO)
        linha.pack(fill="x", pady=(6, 8))
        ttk.Button(linha, text="Mostrar na pasta", style="Extra.TButton", command=self.na_pasta).pack(side="left")
        ttk.Button(linha, text="Assistir", style="Extra.TButton", command=self.assistir).pack(side="left", padx=6)

        self.vars = {}
        for rede, nome in REDES:
            quadro = tk.Frame(dir_, bg="#232336", padx=10, pady=8)
            quadro.pack(fill="x", pady=3)
            tk.Label(
                quadro, text=nome, bg="#232336", fg=COR_DESTAQUE, width=10, anchor="w", font=("Segoe UI", 11, "bold")
            ).pack(side="left")
            if rede == "youtube":
                for txt, campo in [
                    ("Copiar título", "titulo"),
                    ("Copiar descrição", "descricao"),
                    ("Copiar tags", "tags"),
                    ("Título EN", "titulo_en"),
                    ("Desc. EN", "descricao_en"),
                ]:
                    ttk.Button(
                        quadro, text=txt, style="Extra.TButton", command=lambda c=campo: self.copiar_youtube(c)
                    ).pack(side="left", padx=3)
            else:
                ttk.Button(
                    quadro, text="Copiar legenda", style="Extra.TButton", command=lambda r=rede: self.copiar_rede(r)
                ).pack(side="left", padx=3)
            v = tk.BooleanVar()
            tk.Checkbutton(
                quadro,
                text="Postado",
                variable=v,
                bg="#232336",
                fg=COR_TEXTO,
                selectcolor="#14141f",
                activebackground="#232336",
                activeforeground=COR_TEXTO,
                font=("Segoe UI", 10),
                command=lambda r=rede: self.marcar(r),
            ).pack(side="right")
            self.vars[rede] = v

        tk.Label(
            dir_,
            text="Prévia do texto (o que você copiar aparece aqui):",
            bg=COR_FUNDO,
            fg="#9a9ab0",
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(10, 2))
        self.txt = tk.Text(
            dir_,
            height=11,
            wrap="word",
            font=("Segoe UI", 10),
            bg="#0e0e16",
            fg=COR_TEXTO,
            insertbackground=COR_TEXTO,
            relief="flat",
            padx=8,
            pady=6,
        )
        self.txt.pack(fill="both", expand=True)

        self.preencher_lista()
        if self.shorts():
            self.lista.selection_set(0)
            self.mostrar()

    def shorts(self):
        return self.pub.get("shorts", [])

    def preencher_lista(self):
        sel = self.lista.curselection()
        self.lista.delete(0, "end")
        for s in self.shorts():
            p = s.get("postado", {})
            feito = sum(1 for r, _ in REDES if p.get(r))
            marca = "OK " if feito == len(REDES) else f"{feito}/3"
            self.lista.insert("end", f" [{marca}]  {s['arquivo']}")
        if sel:
            self.lista.selection_set(sel[0])

    def atual(self):
        sel = self.lista.curselection()
        return self.shorts()[sel[0]] if sel else None

    def mostrar(self):
        s = self.atual()
        if not s:
            return
        self.lbl_nome.config(text=f"{s['arquivo']}   ({s.get('duracao', '?')}s)")
        for rede, _ in REDES:
            self.vars[rede].set(bool(s.get("postado", {}).get(rede)))
        self.mostrar_texto(s["textos"]["youtube"]["titulo"])

    def preencher(self, t: str) -> str:
        return t.replace("{link}", self.link).replace("{canal}", CANAL_URL)

    def mostrar_texto(self, t: str):
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", t)

    def copiar(self, t: str):
        t = self.preencher(t)
        self.studio.copiar(t)
        self.mostrar_texto(t)

    def copiar_youtube(self, campo):
        s = self.atual()
        if s:
            v = s["textos"]["youtube"].get(campo, "")
            self.copiar(", ".join(v) if isinstance(v, list) else v)

    def copiar_rede(self, rede):
        s = self.atual()
        if s:
            self.copiar(s["textos"].get(rede, ""))

    def marcar(self, rede):
        s = self.atual()
        if not s:
            return
        s.setdefault("postado", {})[rede] = bool(self.vars[rede].get())
        gravar_json(self.arq, self.pub)
        self.preencher_lista()
        self.studio.atualizar()

    def arquivo(self):
        s = self.atual()
        return self.prontos / s["arquivo"] if s else None

    def na_pasta(self):
        a = self.arquivo()
        if a:
            mostrar_na_pasta(a)

    def assistir(self):
        a = self.arquivo()
        if a and a.exists():
            abrir(a)

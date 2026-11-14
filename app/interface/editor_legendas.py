# Editor de legendas: revisar a legenda de cada Short antes de postar.
# Mostra a legenda em linhas (inicio, fim, texto), destaca em amarelo o que o Claude marcou como incerto,
# sublinha possiveis erros de portugues, deixa censurar palavras e renderiza de novo so aquele Short.
import copy
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from interface.utilidades import COR_DESTAQUE, COR_FUNDO, COR_TEXTO, abrir, rodar_script
from nucleo.comum import DADOS_APP, ler_json, tempo_txt
from nucleo.ortografia import Corretor
from nucleo.video import achar_programa
from shorts import revisao
from shorts.censura import adicionar_a_lista, indices_da_lista, ler_censura, mascarar

COR_INCERTO = "#6b5a00"  # fundo amarelo escuro: palavra que o Claude marcou como [[incerta]]


class EditorLegendas:
    def __init__(self, studio, info: dict):
        self.studio = studio
        self.pasta = info["pasta"]
        self.video = Path((ler_json(self.pasta / "projeto.json", {}) or {}).get("video", ""))
        self.shorts = (ler_json(self.pasta / "prontos" / "publicacao.json", {}) or {}).get("shorts", [])
        self.corretor = Corretor()
        self.n = None  # numero do Short aberto
        self.palavras = []  # legenda em edicao
        self.originais = []  # legenda como saiu da geracao
        self.linhas = []  # posicoes das palavras de cada linha
        self.desfazer_pilha = []
        self.mudou = False

        self.jan = tk.Toplevel(studio.raiz)
        self.jan.title(f"Revisar legendas - {info['nome']}")
        self.jan.geometry("1180x700")
        self.jan.configure(bg=COR_FUNDO)
        self.jan.protocol("WM_DELETE_WINDOW", self.fechar)
        self.jan.bind("<FocusIn>", self.recarregar_se_chegou_legenda)
        self.censurar_lista = tk.BooleanVar(value=False)
        self._montar_lista_de_shorts()
        self._montar_editor()
        if self.shorts:
            self.lista.selection_set(0)
            self.abrir_short()

    # ---------------------------------------------------------- montagem
    def _montar_lista_de_shorts(self):
        esquerda = tk.Frame(self.jan, bg=COR_FUNDO)
        esquerda.pack(side="left", fill="y", padx=(14, 0), pady=12)
        tk.Label(esquerda, text="Shorts do projeto", bg=COR_FUNDO, fg=COR_DESTAQUE, font=("Segoe UI", 12, "bold")).pack(
            anchor="w"
        )
        self.lista = tk.Listbox(
            esquerda, width=40, font=("Segoe UI", 10), activestyle="none", bg="#232336", fg=COR_TEXTO,
            selectbackground="#3a3a5a", highlightthickness=0, borderwidth=0, exportselection=False,
        )  # fmt: skip
        self.lista.pack(fill="y", expand=True, pady=(6, 0))
        for s in self.shorts:
            marca = "✎ " if revisao.ler_editada(self.pasta, s["n"]) else "   "
            self.lista.insert("end", f"{marca}{s['arquivo']}")
        self.lista.bind("<<ListboxSelect>>", lambda e: self.abrir_short())

    def _montar_editor(self):
        direita = tk.Frame(self.jan, bg=COR_FUNDO)
        direita.pack(side="left", fill="both", expand=True, padx=14, pady=12)
        self.lbl_titulo = tk.Label(
            direita, text="", bg=COR_FUNDO, fg=COR_TEXTO, font=("Segoe UI", 12, "bold"), anchor="w", justify="left"
        )
        self.lbl_titulo.pack(fill="x")
        self.lbl_aviso = tk.Label(
            direita,
            text="",
            bg=COR_FUNDO,
            fg="#c8c8d8",
            font=("Segoe UI", 10),
            anchor="w",
            justify="left",
            wraplength=780,
        )
        self.lbl_aviso.pack(fill="x", pady=(2, 6))

        quadro = tk.Frame(direita, bg=COR_FUNDO)
        quadro.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(quadro, columns=("ini", "fim", "texto", "obs"), show="headings", selectmode="browse")
        for col, titulo, largura, lado in [("ini", "Início", 80, "center"), ("fim", "Fim", 80, "center"),
                                           ("texto", "Legenda", 520, "w"), ("obs", "Atenção", 150, "w")]:  # fmt: skip
            self.tree.heading(col, text=titulo)
            self.tree.column(col, width=largura, anchor=lado, stretch=(col == "texto"))
        barra = ttk.Scrollbar(quadro, command=self.tree.yview)
        self.tree.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.tag_configure("incerto", background="#fff3b0")
        self.tree.tag_configure("erro", foreground="#b00020")
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.mostrar_linha())
        self.tree.bind("<Double-1>", lambda e: self.ouvir())

        tk.Label(
            direita, bg=COR_FUNDO, fg="#9a9ab0", font=("Segoe UI", 9, "bold"), anchor="w",
            text="LINHA SELECIONADA  (edite aqui e aperte Enter)   amarelo = o Claude não teve certeza   "
            "sublinhado = possível erro de português   riscado = censurada",
        ).pack(fill="x", pady=(8, 2))  # fmt: skip
        self.caixa = tk.Text(
            direita, height=3, wrap="word", font=("Segoe UI", 13), bg="#0e0e16", fg=COR_TEXTO, insertbackground=COR_TEXTO,
            relief="flat", padx=8, pady=6, undo=False,
        )  # fmt: skip
        self.caixa.pack(fill="x")
        self.caixa.tag_configure("incerto", background=COR_INCERTO)
        self.caixa.tag_configure("erro", underline=True, underlinefg="#ff6b6b")
        self.caixa.tag_configure("censurada", overstrike=True, foreground="#9a9ab0")
        self.caixa.bind("<Return>", self.aplicar_linha)
        self.caixa.bind("<KeyRelease>", lambda e: self.pintar_caixa())

        linha1 = tk.Frame(direita, bg=COR_FUNDO)
        linha1.pack(fill="x", pady=(8, 0))
        for texto, comando in [("Aplicar linha (Enter)", self.aplicar_linha), ("Ouvir trecho", self.ouvir),
                               ("Censurar palavra", lambda: self.censurar_palavra(True)),
                               ("Tirar censura", lambda: self.censurar_palavra(False)),
                               ("Adicionar sempre à lista", self.adicionar_sempre)]:  # fmt: skip
            ttk.Button(linha1, text=texto, style="Extra.TButton", command=comando).pack(side="left", padx=(0, 6))
        tk.Checkbutton(
            direita, text="Censurar as palavras da lista (censura.txt) neste Short", variable=self.censurar_lista,
            command=self.mudou_censura_lista, bg=COR_FUNDO, fg=COR_TEXTO, selectcolor="#14141f",
            activebackground=COR_FUNDO, activeforeground=COR_TEXTO, font=("Segoe UI", 10), anchor="w",
        ).pack(fill="x", pady=(6, 0))  # fmt: skip

        linha2 = tk.Frame(direita, bg=COR_FUNDO)
        linha2.pack(fill="x", pady=(10, 0))
        ttk.Button(linha2, text="Salvar", style="Passo.TButton", command=self.salvar).pack(side="left")
        ttk.Button(linha2, text="Desfazer", style="Extra.TButton", command=self.desfazer).pack(side="left", padx=6)
        ttk.Button(linha2, text="Voltar ao original", style="Extra.TButton", command=self.voltar_ao_original).pack(
            side="left"
        )
        ttk.Button(
            linha2, text="Renderizar de novo só este Short", style="Passo.TButton", command=self.renderizar
        ).pack(side="right")
        ttk.Button(linha2, text="Assistir o Short", style="Extra.TButton", command=self.assistir).pack(
            side="right", padx=6
        )

    # ---------------------------------------------------------- abrir um Short
    def atual(self):
        sel = self.lista.curselection()
        return self.shorts[sel[0]] if sel else None

    def abrir_short(self):
        s = self.atual()
        if not s or s["n"] == self.n:
            return
        if self.mudou and not messagebox.askyesno(
            "Revisar legendas",
            "Você mudou a legenda e não salvou.\nTrocar de Short e perder as mudanças?",
            parent=self.jan,
        ):
            self.lista.selection_clear(0, "end")
            self.lista.selection_set(next(k for k, x in enumerate(self.shorts) if x["n"] == self.n))
            return
        self.n = s["n"]
        original = revisao.ler_original(self.pasta, self.n)
        editada = revisao.ler_editada(self.pasta, self.n)
        self.originais = original["palavras"] if original else []
        self.palavras = copy.deepcopy(editada["palavras"] if editada else self.originais)
        self.censurar_lista.set(bool(editada and editada.get("censurar_lista")))
        self.desfazer_pilha, self.mudou = [], False
        self.lbl_titulo.config(text=f"{s['arquivo']}   ({s.get('duracao', '?')} s)")
        self.mostrar()

    def recarregar_se_chegou_legenda(self, evento=None):
        """Short antigo sem legenda guardada: depois de renderizar de novo, a legenda aparece sozinha."""
        if self.n is not None and not self.palavras:
            original = revisao.ler_original(self.pasta, self.n)
            if original:
                self.originais = original["palavras"]
                self.palavras = copy.deepcopy(self.originais)
                self.mostrar()

    def mostrar(self, manter=None):
        """Redesenha a lista de linhas. 'manter' = numero da linha que continua selecionada."""
        self.tree.delete(*self.tree.get_children())
        self.caixa.delete("1.0", "end")
        if not self.palavras:
            self.linhas = []
            self.lbl_aviso.config(
                fg="#ffb347",
                text="Esse Short foi gerado numa versão antiga e não tem a legenda guardada.\n"
                'Clique em "Renderizar de novo só este Short" uma vez; depois dá para revisar.',
            )
            return
        self.linhas = revisao.dividir_em_linhas(self.palavras)
        da_lista = indices_da_lista(self.palavras, ler_censura()) if self.censurar_lista.get() else set()
        incertas = erros = 0
        for k, posicoes in enumerate(self.linhas):
            ws = [self.palavras[p] for p in posicoes]
            tem_incerta = any(w.get("inc") for w in ws)
            tem_erro = any(self.corretor.parece_errada(w["p"]) for w in ws)
            incertas += tem_incerta
            erros += tem_erro
            texto = " ".join(
                mascarar(w["p"]) if (w.get("cx") or p in da_lista) else w["p"] for p, w in zip(posicoes, ws)
            )
            obs = ", ".join(x for x, sim in [("incerto", tem_incerta), ("ortografia", tem_erro)] if sim)
            tags = ("incerto",) if tem_incerta else (("erro",) if tem_erro else ())
            self.tree.insert(
                "", "end", iid=str(k), tags=tags, values=(self._tempo(ws[0]["i"]), self._tempo(ws[-1]["f"]), texto, obs)
            )
        sem_corretor = "" if self.corretor.disponivel else "   (corretor ortográfico indisponível neste PC)"
        estado = "editada à mão" if revisao.ler_editada(self.pasta, self.n) else "original"
        self.lbl_aviso.config(
            fg="#c8c8d8",
            text=f"{len(self.linhas)} linhas  •  {incertas} com palavra incerta  •  {erros} com possível erro"
            f"  •  legenda {estado}{' (com mudanças não salvas)' if self.mudou else ''}{sem_corretor}",
        )
        if self.linhas:
            alvo = str(min(manter if manter is not None else 0, len(self.linhas) - 1))
            self.tree.selection_set(alvo)
            self.tree.see(alvo)
            self.mostrar_linha()  # enche a caixa na hora (sem esperar o aviso de selecao da lista)

    def _tempo(self, seg: float) -> str:
        return tempo_txt(seg, ms=True)[3:-2]  # MM:SS.d

    # ---------------------------------------------------------- linha selecionada
    def linha_atual(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def mostrar_linha(self):
        k = self.linha_atual()
        self.caixa.delete("1.0", "end")
        if k is None:
            return
        self.caixa.insert("1.0", revisao.texto_da_linha(self.palavras, self.linhas[k]))
        self.pintar_caixa()

    def pintar_caixa(self):
        """Pinta cada palavra da caixa: incerta (amarelo), possivel erro (sublinhado) e censurada (riscado)."""
        for tag in ("incerto", "erro", "censurada"):
            self.caixa.tag_remove(tag, "1.0", "end")
        k = self.linha_atual()
        if k is None:
            return
        texto = self.caixa.get("1.0", "end-1c")
        ws = [self.palavras[p] for p in self.linhas[k]]
        mesma_quantidade = len(texto.split()) == len(ws)
        pos = 0
        for j, token in enumerate(texto.split()):
            ini = texto.index(token, pos)
            pos = ini + len(token)
            a, b = f"1.0+{ini}c", f"1.0+{pos}c"
            if mesma_quantidade and ws[j].get("inc") and ws[j]["p"] == token:
                self.caixa.tag_add("incerto", a, b)
            if mesma_quantidade and ws[j].get("cx"):
                self.caixa.tag_add("censurada", a, b)
            if self.corretor.parece_errada(token):
                self.caixa.tag_add("erro", a, b)

    def palavra_sob_o_cursor(self):
        """Posicao (dentro da linha) da palavra onde esta o cursor da caixa, ou None."""
        texto = self.caixa.get("1.0", "end-1c")
        cursor = len(self.caixa.get("1.0", "insert"))
        pos = 0
        for j, token in enumerate(texto.split()):
            ini = texto.index(token, pos)
            pos = ini + len(token)
            if ini <= cursor <= pos:
                return j
        return None

    def guardar_para_desfazer(self):
        self.desfazer_pilha.append((copy.deepcopy(self.palavras), self.censurar_lista.get()))
        self.mudou = True

    def aplicar_linha(self, evento=None):
        k = self.linha_atual()
        if k is None:
            return "break"
        novo = " ".join(self.caixa.get("1.0", "end-1c").split())
        if not novo and evento is None:
            return "break"  # caixa vazia sem voce ter apertado Enter: nao apaga a linha
        if novo != revisao.texto_da_linha(self.palavras, self.linhas[k]):
            if not novo and len(self.linhas) == 1:
                messagebox.showinfo("Revisar legendas", "A legenda não pode ficar vazia.", parent=self.jan)
                return "break"
            self.guardar_para_desfazer()
            self.palavras = revisao.trocar_texto_da_linha(self.palavras, self.linhas[k], novo)
            self.mostrar(manter=k + 1 if evento is not None else k)
        elif evento is not None and k + 1 < len(self.linhas):
            self.tree.selection_set(str(k + 1))
            self.tree.see(str(k + 1))
        return "break"

    # ---------------------------------------------------------- censura
    def censurar_palavra(self, ligar: bool):
        k, j = self.linha_atual(), self.palavra_sob_o_cursor()
        if k is None or j is None or j >= len(self.linhas[k]):
            messagebox.showinfo(
                "Censura", "Clique em cima da palavra, na caixa da linha selecionada, e tente de novo.", parent=self.jan
            )
            return
        self.aplicar_linha()  # se o texto da caixa mudou, vale o texto novo
        if j >= len(self.linhas[k]):
            return
        w = self.palavras[self.linhas[k][j]]
        if bool(w.get("cx")) == ligar:
            return
        self.guardar_para_desfazer()
        if ligar:
            w["cx"] = True
        else:
            w.pop("cx", None)
        self.mostrar(manter=k)

    def adicionar_sempre(self):
        k, j = self.linha_atual(), self.palavra_sob_o_cursor()
        if k is None or j is None or j >= len(self.linhas[k]):
            messagebox.showinfo(
                "Censura", "Clique em cima da palavra, na caixa da linha, e tente de novo.", parent=self.jan
            )
            return
        palavra = self.palavras[self.linhas[k][j]]["p"]
        if not messagebox.askyesno(
            "Adicionar sempre à lista",
            f'Gravar "{palavra.strip(".,!?").lower()}" no censura.txt?\n\n'
            "Ela passa a ser censurada em todo Short em que a opção\n"
            '"Censurar as palavras da lista" estiver marcada.',
            parent=self.jan,
        ):
            return
        adicionar_a_lista(palavra)
        if not self.censurar_lista.get():
            self.guardar_para_desfazer()
            self.censurar_lista.set(True)
        self.mostrar(manter=k)

    def mudou_censura_lista(self):
        self.desfazer_pilha.append((copy.deepcopy(self.palavras), not self.censurar_lista.get()))
        self.mudou = True
        self.mostrar(manter=self.linha_atual())

    # ---------------------------------------------------------- ouvir e assistir
    def ouvir(self):
        """Corta do video original so o trecho da linha (com meio segundo de folga) e abre no player."""
        k = self.linha_atual()
        if k is None:
            return
        if not self.video.exists():
            messagebox.showinfo("Ouvir trecho", f"Não achei o vídeo original:\n{self.video}", parent=self.jan)
            return
        ws = [self.palavras[p] for p in self.linhas[k]]
        ini, fim = max(0.0, ws[0]["i"] - 0.5), ws[-1]["f"] + 0.5
        pasta = DADOS_APP / "temp"
        pasta.mkdir(parents=True, exist_ok=True)
        saida = pasta / f"trecho_{self.n:02d}_{k:03d}.mp4"
        comando = [achar_programa("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{ini:.3f}",
                   "-t", f"{fim - ini:.3f}", "-i", str(self.video), "-map", "0:v:0", "-map", "0:a:0", "-vf", "scale=-2:540",
                   "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26", "-c:a", "aac", str(saida)]  # fmt: skip
        r = subprocess.run(
            comando, capture_output=True, text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
        if r.returncode != 0 or not saida.exists():
            messagebox.showerror("Ouvir trecho", "Não consegui cortar o trecho:\n" + r.stderr[-300:], parent=self.jan)
            return
        abrir(saida)

    def assistir(self):
        s = self.atual()
        if s and (self.pasta / "prontos" / s["arquivo"]).exists():
            abrir(self.pasta / "prontos" / s["arquivo"])
        else:
            messagebox.showinfo(
                "Assistir", "Esse Short não está na pasta (foi limpo?). Renderize de novo.", parent=self.jan
            )

    # ---------------------------------------------------------- salvar, desfazer, renderizar
    def desfazer(self):
        if not self.desfazer_pilha:
            return
        self.palavras, lista = self.desfazer_pilha.pop()
        self.censurar_lista.set(lista)
        self.mudou = bool(self.desfazer_pilha)
        self.mostrar(manter=self.linha_atual())

    def voltar_ao_original(self):
        if not self.originais:
            return
        if not messagebox.askyesno(
            "Voltar ao original",
            "Descartar tudo o que foi editado neste Short e voltar à legenda original?",
            parent=self.jan,
        ):
            return
        revisao.apagar_editada(self.pasta, self.n)
        self.palavras = copy.deepcopy(self.originais)
        self.censurar_lista.set(False)
        self.desfazer_pilha, self.mudou = [], False
        self.marcar_na_lista()
        self.mostrar()

    def salvar(self) -> bool:
        if self.n is None or not self.palavras:
            return False
        self.aplicar_linha()
        revisao.salvar_editada(self.pasta, self.n, self.palavras, self.censurar_lista.get())
        self.desfazer_pilha, self.mudou = [], False
        self.marcar_na_lista()
        self.oferecer_correcoes()
        self.mostrar(manter=self.linha_atual())
        return True

    def oferecer_correcoes(self):
        """Palavras trocadas a mao viram sugestao para o correcoes.txt (so grava se voce disser SIM)."""
        pares = [p for p in revisao.sugestoes_de_correcao(self.originais, self.palavras) if "*" not in p[1]]
        ja_perguntadas = getattr(self, "_perguntadas", set())
        pares = [p for p in pares if p not in ja_perguntadas]
        if not pares:
            return
        self._perguntadas = ja_perguntadas | set(pares)
        lista = "\n".join(f"   {errada}  →  {certa}" for errada, certa in pares[:12])
        if messagebox.askyesno(
            "Correções automáticas",
            "Você corrigiu estas palavras à mão:\n\n" + lista + "\n\n"
            "Quer gravar no correcoes.txt, para o erro não se repetir nos próximos vídeos?",
            parent=self.jan,
        ):
            n = revisao.gravar_correcoes(pares)
            messagebox.showinfo(
                "Correções automáticas", f"{n} correção(ões) gravada(s) no correcoes.txt.", parent=self.jan
            )

    def marcar_na_lista(self):
        sel = self.lista.curselection()
        if not sel:
            return
        s = self.shorts[sel[0]]
        marca = "✎ " if revisao.ler_editada(self.pasta, s["n"]) else "   "
        self.lista.delete(sel[0])
        self.lista.insert(sel[0], f"{marca}{s['arquivo']}")
        self.lista.selection_set(sel[0])

    def renderizar(self):
        if self.n is None:
            return
        if self.palavras and self.mudou:
            self.salvar()
        rodar_script("shorts.gerar_shorts", self.pasta, "--so", self.n)
        messagebox.showinfo(
            "Renderizar de novo",
            "Abri a janela preta que monta o Short de novo, só este.\n"
            "A transcrição e os cortes do Claude não são refeitos.\n\n"
            'Quando ela terminar, clique em "Assistir o Short" para conferir.',
            parent=self.jan,
        )

    def fechar(self):
        if self.mudou and not messagebox.askyesno(
            "Revisar legendas", "Você mudou a legenda e não salvou.\nFechar e perder as mudanças?", parent=self.jan
        ):
            return
        self.jan.destroy()

# Painel "Audio e edicao" do editor de legendas: musica tema e efeitos sonoros de um Short.
# Tudo e modular: cada coisa pode ser ligada, trocada ou excluida sem refazer a transcricao nem chamar o Claude.
# As mudancas vao para edicao_shorts\NN_edicao.json (a sugestao do Claude fica guardada a parte).
import copy
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from interface import tema
from interface.utilidades import COR_DESTAQUE, COR_FUNDO, COR_TEXTO
from nucleo.comum import DADOS_APP, config_compartilhada, tempo_txt
from nucleo.video import achar_programa
from shorts import audio_short, biblioteca
from shorts.cortes import CLIMAS, clima_do
from shorts.montagem import volumes_musica


def escolher_da_lista(pai, titulo: str, opcoes: list, atual: str = ""):
    """Janelinha com uma lista para escolher um arquivo. Devolve o escolhido ou None."""
    if not opcoes:
        messagebox.showinfo(titulo, "Não há nenhum arquivo na pasta. Coloque os arquivos e tente de novo.", parent=pai)
        return None
    jan = tk.Toplevel(pai)
    jan.title(titulo)
    jan.geometry("460x380")
    jan.configure(bg=COR_FUNDO)
    lista = tk.Listbox(jan, font=("Segoe UI", 10), bg=tema.PAINEL, fg=COR_TEXTO, selectbackground=tema.LARANJA_ESCURO,
                       highlightthickness=0, exportselection=False)  # fmt: skip
    lista.pack(fill="both", expand=True, padx=10, pady=10)
    for k, o in enumerate(opcoes):
        lista.insert("end", o)
        if o == atual:
            lista.selection_set(k)
            lista.see(k)
    resposta = {}

    def ok(evento=None):
        sel = lista.curselection()
        if sel:
            resposta["v"] = opcoes[sel[0]]
        jan.destroy()

    lista.bind("<Double-1>", ok)
    ttk.Button(jan, text="Escolher", style="Passo.TButton", command=ok).pack(pady=(0, 10))
    jan.transient(pai)
    jan.grab_set()
    pai.wait_window(jan)
    return resposta.get("v")


class PainelAudio:
    def __init__(self, pai, editor):
        self.editor = editor
        self.cfg = config_compartilhada()
        q = tk.Frame(pai, bg=COR_FUNDO)
        q.pack(fill="both", expand=True, padx=8, pady=8)
        self.musica_ligada = tk.BooleanVar(value=True)
        self.efeitos_ligados = tk.BooleanVar(value=True)
        chaves = tk.Frame(q, bg=COR_FUNDO)
        chaves.pack(fill="x")
        for texto, var, chave in (("Música ligada", self.musica_ligada, "musica"),
                                  ("Efeitos ligados", self.efeitos_ligados, "efeitos")):  # fmt: skip
            tk.Checkbutton(chaves, text=texto, variable=var, command=lambda c=chave: self.ligar(c), bg=COR_FUNDO,
                           fg=COR_TEXTO, selectcolor=tema.CAMPO, activebackground=COR_FUNDO, activeforeground=COR_TEXTO,
                           font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 18))  # fmt: skip
        ttk.Button(chaves, text="Restaurar sugestão do Claude", style="Extra.TButton",
                   command=self.restaurar).pack(side="right")  # fmt: skip

        # ---- musica tema
        tk.Label(q, text="MÚSICA TEMA", bg=COR_FUNDO, fg=COR_DESTAQUE, font=("Segoe UI", 9, "bold"), anchor="w").pack(
            fill="x", pady=(10, 2)
        )
        self.lbl_musica = tk.Label(q, text="", bg=COR_FUNDO, fg=COR_TEXTO, font=("Segoe UI", 10), anchor="w",
                                   justify="left")  # fmt: skip
        self.lbl_musica.pack(fill="x")
        linha = tk.Frame(q, bg=COR_FUNDO)
        linha.pack(fill="x", pady=(4, 0))
        for texto, comando in (("▶ Ouvir", self.ouvir_musica), ("🔄 Trocar...", self.trocar_musica),
                               ("🎲 Sortear outra do clima", self.sortear_musica),
                               ("🗑 Excluir (sem música)", self.excluir_musica)):  # fmt: skip
            ttk.Button(linha, text=texto, style="Extra.TButton", command=comando).pack(side="left", padx=(0, 6))
        linha_vol = tk.Frame(q, bg=COR_FUNDO)
        linha_vol.pack(fill="x", pady=(4, 0))
        tk.Label(linha_vol, text="🔊 Volume da música (%):", bg=COR_FUNDO, fg=COR_TEXTO).pack(side="left", padx=(0, 6))
        self.volume = tk.Scale(linha_vol, from_=0, to=100, orient="horizontal", length=260, bg=COR_FUNDO, fg=COR_TEXTO,
                               highlightthickness=0, troughcolor=tema.PAINEL, showvalue=True)  # fmt: skip
        self.volume.pack(side="left")
        self.volume.bind("<ButtonRelease-1>", lambda e: self.mudou_volume())
        self.lbl_trocas = tk.Label(q, text="", bg=COR_FUNDO, fg=tema.TEXTO_2, font=("Segoe UI", 9), anchor="w")
        self.lbl_trocas.pack(fill="x", pady=(2, 0))
        ttk.Button(q, text="🗑 Tirar a troca de música", style="Extra.TButton", command=self.tirar_troca).pack(
            anchor="w", pady=(2, 0)
        )

        # ---- efeitos
        tk.Label(q, text="EFEITOS SONOROS", bg=COR_FUNDO, fg=COR_DESTAQUE, font=("Segoe UI", 9, "bold"),
                 anchor="w").pack(fill="x", pady=(12, 2))  # fmt: skip
        quadro = tk.Frame(q, bg=COR_FUNDO)
        quadro.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(quadro, columns=("tempo", "cat", "arq", "vol", "motivo"), show="headings",
                                 selectmode="browse", height=4)  # fmt: skip
        for col, titulo, largura in (("tempo", "Tempo", 70), ("cat", "Categoria", 90), ("arq", "Arquivo", 190),
                                     ("vol", "Volume", 60), ("motivo", "Motivo do Claude", 300)):  # fmt: skip
            self.tree.heading(col, text=titulo)
            self.tree.column(col, width=largura, anchor="w", stretch=(col == "motivo"))
        self.tree.tag_configure("fala", foreground=tema.VERMELHO)
        self.tree.pack(fill="both", expand=True)
        self.lbl_aviso_efeito = tk.Label(q, text="", bg=COR_FUNDO, fg=tema.AMARELO, font=("Segoe UI", 9), anchor="w")
        self.lbl_aviso_efeito.pack(fill="x")
        linhas = [(("▶ Efeito sozinho", self.ouvir_efeito), ("▶ Trecho com o efeito", self.ouvir_trecho),
                   ("+ Adicionar efeito (no tempo da linha da legenda)", self.adicionar_efeito)),
                  (("✏ Tempo", self.mudar_tempo), ("🔄 Trocar arquivo", self.trocar_efeito),
                   ("🔊 Volume", self.volume_efeito), ("🗑 Excluir", self.excluir_efeito))]  # fmt: skip
        for botoes_da_linha in linhas:
            botoes = tk.Frame(q, bg=COR_FUNDO)
            botoes.pack(fill="x", pady=(4, 0))
            for texto, comando in botoes_da_linha:
                ttk.Button(botoes, text=texto, style="Extra.TButton", command=comando).pack(side="left", padx=(0, 5))

    # ---------------------------------------------------------- desenhar
    @property
    def ed(self) -> dict:
        return self.editor.edicao

    def corte(self) -> dict:
        return self.ed.get("corte") or {}

    def clima(self) -> str:
        return clima_do(self.editor.corte_do(self.editor.n or 0)) if self.editor.n else ""

    def mostrar(self):
        ed = self.ed
        mus = ed["musica"]
        self.musica_ligada.set(bool(mus.get("ligada", True)))
        self.efeitos_ligados.set(bool(ed.get("efeitos_ligados", True)))
        clima = self.clima() or "sem clima (usa geral)"
        if mus.get("arquivo"):
            existe = biblioteca.caminho("musica", mus["arquivo"]) is not None
            texto = f"{mus['arquivo']}   •   clima do corte: {clima}" + (
                "" if existe else "   ⚠ arquivo sumiu da pasta"
            )
        else:
            texto = f"Sem música   •   clima do corte: {clima}"
        self.lbl_musica.config(text=texto + ("" if mus.get("ligada", True) else "   (música DESLIGADA)"))
        vb, _ = volumes_musica(mus.get("volume"))
        self.volume.set(int(round(vb * 100)))
        trocas = ed.get("trocas_musica") or []
        self.lbl_trocas.config(
            text="  ".join(f"Troca de música em {t['tempo']:.1f}s → {t['arquivo']}" for t in trocas)
            or "Sem troca de música no meio do Short."
        )
        self.tree.delete(*self.tree.get_children())
        padrao = float(self.cfg.get("volume_efeitos", 0.8))
        em_cima = []
        for k, e in enumerate(ed.get("efeitos") or []):
            fala = self.cai_em_fala(float(e["tempo"]))
            if fala:
                em_cima.append(f"{float(e['tempo']):.1f}s")
            vol = padrao if e.get("volume") is None else float(e["volume"])
            existe = biblioteca.caminho("efeito", e.get("arquivo", "")) is not None
            self.tree.insert("", "end", iid=str(k), tags=("fala",) if fala else (), values=(
                f"{float(e['tempo']):.1f}s", e.get("categoria", ""), (e.get("arquivo") or "-") + ("" if existe else " ⚠"),
                f"{vol * 100:.0f}%", e.get("motivo", "")))  # fmt: skip
        avisos = []
        if em_cima:
            avisos.append("⚠ efeito em cima de uma fala (" + ", ".join(em_cima) + "): pode cobrir a voz")
        limite = audio_short.maximo_de_efeitos()
        if len(ed.get("efeitos") or []) > limite:
            avisos.append(f"⚠ mais de {limite} efeitos: cuidado com a cara de edição frenética")
        if not ed.get("efeitos_ligados", True):
            avisos.append("(efeitos DESLIGADOS neste Short)")
        self.lbl_aviso_efeito.config(text="   ".join(avisos))

    def cai_em_fala(self, t: float, dur: float = 0.6) -> bool:
        """O efeito (t no tempo do Short) cai em cima de alguma palavra falada?"""
        corte = self.corte()
        for w in self.editor.palavras:
            a, b = audio_short.short_do_video(corte, w["i"]), audio_short.short_do_video(corte, w["f"])
            if a < t + dur and b > t:
                return True
        return False

    # ---------------------------------------------------------- musica
    def ligar(self, qual: str):
        valor = (self.musica_ligada if qual == "musica" else self.efeitos_ligados).get()

        def aplicar():
            if qual == "musica":
                self.ed["musica"]["ligada"] = valor
            else:
                self.ed["efeitos_ligados"] = valor

        self.editor.mudar(aplicar)

    def ouvir_musica(self):
        arq = biblioteca.caminho("musica", self.ed["musica"].get("arquivo", ""))
        if arq:
            self.editor.abrir_arquivo(arq)
        else:
            messagebox.showinfo(
                "Música", "Este Short está sem música (ou o arquivo sumiu da pasta).", parent=self.editor.jan
            )

    def _por_musica(self, rel: str):
        def aplicar():
            self.ed["musica"]["arquivo"] = rel
            self.ed["musica"]["ligada"] = True

        self.editor.mudar(aplicar)

    def trocar_musica(self):
        todas = biblioteca.listar("musica")
        ordem = [c for c in (self.clima(), *CLIMAS, biblioteca.GERAL) if c]
        opcoes = []
        for cat in dict.fromkeys(ordem + sorted(todas)):
            opcoes += list((todas.get(cat) or {}).keys())
        rel = escolher_da_lista(self.editor.jan, "Trocar a música", opcoes, self.ed["musica"].get("arquivo", ""))
        if rel:
            self._por_musica(rel)

    def sortear_musica(self):
        opcoes = biblioteca.opcoes_de_musica(self.clima())
        atual = self.ed["musica"].get("arquivo", "")
        if not [o for o in opcoes if o != atual]:
            messagebox.showinfo(
                "Sortear", "Não há outra música para esse clima (nem em geral).", parent=self.editor.jan
            )
            return
        import random

        self._por_musica(random.choice([o for o in opcoes if o != atual]))

    def excluir_musica(self):
        def aplicar():
            self.ed["musica"]["arquivo"] = ""
            self.ed["trocas_musica"] = []

        self.editor.mudar(aplicar)

    def mudou_volume(self):
        v = self.volume.get() / 100
        if abs(v - volumes_musica(self.ed["musica"].get("volume"))[0]) > 0.005:
            self.editor.mudar(lambda: self.ed["musica"].update(volume=round(v, 3)))

    def tirar_troca(self):
        if self.ed.get("trocas_musica"):
            self.editor.mudar(lambda: self.ed.update(trocas_musica=[]))

    def restaurar(self):
        sug = copy.deepcopy(self.editor.sugestao_do_short())

        def aplicar():
            self.editor.edicao = sug

        self.editor.mudar(aplicar)

    # ---------------------------------------------------------- efeitos
    def efeito_atual(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Efeitos sonoros", "Escolha um efeito na lista primeiro.", parent=self.editor.jan)
            return None
        return int(sel[0])

    def _arquivo_do_efeito(self, k: int):
        e = self.ed["efeitos"][k]
        arq = biblioteca.caminho("efeito", e.get("arquivo", ""))
        if not arq:
            messagebox.showinfo("Efeitos sonoros", "O arquivo desse efeito não está na pasta.", parent=self.editor.jan)
        return arq

    def ouvir_efeito(self):
        k = self.efeito_atual()
        arq = self._arquivo_do_efeito(k) if k is not None else None
        if arq:
            self.editor.abrir_arquivo(arq)

    def ouvir_trecho(self):
        k = self.efeito_atual()
        arq = self._arquivo_do_efeito(k) if k is not None else None
        if not arq:
            return
        e = self.ed["efeitos"][k]
        vol = float(self.cfg.get("volume_efeitos", 0.8)) if e.get("volume") is None else float(e["volume"])
        pasta = DADOS_APP / "temp"
        pasta.mkdir(parents=True, exist_ok=True)
        saida = pasta / f"previa_{self.editor.n:02d}_efeito{k}.m4a"
        cmd = audio_short.comando_previa(achar_programa("ffmpeg"), self.editor.video, self.ed, float(e["tempo"]),
                                         {"arquivo": arq, "volume": vol}, saida=saida)  # fmt: skip
        self.editor.rodar_e_abrir(cmd, saida, "Ouvir trecho com o efeito")

    def _pedir_numero(self, titulo: str, texto: str, atual: float):
        r = simpledialog.askstring(titulo, texto, initialvalue=f"{atual:g}", parent=self.editor.jan)
        if r is None:
            return None
        try:
            return float(r.replace(",", ".").replace("%", "").strip())
        except ValueError:
            messagebox.showinfo(titulo, f'"{r}" não é um número.', parent=self.editor.jan)
            return None

    def mudar_tempo(self):
        k = self.efeito_atual()
        if k is None:
            return
        total = float(self.corte().get("total") or 600)
        t = self._pedir_numero(
            "Tempo do efeito", f"Em que segundo do Short (0 a {total:.1f})?", self.ed["efeitos"][k]["tempo"]
        )
        if t is None:
            return
        if not 0 <= t < total:
            messagebox.showinfo("Tempo do efeito", f"Use um tempo entre 0 e {total:.1f} s.", parent=self.editor.jan)
            return

        def aplicar():
            self.ed["efeitos"][k]["tempo"] = round(t, 2)
            self.ed["efeitos"].sort(key=lambda e: float(e["tempo"]))

        self.editor.mudar(aplicar)

    def trocar_efeito(self):
        k = self.efeito_atual()
        if k is None:
            return
        todas = biblioteca.listar("efeito")
        cat = self.ed["efeitos"][k].get("categoria", "")
        opcoes = list((todas.get(cat) or {}).keys()) + [o for c in sorted(todas) if c != cat for o in todas[c]]
        rel = escolher_da_lista(self.editor.jan, "Trocar o efeito", opcoes, self.ed["efeitos"][k].get("arquivo", ""))
        if rel:
            self.editor.mudar(lambda: self.ed["efeitos"][k].update(arquivo=rel, categoria=rel.split("/", 1)[0]))

    def volume_efeito(self):
        k = self.efeito_atual()
        if k is None:
            return
        e = self.ed["efeitos"][k]
        atual = float(self.cfg.get("volume_efeitos", 0.8)) if e.get("volume") is None else float(e["volume"])
        v = self._pedir_numero("Volume do efeito", "Volume em % (0 a 150; 80 = padrão):", round(atual * 100))
        if v is not None:
            self.editor.mudar(lambda: e.update(volume=round(max(0.0, min(150.0, v)) / 100, 3)))

    def excluir_efeito(self):
        k = self.efeito_atual()
        if k is not None:
            self.editor.mudar(lambda: self.ed["efeitos"].pop(k))

    def adicionar_efeito(self):
        """Novo efeito no tempo da linha selecionada na aba Legenda (ou no comeco do Short)."""
        todas = biblioteca.listar("efeito")
        opcoes = [o for c in sorted(todas) for o in todas[c]]
        rel = escolher_da_lista(self.editor.jan, "Adicionar efeito", opcoes)
        if not rel:
            return
        k = self.editor.linha_atual()
        t = 0.0
        if k is not None and self.editor.linhas:
            t = max(0.0, audio_short.short_do_video(self.corte(), self.editor.palavras[self.editor.linhas[k][0]]["i"]))
        novo = {"tempo": round(t, 2), "categoria": rel.split("/", 1)[0], "arquivo": rel, "volume": None,
                "motivo": f"adicionado à mão em {tempo_txt(t)}"}  # fmt: skip

        def aplicar():
            self.ed["efeitos"].append(novo)
            self.ed["efeitos"].sort(key=lambda e: float(e["tempo"]))

        self.editor.mudar(aplicar)

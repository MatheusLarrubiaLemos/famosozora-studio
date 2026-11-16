# Editor de legendas: revisar cada Short antes de postar.
# Aba "Legenda": a legenda em linhas (inicio, fim, quem fala, texto), destaca em amarelo o que o Claude marcou
# como incerto, sublinha possiveis erros de portugues, deixa censurar palavras e trocar quem fala na linha.
# Aba "Falantes": liga cada voz detectada a uma pessoa do cadastro (nome e cor).
# Aba "Audio e edicao": musica tema e efeitos sonoros do Short (ligar, trocar, volume, excluir, ouvir).
# Embaixo: Salvar, Desfazer (vale para tudo) e renderizar de novo so aquele Short.
import copy
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from interface.janela_pessoas import nova_pessoa
from interface.painel_audio import PainelAudio
from interface.painel_falantes import NOVA, PainelFalantes
from interface.utilidades import COR_DESTAQUE, COR_FUNDO, COR_TEXTO, abrir, rodar_script
from nucleo.comum import DADOS_APP, ler_json, tempo_txt
from nucleo.ortografia import Corretor
from nucleo.video import achar_programa
from shorts import edicao as edicao_short
from shorts import pessoas, revisao
from shorts.censura import adicionar_a_lista, indices_da_lista, ler_censura, mascarar
from shorts.cortes import clima_do, ler_cortes, nota_do

COR_INCERTO = "#6b5a00"  # fundo amarelo escuro: palavra que o Claude marcou como [[incerta]]
AUTOMATICO = "(voz detectada)"


class EditorLegendas:
    def __init__(self, studio, info: dict):
        self.studio = studio
        self.pasta = info["pasta"]
        self.video = Path((ler_json(self.pasta / "projeto.json", {}) or {}).get("video", ""))
        self.shorts = (ler_json(self.pasta / "prontos" / "publicacao.json", {}) or {}).get("shorts", [])
        dados = ler_cortes(self.pasta, gravar_migracao=False) or {"cortes": []}
        self.cortes = dados["cortes"] if isinstance(dados["cortes"], list) else []
        self.shorts.sort(key=lambda s: (-nota_do(self.corte_do(s["n"])), s["n"]))  # os mais fortes primeiro
        self.corretor = Corretor()
        self.n = None  # numero do Short aberto
        self.palavras = []  # legenda em edicao
        self.originais = []  # legenda como saiu da geracao
        self.linhas = []  # posicoes das palavras de cada linha
        self.ligacoes = {}  # voz detectada -> pessoa (so deste Short)
        self.edicao = edicao_short.vazia()  # musica, efeitos e nome de quem fala deste Short
        self.trecho = (None, None)  # inicio e fim do corte no video original
        self.quem = pessoas.QuemFala()
        self.desfazer_pilha = []
        self.mudou = False

        self.jan = tk.Toplevel(studio.raiz)
        self.jan.title(f"Revisar legendas - {info['nome']}")
        self.jan.geometry("1180x780")
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
            self.lista.insert("end", self.rotulo_na_lista(s))
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

        self.abas = ttk.Notebook(direita)
        self.abas.pack(fill="both", expand=True)
        aba_legenda = tk.Frame(self.abas, bg=COR_FUNDO)
        aba_falantes = tk.Frame(self.abas, bg=COR_FUNDO)
        aba_audio = tk.Frame(self.abas, bg=COR_FUNDO)
        self.abas.add(aba_legenda, text="  Legenda  ")
        self.abas.add(aba_falantes, text="  Falantes  ")
        self.abas.add(aba_audio, text="  Áudio e edição  ")
        self._montar_aba_legenda(aba_legenda)
        self.painel_falantes = PainelFalantes(aba_falantes, self)
        self.painel_audio = PainelAudio(aba_audio, self)
        self._montar_botoes_de_baixo(direita)

    def _montar_aba_legenda(self, direita):
        quadro = tk.Frame(direita, bg=COR_FUNDO)
        quadro.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(
            quadro, columns=("ini", "fim", "quem", "texto", "obs"), show="headings", selectmode="browse"
        )
        for col, titulo, largura, lado in [("ini", "Início", 80, "center"), ("fim", "Fim", 80, "center"),
                                           ("quem", "Quem fala", 110, "w"), ("texto", "Legenda", 440, "w"),
                                           ("obs", "Atenção", 130, "w")]:  # fmt: skip
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

        quem = tk.Frame(direita, bg=COR_FUNDO)
        quem.pack(fill="x", pady=(6, 0))
        tk.Label(quem, text="Quem fala nesta linha:", bg=COR_FUNDO, fg=COR_TEXTO, font=("Segoe UI", 10)).pack(
            side="left"
        )
        self.cb_quem = ttk.Combobox(quem, state="readonly", width=22)
        self.cb_quem.pack(side="left", padx=6)
        self.cb_quem.bind("<<ComboboxSelected>>", lambda e: self.trocar_quem_da_linha(self.cb_quem.get()))
        self.lbl_contraste = tk.Label(quem, text="", bg=COR_FUNDO, fg="#ffb347", font=("Segoe UI", 9))
        self.lbl_contraste.pack(side="left", padx=6)

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

    def _montar_botoes_de_baixo(self, direita):
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
    def corte_do(self, n: int) -> dict:
        """O corte do Claude (cortes.json) que virou o Short n."""
        return self.cortes[n - 1] if 0 < n <= len(self.cortes) and isinstance(self.cortes[n - 1], dict) else {}

    def rotulo_na_lista(self, s: dict) -> str:
        marca = "✎ " if self.foi_editado(s["n"]) else "   "
        c = self.corte_do(s["n"])
        nota = f"[{nota_do(c):.0f}] " if "nota" in c else ""
        return f"{marca}{nota}{s['arquivo']}"

    def atual(self):
        sel = self.lista.curselection()
        return self.shorts[sel[0]] if sel else None

    def abrir_short(self):
        s = self.atual()
        if not s or s["n"] == self.n:
            return
        if self.mudou and not messagebox.askyesno(
            "Revisar legendas",
            "Você mudou este Short e não salvou.\nTrocar de Short e perder as mudanças?",
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
        self.trecho = (original.get("inicio"), original.get("fim")) if original else (None, None)
        self.ligacoes = pessoas.ler_ligacoes(self.pasta, self.n)
        self.edicao = self.ler_edicao_do_short()
        self.desfazer_pilha, self.mudou = [], False
        c = self.corte_do(self.n)
        detalhes = [f"nota {nota_do(c):.0f}/10" if "nota" in c else "", f"clima: {clima_do(c)}" if clima_do(c) else "",
                    f"por que prende: {c['motivo']}" if c.get("motivo") else ""]  # fmt: skip
        detalhes = "   •   ".join(x for x in detalhes if x)
        self.lbl_titulo.config(
            text=f"{s['arquivo']}   ({s.get('duracao', '?')} s)" + (f"\n{detalhes}" if detalhes else "")
        )
        self.redesenhar(manter=0)

    def sugestao_do_short(self) -> dict:
        """O que saiu da geracao (sugestao do Claude). Short sem sugestao guardada: tudo no padrao."""
        ini, fim = self.trecho
        sug = edicao_short.ler_sugestao(self.pasta, self.n)
        if sug is not None and (ini is None or edicao_short.mesmo_corte(sug, ini, fim)):
            return sug
        from shorts.gerar_shorts import sugestao_sem_render  # Short gerado antes da 1.4.0: monta a sugestao agora

        sug = sugestao_sem_render(self.pasta, self.n)
        if sug is not None and (ini is None or edicao_short.mesmo_corte(sug, ini, fim)):
            return sug
        return edicao_short.vazia(ini, fim)

    def ler_edicao_do_short(self) -> dict:
        ini, fim = self.trecho
        ed = edicao_short.ler_edicao(self.pasta, self.n)
        if ed is not None and (ini is None or edicao_short.mesmo_corte(ed, ini, fim)):
            return ed
        return copy.deepcopy(self.sugestao_do_short())

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
        self.quem = pessoas.QuemFala(self.ligacoes)
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
            valores = (self._tempo(ws[0]["i"]), self._tempo(ws[-1]["f"]), self.quem.pessoa(ws[0])["nome"], texto, obs)
            self.tree.insert("", "end", iid=str(k), tags=tags, values=valores)
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
            self.cb_quem.set("")
            return
        self.caixa.insert("1.0", revisao.texto_da_linha(self.palavras, self.linhas[k]))
        self.pintar_caixa()
        self.mostrar_quem_da_linha(k)

    # ---------------------------------------------------------- quem fala na linha
    def mostrar_quem_da_linha(self, k: int):
        """Lista de pessoas da linha e a cor da pessoa na caixa (previa da cor da legenda)."""
        w = self.palavras[self.linhas[k][0]]
        cadastro = pessoas.ler_pessoas()
        self.quem = pessoas.QuemFala(self.ligacoes, cadastro)
        opcoes = ([AUTOMATICO] if "s" in w else []) + [p["nome"] for p in cadastro] + [NOVA]
        self.cb_quem.configure(values=opcoes)
        pessoa = self.quem.pessoa(w)
        self.cb_quem.set(pessoa["nome"] if w.get("pessoa") or "s" not in w else AUTOMATICO)
        self.caixa.configure(fg=pessoa["cor"])
        self.lbl_contraste.config(
            text=f"cor de {pessoa['nome']}"
            + ("  ⚠ escura: difícil de ler" if pessoas.dificil_de_ler(pessoa["cor"]) else "")
        )

    def trocar_quem_da_linha(self, escolha: str):
        """Corrige o detector: grava a pessoa em cada palavra da linha (fica firme mesmo editando o texto)."""
        k = self.linha_atual()
        if k is None:
            return
        if escolha == NOVA:
            p = nova_pessoa(self.jan)
            if not p:
                self.mostrar_quem_da_linha(k)
                return
            escolha = p["nome"]
        self.aplicar_linha()
        posicoes = self.linhas[k]

        def aplicar():
            for pos in posicoes:
                w = self.palavras[pos]
                if escolha == AUTOMATICO:
                    w.pop("pessoa", None)
                else:
                    w["pessoa"] = escolha

        self.mudar(aplicar, manter=k)

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

    def estado(self, censurar=None) -> dict:
        """Foto de tudo o que da para mudar neste Short (para o Desfazer)."""
        return copy.deepcopy({
            "palavras": self.palavras, "censurar": self.censurar_lista.get() if censurar is None else censurar,
            "ligacoes": self.ligacoes, "edicao": self.edicao,
        })  # fmt: skip

    def guardar_para_desfazer(self, censurar=None):
        self.desfazer_pilha.append(self.estado(censurar))
        self.mudou = True

    def mudar(self, aplicar, manter=None):
        """Guarda a foto para o Desfazer, faz a mudanca e redesenha tudo."""
        self.guardar_para_desfazer()
        aplicar()
        self.redesenhar(manter)

    def redesenhar(self, manter=None):
        self.mostrar(manter=self.linha_atual() if manter is None else manter)
        self.painel_falantes.mostrar()
        self.painel_audio.mostrar()

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
        self.guardar_para_desfazer(censurar=not self.censurar_lista.get())
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
        self.tocar_trecho(max(0.0, ws[0]["i"] - 0.5), ws[-1]["f"] + 0.5, f"{k:03d}")

    def tocar_trecho(self, ini: float, fim: float, nome: str):
        """Corta o trecho do video original (ini e fim em segundos) e abre no player."""
        if not self.video.exists():
            messagebox.showinfo("Ouvir trecho", f"Não achei o vídeo original:\n{self.video}", parent=self.jan)
            return
        pasta = DADOS_APP / "temp"
        pasta.mkdir(parents=True, exist_ok=True)
        saida = pasta / f"trecho_{self.n:02d}_{nome}.mp4"
        comando = [achar_programa("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{ini:.3f}",
                   "-t", f"{fim - ini:.3f}", "-i", str(self.video), "-map", "0:v:0", "-map", "0:a:0", "-vf", "scale=-2:540",
                   "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26", "-c:a", "aac", str(saida)]  # fmt: skip
        self.rodar_e_abrir(comando, saida, "Ouvir trecho")

    def rodar_e_abrir(self, comando: list, saida: Path, titulo: str):
        """Roda o ffmpeg (corte ou previa de audio) e abre o resultado no player."""
        if not self.video.exists():
            messagebox.showinfo(titulo, f"Não achei o vídeo original:\n{self.video}", parent=self.jan)
            return
        r = subprocess.run(
            comando, capture_output=True, text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
        if r.returncode != 0 or not Path(saida).exists():
            messagebox.showerror(titulo, "Não consegui montar o trecho:\n" + (r.stderr or "")[-300:], parent=self.jan)
            return
        abrir(saida)

    def abrir_arquivo(self, arquivo: Path):
        abrir(arquivo)

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
        foto = self.desfazer_pilha.pop()
        self.palavras, self.ligacoes, self.edicao = foto["palavras"], foto["ligacoes"], foto["edicao"]
        self.censurar_lista.set(foto["censurar"])
        self.mudou = bool(self.desfazer_pilha)
        self.redesenhar()

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
        self.redesenhar()

    def salvar(self) -> bool:
        if self.n is None:
            return False
        if self.palavras:
            self.aplicar_linha()
            if self.palavras == self.originais and not self.censurar_lista.get():
                revisao.apagar_editada(self.pasta, self.n)  # igual ao original: nada para guardar
            else:
                revisao.salvar_editada(self.pasta, self.n, self.palavras, self.censurar_lista.get())
        pessoas.salvar_ligacoes(self.pasta, self.n, self.ligacoes)
        if edicao_short.normalizar(self.edicao) == edicao_short.normalizar(self.sugestao_do_short()):
            edicao_short.restaurar_sugestao(self.pasta, self.n)  # igual a sugestao do Claude
        else:
            edicao_short.salvar_edicao(self.pasta, self.n, self.edicao)
        self.desfazer_pilha, self.mudou = [], False
        self.marcar_na_lista()
        self.oferecer_correcoes()
        self.redesenhar()
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
        self.lista.delete(sel[0])
        self.lista.insert(sel[0], self.rotulo_na_lista(s))
        self.lista.selection_set(sel[0])

    def foi_editado(self, n: int) -> bool:
        return bool(revisao.ler_editada(self.pasta, n) or edicao_short.ler_edicao(self.pasta, n))

    def renderizar(self):
        if self.n is None:
            return
        if self.mudou:
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
            "Revisar legendas", "Você mudou este Short e não salvou.\nFechar e perder as mudanças?", parent=self.jan
        ):
            return
        self.jan.destroy()

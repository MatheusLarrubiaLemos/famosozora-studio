# Editor de legendas: revisar cada Short antes de postar.
# Aba "Legenda": a legenda em linhas (inicio, fim, quem fala, texto), destaca em amarelo o que o Claude marcou
# como incerto e sublinha possiveis erros de portugues. Duplo clique edita o texto ou o tempo ali mesmo
# (Enter salva, Esc cancela); o botao direito abre o menu da linha (ouvir, editar, trocar quem fala, censurar,
# inserir e excluir linha). Atalhos: Ctrl+S salvar, Ctrl+Z desfazer, Espaco tocar/parar, Delete, F2.
# Na lista de Shorts (esquerda), a tecla Delete exclui o Short selecionado.
# Aba "Falantes": liga cada voz detectada a uma pessoa do cadastro (nome e cor).
# Aba "Audio e edicao": musica tema e efeitos sonoros do Short (botao direito: ouvir, trocar, volume, excluir).
# Lista de Shorts (esquerda), botao direito: abrir, renderizar de novo, publicar, abrir pasta, excluir.
# Embaixo ficam so os botoes principais: Salvar, Renderizar e Publicar.
# A esquerda, embaixo da lista de Shorts, o player embutido (interface/player.py): "Original" mostra o trecho
# do corte no video da live (com 10 s de folga antes e depois), a lista de linhas acompanha o video e a legenda da
# hora aparece embaixo dele; "[ Corte começa aqui" / "Corte acaba aqui ]" mudam o corte no cortes.json e
# renderizam so este Short. "Short pronto" toca o Short ja renderizado. Sem o player (falta o mpv), tudo volta a
# abrir no player do Windows.
import copy
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from interface import tema
from interface.janela_pessoas import nova_pessoa
from interface.menus import abrir_menu, ligar_botao_direito, montar_menu
from interface.notificacao import notificar
from interface.painel_audio import PainelAudio
from interface.painel_falantes import NOVA, PainelFalantes
from interface.player import Player
from interface.utilidades import COR_FUNDO, COR_TEXTO, abrir, em_segundo_plano, mostrar_na_pasta, rodar_script
from nucleo import reproducao, tocador
from nucleo.comum import DADOS_APP, gravar_json, ler_ajustes, ler_json, ler_tempo, salvar_ajustes, tempo_txt
from nucleo.ortografia import Corretor
from nucleo.video import achar_programa
from shorts import edicao as edicao_short
from shorts import pessoas, revisao
from shorts.censura import adicionar_a_lista, indices_da_lista, ler_censura, mascarar
from shorts.cortes import clima_do, ler_cortes, nota_do

COR_INCERTO = tema.INCERTO  # fundo amarelo escuro: palavra que o Claude marcou como [[incerta]]
AUTOMATICO = "(voz detectada)"
VEZES_DA_DICA = 5  # a dica do rodape aparece nas primeiras vezes que o editor abre
FOLGA_PLAYER = 10.0  # segundos do video original mostrados antes e depois do corte (para dar para aumentar o corte)


class EditorLegendas:
    abertos = {}  # pasta do projeto -> editor aberto dela

    @classmethod
    def abrir(cls, studio, info: dict):
        """Abre o editor do projeto. Se ja tem um aberto para ele, so traz essa janela para a frente."""
        aberto = cls.abertos.get(str(info["pasta"]))
        if aberto is not None:
            try:
                if aberto.jan.winfo_exists():
                    aberto.jan.deiconify()  # se estava minimizada, volta
                    aberto.jan.lift()
                    aberto.jan.focus_force()
                    return aberto
            except tk.TclError:
                pass
            cls.abertos.pop(str(info["pasta"]), None)
        return cls(studio, info)

    def __init__(self, studio, info: dict):
        self.studio = studio
        self.info = info
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
        self._linha_do_player = None  # linha que o PLAYER selecionou (essa selecao nao leva o video para la)

        self.jan = tk.Toplevel(studio.raiz)
        self.jan.title(f"Revisar legendas - {info['nome']}")
        largura, altura = self.jan.winfo_screenwidth(), self.jan.winfo_screenheight()
        self.jan.geometry(f"{min(1280, largura - 40)}x{min(820, altura - 90)}+20+10")
        self.jan.configure(bg=COR_FUNDO)
        self.jan.protocol("WM_DELETE_WINDOW", self.fechar)
        EditorLegendas.abertos[str(self.pasta)] = self
        self.jan.bind("<Destroy>", self._fechou, add="+")
        self.jan.bind("<FocusIn>", self.recarregar_se_chegou_legenda)
        self.censurar_lista = tk.BooleanVar(value=False)
        self._montar_lista_de_shorts()
        self._montar_editor()
        self._ligar_atalhos()
        self.editando = None  # caixinha de edicao aberta em cima da linha (duplo clique)
        if self.shorts:
            self.lista.selection_set(0)
            self.abrir_short()

    # ---------------------------------------------------------- montagem
    def _montar_lista_de_shorts(self):
        esquerda = tk.Frame(self.jan, bg=COR_FUNDO, width=360)
        esquerda.pack(side="left", fill="y", padx=(14, 0), pady=12)
        tk.Label(esquerda, text="Shorts do projeto", bg=COR_FUNDO, fg=COR_TEXTO, font=tema.F_SUBTITULO).pack(anchor="w")
        tk.Label(esquerda, text="botão direito: abrir, renderizar, publicar, excluir", bg=COR_FUNDO, fg=tema.TEXTO_2,
                 font=tema.F_PEQUENA).pack(anchor="w")  # fmt: skip
        self.lista = tk.Listbox(
            esquerda, width=34, font=("Segoe UI", 10), activestyle="none", bg=tema.PAINEL, fg=COR_TEXTO,
            selectbackground=tema.LARANJA_ESCURO, selectforeground=tema.TEXTO, highlightthickness=0, borderwidth=0, exportselection=False,
        )  # fmt: skip
        self.lista.configure(height=8)
        self.lista.pack(fill="x", pady=(6, 0))
        for s in self.shorts:
            self.lista.insert("end", self.rotulo_na_lista(s))
        self.lista.bind("<<ListboxSelect>>", lambda e: self.abrir_short())
        self.lista.bind("<Double-1>", lambda e: self.assistir())
        ligar_botao_direito(self.lista, self.menu_do_short)
        self._montar_player(esquerda)

    def _montar_player(self, coluna):
        """Player embutido embaixo da lista de Shorts: video original (trecho do corte) ou o Short pronto."""
        self.player = Player(coluna, altura=200, ao_tempo=self.no_tempo, compacto=True)
        self.player.pack(fill="both", expand=True, pady=(10, 0))
        self.modo_player = tk.StringVar(value="original")
        for texto, valor in (("Original", "original"), ("Short pronto", "pronto")):
            ttk.Radiobutton(self.player.extras, text=texto, value=valor, variable=self.modo_player,
                            command=self.mostrar_no_player).pack(side="left", padx=(0, 6))  # fmt: skip
        self.lbl_legenda_video = tk.Label(coluna, text="", bg=tema.CAMPO, fg=COR_TEXTO, font=(tema.FONTE, 11, "bold"),
                                          anchor="center", height=2, wraplength=250)  # fmt: skip
        self.lbl_legenda_video.pack(fill="x", pady=(4, 0))
        botoes = tk.Frame(coluna, bg=COR_FUNDO)
        botoes.pack(fill="x", pady=(4, 0))
        ttk.Button(botoes, text="[ Corte começa aqui", style="Player.TButton",
                   command=lambda: self.ajustar_corte("inicio")).pack(side="left")  # fmt: skip
        ttk.Button(botoes, text="Corte acaba aqui ]", style="Player.TButton",
                   command=lambda: self.ajustar_corte("fim")).pack(side="right")  # fmt: skip

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
            fg=tema.TEXTO_2,
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
                                           ("quem", "Quem fala", 110, "w"), ("texto", "Legenda", 380, "w"),
                                           ("obs", "Atenção", 130, "w")]:  # fmt: skip
            self.tree.heading(col, text=titulo)
            self.tree.column(col, width=largura, anchor=lado, stretch=(col == "texto"))
        barra = ttk.Scrollbar(quadro, command=self.tree.yview)
        self.tree.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.tag_configure("incerto", background=tema.INCERTO)
        self.tree.tag_configure("erro", foreground=tema.AMARELO)
        self.tree.bind("<<TreeviewSelect>>", lambda e: (self.mostrar_linha(), self.linha_no_player()))
        # duplo clique edita ali mesmo (texto ou tempo); botao direito abre o menu da linha
        self.tree.bind("<Double-1>", self.duplo_clique)
        ligar_botao_direito(self.tree, self.menu_da_linha)

        tk.Label(
            direita, bg=COR_FUNDO, fg=tema.TEXTO_2, font=tema.F_SECAO, anchor="w",
            text="LINHA SELECIONADA   amarelo = o Claude não teve certeza   sublinhado = possível erro de português"
            "   riscado = censurada",
        ).pack(fill="x", pady=(8, 2))  # fmt: skip
        self.caixa = tk.Text(
            direita, height=2, wrap="word", font=("Segoe UI", 13), bg=tema.CAMPO, fg=COR_TEXTO, insertbackground=COR_TEXTO,
            relief="flat", padx=8, pady=6, undo=False,
        )  # fmt: skip
        self.caixa.pack(fill="x")
        self.caixa.tag_configure("incerto", background=COR_INCERTO)
        self.caixa.tag_configure("erro", underline=True, underlinefg=tema.VERMELHO)
        self.caixa.tag_configure("censurada", overstrike=True, foreground=tema.TEXTO_2)
        self.caixa.bind("<Return>", self.aplicar_linha)
        self.caixa.bind("<KeyRelease>", lambda e: self.pintar_caixa())
        ligar_botao_direito(self.caixa, self.menu_da_caixa)

        quem = tk.Frame(direita, bg=COR_FUNDO)
        quem.pack(fill="x", pady=(6, 0))
        self.lbl_quem = tk.Label(quem, text="", bg=COR_FUNDO, fg=COR_TEXTO, font=tema.F_TEXTO)
        self.lbl_quem.pack(side="left")
        self.lbl_contraste = tk.Label(quem, text="", bg=COR_FUNDO, fg=tema.AMARELO, font=tema.F_PEQUENA)
        self.lbl_contraste.pack(side="left", padx=6)
        ttk.Checkbutton(
            quem, text="Censurar as palavras da lista (censura.txt) neste Short", variable=self.censurar_lista,
            command=self.mudou_censura_lista,
        ).pack(side="right")  # fmt: skip

    def _montar_botoes_de_baixo(self, direita):
        """So os botoes principais. O resto esta no botao direito e nos atalhos."""
        linha2 = tk.Frame(direita, bg=COR_FUNDO)
        linha2.pack(fill="x", pady=(10, 0))
        ttk.Button(linha2, text="Salvar  (Ctrl+S)", style="Extra.TButton", command=self.salvar).pack(side="left")
        ttk.Button(linha2, text="Publicar", style="Passo.TButton", command=self.publicar).pack(side="right")
        ttk.Button(linha2, text="Renderizar", style="Extra.TButton", command=self.renderizar).pack(side="right", padx=8)
        self.lbl_dica = tk.Label(
            direita,
            text="",
            bg=COR_FUNDO,
            fg=tema.TEXTO_2,
            font=tema.F_PEQUENA,
            anchor="w",
            justify="left",
            wraplength=760,
        )
        self.lbl_dica.pack(fill="x", pady=(6, 0))
        vezes = int(ler_ajustes().get("dica_editor_vezes", 0) or 0)
        if vezes < VEZES_DA_DICA:  # dica discreta so nas primeiras vezes
            salvar_ajustes({"dica_editor_vezes": vezes + 1})
            self.lbl_dica.config(
                text="Dica: clique duas vezes para editar, botão direito para mais opções.  "
                "Espaço = tocar/pausar · F2 = editar · Delete = excluir linha · Ctrl+Z = desfazer · J/L = 5 s"
            )

    def _ligar_atalhos(self):
        j = self.jan
        j.bind("<Control-s>", lambda e: (self.salvar(), "break")[1])
        j.bind("<Control-S>", lambda e: (self.salvar(), "break")[1])
        j.bind("<Control-z>", self._atalho(self.desfazer))
        j.bind("<Control-Z>", self._atalho(self.desfazer))
        self.tree.bind("<space>", self._atalho(self.tocar_ou_pausar))
        self.tree.bind("<Delete>", self._atalho(self.excluir_linha))
        self.tree.bind("<F2>", self._atalho(lambda: self.editar_celula("texto")))
        self.tree.bind("<Return>", self._atalho(lambda: self.editar_celula("texto")))
        self.lista.bind("<space>", self._atalho(self.tocar_ou_pausar))
        self.lista.bind("<Delete>", self._atalho(self.excluir_short))  # na lista de Shorts: exclui o Short
        self.player.ligar_atalhos(self.jan)

    def _atalho(self, funcao):
        """Atalho que nao atrapalha quando voce esta digitando numa caixa de texto."""

        def rodar(evento):
            if isinstance(evento.widget, (tk.Entry, ttk.Entry, tk.Text)) and evento.widget is not self.tree:
                return None
            funcao()
            return "break"

        return rodar

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
        self.trecho = (original.get("inicio"), original.get("fim")) if original else (None, None)
        editada = revisao.editada_do_trecho(self.pasta, self.n, *self.trecho)  # editada de outro corte nao vale
        self.originais = original["palavras"] if original else []
        self.palavras = copy.deepcopy(editada["palavras"] if editada else self.originais)
        self.censurar_lista.set(bool(editada and editada.get("censurar_lista")))
        self.ligacoes = pessoas.ler_ligacoes(self.pasta, self.n, *self.trecho)
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
        self.mostrar_no_player()

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
                fg=tema.AMARELO,
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
            fg=tema.TEXTO_2,
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
            self.lbl_quem.config(text="")
            return
        self.caixa.insert("1.0", revisao.texto_da_linha(self.palavras, self.linhas[k]))
        self.pintar_caixa()
        self.mostrar_quem_da_linha(k)

    # ---------------------------------------------------------- quem fala na linha
    def mostrar_quem_da_linha(self, k: int):
        """Lista de pessoas da linha e a cor da pessoa na caixa (previa da cor da legenda)."""
        w = self.palavras[self.linhas[k][0]]
        self.quem = pessoas.QuemFala(self.ligacoes, pessoas.ler_pessoas())
        pessoa = self.quem.pessoa(w)
        automatico = "s" in w and not w.get("pessoa")
        self.lbl_quem.config(text=f"Quem fala: {pessoa['nome']}" + ("  (voz detectada)" if automatico else ""),
                             fg=pessoa["cor"])  # fmt: skip
        self.caixa.configure(fg=pessoa["cor"])
        self.lbl_contraste.config(
            text=f"cor de {pessoa['nome']}"
            + ("  ⚠ escura: difícil de ler" if pessoas.dificil_de_ler(pessoa["cor"]) else "")
        )

    def opcoes_de_quem(self, k: int) -> list:
        """Quem pode falar na linha k: (voz detectada), as pessoas do cadastro e '+ nova pessoa...'."""
        w = self.palavras[self.linhas[k][0]]
        return ([AUTOMATICO] if "s" in w else []) + [p["nome"] for p in pessoas.ler_pessoas()] + [NOVA]

    def quem_esta_na_linha(self, k: int) -> str:
        w = self.palavras[self.linhas[k][0]]
        return w["pessoa"] if w.get("pessoa") else (AUTOMATICO if "s" in w else self.quem.pessoa(w)["nome"])

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
    def censurar_palavra(self, ligar: bool, j=None):
        """Censura (ou tira a censura) da palavra j da linha. Sem j: a palavra onde esta o cursor da caixa."""
        k = self.linha_atual()
        if j is None:
            j = self.palavra_sob_o_cursor()
        else:
            self.mostrar_linha()  # a caixa volta para o texto da linha (o menu ja mostra as palavras certas)
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

    def adicionar_sempre(self, j=None):
        k = self.linha_atual()
        j = self.palavra_sob_o_cursor() if j is None else j
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
        if self.usar_player():
            self.player.tocar(max(0.0, ws[0]["i"] - 0.5), ws[-1]["f"] + 0.5)
            return
        self.tocar_trecho(max(0.0, ws[0]["i"] - 0.5), ws[-1]["f"] + 0.5, f"{k:03d}")

    # ---------------------------------------------------------- player embutido
    def trecho_do_corte(self):
        """(inicio, fim) do corte no video original: o da legenda gerada ou, se nao tiver, o do cortes.json."""
        ini, fim = self.trecho
        if ini is None or fim is None:
            c = self.corte_do(self.n) if self.n else {}
            try:
                ini, fim = ler_tempo(c["inicio"]), ler_tempo(c["fim"])
            except (KeyError, TypeError, ValueError):
                return None, None
        return float(ini), float(fim)

    def mostrar_no_player(self):
        """Abre no player o trecho do corte (video original) ou o Short pronto, conforme a escolha."""
        s = self.atual()
        self.player.pausar()
        self.lbl_legenda_video.config(text="")
        if not s:
            return
        if self.modo_player.get() == "pronto":
            arq = self.pasta / "prontos" / s["arquivo"]
            self.player.faixas, self.player.marcas = [], []
            if arq.exists():
                self.player.abrir(arq)
            return
        ini, fim = self.trecho_do_corte()
        if ini is None or not self.video.exists():
            return
        janela = (max(0.0, ini - FOLGA_PLAYER), fim + FOLGA_PLAYER)
        self.player.faixas = [(janela[0], ini, tema.BOTAO_HOVER), (fim, janela[1], tema.BOTAO_HOVER)]
        self.player.marcas = [(ini, tema.VERDE), (fim, tema.VERDE)]  # risquinhos verdes: comeco e fim do Short
        self.player.abrir(self.video, ini, janela)

    def tempos_das_linhas(self):
        inicios = [self.palavras[ps[0]]["i"] for ps in self.linhas]
        fins = [self.palavras[ps[-1]]["f"] for ps in self.linhas]
        return inicios, fins

    def no_tempo(self, t: float):
        """Chamado pelo player: mostra a legenda daquele momento e, tocando, a lista acompanha o video."""
        if self.modo_player.get() != "original" or not self.linhas:
            return
        inicios, fins = self.tempos_das_linhas()
        k = reproducao.dentro_da_linha(inicios, fins, t)
        texto = revisao.texto_da_linha(self.palavras, self.linhas[k]) if k is not None else ""
        cor = self.quem.pessoa(self.palavras[self.linhas[k][0]])["cor"] if k is not None else COR_TEXTO
        if self.lbl_legenda_video.cget("text") != texto:
            self.lbl_legenda_video.config(text=texto, fg=cor)
        if k is None or not self.player.tocando or k == self.linha_atual() or self.editando is not None:
            return
        if self.jan.focus_get() is self.caixa:  # voce esta digitando na caixa da linha: nao troca a linha
            return
        self._linha_do_player = k
        self.tree.selection_set(str(k))
        self.tree.see(str(k))

    def linha_no_player(self):
        """Voce escolheu uma linha: o video (parado) vai para o comeco dela."""
        k = self.linha_atual()
        if k is None or k == self._linha_do_player:
            self._linha_do_player = None
            return
        self._linha_do_player = None
        if self.player.pronto and self.modo_player.get() == "original" and not self.player.tocando:
            self.player.ir(self.palavras[self.linhas[k][0]]["i"])

    def usar_player(self) -> bool:
        """O player embutido esta funcionando e mostrando o video original (volta para ele se estava no Short)."""
        if not self.player.pronto or not self.video.exists():
            return False
        if self.modo_player.get() != "original":
            self.modo_player.set("original")
            self.mostrar_no_player()
        return True

    def ajustar_corte(self, borda: str):
        """Inicio (ou fim) do corte = onde o video esta. Grava no cortes.json e renderiza so este Short de novo."""
        if self.n is None:
            return
        if not self.player.pronto or self.modo_player.get() != "original":
            messagebox.showinfo("Ajustar o corte", 'Use o player em "Original" para escolher o ponto.',
                                parent=self.jan)  # fmt: skip
            return
        ini, fim = self.trecho_do_corte()
        t = self.player.tempo()
        novo_ini, novo_fim = (t, fim) if borda == "inicio" else (ini, t)
        if ini is None or novo_fim - novo_ini < 3:
            messagebox.showinfo("Ajustar o corte", "O Short precisa ter pelo menos 3 segundos: o início fica antes do "
                                "fim. Leve o vídeo para outro ponto.", parent=self.jan)  # fmt: skip
            return
        if not messagebox.askyesno(
            "Ajustar o corte",
            f"O corte vai ficar de {tempo_txt(novo_ini, ms=True)[:-2]} até {tempo_txt(novo_fim, ms=True)[:-2]} "
            f"({novo_fim - novo_ini:.1f} s).\n\nO Short vai ser renderizado de novo (só ele) e a legenda é refeita para "
            "o trecho novo. As mudanças que você fez na legenda deste Short ficam guardadas em legendas\\antigas.\n\n"
            "Continuar?",
            parent=self.jan,
        ):
            return
        if self.mudou:  # o que voce mudou na legenda fica guardado (vai para legendas\antigas com o trecho velho)
            self.salvar()
        dados = ler_cortes(self.pasta)
        if not dados or not 0 < self.n <= len(dados["cortes"]) or not isinstance(dados["cortes"][self.n - 1], dict):
            messagebox.showerror("Ajustar o corte", "Não achei este corte no cortes.json.", parent=self.jan)
            return
        c = dados["cortes"][self.n - 1]
        c["inicio"], c["fim"] = tempo_txt(novo_ini, ms=True), tempo_txt(novo_fim, ms=True)
        gravar_json(self.pasta / "cortes.json", dados)
        self.cortes[self.n - 1] = c
        self.mudou = False  # a legenda deste Short vai ser refeita para o trecho novo
        self.trecho = (novo_ini, novo_fim)
        self.mostrar_no_player()
        rodar_script("shorts.gerar_shorts", self.pasta, "--so", self.n)
        notificar(self.jan, "Corte ajustado. Renderizando este Short de novo na janela preta que abriu.\n"
                  "Quando terminar, feche e abra o editor para revisar a legenda nova.", "info", 8)  # fmt: skip

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
        """Roda o ffmpeg (corte ou previa de audio) em segundo plano e abre o resultado no player.
        Antes rodava na linha da tela: o editor ficava travado ("Não respondendo") enquanto o trecho era cortado."""
        if not self.video.exists():
            messagebox.showinfo(titulo, f"Não achei o vídeo original:\n{self.video}", parent=self.jan)
            return
        notificar(self.jan, "Preparando o trecho...", "info", 3)

        def rodar():
            return subprocess.run(
                comando, capture_output=True, text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )

        def pronto(r):
            if isinstance(r, Exception) or r.returncode != 0 or not Path(saida).exists():
                detalhe = str(r) if isinstance(r, Exception) else (r.stderr or "")
                pai = self.jan if self.jan.winfo_exists() else self.studio.raiz
                messagebox.showerror(titulo, "Não consegui montar o trecho:\n" + detalhe[-300:], parent=pai)
                return
            abrir(saida)

        em_segundo_plano(self.studio.raiz, rodar, pronto)

    def abrir_arquivo(self, arquivo: Path):
        abrir(arquivo)

    def assistir(self):
        s = self.atual()
        if s and (self.pasta / "prontos" / s["arquivo"]).exists():
            if self.player.pronto:  # toca aqui mesmo, no player do editor
                self.modo_player.set("pronto")
                self.mostrar_no_player()
                self.player.tocar(0.0)
                return
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
                revisao.salvar_editada(self.pasta, self.n, self.palavras, self.censurar_lista.get(), *self.trecho)
        pessoas.salvar_ligacoes(self.pasta, self.n, self.ligacoes, *self.trecho)
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
        notificar(self.jan, "Renderizando este Short de novo (só ele) na janela preta que abriu.\n"
                  "Quando terminar, clique duas vezes no Short da lista para assistir.", "info", 7)  # fmt: skip

    # ---------------------------------------------------------- duplo clique: editar ali mesmo
    def duplo_clique(self, evento):
        linha, coluna = self.tree.identify_row(evento.y), self.tree.identify_column(evento.x)
        if not linha:
            return "break"
        self.tree.selection_set(linha)
        self.mostrar_linha()
        nome = {"#1": "ini", "#2": "fim", "#3": "quem"}.get(coluna, "texto")
        if nome == "quem":
            abrir_menu(evento, montar_menu(self.jan, self.itens_quem(int(linha))))
        else:
            self.editar_celula(nome)
        return "break"

    def editar_celula(self, coluna: str = "texto"):
        """Abre uma caixinha em cima da celula (texto, ini ou fim). Enter salva, Esc cancela."""
        k = self.linha_atual()
        if k is None:
            return None
        self.fechar_edicao(salvar=True)
        self.tree.see(str(k))
        self.tree.update_idletasks()
        caixa = self.tree.bbox(str(k), coluna)
        if not caixa:
            return None
        x, y, largura, altura = caixa
        ws = [self.palavras[p] for p in self.linhas[k]]
        valor = revisao.texto_da_linha(self.palavras, self.linhas[k]) if coluna == "texto" else self._tempo(
            ws[0]["i"] if coluna == "ini" else ws[-1]["f"])  # fmt: skip
        ent = tk.Entry(self.tree, font=tema.F_TEXTO, bg=tema.CAMPO, fg=tema.TEXTO, insertbackground=tema.TEXTO,
                       relief="flat", highlightthickness=1, highlightbackground=tema.LARANJA,
                       highlightcolor=tema.LARANJA)  # fmt: skip
        ent.insert(0, valor)
        ent.select_range(0, "end")
        ent.icursor("end")
        ent.place(x=x, y=y, width=max(largura, 110), height=altura)
        ent.focus_set()
        self.editando = (ent, k, coluna)
        for tecla in ("<Return>", "<KP_Enter>"):
            ent.bind(tecla, lambda e: (self.fechar_edicao(True), "break")[1])
        ent.bind("<Escape>", lambda e: (self.fechar_edicao(False), "break")[1])
        ent.bind("<FocusOut>", lambda e: self.fechar_edicao(True))
        return ent

    def fechar_edicao(self, salvar: bool):
        if not self.editando:
            return
        ent, k, coluna = self.editando
        self.editando = None
        valor = ent.get().strip()
        ent.destroy()
        nova = getattr(self, "_linha_nova", None)
        self._linha_nova = None
        if not salvar:
            if nova == k:  # cancelou a linha que acabou de inserir: ela some
                self.desfazer()
            self.tree.focus_set()
            return
        if coluna == "texto":
            self.trocar_texto(k, valor)
        else:
            self.trocar_tempo(k, coluna, valor)
        if self.jan.winfo_exists():
            self.tree.focus_set()

    def trocar_texto(self, k: int, novo: str):
        novo = " ".join(novo.split())
        if not novo:
            self.excluir_linha(k)
            return
        if novo == revisao.texto_da_linha(self.palavras, self.linhas[k]):
            return
        self.guardar_para_desfazer()
        self.palavras = revisao.trocar_texto_da_linha(self.palavras, self.linhas[k], novo)
        self.mostrar(manter=k)

    def trocar_tempo(self, k: int, coluna: str, valor: str):
        ws = [self.palavras[p] for p in self.linhas[k]]
        ini, fim = ws[0]["i"], ws[-1]["f"]
        antes = ini if coluna == "ini" else fim
        try:
            t = ler_tempo(valor)
        except (TypeError, ValueError):
            messagebox.showinfo("Tempo", f'"{valor}" não é um tempo. Use minutos:segundos, ex.: 12:03.5',
                                parent=self.jan)  # fmt: skip
            return
        if ":" in valor and valor.count(":") == 1:  # a lista mostra MM:SS: a hora vem do tempo de antes
            t += int(antes // 3600) * 3600
        if abs(t - antes) < 0.01:
            return
        novo_ini, novo_fim = (t, fim) if coluna == "ini" else (ini, t)
        try:
            palavras = revisao.mudar_tempo_da_linha(self.palavras, self.linhas[k], novo_ini, novo_fim)
        except ValueError as e:
            messagebox.showinfo("Tempo", f"{e}\n\nO tempo não mudou.", parent=self.jan)
            return
        self.guardar_para_desfazer()
        self.palavras = palavras
        self.mostrar(manter=k)

    # ---------------------------------------------------------- inserir e excluir linha
    def inserir_linha(self):
        k = self.linha_atual()
        if k is None:
            return
        self.guardar_para_desfazer()
        self.palavras, pos = revisao.inserir_linha_depois(self.palavras, self.linhas[k])
        self.mostrar(manter=k)
        nova = next((i for i, linha in enumerate(self.linhas) if pos in linha), k + 1)
        self.tree.selection_set(str(nova))
        self.mostrar_linha()
        self.editar_celula("texto")
        self._linha_nova = nova

    def excluir_linha(self, k=None):
        k = self.linha_atual() if k is None else k
        if k is None:
            return
        try:
            palavras = revisao.excluir_linha(self.palavras, self.linhas[k])
        except ValueError as e:
            messagebox.showinfo("Excluir linha", str(e), parent=self.jan)
            return
        self.guardar_para_desfazer()
        self.palavras = palavras
        self.mostrar(manter=max(0, k - 1) if k >= len(self.linhas) - 1 else k)
        notificar(self.jan, "Linha excluída. Ctrl+Z desfaz.", "info", 3)

    # ---------------------------------------------------------- tocar (Espaco)
    def tocar_ou_pausar(self):
        """Espaco: com o player, toca o video a partir da linha selecionada (a lista acompanha); tocando, pausa.
        Sem o player: toca so o audio da linha dentro do Studio; se ja esta tocando, para."""
        if self.player.pronto and (self.player.tocando or self.modo_player.get() == "pronto"):
            self.player.alternar()
            return
        if self.player.pronto and self.video.exists():
            k = self.linha_atual()
            de = max(0.0, self.palavras[self.linhas[k][0]]["i"] - 0.3) if k is not None else None
            self.player.tocar(de)
            return
        if tocador.tocando():
            tocador.parar()
            return
        k = self.linha_atual()
        if k is None:
            return
        if not tocador.disponivel():  # fora do Windows: abre o trecho no player
            self.ouvir()
            return
        if not self.video.exists():
            messagebox.showinfo("Ouvir trecho", f"Não achei o vídeo original:\n{self.video}", parent=self.jan)
            return
        ws = [self.palavras[p] for p in self.linhas[k]]
        ini, fim = max(0.0, ws[0]["i"] - 0.3), ws[-1]["f"] + 0.3
        wav = DADOS_APP / "temp" / "ouvir_linha.wav"
        tocador.parar()
        if tocador.cortar_audio(achar_programa("ffmpeg"), self.video, ini, fim, wav):
            tocador.tocar(wav, fim - ini)

    # ---------------------------------------------------------- menus do botao direito
    def menu_da_linha(self, evento):
        linha = self.tree.identify_row(evento.y)
        if not linha:
            return None
        self.fechar_edicao(salvar=True)
        self.tree.selection_set(linha)
        self.tree.focus(linha)
        self.mostrar_linha()
        return montar_menu(self.jan, self.itens_da_linha(int(linha)))

    def itens_da_linha(self, k: int) -> list:
        return [
            ("▶  Tocar a partir desta linha", self.tocar_ou_pausar, "Espaço"),
            ("🎬  Assistir este trecho (vídeo)", self.ouvir),
            None,
            ("✏  Editar texto", lambda: self.editar_celula("texto"), "F2"),
            ("⏱  Editar tempo", [("Início", lambda: self.editar_celula("ini")),
                                 ("Fim", lambda: self.editar_celula("fim"))]),  # fmt: skip
            ("🗣  Trocar quem fala", self.itens_quem(k)),
            ("🔇  Censurar palavra", self.itens_censura(k)),
            ("📋  Sempre censurar (pôr na lista)", self.itens_lista(k)),
            None,
            ("➕  Inserir linha abaixo", self.inserir_linha),
            ("🗑  Excluir linha", self.excluir_linha, "Delete"),
            None,
            ("↶  Desfazer", self.desfazer if self.desfazer_pilha else None, "Ctrl+Z"),
        ]

    def itens_quem(self, k: int) -> list:
        atual = self.quem_esta_na_linha(k)
        return [(nome, lambda n=nome: self.trocar_quem_da_linha(n), None, nome == atual) if nome != NOVA
                else (nome, lambda: self.trocar_quem_da_linha(NOVA)) for nome in self.opcoes_de_quem(k)]  # fmt: skip

    def itens_censura(self, k: int) -> list:
        ws = [self.palavras[p] for p in self.linhas[k]]
        return [(w["p"], lambda j=j, w=w: self.censurar_palavra(not w.get("cx"), j), None, bool(w.get("cx")))
                for j, w in enumerate(ws)]  # fmt: skip

    def itens_lista(self, k: int) -> list:
        ws = [self.palavras[p] for p in self.linhas[k]]
        return [(w["p"], lambda j=j: self.adicionar_sempre(j)) for j, w in enumerate(ws)]

    def menu_da_caixa(self, evento):
        """Botao direito na caixa da linha: censurar a palavra clicada."""
        if self.linha_atual() is None:
            return None
        self.caixa.mark_set("insert", f"@{evento.x},{evento.y}")
        return montar_menu(self.jan, [
            ("🔇  Censurar esta palavra", lambda: self.censurar_palavra(True)),
            ("Tirar a censura desta palavra", lambda: self.censurar_palavra(False)),
            ("📋  Sempre censurar (pôr na lista)", self.adicionar_sempre),
        ])  # fmt: skip

    def menu_do_short(self, evento):
        """Botao direito num Short da lista."""
        if not self.shorts:
            return None
        k = self.lista.nearest(evento.y)
        if self.atual() is not self.shorts[k]:
            self.lista.selection_clear(0, "end")
            self.lista.selection_set(k)
            self.abrir_short()
        return montar_menu(self.jan, self.itens_do_short())

    def itens_do_short(self) -> list:
        return [
            ("▶  Abrir (assistir)", self.assistir),
            ("⟳  Renderizar de novo", self.renderizar),
            ("📅  Publicar", self.publicar),
            ("📁  Abrir pasta", self.abrir_pasta_do_short),
            None,
            ("↺  Voltar ao original (legenda)", self.voltar_ao_original),
            None,
            ("🗑  Excluir este Short", self.excluir_short),
        ]

    def abrir_pasta_do_short(self):
        s = self.atual()
        arq = self.pasta / "prontos" / s["arquivo"] if s else None
        if arq and arq.exists():
            mostrar_na_pasta(arq)
        else:
            abrir(self.pasta / "prontos")

    # ---------------------------------------------------------- publicar e excluir
    def publicar(self):
        s = self.atual()
        if not s:
            return
        if self.mudou:
            if not messagebox.askyesno("Publicar", "Você mudou este Short e não salvou.\n\nSalvar e renderizar de "
                                       "novo antes de publicar?", parent=self.jan):  # fmt: skip
                return
            self.renderizar()
            return
        self.studio.publicar_shorts(self.info, [s["n"]], parent=self.jan)

    def excluir_short(self):
        s = self.atual()
        if not s:
            return
        from nucleo.limpeza import excluir_short

        aviso = self.studio.aviso_da_fila([self.pasta / "prontos" / s["arquivo"]])
        if not messagebox.askyesno(
            "Excluir Short",
            f"Excluir o Short \"{s['arquivo']}\"?\n\n" + (aviso + "\n\n" if aviso else "")
            + "O vídeo vai para a Lixeira (dá para restaurar) e esse corte não é gerado de novo.\n"
            "A transcrição e os outros Shorts continuam.",
            icon="warning", parent=self.jan,
        ):  # fmt: skip
            return
        try:
            excluir_short(self.pasta, s["n"], s["arquivo"])
        except OSError as e:
            messagebox.showerror("Excluir Short", str(e), parent=self.jan)
            return
        k = self.shorts.index(s)
        self.shorts.pop(k)
        self.lista.delete(k)
        self.n, self.mudou, self.desfazer_pilha = None, False, []
        if self.shorts:
            self.lista.selection_set(min(k, len(self.shorts) - 1))
            self.abrir_short()
        self.studio.atualizar()
        notificar(self.jan, f"{s['arquivo']} foi para a Lixeira.", "ok")

    def _fechou(self, evento):
        """A janela foi fechada: tira da lista de editores abertos (o proximo clique abre um novo)."""
        if evento.widget is self.jan and EditorLegendas.abertos.get(str(self.pasta)) is self:
            EditorLegendas.abertos.pop(str(self.pasta), None)

    def fechar(self):
        tocador.parar()
        if self.mudou and not messagebox.askyesno(
            "Revisar legendas", "Você mudou este Short e não salvou.\nFechar e perder as mudanças?", parent=self.jan
        ):
            return
        self.jan.destroy()

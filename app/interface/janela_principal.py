# Janela principal do FamosoZora Studio: a barra lateral (Inicio, Shorts, Videos longos, Publicacao,
# Configuracoes) e a tela escolhida ao lado. Abre sempre maximizada no monitor onde estava; F11 = tela cheia.
#   Inicio         -> interface/pagina_inicio.py
#   Shorts         -> interface/aba_shorts.py
#   Videos longos  -> interface/aba_videos_longos.py
#   Publicacao     -> interface/pagina_publicacao.py
#   Configuracoes  -> interface/pagina_configuracoes.py
# Da para arrastar videos para a janela: cada um vira um projeto (o Studio comeca a transcrever).
import gc
import shutil
import subprocess
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, ttk

from interface import tema
from interface.aba_shorts import AbaShorts
from interface.aba_videos_longos import AbaVideosLongos
from interface.aviso_atualizacao import AvisoAtualizacao, avisar_codigo_novo
from interface.janela_texto import JanelaTexto
from interface.notificacao import notificar
from interface.pagina_configuracoes import PaginaConfiguracoes
from interface.pagina_inicio import PaginaInicio
from interface.pagina_publicacao import PaginaPublicacao
from interface.utilidades import (
    ARQ_DIRETRIZES,
    ARQ_NOVIDADES,
    BAT_DEV,
    PY_JANELA,
    abrir,
    achar_git,
    em_segundo_plano,
    gpu_baixada,
    rodar_script,
    tem_nvidia,
)
from nucleo.atualizacao import buscar_release, eh_mais_nova, situacao_git
from nucleo.comum import (
    APP_INSTALADO,
    EXTENSOES_VIDEO,
    FERRAMENTAS,
    PASTA_APP,
    PASTA_CANAL,
    PASTA_VIDEOS,
    REPO_URL,
    carregar_config,
    ler_ajustes,
    preparar_pasta_trabalho,
    salvar_ajustes,
    salvar_config,
)
from nucleo.projetos import listar_projetos
from nucleo.registro import registrar
from versao import VERSAO

# (codigo, texto, simbolo) dos itens da barra lateral
TELAS = [("inicio", "Início", "⌂"), ("shorts", "Shorts", "▶"), ("longos", "Vídeos longos", "▤"),
         ("publicacao", "Publicação", "◷"), ("configuracoes", "Configurações", "⚙")]  # fmt: skip


def criar_janela_raiz():
    """A janela principal. Com a biblioteca tkinterdnd2 ela aceita arrastar e soltar arquivos;
    sem ela (ou se der erro), abre normal, so sem o arrastar."""
    try:
        from tkinterdnd2 import TkinterDnD

        return TkinterDnD.Tk(), True
    except Exception:
        return tk.Tk(), False


def area_das_telas():
    """(x, y, largura, altura) de todos os monitores juntos (Windows). None se nao der para saber."""
    try:
        import ctypes

        m = ctypes.windll.user32.GetSystemMetrics
        return m(76), m(77), m(78), m(79)
    except Exception:
        return None


class Studio:
    def __init__(self):
        try:
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        self.raiz, self.arrastar = criar_janela_raiz()
        self.raiz.title(f"FamosoZora Studio {VERSAO}")
        self.raiz.minsize(1000, 600)
        self.raiz.configure(bg=tema.FUNDO)
        tema.aplicar(self.raiz)
        self.tela_atual = None
        self._precisa_atualizar = False
        self.projetos = {}
        self._montar_lateral()
        self._montar_telas()
        self._abrir_maximizada()
        self._ligar_atalhos()
        if self.arrastar:
            self._aceitar_arquivos(self.raiz)

        self._assinatura = None
        self.lote_atual = None  # o lote de Shorts rodando agora (shorts/lote.py), se tiver
        self.janela_lote = None
        self.lote_avisado = False
        self.atualizar()
        self.mostrar(ler_ajustes().get("ultima_tela") or "inicio")
        self.raiz.protocol("WM_DELETE_WINDOW", self.fechar)
        self.raiz.after(4000, self.auto_atualizar)
        self.raiz.after(600, self.boas_vindas)
        self.raiz.after(1500, self.perguntar_retomar_lote)
        # o modo desenvolvedor confere o GitHub antes de abrir (sincronizar_antes_de_abrir)
        if APP_INSTALADO and ler_ajustes().get("verificar_atualizacoes", True):
            self.raiz.after(2500, self.verificar_atualizacao)

    # ---------------------------------------------------------- janela: tela cheia e monitor
    def _abrir_maximizada(self):
        """Abre maximizada no monitor onde estava da ultima vez."""
        ajustes = ler_ajustes()
        x, y = ajustes.get("janela_x"), ajustes.get("janela_y")
        area = area_das_telas()
        if isinstance(x, int) and isinstance(y, int):
            dentro = area is None or (area[0] <= x < area[0] + area[2] and area[1] <= y < area[1] + area[3])
            if dentro:
                self.raiz.geometry(f"1200x760+{x}+{y}")
        else:
            self.raiz.geometry("1200x760")
        self.maximizar()

    def maximizar(self):
        try:
            self.raiz.state("zoomed")  # Windows
        except tk.TclError:
            try:
                self.raiz.attributes("-zoomed", True)  # Linux
            except tk.TclError:
                pass

    def tela_cheia(self, _evento=None):
        """F11: tela cheia sem bordas (e volta)."""
        cheia = not bool(self.raiz.attributes("-fullscreen"))
        self.raiz.attributes("-fullscreen", cheia)
        if cheia:
            self.notificar("Tela cheia. Aperte F11 ou Esc para sair.", "info", 3)
        return "break"

    def sair_tela_cheia(self, _evento=None):
        if self.raiz.attributes("-fullscreen"):
            self.raiz.attributes("-fullscreen", False)
            return "break"
        return None

    def _ligar_atalhos(self):
        self.raiz.bind("<F11>", self.tela_cheia)
        self.raiz.bind("<Escape>", self.sair_tela_cheia)
        self.raiz.bind("<Delete>", self.tecla_delete)  # excluir o projeto selecionado, onde estiver o foco
        for k, (codigo, _, _) in enumerate(TELAS, 1):  # Ctrl+1 ... Ctrl+5 trocam de tela
            self.raiz.bind(f"<Control-Key-{k}>", lambda e, c=codigo: self.mostrar(c))

    def fechar(self):
        """Ao fechar: lembra o monitor (a posicao) e a ultima tela aberta. Com um lote rodando, pergunta antes
        e para a etapa atual sem deixar arquivo quebrado (da para continuar quando abrir de novo)."""
        if self.lote_rodando():
            if not messagebox.askyesno("Fechar o Studio", "Tem um lote de Shorts rodando.\n\nFechar mesmo assim? "
                                       "Quando abrir o Studio de novo, ele pergunta se quer continuar de onde parou.",
                                       parent=self.raiz):  # fmt: skip
                return
            self.lote_atual.parar_para_fechar()
            gc.enable()
        try:
            salvar_ajustes({"janela_x": self.raiz.winfo_x() + 40, "janela_y": self.raiz.winfo_y() + 40,
                            "ultima_tela": self.tela_atual})  # fmt: skip
        except Exception:
            pass
        self.raiz.destroy()

    # ---------------------------------------------------------- barra lateral e telas
    def _montar_lateral(self):
        lateral = tk.Frame(self.raiz, bg=tema.PAINEL, width=220)
        lateral.pack(side="left", fill="y")
        lateral.pack_propagate(False)
        tk.Label(lateral, text="FamosoZora", bg=tema.PAINEL, fg=tema.LARANJA, font=(tema.FONTE, 17, "bold"),
                 anchor="w").pack(fill="x", padx=20, pady=(22, 0))  # fmt: skip
        tk.Label(lateral, text="Studio", bg=tema.PAINEL, fg=tema.TEXTO, font=(tema.FONTE, 12), anchor="w").pack(
            fill="x", padx=20, pady=(0, 24)
        )
        self.itens_lateral = {}
        for codigo, texto, simbolo in TELAS:
            linha = tk.Frame(lateral, bg=tema.PAINEL)
            linha.pack(fill="x", pady=1)
            faixa = tk.Frame(linha, bg=tema.PAINEL, width=4)
            faixa.pack(side="left", fill="y")
            b = tk.Button(linha, text=f"  {simbolo}   {texto}", anchor="w", relief="flat", bd=0, cursor="hand2",
                          bg=tema.PAINEL, fg=tema.TEXTO_2, activebackground=tema.BORDA, activeforeground=tema.TEXTO,
                          font=(tema.FONTE, 11), padx=12, pady=9, highlightthickness=0, command=lambda c=codigo: self.mostrar(c))  # fmt: skip
            b.pack(side="left", fill="x", expand=True)
            self.itens_lateral[codigo] = (b, faixa)
        rodape = tk.Frame(lateral, bg=tema.PAINEL)
        rodape.pack(side="bottom", fill="x", padx=20, pady=16)
        tk.Label(rodape, text=f"versão {VERSAO}", bg=tema.PAINEL, fg=tema.TEXTO_2, font=tema.F_PEQUENA,
                 anchor="w").pack(fill="x")  # fmt: skip
        tk.Label(rodape, text="F11 tela cheia  ·  Ctrl+1..5 telas", bg=tema.PAINEL, fg=tema.BORDA,
                 font=tema.F_PEQUENA, anchor="w").pack(fill="x")  # fmt: skip

    def _montar_telas(self):
        self.conteudo = tk.Frame(self.raiz, bg=tema.FUNDO)
        self.conteudo.pack(side="left", fill="both", expand=True)
        self.pagina_inicio = PaginaInicio(self, self.conteudo)
        self.aba_shorts = AbaShorts(self, self.conteudo)
        self.aba_longos = AbaVideosLongos(self, self.conteudo)
        self.pagina_publicacao = PaginaPublicacao(self, self.conteudo)
        self.pagina_configuracoes = PaginaConfiguracoes(self, self.conteudo)
        self.telas = {"inicio": self.pagina_inicio, "shorts": self.aba_shorts, "longos": self.aba_longos,
                      "publicacao": self.pagina_publicacao, "configuracoes": self.pagina_configuracoes}  # fmt: skip

    def mostrar(self, codigo: str, projeto: str | None = None):
        """Mostra uma tela (e, se der, ja seleciona um projeto nela)."""
        if codigo not in self.telas:
            codigo = "inicio"
        for c, tela in self.telas.items():
            if c != codigo:
                tela.pack_forget()
        self.telas[codigo].pack(fill="both", expand=True)
        for c, (b, faixa) in self.itens_lateral.items():
            ativo = c == codigo
            b.config(fg=tema.LARANJA if ativo else tema.TEXTO_2, bg=tema.BORDA if ativo else tema.PAINEL,
                     font=(tema.FONTE, 11, "bold" if ativo else "normal"))  # fmt: skip
            faixa.config(bg=tema.LARANJA if ativo else tema.PAINEL)
        self.tela_atual = codigo
        tela = self.telas[codigo]
        if projeto and hasattr(tela, "tree") and tela.tree.exists(projeto):
            tela.tree.selection_set(projeto)
            tela.tree.see(projeto)
        if hasattr(tela, "ao_mostrar"):
            tela.ao_mostrar()

    def tecla_delete(self, evento):
        """Tecla Delete na janela principal: exclui o(s) projeto(s) selecionado(s) da tela Shorts ou Videos
        longos, mesmo que o foco do teclado nao esteja na lista (ex.: depois de clicar num botao).
        Se voce esta digitando numa caixa de texto, o Delete so apaga a letra, como sempre."""
        if isinstance(evento.widget, (tk.Entry, ttk.Entry, tk.Text, tk.Spinbox, ttk.Spinbox, ttk.Combobox)):
            return None
        tela = self.telas.get(getattr(self, "tela_atual", ""))
        if tela is None or not hasattr(tela, "excluir") or not hasattr(tela, "selecionados"):
            return None
        if tela.selecionados():
            tela.excluir()
        return "break"

    # ---------------------------------------------------------- arrastar e soltar videos
    def _aceitar_arquivos(self, widget):
        """Deixa soltar arquivos em qualquer parte da janela."""
        try:
            from tkinterdnd2 import DND_FILES

            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self.soltou_arquivos)
        except Exception:
            return
        for filho in widget.winfo_children():
            self._aceitar_arquivos(filho)

    def soltou_arquivos(self, evento):
        self.criar_projetos([Path(p) for p in self.raiz.tk.splitlist(evento.data)])
        return getattr(evento, "action", None)

    def criar_projetos(self, arquivos: list):
        """Cada video vira um projeto: o Studio abre a transcricao (que cria a pasta do projeto)."""
        videos = [a for a in arquivos if a.suffix.lower() in EXTENSOES_VIDEO and a.exists()]
        if not videos:
            if arquivos:
                self.notificar("Só dá para soltar vídeos (mp4, mkv, mov...).", "aviso")
            return
        rodar_script("nucleo.transcrever", *videos)
        nomes = videos[0].name if len(videos) == 1 else f"{len(videos)} vídeos"
        self.notificar(f"Transcrevendo {nomes}. Acompanhe na janela preta que abriu.", "info", 6)

    def adicionar_video(self):
        """Botao Adicionar video: escolhe um ou mais videos e comeca a transcrever."""
        from tkinter import filedialog

        tipos = [("Vídeos", " ".join(f"*{e}" for e in sorted(EXTENSOES_VIDEO))), ("Todos os arquivos", "*.*")]
        inicio = PASTA_VIDEOS if PASTA_VIDEOS.exists() else PASTA_CANAL
        escolhidos = filedialog.askopenfilenames(title="Escolha o vídeo (ou vários)", initialdir=str(inicio),
                                                 filetypes=tipos, parent=self.raiz)  # fmt: skip
        if escolhidos:
            self.criar_projetos([Path(a) for a in escolhidos])

    # ---------------------------------------------------------- publicar (Shorts e video longo)
    def publicar_shorts(self, info: dict, numeros=None, parent=None):
        """Abre a revisao para publicar os Shorts 'numeros' do projeto (None = todos os prontos)."""
        from interface.janela_publicar import JanelaPublicar
        from publicacao.rascunhos import rascunhos_de_shorts, shorts_prontos

        prontos = shorts_prontos(info)
        if numeros is None:
            numeros = prontos
        ja = [n for n in numeros if n not in prontos]
        numeros = [n for n in numeros if n in prontos]
        if not numeros:
            if ja:
                self.mostrar("publicacao")
            self.notificar("Nenhum Short para publicar: os prontos já foram publicados ou estão na fila "
                           "(veja na tela Publicação).", "aviso", 6)  # fmt: skip
            return None
        return JanelaPublicar(self, rascunhos_de_shorts(info, numeros), parent)

    def publicar_todos_os_shorts(self):
        """Todos os Shorts prontos de todos os projetos, um por dia, a partir do proximo dia livre."""
        from interface.janela_publicar import JanelaPublicar
        from publicacao import fila
        from publicacao.rascunhos import rascunhos_de_shorts, shorts_prontos

        ocupados = fila.horarios_de_shorts()
        itens = []
        for info in reversed(list(self.projetos.values())):  # os projetos mais antigos primeiro
            numeros = shorts_prontos(info)
            if numeros:
                novos = rascunhos_de_shorts(info, numeros, ocupados + [i["horario"] for i in itens])
                itens += novos
        if not itens:
            self.notificar("Nenhum Short pronto para publicar: todos já foram publicados ou estão na fila.", "aviso")
            return None
        return JanelaPublicar(self, itens)

    def publicar_longo(self, info: dict, parent=None):
        """Abre a revisao para publicar o episodio (video longo) do projeto."""
        from interface.janela_publicar import JanelaPublicar
        from publicacao import fila
        from publicacao.horario import texto_horario
        from publicacao.rascunhos import rascunho_longo

        item = rascunho_longo(info)
        if not item:
            self.notificar("Gere o episódio antes de publicar.", "aviso")
            return None
        ja = fila.na_fila(item["video"])
        if ja:
            self.mostrar("publicacao")
            self.notificar(f"Esse episódio já está na fila ({ja['status']}, {texto_horario(ja['horario'])}).", "aviso")
            return None
        return JanelaPublicar(self, [item], parent)

    def aviso_da_fila(self, arquivos: list) -> str:
        """Aviso (em texto) se algum destes arquivos esta na fila de publicacao e ainda nao saiu."""
        from publicacao import fila
        from publicacao.horario import texto_horario

        pendentes = fila.pendentes_em(arquivos)
        if not pendentes:
            return ""
        nao_subiu = [i for i in pendentes if i["status"] in ("na fila", "enviando")]
        exemplo = pendentes[0]
        texto = (f"⚠ {len(pendentes)} vídeo(s) daqui estão na fila de publicação e ainda não saíram "
                 f"(ex.: \"{exemplo['titulo'][:40]}\", {texto_horario(exemplo['horario'])}).")  # fmt: skip
        if nao_subiu:
            texto += " Alguns ainda nem foram para o YouTube: o Claude usa a cópia do pacote, mas confira antes."
        return texto

    # ---------------------------------------------------------- notificacoes
    # ---------------------------------------------------------- lote (Shorts de varios videos de uma vez)
    def lote_rodando(self) -> bool:
        return self.lote_atual is not None and not self.lote_atual.terminou.is_set()

    def preparar_lote(self, selecionados: list):
        """Abre a janela "Preparar lote" com os videos escolhidos (ou a tela do lote, se ja tem um rodando)."""
        if self.lote_rodando():
            self.notificar("Já tem um lote rodando. Espere ele terminar para começar outro.", "aviso")
            return self.mostrar_lote()
        from interface.janela_preparar_lote import JanelaPrepararLote

        return JanelaPrepararLote(self, selecionados)

    def comecar_lote(self, lote: dict, janela=None):
        """Comeca o lote em segundo plano e abre a tela dele. Devolve o RodarLote (ou None se ja tinha outro)."""
        from shorts.lote import RodarLote

        if self.lote_rodando():
            self.notificar("Já tem um lote rodando. Espere ele terminar para começar outro.", "aviso")
            return None
        rodar = RodarLote(lote)
        if not rodar.iniciar():
            self.notificar("Já tem um lote rodando. Espere ele terminar para começar outro.", "aviso")
            return None
        self.lote_atual = rodar
        self.lote_avisado = False
        # Enquanto o lote roda, a limpeza automatica da memoria fica desligada e o Studio faz a limpeza pela
        # linha da tela (em _vigiar_lote). Se a linha do lote recolhesse uma janela ja fechada, o tkinter
        # reclamaria ("main thread is not in main loop") e a tela podia travar por alguns segundos.
        gc.disable()
        if janela is None:
            self.mostrar_lote()
        self.atualizar()
        self.raiz.after(1000, self._vigiar_lote)
        return rodar

    def mostrar_lote(self):
        """Abre (ou traz para frente) a tela do lote."""
        from interface.janela_lote import JanelaLote

        if self.lote_atual is None:
            return None
        if self.janela_lote is not None and self.janela_lote.jan.winfo_exists():
            self.janela_lote.jan.deiconify()
            self.janela_lote.jan.lift()
            return self.janela_lote
        self.janela_lote = JanelaLote(self, self.lote_atual)
        return self.janela_lote

    def _vigiar_lote(self):
        """Avisa no canto quando o lote termina (mesmo com a tela do lote fechada) e atualiza as listas."""
        from shorts.lote import texto_notificacao

        rodar = self.lote_atual
        if rodar is None or not self.raiz.winfo_exists():
            gc.enable()
            return
        gc.collect()
        self.pedir_atualizacao()
        if not rodar.terminou.is_set():
            self.raiz.after(2000, self._vigiar_lote)
            return
        gc.enable()
        self.atualizar()
        lote = rodar.retrato()
        if not self.lote_avisado and lote.get("situacao") == "terminado":
            self.lote_avisado = True
            erros = any(v.get("etapa") == "erro" for v in lote["videos"])
            self.notificar(texto_notificacao(lote) + "\nNada foi publicado: revise antes de publicar.",
                           "aviso" if erros else "ok", 10)  # fmt: skip

    def perguntar_retomar_lote(self):
        """Ao abrir: se um lote parou no meio (app fechado, PC desligou), pergunta se quer continuar."""
        from shorts import lote as motor

        salvo = motor.carregar()
        if not motor.retomavel(salvo):
            return
        faltam = len(motor.pendentes(salvo))
        if messagebox.askyesno("Lote de Shorts", f"Um lote de Shorts parou no meio ({faltam} vídeo(s) faltando).\n\n"
                               "Continuar o lote de onde parou?", parent=self.raiz):  # fmt: skip
            self.comecar_lote(salvo)
        else:
            salvo["situacao"] = "cancelado"
            motor.salvar(salvo)

    def notificar(self, texto: str, tipo: str = "ok", segundos: float = 4.5):
        notificar(self.raiz, texto, tipo, segundos)

    # ---------------------------------------------------------- lista de projetos (igual em todas as telas)
    def atualizar(self, forcar=True):
        projetos = {i["nome"]: i for i in listar_projetos()}
        assinatura = [
            (n, i["transcrito"], i["n_cortes"], i["n_shorts"], i["postados"], i["n_pub"], i["passo"], i["passo_longo"],
             i["projeto"].get("link_video_completo"), i["episodio"], (i["pasta"] / "edicao.json").exists(),
             (i["pasta"] / "miniatura.png").exists())
            for n, i in projetos.items()
        ]  # fmt: skip
        if not forcar and assinatura == self._assinatura:
            return
        self._assinatura = assinatura
        self.projetos = projetos
        for tela in self.telas.values():
            if hasattr(tela, "preencher"):
                tela.preencher(projetos)

    def pedir_atualizacao(self):
        """Pode ser chamado de outra linha (thread): a tela atualiza na proxima conferida."""
        self._precisa_atualizar = True

    def auto_atualizar(self):
        try:
            forcar, self._precisa_atualizar = self._precisa_atualizar, False
            self.atualizar(forcar=forcar)
            if hasattr(self.pagina_publicacao, "conferir"):
                self.pagina_publicacao.conferir()
        finally:
            self.raiz.after(4000, self.auto_atualizar)

    # ---------------------------------------------------------- video longo (tambem usado pela janela de revisao)
    def pedir_edicao(self, i, parent=None):
        from videos_longos.pedido_edicao import info_video, texto_pedido

        _, dur = info_video(i["pasta"])
        self.copiar(texto_pedido(i["nome"], i["pasta"], ARQ_DIRETRIZES, dur))
        messagebox.showinfo(
            "Editar vídeo longo",
            "Pedido de edição copiado!\n\nAgora cole (Ctrl+V) na conversa com o Claude e envie.\n"
            "Quando ele avisar que salvou o edicao.json, selecione o vídeo e clique em "
            "3 - Editar vídeo longo de novo para revisar.\n\n"
            "Se a conversa não tiver acesso ao PC, copie o JSON que o Claude mandar e clique em "
            '"Colar edicao.json".',
            parent=parent or self.raiz,
        )

    def colar_edicao(self, i, parent=None):
        """Le o edicao.json da area de transferencia, valida e salva na pasta do projeto."""
        from videos_longos.pedido_edicao import erro_json_amigavel, extrair_json, gravar_edicao, info_video, normalizar

        if not i:
            return False
        parent = parent or self.raiz
        try:
            texto = self.raiz.clipboard_get()
        except tk.TclError:
            texto = ""
        if not texto.strip():
            messagebox.showinfo(
                "Colar edicao.json",
                "A área de transferência está vazia.\nCopie o JSON que o Claude mandou e clique aqui de novo.",
                parent=parent,
            )
            return False
        try:
            bruto = extrair_json(texto)
        except Exception as e:
            messagebox.showerror("Colar edicao.json", erro_json_amigavel(e), parent=parent)
            return False
        _, dur = info_video(i["pasta"])
        dados, erros, avisos = normalizar(bruto, dur)
        if erros:
            messagebox.showerror(
                "Colar edicao.json",
                "O edicao.json tem problemas e NÃO foi salvo:\n\n- "
                + "\n- ".join(erros[:12])
                + "\n\nPeça pro Claude corrigir.",
                parent=parent,
            )
            return False
        arq = i["pasta"] / "edicao.json"
        if arq.exists():
            if not messagebox.askyesno(
                "Colar edicao.json",
                "Esse vídeo já tem um edicao.json.\n\n"
                "Substituir pelo que você copiou?\n(o atual vira edicao_anterior.json)",
                parent=parent,
            ):
                return False
            shutil.copy2(arq, i["pasta"] / "edicao_anterior.json")
        gravar_edicao(arq, dados)
        msg = f"edicao.json salvo com {len(dados.get('cortes', []))} cortes e {len(dados.get('capitulos', []))} capítulos."
        if avisos:
            msg += "\n\nAvisos:\n- " + "\n- ".join(avisos[:10])
        if avisos:
            messagebox.showinfo("Colar edicao.json", msg, parent=parent)
        else:
            self.notificar(msg)
        self.atualizar()
        return True

    # ---------------------------------------------------------- menu geral
    def maximo_de_shorts(self):
        from tkinter import simpledialog

        from shorts.cortes import maximo_de_shorts

        atual = maximo_de_shorts(carregar_config())
        r = simpledialog.askstring(
            "Máximo de Shorts por vídeo",
            "Teto de Shorts por vídeo (deixe vazio = sem limite).\n"
            "É só um teto, nunca uma meta: o Claude manda só os cortes que valem a pena.",
            initialvalue=str(atual or ""),
            parent=self.raiz,
        )
        if r is None:
            return
        r = r.strip()
        if r and not (r.isdigit() and int(r) > 0):
            messagebox.showinfo("Máximo de Shorts", "Use um número inteiro (ex.: 8) ou deixe vazio.", parent=self.raiz)
            return
        salvar_config({"maximo_shorts": int(r) if r else None})
        self.atualizar()

    def pessoas_e_cores(self):
        from interface.janela_pessoas import JanelaPessoas

        JanelaPessoas(self.raiz)

    def abrir_pasta_segura(self, pasta: Path):
        pasta.mkdir(parents=True, exist_ok=True)
        abrir(pasta)

    def instalar(self):
        if APP_INSTALADO:
            if not tem_nvidia() and not messagebox.askyesno(
                "Placa de vídeo", "Não achei uma placa NVIDIA neste computador. Tentar ativar mesmo assim?"
            ):
                return
            rodar_script("nucleo.ativar_gpu")
            return
        if BAT_DEV.exists():
            subprocess.Popen(["cmd", "/c", "start", "", str(BAT_DEV), "instalar"], cwd=str(PASTA_APP))

    def novidades(self):
        JanelaTexto(self.raiz, f"Novidades - FamosoZora Studio {VERSAO}", ARQ_NOVIDADES)

    def mudar_pasta_trabalho(self):
        from tkinter import filedialog

        nova = filedialog.askdirectory(
            title="Escolha a pasta de trabalho (vídeos e projetos)", initialdir=str(PASTA_CANAL)
        )
        if not nova or Path(nova) == PASTA_CANAL:
            return False
        salvar_ajustes({"pasta_trabalho": str(Path(nova))})
        messagebox.showinfo("Pasta de trabalho", f"Pronto! A pasta agora é:\n{nova}\n\nO Studio vai reabrir.")
        subprocess.Popen([str(PY_JANELA), str(FERRAMENTAS / "main.py")], cwd=str(FERRAMENTAS))
        self.raiz.destroy()
        return True

    def verificar_atualizacao(self, manual=False):
        """Procura versao nova em segundo plano (a tela nao trava). manual=True: veio do Menu, sempre responde."""

        if APP_INSTALADO:
            em_segundo_plano(self.raiz, buscar_release, lambda r: self._resultado_release(r, manual))
        else:
            em_segundo_plano(self.raiz, lambda: situacao_git(achar_git()), lambda s: self._resultado_git(s, manual))

    def _resultado_release(self, release, manual):
        if release and release["versao"] and eh_mais_nova(release["versao"], VERSAO):
            AvisoAtualizacao(self.raiz, release, self.raiz.destroy)
        elif manual and release:
            messagebox.showinfo("Procurar atualização", f"Você já está com a versão mais nova ({VERSAO}).")
        elif manual:
            webbrowser.open(REPO_URL + "/releases/latest")
            messagebox.showinfo(
                "Procurar atualização",
                f"Você está na versão {VERSAO}.\n\nNão consegui consultar o GitHub sozinho (sem internet, ou o "
                "repositório é privado). Abri a página no navegador: se lá tiver uma versão maior, baixe o "
                '"FamosoZora-Studio-Setup-....exe" e instale por cima.',
            )

    def _resultado_git(self, situacao, manual):
        if situacao and (situacao["atras"] or situacao["mudancas"] or situacao["a_frente"]):
            avisar_codigo_novo(self.raiz, situacao, self._baixar_e_avisar)
        elif manual and situacao:
            messagebox.showinfo("Atualizar", "Esta pasta já está igual ao GitHub. Nada para baixar.")
        elif manual:
            messagebox.showinfo(
                "Atualizar",
                "Não consegui falar com o GitHub por aqui (sem internet ou sem login).\n\n"
                'Use o GitHub Desktop: "Fetch origin" e depois "Pull origin".',
            )

    def _baixar_e_avisar(self):
        if baixar_codigo(self.raiz):
            messagebox.showinfo("Atualizar", "Código atualizado!\n\nFeche e abra o FamosoZora Studio de novo.")

    def atualizar_github(self):
        """Menu > Procurar atualizacao."""
        self.verificar_atualizacao(manual=True)

    # ---------------------------------------------------------- primeira abertura e avisos
    def boas_vindas(self):
        ajustes = ler_ajustes()
        if not ajustes.get("pasta_trabalho"):
            usar = messagebox.askyesno(
                "Bem-vindo ao FamosoZora Studio",
                f"Os vídeos e projetos em produção vão ficar nesta pasta:\n\n{PASTA_CANAL}\n\n"
                "SIM = usar essa pasta\nNÃO = escolher outra (por exemplo, a pasta que você já usa)",
            )
            if not usar and self.mudar_pasta_trabalho():
                return
            salvar_ajustes({"pasta_trabalho": str(PASTA_CANAL)})
            preparar_pasta_trabalho()
            self.atualizar()
        if ajustes.get("ultima_versao_vista") != VERSAO:
            salvar_ajustes({"ultima_versao_vista": VERSAO})
            if ajustes.get("ultima_versao_vista"):  # atualizou: mostra o que mudou
                self.novidades()
        if APP_INSTALADO and tem_nvidia() and not gpu_baixada() and not ajustes.get("perguntou_gpu"):
            salvar_ajustes({"perguntou_gpu": True})
            if messagebox.askyesno(
                "Placa de vídeo NVIDIA encontrada",
                "Quer ativar a placa de vídeo para transcrever MUITO mais rápido?\n\n"
                "Vai baixar cerca de 1 GB (só uma vez).",
            ):
                self.instalar()

    # ---------------------------------------------------------- utilidades
    def copiar(self, texto: str):
        self.raiz.clipboard_clear()
        self.raiz.clipboard_append(texto)
        self.raiz.update()

    def rodar(self):
        self.raiz.mainloop()


def baixar_codigo(parent=None) -> bool:
    """Modo desenvolvedor: git pull da main (so avanca, nunca mistura). Devolve True se baixou."""
    git = achar_git()
    if not git:
        messagebox.showinfo(
            "Atualizar",
            'Não achei o Git.\n\nAbra o GitHub Desktop e clique em "Fetch origin" e depois em "Pull origin".',
            parent=parent,
        )
        return False
    try:
        r = subprocess.run(
            [git, "-C", str(PASTA_APP), "pull", "--ff-only"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as e:
        messagebox.showerror("Atualizar", f"Não consegui atualizar:\n{e}", parent=parent)
        return False
    if r.returncode != 0:
        saida = (r.stdout + "\n" + r.stderr).strip()
        messagebox.showerror(
            "Atualizar",
            "Não consegui atualizar pelo Studio.\n"
            'Use o GitHub Desktop: "Fetch origin" → "Pull origin".\n\n' + saida[-800:],
            parent=parent,
        )
        return False
    return True


def sincronizar_antes_de_abrir():
    """Modo desenvolvedor: antes de abrir, confere se o GitHub tem codigo novo (de outro PC) ou se ha
    alteracoes daqui que ainda nao foram para o GitHub. Assim voce nao edita uma versao velha."""
    if APP_INSTALADO or not ler_ajustes().get("verificar_atualizacoes", True):
        return
    situacao = situacao_git(achar_git())
    if not situacao or not (situacao["atras"] or situacao["mudancas"] or situacao["a_frente"]):
        return
    raiz = tk.Tk()
    raiz.withdraw()
    baixou = []
    avisar_codigo_novo(raiz, situacao, lambda: baixou.append(baixar_codigo(raiz)))
    raiz.destroy()
    if any(baixou):  # o codigo mudou: abre o Studio de novo, ja com o codigo novo
        messagebox.showinfo("Atualizar", "Código novo baixado! O Studio vai abrir com ele.")
        subprocess.Popen([str(PY_JANELA), str(FERRAMENTAS / "main.py")], cwd=str(FERRAMENTAS))
        raise SystemExit(0)


def abrir_studio():
    """Abre a janela principal (chamado pelo main.py)."""
    try:
        sincronizar_antes_de_abrir()
        if ler_ajustes().get("pasta_trabalho"):  # 1a vez: o Studio pergunta qual pasta usar
            preparar_pasta_trabalho()
        Studio().rodar()
    except SystemExit:
        pass
    except Exception as e:
        import traceback

        traceback.print_exc()
        registrar("erro ao abrir o Studio", e)
        try:
            messagebox.showerror("FamosoZora Studio - erro", f"{e}\n\nTire um print e mande pro Claude.")
        except Exception:
            pass


if __name__ == "__main__":
    abrir_studio()

# Tela "Tarefa": no lugar da janela preta (console) do Windows. Desde a 1.9.2, transcrever, gerar Shorts, renderizar
# um Short, gerar o episodio etc. rodam ESCONDIDOS e a saida aparece aqui, dentro do Studio:
#   - o texto que o script escreve (com as linhas de andamento "\r ... 45%" atualizando no lugar);
#   - a barra com a % (le "xx%" e "[n/total]" da saida) e o titulo em "Abertas agora" mostra a % tambem;
#   - quando o script pergunta algo (input), a tela vem para a frente e aparece a caixa para responder;
#   - "Parar" encerra; no fim avisa no canto (pronto ou erro) e a tela pode ser fechada com Voltar.
# A tela abre "por tras": quem estava na frente (o editor, por exemplo) continua na frente.
import os
import re
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk

from interface import tema
from interface.telas import TelaInterna
from nucleo.registro import registrar

SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)
NOMES = {"nucleo.transcrever": "Transcrever", "shorts.gerar_shorts": "Gerar Shorts",
         "videos_longos.editar_episodio": "Gerar o episódio", "nucleo.ativar_gpu": "Ativar a placa de vídeo"}  # fmt: skip
RE_PCT = re.compile(r"(\d{1,3}(?:[.,]\d)?)\s?%")
RE_FRACAO = re.compile(r"\[(\d+)\s*/\s*(\d+)\]")
_RODANDO = []  # tarefas que ainda nao terminaram (o Studio pergunta antes de fechar e para todas)


def rodando() -> list:
    """As tarefas que ainda estao rodando agora."""
    return [t for t in _RODANDO if t.fim is None and t.proc.poll() is None]


def nome_da_tarefa(modulo: str, args) -> str:
    nome = NOMES.get(modulo, modulo.split(".")[-1].replace("_", " ").capitalize())
    if modulo == "shorts.gerar_shorts" and "--so" in args:
        k = list(args).index("--so")
        if k + 1 < len(args):
            nome = f"Renderizar o Short {args[k + 1]}"
    return nome


class TelaTarefa:
    def __init__(self, studio, cmd: list, nome: str, env: dict, cwd: str):
        self.studio = studio
        self.nome = nome
        self.fim = None  # codigo de saida quando terminar
        self._chegou = time.monotonic()  # quando chegou texto pela ultima vez
        self._resto = ""
        self._pedacos = []  # texto que chegou do processo (a linha de leitura poe aqui; a tela tira)
        self._trava = threading.Lock()
        nav = studio.navegacao
        antes = nav.visivel
        self.jan = TelaInterna(studio)
        self.jan.title(f"⏳ {nome}")
        self.jan.protocol("WM_DELETE_WINDOW", self.fechar)
        self._montar()
        if antes is not None:  # abre por tras: quem estava na frente continua
            nav.mostrar(antes)
        elif studio.navegacao.visivel is self.jan:
            nav.esconder(self.jan)
            studio.mostrar(studio.tela_atual or "inicio")
        env = dict(env, PYTHONUNBUFFERED="1")
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     env=env, cwd=cwd, creationflags=SEM_JANELA)  # fmt: skip
        _RODANDO.append(self)
        threading.Thread(target=self._ler, daemon=True).start()
        studio.notificar(f"{nome}: rodando (andamento em \"Abertas agora\", à esquerda).", "info", 4)
        self.jan.after(150, self._atualizar)

    # ------------------------------------------------ tela
    def _montar(self):
        j = self.jan
        topo = tk.Frame(j, bg=tema.FUNDO)
        topo.pack(fill="x", padx=16, pady=(12, 6))
        self.lbl = tk.Label(topo, text=f"{self.nome}: rodando...", bg=tema.FUNDO, fg=tema.TEXTO,
                            font=tema.F_TEXTO_NEGRITO, anchor="w")  # fmt: skip
        self.lbl.pack(side="left", fill="x", expand=True)
        self.btn_parar = ttk.Button(topo, text="⏹ Parar", command=self.parar)
        self.btn_parar.pack(side="right")
        self.barra = ttk.Progressbar(j, mode="indeterminate", maximum=100)
        self.barra.pack(fill="x", padx=16)
        self.barra.start(30)
        quadro = tk.Frame(j, bg=tema.FUNDO)
        quadro.pack(fill="both", expand=True, padx=16, pady=8)
        self.texto = tk.Text(quadro, bg="#0c0c0c", fg="#d8d8d8", insertbackground="#d8d8d8", font=("Consolas", 10),
                             relief="flat", wrap="word", state="disabled")  # fmt: skip
        rolagem = ttk.Scrollbar(quadro, command=self.texto.yview)
        self.texto.configure(yscrollcommand=rolagem.set)
        rolagem.pack(side="right", fill="y")
        self.texto.pack(side="left", fill="both", expand=True)
        self.caixa_resposta = tk.Frame(j, bg=tema.FUNDO)
        tk.Label(self.caixa_resposta, text="O programa perguntou algo (veja acima). Resposta:", bg=tema.FUNDO,
                 fg=tema.AMARELO, font=tema.F_TEXTO).pack(side="left")  # fmt: skip
        self.resposta = ttk.Entry(self.caixa_resposta, width=30)
        self.resposta.pack(side="left", padx=8)
        self.resposta.bind("<Return>", lambda e: self.responder())
        ttk.Button(self.caixa_resposta, text="Enviar", command=self.responder).pack(side="left")

    # ------------------------------------------------ processo
    def _ler(self):
        """Linha separada: le a saida do processo aos pedacos (a pergunta do input nao termina com Enter)."""
        try:
            leitor = self.proc.stdout
            while True:
                bloco = leitor.read1(4096) if hasattr(leitor, "read1") else os.read(leitor.fileno(), 4096)
                if not bloco:
                    break
                with self._trava:
                    self._pedacos.append(bloco)
        except Exception as e:
            registrar(f"tarefa {self.nome}: lendo a saída", e)
        self.proc.wait()
        self.fim = self.proc.returncode

    def _atualizar(self):
        try:
            if not self.jan.winfo_exists():
                return
        except tk.TclError:
            return
        with self._trava:
            dados = b"".join(self._pedacos)
            self._pedacos.clear()
        if dados:
            self._escrever(dados.decode("utf-8", errors="replace"))
        if self.fim is not None and not self._pedacos:
            self._terminou()
            return
        if not dados and time.monotonic() - self._chegou > 0.8 and self._parece_pergunta():
            self._perguntou()
        self.jan.after(150, self._atualizar)

    def _escrever(self, texto: str):
        texto = self._resto + texto
        self._resto = ""
        if texto.endswith("\r"):  # pode ser metade de um "\r\n" (Windows): espera o proximo pedaco
            self._resto, texto = "\r", texto[:-1]
        t = self.texto
        t.configure(state="normal")
        for parte in re.split(r"(\r\n|\n|\r)", texto):
            if parte == "\r":  # volta ao comeco da linha: a proxima parte escreve por cima
                t.delete("end-1c linestart", "end-1c")
            elif parte in ("\n", "\r\n"):
                t.insert("end", "\n")
            elif parte:
                t.insert("end", parte)
        linhas = int(t.index("end-1c").split(".")[0])
        if linhas > 3000:  # nao deixa crescer sem fim
            t.delete("1.0", f"{linhas - 3000}.0")
        t.configure(state="disabled")
        t.see("end")
        self._ler_andamento()
        self._chegou = time.monotonic()

    def _ler_andamento(self):
        ultimas = self.texto.get("end-4l", "end")
        pct = None
        achados = RE_PCT.findall(ultimas)
        if achados:
            pct = float(achados[-1].replace(",", "."))
        else:
            fr = RE_FRACAO.findall(ultimas)
            if fr:
                n, total = int(fr[-1][0]), int(fr[-1][1])
                pct = 100 * max(0, n - 1) / total if total else None
        if pct is not None and 0 <= pct <= 100:
            if str(self.barra.cget("mode")) != "determinate":
                self.barra.stop()
                self.barra.configure(mode="determinate")
            self.barra["value"] = pct
            self.jan.title(f"⏳ {self.nome} {pct:.0f}%")

    def _parece_pergunta(self) -> bool:
        """input() esperando: a ultima linha termina em ": " ou "? " e nada mais chegou faz quase 1 s."""
        ultima = self.texto.get("end-1c linestart", "end-1c")
        return ultima.endswith(" ") and ultima.rstrip().endswith((":", "?"))

    def _perguntou(self):
        if not self.caixa_resposta.winfo_ismapped():
            self.caixa_resposta.pack(fill="x", padx=16, pady=(0, 12))
            self.studio.navegacao.mostrar(self.jan)
            self.studio.notificar(f"{self.nome}: o programa está perguntando algo.", "aviso", 6)
        self.resposta.focus_set()

    def responder(self):
        texto = self.resposta.get()
        self.resposta.delete(0, "end")
        self.caixa_resposta.pack_forget()
        try:
            self.proc.stdin.write((texto + "\n").encode("utf-8"))
            self.proc.stdin.flush()
        except OSError:
            pass
        self._escrever(texto + "\n")

    def _terminou(self):
        if self in _RODANDO:
            _RODANDO.remove(self)
        self.barra.stop()
        self.btn_parar.configure(state="disabled")
        self.caixa_resposta.pack_forget()
        if self.fim == 0:
            self.barra.configure(mode="determinate")
            self.barra["value"] = 100
            self.lbl.configure(text=f"{self.nome}: pronto ✔", fg=tema.VERDE)
            self.jan.title(f"✔ {self.nome}")
            self.studio.notificar(f"{self.nome}: pronto.", "ok", 5)
        else:
            self.lbl.configure(text=f"{self.nome}: deu erro (veja o texto abaixo)", fg=tema.VERMELHO)
            self.jan.title(f"✖ {self.nome}")
            self.studio.notificar(f"{self.nome}: deu erro. Abra em \"Abertas agora\" para ver.", "erro", 8)
        try:
            self.studio.pedir_atualizacao()
        except Exception:
            pass

    def parar(self):
        """Encerra a tarefa E os programas que ela abriu (o ffmpeg do episodio, por exemplo). So o terminate()
        deixava o ffmpeg rodando escondido no Windows, segurando o arquivo do pedaco que estava fazendo."""
        if self.fim is None:
            if os.name == "nt":
                try:
                    subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.proc.pid)], capture_output=True,
                                   timeout=15, creationflags=SEM_JANELA)  # fmt: skip
                except (OSError, subprocess.SubprocessError):
                    pass
            try:
                self.proc.terminate()
            except OSError:
                pass

    def fechar(self):
        if self.fim is None:
            from tkinter import messagebox

            if not messagebox.askyesno("Tarefa", f"\"{self.nome}\" ainda está rodando.\n\nParar e fechar?",
                                       parent=self.jan):  # fmt: skip
                return
            self.parar()
        self.jan.destroy()

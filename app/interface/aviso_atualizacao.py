# Aviso de versao nova: uma janela pequena com o numero da versao, as novidades (patch notes)
# e os botoes "Atualizar agora" e "Depois". "Atualizar agora" baixa o instalador e chama ao_instalar(arquivo):
# o Studio fecha, instala sozinho (so aparece a barrinha de progresso) e abre de novo, sem clicar em mais nada.
# Com a atualizacao automatica ligada (Configuracoes), esta janela so aparece pelo "Procurar atualização":
# ao abrir, o Studio baixa a versao nova sozinho e instala quando voce fecha (janela_principal.baixar_atualizacao).
# No modo desenvolvedor, o aviso fala de codigo novo no GitHub (de outro PC) em vez de instalador.
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk

from interface import tema
from interface.utilidades import COR_DESTAQUE, COR_FUNDO, COR_TEXTO, em_segundo_plano
from nucleo.atualizacao import baixar_instalador
from nucleo.registro import registrar
from versao import VERSAO


def _limpar_markdown(texto: str) -> str:
    linhas = []
    for linha in texto.replace("\r\n", "\n").splitlines():
        linha = linha.replace("**", "").replace("`", "")
        if linha.startswith("#"):
            linha = linha.lstrip("#").strip().upper()
        elif linha.lstrip().startswith("- "):
            linha = linha.replace("- ", "• ", 1)
        linhas.append(linha)
    return "\n".join(linhas).strip()


class AvisoAtualizacao:
    """Janela do app instalado: versao nova no GitHub."""

    def __init__(self, raiz, release: dict, ao_instalar):
        self.raiz = raiz
        self.release = release
        self.ao_instalar = ao_instalar
        self.jan = tk.Toplevel(raiz)
        self.jan.title("Atualização disponível")
        self.jan.geometry("640x520")
        self.jan.configure(bg=COR_FUNDO)
        self.jan.transient(raiz)

        tk.Label(
            self.jan, text=f"Versão nova: {release['versao']}", bg=COR_FUNDO, fg=COR_DESTAQUE,
            font=("Segoe UI", 15, "bold"), anchor="w",
        ).pack(fill="x", padx=16, pady=(14, 0))  # fmt: skip
        tk.Label(
            self.jan, text=f"Você está na {VERSAO}. Seus vídeos, Shorts e configurações não são apagados.\n"
            '"Atualizar agora" fecha o Studio, instala sozinho e abre de novo (sem precisar clicar em nada).',
            bg=COR_FUNDO, fg=tema.TEXTO_2, font=("Segoe UI", 10), anchor="w", justify="left",
        ).pack(fill="x", padx=16, pady=(2, 8))  # fmt: skip

        self.lbl = tk.Label(self.jan, text="", bg=COR_FUNDO, fg=tema.TEXTO_2, font=("Segoe UI", 10), anchor="w")
        barra = tk.Frame(self.jan, bg=COR_FUNDO)
        barra.pack(side="bottom", fill="x", padx=16, pady=12)
        self.btn = ttk.Button(barra, text="Atualizar agora", style="Passo.TButton", command=self.atualizar)
        self.btn.pack(side="right")
        ttk.Button(barra, text="Depois", style="Extra.TButton", command=self.jan.destroy).pack(side="right", padx=8)
        self.lbl.pack(side="bottom", fill="x", padx=16, pady=(8, 0))  # botoes primeiro: o texto nunca os esconde
        texto = tk.Text(self.jan, wrap="word", bg=tema.CAMPO, fg=COR_TEXTO, font=("Segoe UI", 10), relief="flat",
                        padx=12, pady=10)  # fmt: skip
        texto.insert("1.0", _limpar_markdown(release.get("notas") or "(sem notas desta versão)"))
        texto.configure(state="disabled")
        texto.pack(fill="both", expand=True, padx=16)

        if not release.get("url_instalador"):
            self.btn.configure(text="Abrir a página da versão", command=lambda: webbrowser.open(release["pagina"]))

    def atualizar(self):
        self.btn.configure(state="disabled")
        self.lbl.configure(text="Baixando o instalador...")

        andamento = {"texto": "Baixando o instalador..."}

        def progresso(feito, total):  # roda na linha do download: so guarda o texto
            andamento["texto"] = f"Baixando o instalador... {feito / 1e6:.0f} MB" + (
                f" de {total / 1e6:.0f} MB" if total else ""
            )

        def mostrar_andamento():  # roda na tela
            if self.jan.winfo_exists() and str(self.btn["state"]) == "disabled":
                self.lbl.configure(text=andamento["texto"])
                self.jan.after(300, mostrar_andamento)

        def terminou(resultado):
            if isinstance(resultado, Exception):
                registrar("atualizacao: download do instalador falhou", resultado)
                self._falhou(resultado)
            else:
                self._instalar(resultado)

        mostrar_andamento()
        em_segundo_plano(self.raiz, lambda: baixar_instalador(self.release, progresso), terminou)

    def _falhou(self, erro):
        self.lbl.configure(text="")
        self.btn.configure(state="normal")
        messagebox.showerror(
            "Atualização",
            f"Não consegui baixar o instalador:\n{erro}\n\nVou abrir a página da versão no navegador.",
            parent=self.jan,
        )
        webbrowser.open(self.release["pagina"])

    def _instalar(self, arquivo):
        self.lbl.configure(text="Instalando: o Studio fecha e abre de novo sozinho...")
        if not self.ao_instalar(arquivo):  # o instalador troca os arquivos do programa: o Studio precisa fechar
            self.lbl.configure(text="")
            self.btn.configure(state="normal")


def avisar_codigo_novo(raiz, situacao: dict, ao_baixar):
    """Modo desenvolvedor: avisa que o GitHub tem codigo novo (de outro PC) e/ou que ha mudancas nao enviadas."""
    partes = []
    if situacao["atras"]:
        partes.append(
            f"Tem código novo no GitHub ({situacao['atras']} commit(s)), provavelmente feito em outro PC.\n"
            "Baixe antes de mexer, para não editar uma versão velha e dar conflito."
        )
    if situacao["mudancas"] or situacao["a_frente"]:
        detalhes = []
        if situacao["mudancas"]:
            detalhes.append(f"{situacao['mudancas']} arquivo(s) mudado(s) sem Commit")
        if situacao["a_frente"]:
            detalhes.append(f"{situacao['a_frente']} commit(s) sem Push")
        partes.append(
            "Você tem alterações que ainda não foram para o GitHub (" + ", ".join(detalhes) + ").\n"
            "No GitHub Desktop: Commit e depois Push."
        )
    if situacao["ramo"] not in ("main", "HEAD"):
        partes.append(f'(Você está no ramo "{situacao["ramo"]}", não na main.)')
    if not partes:
        return
    if situacao["atras"] and not situacao["mudancas"]:
        if messagebox.askyesno("Código novo no GitHub", "\n\n".join(partes) + "\n\nBaixar agora (Pull)?", parent=raiz):
            ao_baixar()
        return
    messagebox.showinfo("Modo desenvolvedor", "\n\n".join(partes), parent=raiz)

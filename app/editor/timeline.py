# Timeline do editor (um Canvas do Tkinter), com as faixas, de cima para baixo:
#   regua de tempo | miniaturas | onda de som | SUGESTOES (vermelho = silencio, cinza = sem jogo, roxo = sem acao,
#   amarelo = duvida/papo fora; laranja = corte seu) | RESULTADO (verde = fica, riscado = sai, azul = acelera)
#   | marcadores (⭐ Short, 📑 capitulo, 📝 nota)
# Ctrl + roda do mouse = zoom; roda sozinha = anda para os lados; clicar = pular para o ponto; clicar num trecho =
# selecionar; arrastar a borda de um trecho = ajustar (com ima; segurando Alt, sem ima).
import tkinter as tk

from interface import tema

CORES = {"silencio": "#D9534F", "sem_jogo": "#8A8A8A", "sem_acao": "#9B6BD6", "papo_fora": "#E0B050",
         "duvida": "#E0B050", "manual": "#D97757"}  # fmt: skip
VERDE, SAI, ACELERA, INTRO = "#4F7A3F", "#5A2523", "#3D6E9E", "#2F5F8F"
ICONES = {"short": "⭐", "capitulo": "📑", "nota": "📝"}
ALTURAS = [("regua", 16), ("mini", 46), ("onda", 40), ("sugestoes", 20), ("resultado", 16), ("marcadores", 18)]
PEGA = 5  # pixels perto da borda que contam como "pegar a borda"


class Timeline(tk.Canvas):
    def __init__(self, pai, estado, ao_pular, ao_selecionar, ao_menu=None, ao_mudar=None):
        self.y = {}
        y = 0
        for nome, h in ALTURAS:
            self.y[nome] = (y, y + h)
            y += h + 2
        super().__init__(pai, height=y, bg=tema.CAMPO, highlightthickness=0, cursor="hand2")
        self.estado = estado
        self.ao_pular, self.ao_selecionar, self.ao_menu, self.ao_mudar = ao_pular, ao_selecionar, ao_menu, ao_mudar
        self.ini = estado.inicio
        self.pps = 0.0  # pixels por segundo (0 = ajustar para caber tudo)
        self.onda = b""
        self.onda_ms = 10
        self.mini = None  # (info, funcao que devolve PhotoImage da miniatura de t)
        self.cursor_t = estado.inicio
        self._arrasto = None
        self.bind("<Configure>", lambda e: self.desenhar())
        self.bind("<Button-1>", self._clique)
        self.bind("<B1-Motion>", self._arrastar)
        self.bind("<ButtonRelease-1>", self._soltar)
        self.bind("<Button-3>", self._menu)
        self.bind("<MouseWheel>", self._roda)
        self.bind("<Button-4>", lambda e: self._roda(e, 120))
        self.bind("<Button-5>", lambda e: self._roda(e, -120))
        self.bind("<Motion>", self._passar)

    # ---------------------------------------------------------- escala
    def largura(self) -> int:
        return max(100, self.winfo_width())

    def ajustar_tudo(self):
        self.ini = self.estado.inicio
        self.pps = self.largura() / max(1.0, self.estado.fim - self.estado.inicio)

    def x_de(self, t: float) -> float:
        if self.pps <= 0:
            self.ajustar_tudo()
        return (t - self.ini) * self.pps

    def t_de(self, x: float) -> float:
        if self.pps <= 0:
            self.ajustar_tudo()
        return min(self.estado.fim, max(self.estado.inicio, self.ini + x / self.pps))

    def visivel(self) -> tuple:
        return self.ini, self.ini + self.largura() / max(1e-6, self.pps)

    def zoom(self, fator: float, em_x: float | None = None):
        em_x = self.largura() / 2 if em_x is None else em_x
        t = self.t_de(em_x)
        minimo = self.largura() / max(1.0, self.estado.fim - self.estado.inicio)
        self.pps = min(400.0, max(minimo, self.pps * fator))
        self.ini = t - em_x / self.pps
        self._limitar_vista()
        self.desenhar()

    def _limitar_vista(self):
        largura_t = self.largura() / self.pps
        self.ini = min(max(self.estado.inicio, self.ini), max(self.estado.inicio, self.estado.fim - largura_t))

    def seguir(self, t: float):
        """Mantem o cursor a vista quando o video anda."""
        a, b = self.visivel()
        if not a <= t <= b:
            self.ini = t - (b - a) * 0.1
            self._limitar_vista()
            self.desenhar()

    # ---------------------------------------------------------- desenho
    def desenhar(self):
        self.delete("all")
        if self.pps <= 0:
            self.ajustar_tudo()
        w = self.largura()
        self._regua(w)
        self._miniaturas(w)
        self._onda(w)
        self._sugestoes()
        self._resultado(w)
        self._marcadores()
        self._marcas_io()
        self.mover_cursor(self.cursor_t)

    def _regua(self, w):
        y0, y1 = self.y["regua"]
        a, b = self.visivel()
        passos = (1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600)
        passo = next((p for p in passos if p * self.pps >= 70), 3600)
        t = (int(a // passo) + 1) * passo
        while t < b:
            x = self.x_de(t)
            self.create_line(x, y0 + 10, x, y1, fill=tema.BORDA)
            self.create_text(x + 2, y0 + 1, text=_hms(t), anchor="nw", fill=tema.TEXTO_2, font=tema.F_PEQUENA)
            t += passo

    def _miniaturas(self, w):
        y0, y1 = self.y["mini"]
        if not self.mini:
            self.create_text(6, y0 + 4, text="(miniaturas aparecem depois da análise)", anchor="nw",
                             fill=tema.TEXTO_2, font=tema.F_PEQUENA)  # fmt: skip
            return
        info, imagem_de = self.mini
        a, b = self.visivel()
        passo = max(info["a_cada"], 82 / max(1e-6, self.pps))
        passo = info["a_cada"] * max(1, round(passo / info["a_cada"]))
        t = int(a // passo) * passo
        while t < b:
            img = imagem_de(t)
            if img is not None:
                self.create_image(self.x_de(t), y0, image=img, anchor="nw")
            t += passo

    def _onda(self, w):
        y0, y1 = self.y["onda"]
        meio, alto = (y0 + y1) / 2, (y1 - y0) / 2
        self.create_line(0, meio, w, meio, fill=tema.BORDA)
        if not self.onda:
            return
        n = len(self.onda)
        if getattr(self, "_onda_id", None) is not id(self.onda):  # escala: o pico mais alto da live enche a faixa
            self._onda_id, self._onda_max = id(self.onda), max(8, max(self.onda))
        por_seg = 1000 / self.onda_ms
        base = self.estado_inicio_onda if hasattr(self, "estado_inicio_onda") else 0.0
        pontos = []
        for x in range(0, w, 2):
            ta, tb = self.ini + x / self.pps, self.ini + (x + 2) / self.pps
            ka, kb = int((ta - base) * por_seg), int((tb - base) * por_seg) + 1
            if kb <= 0 or ka >= n:
                continue
            pico = max(self.onda[max(0, ka) : min(n, kb)] or b"\0") / self._onda_max
            pontos.append((x, pico))
        for x, p in pontos:
            h = max(1, p * alto)
            self.create_line(x, meio - h, x, meio + h, fill="#6B8FB3")

    def _sugestoes(self):
        y0, y1 = self.y["sugestoes"]
        a, b = self.visivel()
        sel = self.estado.selecionado
        for k, t in enumerate(self.estado.trechos):
            if t["fim"] < a or t["inicio"] > b:
                continue
            x0, x1 = self.x_de(t["inicio"]), max(self.x_de(t["inicio"]) + 2, self.x_de(t["fim"]))
            cor = CORES["manual"] if t["origem"] == "manual" else CORES.get(t["motivo"], "#888888")
            recusada = t["revisado"] and t["acao"] == "manter"
            pendente = not t["revisado"] and t["origem"] == "auto"
            self.create_rectangle(x0, y0 + 2, x1, y1 - 2, fill="" if recusada else cor, outline=cor,
                                  width=2 if k == sel else 1, dash=(3, 2) if pendente else None,
                                  tags=("trecho", f"t{k}"))  # fmt: skip
            if k == sel:
                self.create_rectangle(x0 - 1, y0, x1 + 1, y1, outline=tema.TEXTO, width=2)
        if self.estado.introducao:
            ia, ib = self.estado.introducao["inicio"], self.estado.introducao["fim"]
            self.create_rectangle(self.x_de(ia), y0, self.x_de(ib), y0 + 4, fill="#6FA8DC", outline="")

    def _resultado(self, w):
        y0, y1 = self.y["resultado"]
        self.create_rectangle(self.x_de(self.estado.inicio), y0, self.x_de(self.estado.fim), y1, fill=VERDE, outline="")
        for a, b, acao, vel in self.estado.resolvidos():
            x0, x1 = self.x_de(a), max(self.x_de(a) + 1, self.x_de(b))
            if x1 < 0 or x0 > w:
                continue
            if acao == "cortar":
                self.create_rectangle(x0, y0, x1, y1, fill=SAI, outline="")
                x = max(0, x0)
                while x < min(w, x1):  # riscado
                    self.create_line(x, y1, min(x1, x + (y1 - y0)), y0, fill="#A04040")
                    x += 8
            else:
                self.create_rectangle(x0, y0, x1, y1, fill=ACELERA, outline="")
                if x1 - x0 > 24:
                    self.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=f"{vel:g}x", fill=tema.TEXTO,
                                     font=tema.F_PEQUENA)  # fmt: skip
        if self.estado.introducao:
            ia, ib = self.estado.introducao["inicio"], self.estado.introducao["fim"]
            self.create_rectangle(self.x_de(ia), y0, self.x_de(ib), y1, outline="#6FA8DC", width=2)
            self.create_text(self.x_de(ia) + 3, y0 + 1, text="INTRO", anchor="nw", fill="#CFE2F3",
                             font=tema.F_PEQUENA)  # fmt: skip
        lim = getattr(self.estado, "limites", None)
        if lim:  # Short: fora do corte fica escuro
            for xa, xb in ((self.x_de(self.estado.inicio), self.x_de(lim[0])), (self.x_de(lim[1]),
                                                                                self.x_de(self.estado.fim))):  # fmt: skip
                if xb > xa:
                    self.create_rectangle(xa, 0, xb, self.y["marcadores"][1], fill="#000000", stipple="gray50",
                                          outline="")  # fmt: skip
            for t in lim:
                x = self.x_de(t)
                self.create_line(x, 0, x, self.y["marcadores"][1], fill=tema.LARANJA, width=3)

    def _marcadores(self):
        y0, y1 = self.y["marcadores"]
        for m in self.estado.marcadores:
            x = self.x_de(m["tempo"])
            self.create_text(x, y0 + 1, text=ICONES.get(m["tipo"], "•"), anchor="n", fill=tema.AMARELO,
                             font=tema.F_PEQUENA)  # fmt: skip

    def _marcas_io(self):
        for t, nome in ((self.estado.marca_in, "I"), (self.estado.marca_out, "O")):
            if t is not None:
                x = self.x_de(t)
                self.create_line(x, 0, x, self.y["marcadores"][1], fill="#FFD966", dash=(2, 2))
                self.create_text(x + 2, 0, text=nome, anchor="nw", fill="#FFD966", font=tema.F_TEXTO_NEGRITO)

    def mover_cursor(self, t: float):
        self.cursor_t = t
        self.delete("cursor")
        x = self.x_de(t)
        self.create_line(x, 0, x, self.y["marcadores"][1], fill=tema.LARANJA, width=2, tags="cursor")

    # ---------------------------------------------------------- mouse
    def _borda_perto(self, x: float):
        """(posicao do trecho, 'inicio'|'fim') se o mouse esta numa borda de trecho, ou ('limite', lado)."""
        lim = getattr(self.estado, "limites", None)
        if lim:
            for lado, t in zip(("inicio", "fim"), lim):
                if abs(self.x_de(t) - x) <= PEGA:
                    return ("limite", lado)
        k = self.estado.selecionado
        candidatos = ([k] if k is not None else []) + list(range(len(self.estado.trechos)))
        for k in candidatos:
            if k is None or k >= len(self.estado.trechos):
                continue
            t = self.estado.trechos[k]
            if abs(self.x_de(t["inicio"]) - x) <= PEGA:
                return (k, "inicio")
            if abs(self.x_de(t["fim"]) - x) <= PEGA:
                return (k, "fim")
        return None

    def _passar(self, e):
        na_faixa = self.y["sugestoes"][0] <= e.y <= self.y["resultado"][1] or getattr(self.estado, "limites", None)
        self.configure(cursor="sb_h_double_arrow" if na_faixa and self._borda_perto(e.x) else "hand2")

    def _clique(self, e):
        self.focus_set()
        y_sug = self.y["sugestoes"]
        borda = self._borda_perto(e.x) if (y_sug[0] <= e.y <= self.y["resultado"][1]
                                           or getattr(self.estado, "limites", None)) else None  # fmt: skip
        if borda:
            self._arrasto = borda
            return
        if y_sug[0] <= e.y <= y_sug[1]:
            k = self.estado.trecho_em(self.t_de(e.x))
            self.ao_selecionar(k)
        self.ao_pular(self.t_de(e.x))

    def _arrastar(self, e):
        if not self._arrasto:
            if self.y["regua"][0] <= e.y <= self.y["onda"][1]:
                self.ao_pular(self.t_de(e.x))  # arrastar na regua/miniaturas = procurar
            return
        sem_ima = bool(e.state & 0x20000) or bool(e.state & 0x0008)  # Alt (Windows / Linux)
        k, lado = self._arrasto
        if k == "limite":
            self.estado.mover_limite(lado, self.t_de(e.x), com_ima=not sem_ima)
        else:
            self.estado.mover_borda(k, lado, self.t_de(e.x), com_ima=not sem_ima)
        self.desenhar()

    def _soltar(self, e):
        if self._arrasto:
            self._arrasto = None
            self.estado.fim_do_arrasto()
            if self.ao_mudar:
                self.ao_mudar()

    def _menu(self, e):
        t = self.t_de(e.x)
        k = self.estado.trecho_em(t)
        if k is not None:
            self.ao_selecionar(k)
        if self.ao_menu:
            self.ao_menu(e, t, k)

    def _roda(self, e, delta=None):
        delta = delta if delta is not None else e.delta
        if e.state & 0x0004:  # Ctrl: zoom no ponto do mouse
            self.zoom(1.25 if delta > 0 else 0.8, e.x)
        else:
            a, b = self.visivel()
            self.ini -= (b - a) * 0.1 * (1 if delta > 0 else -1)
            self._limitar_vista()
            self.desenhar()


def _hms(t: float) -> str:
    t = int(t)
    h, m, s = t // 3600, t % 3600 // 60, t % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

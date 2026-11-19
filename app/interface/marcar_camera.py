# Ferramenta visual: marque onde fica a CAMERA e qual parte da GAMEPLAY usar
# no layout "camera" (camera em cima, gameplay embaixo). Salva no config.json.
import subprocess
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from interface import tema
from nucleo.comum import DADOS_APP, PASTA_SHORTS, PASTA_VIDEOS, carregar_config, escolher_arquivo, salvar_config
from nucleo.video import SEM_JANELA, achar_programa, dimensoes_video, duracao_video, filtro_layout

LARG, ALT = 1080, 1920
MAX_W, MAX_H = 1280, 720
ALTURA_CAMERA = 600  # padrao do canal: camera 1080x600 em cima, jogo 1080x1320 embaixo
TMP = Path(tempfile.gettempdir())
PASTA_IMAGENS = DADOS_APP / "marcar_camera"  # imagens de conferencia (fora do GitHub)


class Marcador:
    def __init__(self, video: Path):
        self.video = video
        self.cfg = carregar_config()
        self.src_w, self.src_h = dimensoes_video(video)
        self.ffmpeg = achar_programa("ffmpeg")
        dur = duracao_video(video)
        self.instante = dur * 0.3 if dur > 0 else 10

        # extrai um quadro do video
        self.quadro = TMP / "famosozora_quadro.png"
        esc = min(MAX_W / self.src_w, MAX_H / self.src_h, 1.0)
        self.dw, self.dh = int(self.src_w * esc) // 2 * 2, int(self.src_h * esc) // 2 * 2
        subprocess.run(
            [
                self.ffmpeg,
                "-v",
                "error",
                "-y",
                "-ss",
                f"{self.instante:.2f}",
                "-i",
                str(video),
                "-frames:v",
                "1",
                "-vf",
                f"scale={self.dw}:{self.dh}",
                str(self.quadro),
            ],
            check=True,
            creationflags=SEM_JANELA,
        )

        self.etapas = [
            [
                "CAMERA",
                LARG / ALTURA_CAMERA,
                "#00e5ff",
                "PASSO 1 de 2: arraste com o mouse um retangulo BEM EM CIMA da sua CAMERA (o seu rosto).\n"
                "O formato e fixo (padrao do canal). Se errar, e so arrastar de novo.",
            ],
            [
                "GAMEPLAY",
                LARG / (ALT - ALTURA_CAMERA),
                "#ffd400",
                "PASSO 2 de 2: arraste em volta da parte da GAMEPLAY. Ela vai ocupar o resto da tela.\n"
                "O retangulo ja tem o formato do espaco que sobrou. Ou clique em 'Usar o centro da tela'.",
            ],
        ]
        self.altura_camera = ALTURA_CAMERA
        self.etapa = 0
        self.areas = {}
        self.ret = None
        self.inicio = None

        self.raiz = tk.Tk()
        self.raiz.title("Marcar camera e gameplay - FamosoZora")
        self.raiz.attributes("-topmost", True)
        self.raiz.after(500, lambda: self.raiz.attributes("-topmost", False))
        self.lbl = tk.Label(self.raiz, font=("Segoe UI", 11), justify="left", anchor="w")
        self.lbl.pack(fill="x", padx=10, pady=8)
        self.img = tk.PhotoImage(file=str(self.quadro))
        self.canvas = tk.Canvas(self.raiz, width=self.dw, height=self.dh, cursor="crosshair", highlightthickness=0)
        self.canvas.pack(padx=10)
        self.canvas.create_image(0, 0, anchor="nw", image=self.img)
        barra = tk.Frame(self.raiz)
        barra.pack(fill="x", padx=10, pady=10)
        self.btn_ok = tk.Button(
            barra,
            text="Confirmar  >",
            font=("Segoe UI", 11, "bold"),
            width=16,
            bg=tema.VERDE,
            fg="white",
            command=self.confirmar,
            state="disabled",
        )
        self.btn_ok.pack(side="right")
        self.btn_centro = tk.Button(
            barra, text="Usar o centro da tela", font=("Segoe UI", 10), command=self.usar_centro
        )
        self.btn_voltar = tk.Button(barra, text="<  Voltar", font=("Segoe UI", 10), command=self.voltar)

        self.canvas.bind("<ButtonPress-1>", self.apertar)
        self.canvas.bind("<B1-Motion>", self.arrastar)
        self.canvas.bind("<ButtonRelease-1>", self.soltar)
        self.mostrar_etapa()

    # ---------------------------------------------------- etapas
    def mostrar_etapa(self):
        nome, _, _, texto = self.etapas[self.etapa]
        self.lbl.config(text=texto)
        self.canvas.delete("ret")
        self.ret = None
        self.btn_ok.config(state="disabled")
        if self.etapa == 1:
            self.btn_centro.pack(side="right", padx=8)
            self.btn_voltar.pack(side="left")
            # mostra a camera ja marcada, apagadinha
            x, y, w, h = self.areas["CAMERA"]
            self.canvas.create_rectangle(
                x * self.dw,
                y * self.dh,
                (x + w) * self.dw,
                (y + h) * self.dh,
                outline="#00e5ff",
                dash=(4, 4),
                width=2,
                tags="ret_cam",
            )
        else:
            self.btn_centro.pack_forget()
            self.btn_voltar.pack_forget()
            self.canvas.delete("ret_cam")

    def voltar(self):
        self.etapa = 0
        self.mostrar_etapa()

    # ---------------------------------------------------- desenho com proporcao fixa
    def apertar(self, e):
        self.inicio = (min(max(e.x, 0), self.dw), min(max(e.y, 0), self.dh))
        self.canvas.delete("ret")

    def arrastar(self, e):
        if not self.inicio:
            return
        _, prop, cor, _ = self.etapas[self.etapa]
        x0, y0 = self.inicio
        sx = 1 if e.x >= x0 else -1
        sy = 1 if e.y >= y0 else -1
        max_w = (self.dw - x0) if sx > 0 else x0
        max_h = (self.dh - y0) if sy > 0 else y0
        w = min(abs(e.x - x0), max_w)
        if prop is None:  # formato livre
            h = min(abs(e.y - y0), max_h)
        else:  # formato fixo
            h = w / prop
            if h > max_h:
                h = max_h
                w = h * prop
        x1, y1 = x0 + sx * w, y0 + sy * h
        self.canvas.delete("ret")
        self.canvas.create_rectangle(x0, y0, x1, y1, outline=cor, width=3, tags="ret")
        self.ret = (min(x0, x1), min(y0, y1), w, h)

    def soltar(self, e):
        self.inicio = None
        if self.ret and self.ret[2] > 20 and self.ret[3] > 20:
            self.btn_ok.config(state="normal")

    # ---------------------------------------------------- confirmar
    def usar_centro(self):
        self.areas["GAMEPLAY"] = None
        self.previa()

    def confirmar(self):
        if not self.ret:
            return
        x, y, w, h = self.ret
        nome = self.etapas[self.etapa][0]
        self.areas[nome] = [round(x / self.dw, 4), round(y / self.dh, 4), round(w / self.dw, 4), round(h / self.dh, 4)]
        if self.etapa == 0:
            self.etapa = 1
            self.mostrar_etapa()
        else:
            self.previa()

    def previa(self):
        cfg = dict(self.cfg)
        cfg.update(
            {
                "layout": "camera",
                "camera_area": self.areas["CAMERA"],
                "gameplay_area": self.areas.get("GAMEPLAY"),
                "altura_camera": self.altura_camera,
            }
        )
        arq = TMP / "famosozora_previa.png"
        filtro = filtro_layout(cfg, self.src_w, self.src_h, LARG, ALT) + ",scale=405:720[v]"
        r = subprocess.run(
            [
                self.ffmpeg,
                "-v",
                "error",
                "-y",
                "-ss",
                f"{self.instante:.2f}",
                "-i",
                str(self.video),
                "-frames:v",
                "1",
                "-filter_complex",
                filtro,
                "-map",
                "[v]",
                str(arq),
            ],
            capture_output=True,
            text=True,
            creationflags=SEM_JANELA,
        )
        if r.returncode != 0:
            messagebox.showerror("Erro", "Nao consegui gerar a previa:\n" + r.stderr[-400:])
            return

        jan = tk.Toplevel(self.raiz)
        jan.title("Previa do Short")
        jan.transient(self.raiz)
        jan.grab_set()
        foto = tk.PhotoImage(file=str(arq))
        jan.foto = foto
        tk.Label(jan, text="Assim vai ficar o Short. Gostou?", font=("Segoe UI", 11, "bold")).pack(pady=6)
        tk.Label(jan, image=foto).pack(padx=10)
        bar = tk.Frame(jan)
        bar.pack(fill="x", padx=10, pady=10)

        def salvar():
            try:
                PASTA_IMAGENS.mkdir(parents=True, exist_ok=True)
                cx, cy, cw, ch = self.areas["CAMERA"]
                caixas = [f"drawbox=x=iw*{cx}:y=ih*{cy}:w=iw*{cw}:h=ih*{ch}:color=cyan:t=6"]
                if self.areas.get("GAMEPLAY"):
                    gx, gy, gw, gh = self.areas["GAMEPLAY"]
                    caixas.append(f"drawbox=x=iw*{gx}:y=ih*{gy}:w=iw*{gw}:h=ih*{gh}:color=yellow:t=6")
                subprocess.run(
                    [
                        self.ffmpeg,
                        "-v",
                        "error",
                        "-y",
                        "-ss",
                        f"{self.instante:.2f}",
                        "-i",
                        str(self.video),
                        "-frames:v",
                        "1",
                        "-vf",
                        ",".join(caixas) + ",scale=1280:-2",
                        str(PASTA_IMAGENS / "marcacao_camera.png"),
                    ],
                    creationflags=SEM_JANELA,
                )
                import shutil

                shutil.copy(arq, PASTA_IMAGENS / "previa_short.png")
            except Exception:
                pass
            salvar_config(
                {
                    "layout": "camera",
                    "camera_area": self.areas["CAMERA"],
                    "gameplay_area": self.areas.get("GAMEPLAY"),
                    "altura_camera": self.altura_camera,
                }
            )
            messagebox.showinfo(
                "Salvo!",
                "Pronto! Os proximos Shorts vao sair com a camera em cima.\n\n"
                "Para refazer os Shorts que ja existem: 3 - Gerar Shorts e escolha SIM.",
            )
            self.raiz.destroy()

        def refazer():
            jan.destroy()
            self.etapa = 0
            self.areas = {}
            self.mostrar_etapa()

        tk.Button(
            bar, text="Salvar", font=("Segoe UI", 11, "bold"), bg=tema.VERDE, fg="white", width=12, command=salvar
        ).pack(side="right")
        tk.Button(bar, text="Refazer", font=("Segoe UI", 10), command=refazer).pack(side="left")

    def rodar(self):
        self.raiz.mainloop()


def main():
    if len(sys.argv) > 1:
        video = Path(sys.argv[1])
    else:
        print("Escolha um video gravado com a camera na janela que abriu...")
        video = escolher_arquivo(
            "Escolha um video com a camera aparecendo", PASTA_VIDEOS if PASTA_VIDEOS.exists() else PASTA_SHORTS
        )
    if not video or not video.exists():
        print("Nenhum video escolhido.")
        return
    Marcador(video).rodar()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback

        traceback.print_exc()
        try:
            messagebox.showerror("Marcar camera - erro", f"{e}\n\nTire um print desta mensagem e mande pro Claude.")
        except Exception:
            print(f"\n[ERRO] {e}\nTire um print desta janela e mande pro Claude.")

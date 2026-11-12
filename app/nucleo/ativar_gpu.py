# App: baixa as bibliotecas da NVIDIA (CUDA 12 + cuDNN 9) para o Whisper usar a placa de video.
# Ficam em %LOCALAPPDATA%\FamosoZora Studio\gpu (fora da pasta do programa, sobrevivem a atualizacoes).
import subprocess
import sys

from nucleo.comum import DADOS_APP, rodar


def main():
    destino = DADOS_APP / "gpu"
    destino.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print(" Ativando a placa de video NVIDIA (cerca de 1 GB, so uma vez)")
    print(f" Pasta: {destino}")
    print("=" * 60 + "\n")
    r = subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "--target", str(destino),
                        "nvidia-cublas-cu12", "nvidia-cudnn-cu12==9.*"])
    if r.returncode == 0:
        print("\nPRONTO! Na proxima transcricao deve aparecer 'Usando a PLACA DE VIDEO'.")
    else:
        print("\n[ERRO] Nao consegui baixar. Confira a internet e tente de novo, ou mande um print pro Claude.")


if __name__ == "__main__":
    rodar(main)

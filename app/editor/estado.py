# O "cerebro" do editor de video (sem tela): os trechos, os marcadores, a introducao, a selecao, o ponto de
# entrada/saida (I/O), o ima nas palavras e trocas de cena, e o desfazer/refazer sem limite.
# A tela (janela_editor.py) so chama estas funcoes e redesenha. Assim da para testar tudo sem abrir janela.
import copy

from autoedit import decidir_cortes
from autoedit import trechos as tr

VELOCIDADES = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0)


class EstadoEditor:
    def __init__(self, tipo: str, duracao: float, regras: dict, trechos=(), marcadores=(), introducao=None,
                 inicio: float = 0.0, fim: float | None = None, palavras=(), trocas=(), protegidos_extra=(),
                 limites=None):  # fmt: skip
        self.tipo = tipo  # "longo" ou "short"
        self.duracao = float(duracao)
        self.inicio = float(inicio)  # janela visivel (Short: o corte com folga de 10 s)
        self.fim = float(fim if fim is not None else duracao)
        self.regras = regras
        self.palavras = sorted((float(i), float(f)) for i, f in palavras)
        self.trocas = sorted(float(t) for t in trocas)
        self.protegidos_extra = list(protegidos_extra)  # o que o Claude mandou manter
        self.trechos = tr.normalizar(trechos, self.duracao)
        self.marcadores = [dict(m) for m in marcadores]
        self.introducao = dict(introducao) if introducao else None
        self.limites = tuple(limites) if limites else None  # Short: (comeco, fim) do corte, arrastaveis
        self.selecionado = None  # posicao em self.trechos
        self.marca_in = self.marca_out = None
        self.mudou_desde_salvar = False
        self.historico = tr.Historico(self._foto())

    # ---------------------------------------------------------- desfazer / refazer
    def _foto(self) -> dict:
        return {"trechos": self.trechos, "marcadores": self.marcadores, "introducao": self.introducao,
                "limites": self.limites}  # fmt: skip

    def _voltar(self, foto):
        self.limites = foto.get("limites")
        self.trechos = copy.deepcopy(foto["trechos"])
        self.marcadores = copy.deepcopy(foto["marcadores"])
        self.introducao = copy.deepcopy(foto["introducao"])
        self.selecionado = None
        self.mudou_desde_salvar = True

    def _mudou(self):
        self.trechos = sorted(self.trechos, key=lambda t: (t["inicio"], t["fim"]))
        self.historico.mudar(self._foto())
        self.mudou_desde_salvar = True

    def desfazer(self) -> bool:
        foto = self.historico.desfazer()
        if foto is None:
            return False
        self._voltar(foto)
        return True

    def refazer(self) -> bool:
        foto = self.historico.refazer()
        if foto is None:
            return False
        self._voltar(foto)
        return True

    # ---------------------------------------------------------- contas
    def protegidos(self) -> list:
        out = list(self.protegidos_extra)
        if self.introducao:
            out.append((self.introducao["inicio"], self.introducao["fim"]))
        return out

    def resolvidos(self) -> list:
        return tr.resolver(self.trechos, self.duracao, self.protegidos())

    def mapa(self) -> tr.MapaTempo:
        a, b = self.limites or (self.inicio, self.fim)
        return tr.MapaTempo(self.resolvidos(), a, b)

    def duracao_final(self) -> float:
        return self.mapa().final(self.limites[1] if self.limites else self.fim)

    def duracao_bruta(self) -> float:
        a, b = self.limites or (0.0, self.duracao)
        return b - a

    def relatorio(self) -> dict:
        return decidir_cortes.relatorio(self.trechos)

    def texto_relatorio(self) -> str:
        r = self.relatorio()
        saiu = r["saiu"]
        total = sum(saiu.values())
        if not total:
            partes = "nada sai ainda"
        else:
            nomes = ", ".join(f"{_min(v)} de {tr.NOMES_MOTIVO.get(k, k)}" for k, v in sorted(saiu.items(),
                                                                                         key=lambda x: -x[1]))  # fmt: skip
            partes = f"Saem {_min(total)}: {nomes}"
        rec = r["recusadas"]
        if rec:
            partes += ". Recusadas: " + ", ".join(f"{v} de {tr.NOMES_MOTIVO.get(k, k)}" for k, v in rec.items())
        return partes

    def dica_de_regra(self) -> str:
        return decidir_cortes.sugestao_de_regra(self.trechos, self.regras)

    def acao_em(self, t: float):
        """('cortar'|'acelerar', vel, (a, b)) do que vale no instante t, ou None se fica."""
        for a, b, acao, vel in self.resolvidos():
            if a <= t < b:
                return acao, vel, (a, b)
        return None

    def trecho_em(self, t: float):
        """Posicao do trecho (o de cima, que vale) no instante t, ou None."""
        melhor = None
        for k, x in enumerate(self.trechos):
            if x["inicio"] <= t < x["fim"]:
                chave = (tr.prioridade(x), k)
                if melhor is None or chave > melhor[0]:
                    melhor = (chave, k)
        return melhor[1] if melhor else None

    def sugestoes(self, motivo: str | None = None) -> list:
        """Posicoes dos trechos automaticos (as sugestoes), em ordem de tempo; motivo filtra."""
        return [k for k, t in enumerate(self.trechos) if t["origem"] == "auto" and (motivo in (None, "", "todos")
                                                                                     or t["motivo"] == motivo)]  # fmt: skip

    def proxima_sugestao(self, t: float, para_tras: bool = False, motivo: str | None = None):
        lista = self.sugestoes(motivo)
        if para_tras:
            antes = [k for k in lista if self.trechos[k]["inicio"] < t - 0.05]
            return antes[-1] if antes else None
        depois = [k for k in lista if self.trechos[k]["inicio"] > t + 0.05]
        return depois[0] if depois else None

    # ---------------------------------------------------------- ima
    def ima(self, t: float, alcance: float = 0.4) -> float:
        """Leva t para o comeco/fim de palavra ou troca de cena mais perto (ate 'alcance' s)."""
        pontos = [x for i, f in self.palavras for x in (i, f) if abs(x - t) <= alcance]
        pontos += [x for x in self.trocas if abs(x - t) <= alcance]
        if not pontos:
            return t
        return min(pontos, key=lambda x: abs(x - t))

    def limitar(self, t: float) -> float:
        return round(min(self.fim, max(self.inicio, float(t))), 3)

    # ---------------------------------------------------------- acoes
    def _novo(self, a, b, acao="cortar", vel=None, motivo="manual", forcar=False) -> dict:
        t = {"inicio": round(min(a, b), 3), "fim": round(max(a, b), 3), "acao": acao, "motivo": motivo,
             "origem": "manual", "confianca": "alta", "revisado": True}  # fmt: skip
        if acao == "acelerar":
            t["velocidade"] = float(vel or 2.0)
        if forcar:
            t["forcar"] = True
        return t

    def toca_protegido(self, a: float, b: float) -> bool:
        return any(a < pb and b > pa for pa, pb in self.protegidos())

    def cortar(self, a: float, b: float, forcar: bool = False) -> int | None:
        """Corte manual de a ate b (X, ou Delete na selecao). Devolve a posicao do trecho novo."""
        a, b = self.limitar(a), self.limitar(b)
        if b - a < 0.05:
            return None
        novo = self._novo(a, b, forcar=forcar)
        self.trechos.append(novo)
        self._mudou()
        self.selecionado = self.trechos.index(novo)
        return self.selecionado

    def marcar(self, a: float, b: float, acao: str, vel: float | None = None, forcar=False) -> int | None:
        a, b = self.limitar(a), self.limitar(b)
        if b - a < 0.05:
            return None
        novo = self._novo(a, b, acao, vel, forcar=forcar)
        self.trechos.append(novo)
        self._mudou()
        self.selecionado = self.trechos.index(novo)
        return self.selecionado

    def cortar_marcado(self, forcar: bool = False):
        """X: corta do ponto de entrada (I) ao de saida (O)."""
        if self.marca_in is None or self.marca_out is None:
            return None
        k = self.cortar(self.marca_in, self.marca_out, forcar)
        self.marca_in = self.marca_out = None
        return k

    def dividir(self, t: float) -> bool:
        """C: divide o trecho que esta no instante t em dois."""
        k = self.trecho_em(t)
        if k is None:
            return False
        x = self.trechos[k]
        if t - x["inicio"] < 0.05 or x["fim"] - t < 0.05:
            return False
        dir_ = dict(x, inicio=round(t, 3))
        x["fim"] = round(t, 3)
        self.trechos.append(dir_)
        self._mudou()
        return True

    def definir_acao(self, k: int, acao: str, vel: float | None = None, forcar: bool = False):
        """Muda o que acontece com o trecho k (manter / cortar / acelerar). Conta como revisado."""
        if k is None or not 0 <= k < len(self.trechos):
            return
        x = self.trechos[k]
        x["acao"] = acao
        x["revisado"] = True
        if acao == "acelerar":
            x["velocidade"] = float(vel or x.get("velocidade") or 2.0)
        else:
            x.pop("velocidade", None)
        if forcar:
            x["forcar"] = True
        self._mudou()

    def aceitar(self, k: int):
        """Enter: aceita a sugestao (sai; ou acelera, se a sugestao era acelerar)."""
        if k is None:
            return
        x = self.trechos[k]
        self.definir_acao(k, "acelerar" if x["acao"] == "acelerar" else "cortar")

    def recusar(self, k: int):
        """Backspace: recusa a sugestao (fica)."""
        self.definir_acao(k, "manter")

    def aceitar_tipo(self, motivo: str) -> int:
        """Aceita todas as sugestoes (ainda nao revisadas) deste tipo. Devolve quantas."""
        n = 0
        for k in self.sugestoes(motivo):
            x = self.trechos[k]
            if not x["revisado"]:
                x["acao"] = "acelerar" if x["acao"] == "acelerar" else "cortar"
                x["revisado"] = True
                n += 1
        if n:
            self._mudou()
        return n

    def apagar_trecho(self, k: int):
        """Tira o trecho da lista (corte manual que voce desistiu)."""
        if k is None or not 0 <= k < len(self.trechos):
            return
        self.trechos.pop(k)
        self.selecionado = None
        self._mudou()

    def mover_borda(self, k: int, lado: str, t: float, com_ima: bool = True):
        """Arrastar a borda ('inicio' ou 'fim') do trecho k para t (com ima, a nao ser com Alt)."""
        if k is None or not 0 <= k < len(self.trechos):
            return
        x = self.trechos[k]
        t = self.limitar(self.ima(t) if com_ima else t)
        if lado == "inicio":
            x["inicio"] = round(min(t, x["fim"] - 0.05), 3)
        else:
            x["fim"] = round(max(t, x["inicio"] + 0.05), 3)
        x["revisado"] = True

    def mover_limite(self, lado: str, t: float, com_ima: bool = True):
        """Short: arrastar o comeco ou o fim do corte."""
        if not self.limites:
            return
        t = self.limitar(self.ima(t) if com_ima else t)
        a, b = self.limites
        self.limites = (round(min(t, b - 1.0), 3), b) if lado == "inicio" else (a, round(max(t, a + 1.0), 3))

    def fim_do_arrasto(self):
        self._mudou()

    def adicionar_marcador(self, t: float, tipo: str, texto: str = ""):
        self.marcadores.append({"tempo": round(float(t), 3), "tipo": tipo, "texto": texto})
        self.marcadores.sort(key=lambda m: m["tempo"])
        self._mudou()

    def remover_marcador(self, k: int):
        if 0 <= k < len(self.marcadores):
            self.marcadores.pop(k)
            self._mudou()

    def definir_introducao(self, a: float | None, b: float | None = None):
        self.introducao = None if a is None or b is None or b <= a else {"inicio": round(a, 3), "fim": round(b, 3)}
        self._mudou()

    def reanalisar(self, sugestoes_novas: list):
        """Analisar de novo com outra predefinicao: ficam os seus cortes manuais e as sugestoes ja revisadas."""
        self.trechos = tr.mesclar_reanalise(self.trechos, tr.normalizar(sugestoes_novas, self.duracao))
        self.selecionado = None
        self._mudou()

    # ---------------------------------------------------------- arquivo
    def para_dict(self) -> dict:
        return {"trechos": copy.deepcopy(self.trechos), "marcadores": copy.deepcopy(self.marcadores),
                "introducao": copy.deepcopy(self.introducao), "limites": self.limites}  # fmt: skip


def _min(segundos: float) -> str:
    """'41 min', '2 min 10 s' ou '35 s'."""
    s = int(round(segundos))
    if s >= 600:
        return f"{round(s / 60)} min"
    if s >= 60:
        return f"{s // 60} min {s % 60:02d} s"
    return f"{s} s"


def proxima_velocidade(atual: float, mais: bool) -> float:
    """L acelera (1 -> 1,5 -> 2 -> 3 -> 4), J desacelera."""
    lista = list(VELOCIDADES)
    perto = min(range(len(lista)), key=lambda k: abs(lista[k] - atual))
    k = min(len(lista) - 1, perto + 1) if mais else max(0, perto - 1)
    return lista[k]

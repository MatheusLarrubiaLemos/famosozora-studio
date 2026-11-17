# Regras da selecao de varios itens numa lista (sem tela, para dar para testar):
# clique simples = so ele; Ctrl + clique = marca/desmarca um; Shift + clique = intervalo;
# caixinha = marca/desmarca um (igual ao Ctrl); "Selecionar todos" e "Limpar selecao".


def clicar(itens: list, selecionados: list, ancora, item, ctrl: bool = False, shift: bool = False,
           caixinha: bool = False) -> tuple:  # fmt: skip
    """Devolve (nova selecao, nova ancora). itens = ordem da lista; ancora = ultimo item clicado sem Shift."""
    if item not in itens:
        return list(selecionados), ancora
    if shift and ancora in itens:
        a, b = sorted((itens.index(ancora), itens.index(item)))
        intervalo = itens[a : b + 1]
        if ctrl:  # Ctrl + Shift: soma o intervalo ao que ja estava marcado
            return ordenar(itens, set(selecionados) | set(intervalo)), ancora
        return intervalo, ancora
    if ctrl or caixinha:
        atual = set(selecionados)
        atual ^= {item}
        return ordenar(itens, atual), item
    return [item], item


def todos(itens: list) -> list:
    return list(itens)


def nenhum() -> list:
    return []


def ordenar(itens: list, escolhidos) -> list:
    """Os escolhidos na ordem da lista."""
    escolhidos = set(escolhidos)
    return [i for i in itens if i in escolhidos]


def texto_contador(n: int) -> str:
    if n == 0:
        return "Nenhum vídeo selecionado"
    return "1 vídeo selecionado" if n == 1 else f"{n} vídeos selecionados"

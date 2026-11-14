# Corretor ortografico em portugues (biblioteca pyspellchecker), usado no editor de legendas.
# So aponta possiveis erros: nunca muda o texto sozinho. Se a biblioteca faltar, o editor funciona sem ele.
import re

from nucleo.comum import ler_correcoes, ler_vocabulario


class Corretor:
    def __init__(self):
        self._dicionario = None
        self._tentou = False
        self._cache = {}

    def _carregar(self):
        self._tentou = True
        try:
            from spellchecker import SpellChecker

            d = SpellChecker(language="pt")
            # nomes e termos do canal nao sao erro
            conhecidas = [p for termo in ler_vocabulario() for p in termo.lower().split()]
            conhecidas += [p for certo in ler_correcoes().values() for p in certo.lower().split()]
            d.word_frequency.load_words(conhecidas)
            self._dicionario = d
        except Exception:
            self._dicionario = None

    @property
    def disponivel(self) -> bool:
        if not self._tentou:
            self._carregar()
        return self._dicionario is not None

    def parece_errada(self, palavra: str) -> bool:
        """True se a palavra nao esta no dicionario (numeros, siglas e palavras de 1 ou 2 letras passam)."""
        if not self.disponivel:
            return False
        limpa = re.sub(r"^\W+|\W+$", "", palavra)
        if len(limpa) < 3 or any(c.isdigit() for c in limpa) or limpa.isupper() or "*" in limpa:
            return False
        chave = limpa.lower()
        if chave not in self._cache:
            partes = [p for p in re.split(r"[-']", chave) if p]
            self._cache[chave] = bool(self._dicionario.unknown(partes))
        return self._cache[chave]

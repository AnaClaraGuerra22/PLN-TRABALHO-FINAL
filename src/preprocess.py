import re

import spacy

from nltk.corpus import stopwords
from nltk.stem import PorterStemmer


# ============================================================
# RECURSOS
# ============================================================

NLP = spacy.load(
    "en_core_web_sm",
    disable=[
        "ner",
        "parser",
    ],
)

STEMMER = PorterStemmer()


# ============================================================
# STOPWORDS
# ============================================================

ENGLISH_STOPWORDS = set(
    stopwords.words("english")
)


PROTECTED_TERMS = {
    "no",
    "not",
    "nor",
    "never",
    "without",

    "before",
    "after",
    "since",
    "until",
    "during",
    "between",
    "from",
    "to",
    "earlier",
    "later",
    "prior",
    "following",

    "and",
    "or",
    "but",
    "if",
    "whether",


    "all",
    "any",
    "each",
    "every",
    "only",
    "same",

    "more",
    "less",
    "most",
    "least",
    "than",
    "above",
    "below",
    "under",
    "over",
    "greater",
    "lower",
    "higher",


    "against",
    "while",
}



STOPWORDS_P2 = (
    ENGLISH_STOPWORDS
    - PROTECTED_TERMS
)


# ============================================================
# P0
# ============================================================

def preprocess_p0(text: str) -> str:
    """
    Baseline.

    Mantém exatamente o texto recebido.
    """

    return text


# ============================================================
# P1
# ============================================================

def preprocess_p1(text: str) -> str:
    """
    Lowercase somente.

    Não remove:
    - números
    - pontuação
    - símbolos
    - palavras
    """

    return text.lower()


# ============================================================
# UTILIDADE PARA P2
# ============================================================

WORD_PATTERN = re.compile(
    r"\b[A-Za-z]+\b"
)


def remove_stopwords_preserving_text(
    text: str
) -> str:

    def substituir(match):

        token = match.group(0)

        if token.lower() in STOPWORDS_P2:
            return ""

        return token

    resultado = WORD_PATTERN.sub(
        substituir,
        text,
    )

    # Corrige apenas espaços criados
    # pela remoção das palavras.
    resultado = re.sub(
        r"[ \t]+",
        " ",
        resultado,
    )

    resultado = re.sub(
        r" +([,.;:!?])",
        r"\1",
        resultado,
    )

    return resultado.strip()


# ============================================================
# P2
# ============================================================

def preprocess_p2(text: str) -> str:
    """
    P1 + remoção de stopwords.

    A stoplist preserva operadores
    semanticamente críticos.
    """

    text = preprocess_p1(text)

    return remove_stopwords_preserving_text(
        text
    )


# ============================================================
# P3
# ============================================================

def preprocess_p3(text: str) -> str:
    """
    P1 + lematização em inglês.

    A lematização é aplicada às palavras alfabéticas,
    exceto operadores semanticamente críticos,
    que permanecem preservados.

    Preserva números, pontuação e símbolos.
    """

    text = preprocess_p1(text)

    doc = NLP(text)

    partes = []

    for token in doc:

        if token.is_alpha:

            if token.text.lower() in PROTECTED_TERMS:
                partes.append(
                    token.text + token.whitespace_
                )

            else:
                lemma = token.lemma_

                if not lemma:
                    lemma = token.text

                partes.append(
                    lemma + token.whitespace_
                )

        else:
            partes.append(
                token.text + token.whitespace_
            )

    return "".join(partes).strip()


# ============================================================
# P4
# ============================================================

def preprocess_p4(text: str) -> str:
    """
    P1 + Porter stemming.

    O stemming é aplicado às palavras alfabéticas,
    exceto operadores semanticamente críticos,
    que permanecem preservados.

    Números e pontuação também permanecem.
    """

    text = preprocess_p1(text)

    def aplicar_stem(match):

        palavra = match.group(0)

        # Preservar operadores semânticos
        if palavra.lower() in PROTECTED_TERMS:
            return palavra

        return STEMMER.stem(
            palavra
        )

    resultado = WORD_PATTERN.sub(
        aplicar_stem,
        text,
    )

    return resultado


# ============================================================
# INTERFACE ÚNICA
# ============================================================

def preprocess(
    text: str,
    variant: str
) -> str:

    variant = variant.upper()

    funcoes = {
        "P0": preprocess_p0,
        "P1": preprocess_p1,
        "P2": preprocess_p2,
        "P3": preprocess_p3,
        "P4": preprocess_p4,
    }

    if variant not in funcoes:

        raise ValueError(
            f"Variante desconhecida: "
            f"{variant}"
        )

    resultado = funcoes[variant](
        text
    )

    if not resultado.strip():

        raise ValueError(
            f"{variant} produziu "
            "texto vazio."
        )

    return resultado
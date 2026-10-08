import re


def canonicalize_chunk(metadata: dict) -> str:
    """
    Converte os metadados de um chunk do corpus P0
    em um identificador canônico de documento.

    A fonte (source) é priorizada porque chapter_number
    não distingue Cross Chapter 1 de Chapter 1 nem
    Cross Chapter 2 de Chapter 2.
    """

    source = str(metadata.get("source", "")).strip()
    chapter_number = str(
        metadata.get("chapter_number", "")
    ).strip()

    source_lower = source.lower()

    # --------------------------------------------------------
    # CROSS CHAPTERS
    # --------------------------------------------------------

    if "cross chapter 1" in source_lower:
        return "cross_chapter_1"

    if "cross chapter 2" in source_lower:
        return "cross_chapter_2"

    # --------------------------------------------------------
    # ANNEXES
    # --------------------------------------------------------

    if (
        "annex_01" in source_lower
        or chapter_number.lower() == "annex i"
    ):
        return "annex_01"

    if (
        "annex_02" in source_lower
        or chapter_number.lower() == "annex ii"
    ):
        return "annex_02"

    # --------------------------------------------------------
    # CAPÍTULOS NORMAIS
    # --------------------------------------------------------

    match = re.search(
        r"_cap_(\d{2})_",
        source_lower
    )

    if match:
        numero = int(match.group(1))

        if 1 <= numero <= 34:
            return f"chapter_{numero:02d}"

    # Fallback usando chapter_number
    if chapter_number.isdigit():

        numero = int(chapter_number)

        if 1 <= numero <= 34:
            return f"chapter_{numero:02d}"

    raise ValueError(
        "Não foi possível canonicalizar chunk:\n"
        f"source={source!r}\n"
        f"chapter_number={chapter_number!r}"
    )


def canonicalize_target(value: str) -> str:
    """
    Canonicaliza o capitulo_alvo proveniente
    do SPAmazon-QA.
    """

    original = str(value).strip()

    value = original.lower().strip()

    # normalização básica
    value = re.sub(r"\s+", " ", value)

    # --------------------------------------------------------
    # CROSS CHAPTER 2 / CC2
    # --------------------------------------------------------

    if value in {
        "cc2",
        "capítulo cc2",
        "capitulo cc2",
        "cross_chapter_2",
        "cross chapter 2",
        "capítulo cross chapter 2",
        "capitulo cross chapter 2",
    }:
        return "cross_chapter_2"

    # --------------------------------------------------------
    # CROSS CHAPTER 1
    # --------------------------------------------------------

    if value in {
        "cc1",
        "capítulo cc1",
        "capitulo cc1",
        "cross_chapter_1",
        "cross chapter 1",
        "capítulo cross chapter 1",
        "capitulo cross chapter 1",
    }:
        return "cross_chapter_1"

    # --------------------------------------------------------
    # ANNEX
    # --------------------------------------------------------

    if value in {
        "annex i",
        "annex 1",
        "capítulo annex 1",
        "capitulo annex 1",
        "annex_01",
    }:
        return "annex_01"

    if value in {
        "annex ii",
        "annex 2",
        "capítulo annex 2",
        "capitulo annex 2",
        "annex_02",
    }:
        return "annex_02"

    # --------------------------------------------------------
    # CAPÍTULO NORMAL
    # --------------------------------------------------------

    match = re.fullmatch(
        r"(?:capítulo|capitulo|chapter)?\s*(\d{1,2})",
        value
    )

    if match:

        numero = int(match.group(1))

        if 1 <= numero <= 34:
            return f"chapter_{numero:02d}"

    # Já canônico
    match = re.fullmatch(
        r"chapter_(\d{2})",
        value
    )

    if match:

        numero = int(match.group(1))

        if 1 <= numero <= 34:
            return f"chapter_{numero:02d}"

    raise ValueError(
        f"Capítulo-alvo desconhecido: {original!r}"
    )
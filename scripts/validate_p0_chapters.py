import json
import sys
from pathlib import Path
from collections import Counter


BASE_DIR = Path(__file__).resolve().parents[1]

sys.path.insert(
    0,
    str(BASE_DIR)
)

from src.chapters import canonicalize_chunk


ARQUIVO = (
    BASE_DIR
    / "data"
    / "reference"
    / "p0_chunks.jsonl"
)


def main():

    contador = Counter()
    total = 0

    with ARQUIVO.open(
        "r",
        encoding="utf-8"
    ) as f:

        for linha in f:

            registro = json.loads(linha)

            metadata = registro["metadata"]

            canonical_id = canonicalize_chunk(
                metadata
            )

            contador[canonical_id] += 1
            total += 1

    print("=" * 70)
    print("VALIDAÇÃO DOS DOCUMENTOS CANÔNICOS")
    print("=" * 70)

    print(f"\nTotal de chunks: {total}")
    print(
        f"Documentos canônicos distintos: "
        f"{len(contador)}"
    )

    print()

    for chapter_id, quantidade in sorted(
        contador.items()
    ):
        print(
            f"{chapter_id:<25} "
            f"{quantidade:>5} chunks"
        )

    print("\n" + "=" * 70)

    if len(contador) != 38:
        raise RuntimeError(
            f"Esperados 38 documentos, "
            f"mas encontrados {len(contador)}."
        )

    if contador["cross_chapter_1"] != 61:
        raise RuntimeError(
            "Quantidade inesperada em Cross Chapter 1."
        )

    if contador["cross_chapter_2"] != 18:
        raise RuntimeError(
            "Quantidade inesperada em Cross Chapter 2."
        )

    print("OK: 38 documentos canônicos identificados.")
    print("OK: Cross Chapter 1 separado de Chapter 1.")
    print("OK: Cross Chapter 2 separado de Chapter 2.")


if __name__ == "__main__":
    main()
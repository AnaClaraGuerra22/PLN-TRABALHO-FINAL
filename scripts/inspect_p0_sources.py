import json
from pathlib import Path
from collections import Counter


BASE_DIR = Path(__file__).resolve().parents[1]

ARQUIVO = (
    BASE_DIR
    / "data"
    / "reference"
    / "p0_chunks.jsonl"
)


def main():

    fontes = Counter()
    capitulos = Counter()

    suspeitos = []

    with ARQUIVO.open(
        "r",
        encoding="utf-8"
    ) as f:

        for linha in f:

            registro = json.loads(linha)

            metadata = registro.get("metadata") or {}

            source = str(
                metadata.get("source", "")
            )

            chapter = str(
                metadata.get("chapter_number", "")
            )

            fontes[source] += 1
            capitulos[chapter] += 1

            texto_busca = (
                source + " " +
                chapter
            ).lower()

            if (
                "cross" in texto_busca
                or "cc1" in texto_busca
                or "cc2" in texto_busca
            ):
                suspeitos.append(
                    {
                        "chunk_id": registro["chunk_id"],
                        "source": source,
                        "chapter_number": chapter
                    }
                )

    print("=" * 70)
    print("FONTES DISTINTAS NO P0")
    print("=" * 70)

    print(f"\nTotal de fontes distintas: {len(fontes)}\n")

    for source, quantidade in sorted(
        fontes.items()
    ):
        print(
            f"{source:<60} "
            f"{quantidade:>5} chunks"
        )

    print("\n" + "=" * 70)
    print("CHAPTER_NUMBER")
    print("=" * 70)

    print(
        f"\nValores distintos: "
        f"{len(capitulos)}\n"
    )

    for chapter, quantidade in sorted(
        capitulos.items()
    ):
        print(
            f"{chapter:<30} "
            f"{quantidade:>5}"
        )

    print("\n" + "=" * 70)
    print("POSSÍVEIS CROSS CHAPTERS")
    print("=" * 70)

    print(
        f"\nRegistros encontrados: "
        f"{len(suspeitos)}"
    )

    for item in suspeitos[:20]:
        print(item)


if __name__ == "__main__":
    main()
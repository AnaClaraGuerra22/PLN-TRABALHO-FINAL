import csv
import json
import sys
from pathlib import Path
from collections import defaultdict


# ============================================================
# CAMINHOS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

sys.path.insert(
    0,
    str(BASE_DIR)
)

from src.chapters import canonicalize_chunk


INPUT_FILE = (
    BASE_DIR
    / "data"
    / "reference"
    / "p0_chunks.jsonl"
)

OUTPUT_DIR = (
    BASE_DIR
    / "results"
    / "tables"
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "chunks_por_documento.csv"
)


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def obter_tipo(canonical_id: str) -> str:

    if canonical_id.startswith("cross_chapter"):
        return "Cross Chapter"

    if canonical_id.startswith("annex"):
        return "Annex"

    return "Chapter"


def obter_parte(source: str) -> str:

    source_lower = source.lower()

    if source_lower.startswith("part_i_"):
        return "Part I"

    if source_lower.startswith("part_ii_"):
        return "Part II"

    if source_lower.startswith("part_iii_"):
        return "Part III"

    if source_lower.startswith("annex"):
        return "Annex"

    return "Unknown"


def obter_nome_documento(source: str) -> str:
    """
    Remove a extensão .pdf para deixar
    a planilha mais legível.
    """

    if source.lower().endswith(".pdf"):
        return source[:-4]

    return source


def ordem_documento(canonical_id: str):

    # Capítulos normais
    if canonical_id.startswith("chapter_"):
        numero = int(
            canonical_id.split("_")[1]
        )

        return (1, numero)

    # Cross Chapters
    if canonical_id.startswith("cross_chapter_"):
        numero = int(
            canonical_id.split("_")[-1]
        )

        return (2, numero)

    # Annexes
    if canonical_id.startswith("annex_"):
        numero = int(
            canonical_id.split("_")[1]
        )

        return (3, numero)

    return (99, canonical_id)


# ============================================================
# EXECUÇÃO
# ============================================================

def main():

    print("=" * 70)
    print("GERAÇÃO DA PLANILHA DE CHUNKS POR DOCUMENTO")
    print("=" * 70)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado:\n{INPUT_FILE}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    documentos = defaultdict(
        lambda: {
            "source": "",
            "chapter_number_original": "",
            "chunks": 0
        }
    )

    total_chunks = 0

    # ========================================================
    # LER CORPUS
    # ========================================================

    with INPUT_FILE.open(
        "r",
        encoding="utf-8"
    ) as f:

        for linha in f:

            registro = json.loads(linha)

            metadata = registro.get(
                "metadata"
            ) or {}

            canonical_id = canonicalize_chunk(
                metadata
            )

            source = str(
                metadata.get(
                    "source",
                    ""
                )
            )

            chapter_original = str(
                metadata.get(
                    "chapter_number",
                    ""
                )
            )

            documentos[canonical_id]["source"] = source
            documentos[canonical_id][
                "chapter_number_original"
            ] = chapter_original

            documentos[canonical_id][
                "chunks"
            ] += 1

            total_chunks += 1

    # ========================================================
    # VALIDAR
    # ========================================================

    if len(documentos) != 38:

        raise RuntimeError(
            f"Esperados 38 documentos, "
            f"mas encontrados {len(documentos)}."
        )

    if total_chunks != 6900:

        raise RuntimeError(
            f"Esperados 6900 chunks, "
            f"mas encontrados {total_chunks}."
        )

    # ========================================================
    # PREPARAR LINHAS
    # ========================================================

    linhas = []

    for canonical_id, dados in documentos.items():

        quantidade = dados["chunks"]

        percentual = (
            quantidade
            / total_chunks
            * 100
        )

        linhas.append(
            {
                "id_canonico": canonical_id,
                "tipo_documento": obter_tipo(
                    canonical_id
                ),
                "parte": obter_parte(
                    dados["source"]
                ),
                "chapter_number_original":
                    dados[
                        "chapter_number_original"
                    ],
                "documento": obter_nome_documento(
                    dados["source"]
                ),
                "chunks": quantidade,
                "percentual_corpus": round(
                    percentual,
                    2
                )
            }
        )

    linhas.sort(
        key=lambda x: ordem_documento(
            x["id_canonico"]
        )
    )

    # ========================================================
    # SALVAR CSV
    # ========================================================

    campos = [
        "id_canonico",
        "tipo_documento",
        "parte",
        "chapter_number_original",
        "documento",
        "chunks",
        "percentual_corpus"
    ]

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=campos,
            delimiter=";"
        )

        writer.writeheader()

        for linha in linhas:
            writer.writerow(linha)

        # Linha total
        writer.writerow(
            {
                "id_canonico": "TOTAL",
                "tipo_documento": "",
                "parte": "",
                "chapter_number_original": "",
                "documento":
                    "Corpus completo",
                "chunks": total_chunks,
                "percentual_corpus": 100.00
            }
        )

    # ========================================================
    # RESUMO NO TERMINAL
    # ========================================================

    print(
        f"\nDocumentos: {len(documentos)}"
    )

    print(
        f"Chunks: {total_chunks}"
    )

    print("\nCross Chapters:")

    print(
        "Cross Chapter 1:",
        documentos[
            "cross_chapter_1"
        ]["chunks"]
    )

    print(
        "Cross Chapter 2:",
        documentos[
            "cross_chapter_2"
        ]["chunks"]
    )

    print("\nAnnexes:")

    print(
        "Annex I:",
        documentos[
            "annex_01"
        ]["chunks"]
    )

    print(
        "Annex II:",
        documentos[
            "annex_02"
        ]["chunks"]
    )

    print("\n" + "=" * 70)
    print("PLANILHA SALVA")
    print("=" * 70)

    print(
        f"\n{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
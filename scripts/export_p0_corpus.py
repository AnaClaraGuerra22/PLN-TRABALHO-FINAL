import json
import hashlib
from pathlib import Path
from collections import Counter

import chromadb


# ============================================================
# CAMINHOS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

DB_PATH = Path(
    r"C:\PLN_EXPERIMENTOS\VECTOR_DB_P0_FRESH"
)

OUTPUT_DIR = BASE_DIR / "data" / "reference"

OUTPUT_JSONL = OUTPUT_DIR / "p0_chunks.jsonl"
OUTPUT_AUDIT = BASE_DIR / "results" / "runs" / "p0_export_audit.json"

COLLECTION_NAME = "langchain"

BATCH_SIZE = 500


# ============================================================
# HASH
# ============================================================

def calcular_sha256(caminho: Path) -> str:

    sha = hashlib.sha256()

    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(bloco)

    return sha.hexdigest()


# ============================================================
# EXPORTAÇÃO
# ============================================================

def main():

    print("=" * 70)
    print("EXPORTAÇÃO DA BASELINE P0")
    print("=" * 70)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT_AUDIT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    print(f"\nBanco:\n{DB_PATH}")

    client = chromadb.PersistentClient(
        path=str(DB_PATH)
    )

    collection = client.get_collection(
        name=COLLECTION_NAME
    )

    total = collection.count()

    print(f"\nTotal informado pelo ChromaDB: {total}")

    registros = []

    # ========================================================
    # LEITURA EM LOTES
    # ========================================================

    for offset in range(0, total, BATCH_SIZE):

        print(
            f"Lendo chunks "
            f"{offset + 1} até "
            f"{min(offset + BATCH_SIZE, total)}..."
        )

        lote = collection.get(
            limit=BATCH_SIZE,
            offset=offset,
            include=[
                "documents",
                "metadatas"
            ]
        )

        ids = lote["ids"]
        documents = lote["documents"]
        metadatas = lote["metadatas"]

        for chunk_id, document, metadata in zip(
            ids,
            documents,
            metadatas
        ):

            registro = {
                "chunk_id": chunk_id,
                "document": document,
                "metadata": metadata
            }

            registros.append(registro)

    # ========================================================
    # ORDENAÇÃO DETERMINÍSTICA
    # ========================================================

    registros = sorted(
        registros,
        key=lambda x: x["chunk_id"]
    )

    # ========================================================
    # VALIDAÇÕES
    # ========================================================

    ids = [
        r["chunk_id"]
        for r in registros
    ]

    ids_unicos = set(ids)

    documentos_vazios = [
        r["chunk_id"]
        for r in registros
        if not r["document"]
    ]

    metadados_ausentes = [
        r["chunk_id"]
        for r in registros
        if not r["metadata"]
    ]

    chapter_counter = Counter()

    fontes = Counter()

    campos_metadata = set()

    intext_metadata_count = 0

    for registro in registros:

        metadata = registro["metadata"] or {}

        campos_metadata.update(
            metadata.keys()
        )

        chapter = str(
            metadata.get(
                "chapter_number",
                "AUSENTE"
            )
        )

        chapter_counter[chapter] += 1

        source = str(
            metadata.get(
                "source",
                "AUSENTE"
            )
        )

        fontes[source] += 1

        document = registro["document"] or ""

        if (
            document.startswith("Chapter:")
            and "\nSection" in document
            and "\nContent:" in document
        ):
            intext_metadata_count += 1

    print("\n" + "=" * 70)
    print("VALIDAÇÃO")
    print("=" * 70)

    print(f"Registros exportados: {len(registros)}")
    print(f"IDs únicos: {len(ids_unicos)}")
    print(f"Documentos vazios: {len(documentos_vazios)}")
    print(f"Metadados ausentes: {len(metadados_ausentes)}")

    print(
        "Chunks com estrutura "
        "'Chapter / Section / Content': "
        f"{intext_metadata_count}"
    )

    print("\nCampos de metadata:")

    for campo in sorted(campos_metadata):
        print(f"- {campo}")

    print("\n" + "=" * 70)
    print("CHUNKS POR chapter_number")
    print("=" * 70)

    for chapter, quantidade in sorted(
        chapter_counter.items(),
        key=lambda x: x[0].lower()
    ):
        print(
            f"{chapter:<30} {quantidade}"
        )

    # ========================================================
    # ERROS CRÍTICOS
    # ========================================================

    if len(registros) != total:
        raise RuntimeError(
            f"Esperados {total}, "
            f"mas foram obtidos {len(registros)}."
        )

    if len(ids_unicos) != total:
        raise RuntimeError(
            "Existem IDs duplicados."
        )

    if documentos_vazios:
        raise RuntimeError(
            f"Existem {len(documentos_vazios)} "
            "documentos vazios."
        )

    if metadados_ausentes:
        raise RuntimeError(
            f"Existem {len(metadados_ausentes)} "
            "chunks sem metadata."
        )

    # ========================================================
    # SALVAR JSONL
    # ========================================================

    print("\nSalvando corpus de referência...")

    with OUTPUT_JSONL.open(
        "w",
        encoding="utf-8",
        newline="\n"
    ) as f:

        for registro in registros:

            f.write(
                json.dumps(
                    registro,
                    ensure_ascii=False,
                    sort_keys=True
                )
            )

            f.write("\n")

    hash_jsonl = calcular_sha256(
        OUTPUT_JSONL
    )

    # ========================================================
    # AUDITORIA
    # ========================================================

    auditoria = {
        "collection": COLLECTION_NAME,
        "total_chunks": total,
        "unique_ids": len(ids_unicos),
        "empty_documents": len(documentos_vazios),
        "missing_metadata": len(metadados_ausentes),
        "intext_metadata_structure": intext_metadata_count,
        "metadata_fields": sorted(campos_metadata),
        "distinct_chapter_numbers": len(chapter_counter),
        "chapter_distribution": dict(
            sorted(
                chapter_counter.items(),
                key=lambda x: x[0].lower()
            )
        ),
        "distinct_sources": len(fontes),
        "sha256_p0_chunks_jsonl": hash_jsonl
    }

    with OUTPUT_AUDIT.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            auditoria,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("\n" + "=" * 70)
    print("EXPORTAÇÃO CONCLUÍDA")
    print("=" * 70)

    print(f"\nArquivo:")
    print(OUTPUT_JSONL)

    print("\nSHA-256:")
    print(hash_jsonl)

    print("\nAuditoria:")
    print(OUTPUT_AUDIT)


if __name__ == "__main__":
    main()
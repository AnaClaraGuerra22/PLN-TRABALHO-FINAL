import hashlib
import json
import platform
import shutil
import sys
from datetime import datetime
from importlib.metadata import version
from pathlib import Path

import chromadb
from langchain_huggingface import HuggingFaceEmbeddings


# ============================================================
# PROJETO
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]


# ============================================================
# CONFIGURAÇÃO EXPERIMENTAL
# ============================================================

MODEL_NAME = (
    "sentence-transformers/all-mpnet-base-v2"
)

COLLECTION_NAME = "langchain"

BATCH_SIZE = 128

EXPECTED_CHUNKS = 6900

EXPECTED_DIMENSION = 768


# ============================================================
# DIRETÓRIO DOS BANCOS
#
# FORA DO ONEDRIVE
# ============================================================

DB_ROOT = Path(
    r"C:\PLN_EXPERIMENTOS\VECTOR_DB_CONTROLLED"
)


# ============================================================
# CORPORA
# ============================================================

CORPORA = {
    "P0": (
        BASE_DIR
        / "data"
        / "reference"
        / "p0_chunks.jsonl"
    ),

    "P1": (
        BASE_DIR
        / "data"
        / "processed"
        / "p1_chunks.jsonl"
    ),

    "P2": (
        BASE_DIR
        / "data"
        / "processed"
        / "p2_chunks.jsonl"
    ),

    "P3": (
        BASE_DIR
        / "data"
        / "processed"
        / "p3_chunks.jsonl"
    ),

    "P4": (
        BASE_DIR
        / "data"
        / "processed"
        / "p4_chunks.jsonl"
    ),
}


# ============================================================
# AUDITORIA
# ============================================================

AUDIT_FILE = (
    BASE_DIR
    / "results"
    / "runs"
    / "controlled_vector_dbs_build.json"
)


# ============================================================
# UTILIDADES
# ============================================================

def package_version(name):

    try:
        return version(name)

    except Exception:
        return None


def sha256_file(path):

    sha = hashlib.sha256()

    with path.open("rb") as f:

        while True:

            block = f.read(
                1024 * 1024
            )

            if not block:
                break

            sha.update(block)

    return sha.hexdigest()


def load_corpus(path):

    records = []

    with path.open(
        "r",
        encoding="utf-8"
    ) as f:

        for line in f:

            records.append(
                json.loads(line)
            )

    return records


# ============================================================
# VALIDAÇÃO CRUZADA DOS CORPORA
# ============================================================

def validate_corpora():

    print("=" * 72)
    print("VALIDAÇÃO CRUZADA DOS CORPORA")
    print("=" * 72)

    loaded = {}

    reference_ids = None
    reference_metadata = None

    for variant, path in CORPORA.items():

        if not path.exists():

            raise FileNotFoundError(
                f"{variant}: arquivo não encontrado:\n"
                f"{path}"
            )

        records = load_corpus(
            path
        )

        if len(records) != EXPECTED_CHUNKS:

            raise RuntimeError(
                f"{variant}: esperados "
                f"{EXPECTED_CHUNKS} chunks; "
                f"encontrados {len(records)}."
            )

        ids = [
            r["chunk_id"]
            for r in records
        ]

        if len(set(ids)) != EXPECTED_CHUNKS:

            raise RuntimeError(
                f"{variant}: IDs não são únicos."
            )

        # A ordem precisa ser idêntica.
        if reference_ids is None:

            reference_ids = ids

        elif ids != reference_ids:

            raise RuntimeError(
                f"{variant}: ordem dos IDs "
                "difere de P0."
            )

        metadata_map = {
            r["chunk_id"]:
                r["metadata"]
            for r in records
        }

        if reference_metadata is None:

            reference_metadata = (
                metadata_map
            )

        elif metadata_map != reference_metadata:

            raise RuntimeError(
                f"{variant}: metadados "
                "diferem de P0."
            )

        for record in records:

            if not record[
                "document"
            ].strip():

                raise RuntimeError(
                    f"{variant}: texto vazio em "
                    f"{record['chunk_id']}"
                )

        loaded[variant] = records

        print(
            f"{variant}: "
            f"{len(records)} chunks | "
            f"SHA256 "
            f"{sha256_file(path)}"
        )

    print(
        "\nOK: os cinco corpora possuem "
        "os mesmos IDs, mesma ordem "
        "e mesmos metadados."
    )

    return loaded


# ============================================================
# CRIAR UM BANCO
# ============================================================

def build_database(
    variant,
    records,
    embeddings,
):

    db_path = (
        DB_ROOT
        / variant
    )

    print("\n" + "=" * 72)
    print(
        f"CONSTRUINDO ÍNDICE {variant}"
    )
    print("=" * 72)

    print(
        f"Destino: {db_path}"
    )

    # --------------------------------------------------------
    # Segurança
    # --------------------------------------------------------

    if db_path.exists():

        if any(
            db_path.iterdir()
        ):

            raise RuntimeError(
                f"\nO diretório já existe "
                f"e não está vazio:\n"
                f"{db_path}\n\n"
                "O script não apagará um "
                "banco existente automaticamente."
            )

    db_path.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Chroma
    # --------------------------------------------------------

    client = (
        chromadb.PersistentClient(
            path=str(db_path)
        )
    )

    collection = (
        client.create_collection(
            name=COLLECTION_NAME,
            embedding_function=None,
        )
    )

    total_batches = (
        len(records)
        + BATCH_SIZE
        - 1
    ) // BATCH_SIZE

    detected_dimension = None

    # --------------------------------------------------------
    # Batches
    # --------------------------------------------------------

    for batch_number, start in enumerate(
        range(
            0,
            len(records),
            BATCH_SIZE,
        ),
        start=1,
    ):

        end = min(
            start + BATCH_SIZE,
            len(records),
        )

        batch = (
            records[start:end]
        )

        texts = [
            r["document"]
            for r in batch
        ]

        ids = [
            r["chunk_id"]
            for r in batch
        ]

        metadatas = [
            r["metadata"]
            for r in batch
        ]

        # ----------------------------------------------
        # Embeddings
        # ----------------------------------------------

        vectors = (
            embeddings.embed_documents(
                texts
            )
        )

        if not vectors:

            raise RuntimeError(
                f"{variant}: batch sem embeddings."
            )

        if detected_dimension is None:

            detected_dimension = len(
                vectors[0]
            )

            if (
                detected_dimension
                != EXPECTED_DIMENSION
            ):

                raise RuntimeError(
                    f"{variant}: dimensão "
                    f"{detected_dimension}; "
                    f"esperada "
                    f"{EXPECTED_DIMENSION}."
                )

        # ----------------------------------------------
        # Inserção
        # ----------------------------------------------

        collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=vectors,
        )

        print(
            f"Batch "
            f"{batch_number:02d}/"
            f"{total_batches:02d} | "
            f"{end}/"
            f"{len(records)}"
        )

    # --------------------------------------------------------
    # Validar
    # --------------------------------------------------------

    count = collection.count()

    if count != EXPECTED_CHUNKS:

        raise RuntimeError(
            f"{variant}: banco contém "
            f"{count} chunks; "
            f"esperados {EXPECTED_CHUNKS}."
        )

    # Verificar IDs e metadata no banco
    result = collection.get(
        include=[
            "metadatas",
            "documents",
        ]
    )

    db_ids = set(
        result["ids"]
    )

    source_ids = {
        r["chunk_id"]
        for r in records
    }

    if db_ids != source_ids:

        raise RuntimeError(
            f"{variant}: IDs do banco "
            "não correspondem ao corpus."
        )

    # --------------------------------------------------------
    # Auditoria
    # --------------------------------------------------------

    info = {
        "variant":
            variant,

        "path":
            str(db_path),

        "collection":
            COLLECTION_NAME,

        "chunks":
            count,

        "embedding_dimension":
            detected_dimension,

        "batch_size":
            BATCH_SIZE,

        "corpus_file":
            str(CORPORA[variant]),

        "corpus_sha256":
            sha256_file(
                CORPORA[variant]
            ),

        "collection_metadata":
            collection.metadata,
    }

    print(
        f"\n{variant} concluído:"
    )

    print(
        f"  chunks: {count}"
    )

    print(
        "  dimensão: "
        f"{detected_dimension}"
    )

    print(
        "  coleção: "
        f"{COLLECTION_NAME}"
    )

    return info


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 72)
    print(
        "CONSTRUÇÃO DOS ÍNDICES CONTROLADOS P0–P4"
    )
    print("=" * 72)

    print(
        "\nIMPORTANTE:"
    )

    print(
        "estes bancos são experimentais "
        "e não alteram o VECTOR_DB original."
    )

    # ========================================================
    # CORPORA
    # ========================================================

    corpora = validate_corpora()

    # ========================================================
    # MODELO
    # ========================================================

    print("\n" + "=" * 72)
    print("CARREGANDO MODELO DE EMBEDDINGS")
    print("=" * 72)

    print(MODEL_NAME)

    embeddings = HuggingFaceEmbeddings(
        model_name=MODEL_NAME
    )

    # Sanity check do encoder
    test_vector = (
        embeddings.embed_query(
            "Amazon"
        )
    )

    if (
        len(test_vector)
        != EXPECTED_DIMENSION
    ):

        raise RuntimeError(
            "Dimensão inesperada do "
            "modelo de embeddings."
        )

    print(
        "Dimensão confirmada: "
        f"{len(test_vector)}"
    )

    # ========================================================
    # DIRETÓRIO
    # ========================================================

    DB_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )

    # ========================================================
    # BUILD
    # ========================================================

    database_results = {}

    for variant in [
        "P0",
        "P1",
        "P2",
        "P3",
        "P4",
    ]:

        database_results[
            variant
        ] = build_database(
            variant,
            corpora[variant],
            embeddings,
        )

    # ========================================================
    # REGISTRO
    # ========================================================

    audit = {
        "timestamp":
            datetime.now().isoformat(),

        "python":
            platform.python_version(),

        "chromadb":
            package_version(
                "chromadb"
            ),

        "langchain_huggingface":
            package_version(
                "langchain-huggingface"
            ),

        "sentence_transformers":
            package_version(
                "sentence-transformers"
            ),

        "embedding_model":
            MODEL_NAME,

        "embedding_dimension":
            EXPECTED_DIMENSION,

        "collection_name":
            COLLECTION_NAME,

        "batch_size":
            BATCH_SIZE,

        "insertion_order":
            "identical P0-P4",

        "databases":
            database_results,
    }

    AUDIT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with AUDIT_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            audit,
            f,
            ensure_ascii=False,
            indent=2,
        )

    # ========================================================
    # FINAL
    # ========================================================

    print("\n" + "=" * 72)
    print(
        "TODOS OS ÍNDICES FORAM CRIADOS"
    )
    print("=" * 72)

    for variant in [
        "P0",
        "P1",
        "P2",
        "P3",
        "P4",
    ]:

        print(
            f"{variant}: "
            f"{DB_ROOT / variant}"
        )

    print(
        "\nAuditoria:"
    )

    print(AUDIT_FILE)


if __name__ == "__main__":
    main()
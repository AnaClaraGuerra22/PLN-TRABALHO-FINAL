import csv
import hashlib
import json
import platform
import re
import unicodedata
from collections import Counter
from datetime import datetime
from importlib.metadata import version
from pathlib import Path

import chromadb
from langchain_huggingface import HuggingFaceEmbeddings


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

DB_ROOT = Path(
    r"C:\PLN_EXPERIMENTOS\VECTOR_DB_CONTROLLED"
)

COLLECTION_NAME = "langchain"

MODEL_NAME = (
    "sentence-transformers/all-mpnet-base-v2"
)

EXPECTED_DIMENSION = 768
EXPECTED_CHUNKS = 6900
EXPECTED_QUESTIONS = 130

TOP_K = 10

VARIANTS = [
    "P0",
    "P1",
    "P2",
    "P3",
    "P4",
]


# ============================================================
# ARQUIVOS
# ============================================================

P0_CORPUS = (
    BASE_DIR
    / "data"
    / "reference"
    / "p0_chunks.jsonl"
)

QUESTION_FILES = {
    variant: (
        BASE_DIR
        / "data"
        / "processed"
        / f"{variant.lower()}_questions.jsonl"
    )
    for variant in VARIANTS
}

DOWNSTREAM_CASES = (
    BASE_DIR
    / "data"
    / "reference"
    / "downstream_critical_cases.jsonl"
)


# ============================================================
# SAÍDAS
# ============================================================

RAW_DIR = (
    BASE_DIR
    / "results"
    / "raw"
)

METRICS_DIR = (
    BASE_DIR
    / "results"
    / "metrics"
)

CASES_DIR = (
    BASE_DIR
    / "results"
    / "cases"
)

RUNS_DIR = (
    BASE_DIR
    / "results"
    / "runs"
)


RANKINGS_FILE = (
    RAW_DIR
    / "controlled_rankings.csv"
)

QUESTION_METRICS_FILE = (
    METRICS_DIR
    / "controlled_question_metrics.csv"
)

SUMMARY_FILE = (
    METRICS_DIR
    / "controlled_summary.csv"
)

DELTA_FILE = (
    METRICS_DIR
    / "controlled_deltas_vs_p0.csv"
)

QUESTION_DELTA_FILE = (
    METRICS_DIR
    / "controlled_question_deltas_vs_p0.csv"
)

CASE11_FILE = (
    CASES_DIR
    / "controlled_case_11_top10.csv"
)

DOWNSTREAM_TOP5_FILE = (
    CASES_DIR
    / "downstream_retrieval_top5.csv"
)

RUN_FILE = (
    RUNS_DIR
    / "controlled_retrieval_run.json"
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

    h = hashlib.sha256()

    with path.open("rb") as f:

        for bloco in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b""
        ):
            h.update(bloco)

    return h.hexdigest()


def normalize_text(text):

    text = str(text)

    text = unicodedata.normalize(
        "NFKD",
        text
    )

    text = "".join(
        c
        for c in text
        if not unicodedata.combining(c)
    )

    return text.lower()


# ============================================================
# CANONICALIZAÇÃO DO DOCUMENTO-ALVO
# ============================================================

def canonicalize_target(raw):

    s = normalize_text(raw)

    s = s.replace(
        "_",
        " "
    )

    s = s.replace(
        "-",
        " "
    )

    s = re.sub(
        r"\s+",
        " ",
        s
    ).strip()

    # --------------------------------------------------------
    # CROSS CHAPTER
    # Deve vir antes da regra genérica de "chapter".
    # --------------------------------------------------------

    match = re.search(
        r"(?:cross\s*chapter|cc)\s*0?([12])",
        s
    )

    if match:

        n = int(
            match.group(1)
        )

        return (
            f"cross_chapter_{n}"
        )

    # --------------------------------------------------------
    # ANNEX / ANEXO
    # --------------------------------------------------------

    if (
        "annex" in s
        or "anexo" in s
    ):

        if re.search(
            r"\b(?:ii|2)\b",
            s
        ):
            return "annex_02"

        if re.search(
            r"\b(?:i|1)\b",
            s
        ):
            return "annex_01"

    # --------------------------------------------------------
    # CHAPTER
    # --------------------------------------------------------

    match = re.search(
        r"(?:capitulo|chapter|cap)\s*0?(\d{1,2})",
        s
    )

    if match:

        n = int(
            match.group(1)
        )

        return (
            f"chapter_{n:02d}"
        )

    raise ValueError(
        "Não foi possível canonicalizar "
        f"o capítulo-alvo: {raw}"
    )


# ============================================================
# CANONICALIZAÇÃO DE SOURCE
# ============================================================

def canonicalize_source(source):

    s = normalize_text(source)

    s = s.replace(
        "\\",
        "/"
    )

    filename = s.split(
        "/"
    )[-1]

    normalized = filename.replace(
        "_",
        " "
    )

    normalized = normalized.replace(
        "-",
        " "
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized
    )

    # --------------------------------------------------------
    # CROSS CHAPTER
    # --------------------------------------------------------

    match = re.search(
        r"(?:cross\s*chapter|cc)\s*0?([12])",
        normalized
    )

    if match:

        n = int(
            match.group(1)
        )

        return (
            f"cross_chapter_{n}"
        )

    # --------------------------------------------------------
    # ANNEX
    # --------------------------------------------------------

    if (
        "annex" in normalized
        or "anexo" in normalized
    ):

        if re.search(
            r"\b(?:ii|02|2)\b",
            normalized
        ):
            return "annex_02"

        if re.search(
            r"\b(?:i|01|1)\b",
            normalized
        ):
            return "annex_01"

    # --------------------------------------------------------
    # REGULAR CHAPTER
    # --------------------------------------------------------

    match = re.search(
        r"(?:chapter|capitulo|cap)\s*0?(\d{1,2})",
        normalized
    )

    if match:

        n = int(
            match.group(1)
        )

        return (
            f"chapter_{n:02d}"
        )

    raise ValueError(
        "Não foi possível canonicalizar "
        f"source: {source}"
    )


# ============================================================
# CARREGAR P0
# ============================================================

def load_p0_lookup():

    print("=" * 72)
    print("CARREGANDO REFERÊNCIA P0")
    print("=" * 72)

    lookup = {}

    counts = Counter()

    with P0_CORPUS.open(
        "r",
        encoding="utf-8"
    ) as f:

        for line in f:

            record = json.loads(
                line
            )

            chunk_id = record[
                "chunk_id"
            ]

            metadata = record[
                "metadata"
            ]

            source = metadata[
                "source"
            ]

            canonical = (
                canonicalize_source(
                    source
                )
            )

            if chunk_id in lookup:

                raise RuntimeError(
                    "ID duplicado no P0: "
                    f"{chunk_id}"
                )

            lookup[
                chunk_id
            ] = {
                "canonical":
                    canonical,

                "source":
                    source,

                "metadata":
                    metadata,

                "document":
                    record[
                        "document"
                    ],
            }

            counts[
                canonical
            ] += 1

    if len(lookup) != EXPECTED_CHUNKS:

        raise RuntimeError(
            f"P0 contém {len(lookup)} chunks; "
            f"esperados {EXPECTED_CHUNKS}."
        )

    expected_documents = {
        "annex_01",
        "annex_02",
        "cross_chapter_1",
        "cross_chapter_2",
    }

    expected_documents.update({
        f"chapter_{n:02d}"
        for n in range(
            1,
            35
        )
    })

    if (
        set(counts.keys())
        != expected_documents
    ):

        missing = (
            expected_documents
            - set(counts.keys())
        )

        extra = (
            set(counts.keys())
            - expected_documents
        )

        raise RuntimeError(
            "Documentos canônicos inesperados.\n"
            f"Faltando: {sorted(missing)}\n"
            f"Extras: {sorted(extra)}"
        )

    print(
        f"Chunks: {len(lookup)}"
    )

    print(
        f"Documentos: {len(counts)}"
    )

    print(
        "Referência P0 validada."
    )

    return lookup


# ============================================================
# CARREGAR PERGUNTAS
# ============================================================

def load_questions(
    variant
):

    path = QUESTION_FILES[
        variant
    ]

    records = []

    with path.open(
        "r",
        encoding="utf-8"
    ) as f:

        for line in f:

            record = json.loads(
                line
            )

            records.append(
                record
            )

    if (
        len(records)
        != EXPECTED_QUESTIONS
    ):

        raise RuntimeError(
            f"{variant}: "
            f"{len(records)} perguntas."
        )

    ids = [
        int(
            r["id_questao"]
        )
        for r in records
    ]

    if len(set(ids)) != 130:

        raise RuntimeError(
            f"{variant}: IDs duplicados."
        )

    records.sort(
        key=lambda x:
        int(
            x["id_questao"]
        )
    )

    return records


# ============================================================
# CASOS DOWNSTREAM
# ============================================================

def load_downstream_ids():

    ids = set()

    with DOWNSTREAM_CASES.open(
        "r",
        encoding="utf-8"
    ) as f:

        for line in f:

            record = json.loads(
                line
            )

            ids.add(
                int(
                    record[
                        "id_questao"
                    ]
                )
            )

    if len(ids) != 32:

        raise RuntimeError(
            "Esperados 32 casos downstream; "
            f"encontrados {len(ids)}."
        )

    return ids


# ============================================================
# VALIDAR BANCOS
# ============================================================

def load_collections():

    print("\n" + "=" * 72)
    print("VALIDAÇÃO DOS CINCO ÍNDICES")
    print("=" * 72)

    collections = {}
    counts = {}

    for variant in VARIANTS:

        db_path = (
            DB_ROOT
            / variant
        )

        if not db_path.exists():

            raise FileNotFoundError(
                f"{variant}: banco não encontrado:\n"
                f"{db_path}"
            )

        client = (
            chromadb.PersistentClient(
                path=str(
                    db_path
                )
            )
        )

        collection = (
            client.get_collection(
                name=COLLECTION_NAME,
                embedding_function=None,
            )
        )

        count = collection.count()

        if (
            count
            != EXPECTED_CHUNKS
        ):

            raise RuntimeError(
                f"{variant}: "
                f"{count} chunks no banco; "
                f"esperados {EXPECTED_CHUNKS}."
            )

        print(
            f"{variant}: "
            f"{count} chunks"
        )

        collections[
            variant
        ] = {
            "client":
                client,

            "collection":
                collection,
        }

        counts[
            variant
        ] = count

    print(
        "\nOK: cinco bancos disponíveis."
    )

    return (
        collections,
        counts
    )


# ============================================================
# ESCREVER CSV
# ============================================================

def write_csv(
    path,
    rows,
    fieldnames
):

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 72)
    print(
        "EXPERIMENTO CONTROLADO DE RECUPERAÇÃO P0–P4"
    )
    print("=" * 72)

    # ========================================================
    # REFERÊNCIAS
    # ========================================================

    p0_lookup = (
        load_p0_lookup()
    )

    downstream_ids = (
        load_downstream_ids()
    )

    # ========================================================
    # BANCOS
    # ========================================================

    collections, db_counts = (
        load_collections()
    )

    # ========================================================
    # EMBEDDINGS
    # ========================================================

    print("\n" + "=" * 72)
    print("CARREGANDO EMBEDDINGS")
    print("=" * 72)

    embeddings = (
        HuggingFaceEmbeddings(
            model_name=MODEL_NAME
        )
    )

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
            "Dimensão inesperada: "
            f"{len(test_vector)}"
        )

    print(
        f"Dimensão: "
        f"{len(test_vector)}"
    )

    # ========================================================
    # RESULTADOS
    # ========================================================

    ranking_rows = []
    metric_rows = []

    # ========================================================
    # VARIANTES
    # ========================================================

    for variant in VARIANTS:

        print("\n" + "=" * 72)
        print(
            f"RECUPERAÇÃO {variant}"
        )
        print("=" * 72)

        questions = (
            load_questions(
                variant
            )
        )

        collection = (
            collections[
                variant
            ][
                "collection"
            ]
        )

        for i, question in enumerate(
            questions,
            start=1
        ):

            id_questao = int(
                question[
                    "id_questao"
                ]
            )

            query = question[
                "query"
            ]

            target_raw = question[
                "capitulo_alvo"
            ]

            target = (
                canonicalize_target(
                    target_raw
                )
            )

            query_vector = (
                embeddings.embed_query(
                    query
                )
            )

            result = (
                collection.query(
                    query_embeddings=[
                        query_vector
                    ],
                    n_results=TOP_K,
                    include=[
                        "metadatas",
                        "distances",
                    ],
                )
            )

            ids = result[
                "ids"
            ][0]

            distances = result[
                "distances"
            ][0]

            if len(ids) != TOP_K:

                raise RuntimeError(
                    f"{variant} / Q{id_questao}: "
                    f"retornou {len(ids)} resultados."
                )

            first_relevant_rank = None

            for rank, (
                chunk_id,
                distance
            ) in enumerate(
                zip(
                    ids,
                    distances
                ),
                start=1
            ):

                if (
                    chunk_id
                    not in p0_lookup
                ):

                    raise RuntimeError(
                        "Chunk recuperado não existe "
                        "na referência P0: "
                        f"{chunk_id}"
                    )

                ref = (
                    p0_lookup[
                        chunk_id
                    ]
                )

                retrieved_canonical = (
                    ref[
                        "canonical"
                    ]
                )

                is_target = (
                    retrieved_canonical
                    == target
                )

                if (
                    is_target
                    and
                    first_relevant_rank is None
                ):

                    first_relevant_rank = (
                        rank
                    )

                metadata = ref[
                    "metadata"
                ]

                ranking_rows.append({
                    "variant":
                        variant,

                    "id_questao":
                        id_questao,

                    "rank":
                        rank,

                    "chunk_id":
                        chunk_id,

                    "distance":
                        float(
                            distance
                        ),

                    "target_raw":
                        target_raw,

                    "target_canonical":
                        target,

                    "retrieved_canonical":
                        retrieved_canonical,

                    "is_target":
                        int(
                            is_target
                        ),

                    "source":
                        ref[
                            "source"
                        ],

                    "chapter_number":
                        metadata.get(
                            "chapter_number"
                        ),

                    "section_number":
                        metadata.get(
                            "section_number"
                        ),

                    "page":
                        metadata.get(
                            "page"
                        ),

                    "dificuldade":
                        question.get(
                            "dificuldade"
                        ),

                    "tipo":
                        question.get(
                            "tipo"
                        ),

                    "indice_subjetividade":
                        question.get(
                            "indice_subjetividade"
                        ),
                })

            hit1 = (
                first_relevant_rank
                is not None
                and first_relevant_rank <= 1
            )

            hit3 = (
                first_relevant_rank
                is not None
                and first_relevant_rank <= 3
            )

            hit5 = (
                first_relevant_rank
                is not None
                and first_relevant_rank <= 5
            )

            hit10 = (
                first_relevant_rank
                is not None
                and first_relevant_rank <= 10
            )

            reciprocal_rank = (
                0.0
                if first_relevant_rank is None
                else
                1.0 / first_relevant_rank
            )

            metric_rows.append({
                "variant":
                    variant,

                "id_questao":
                    id_questao,

                "target_canonical":
                    target,

                "dificuldade":
                    question.get(
                        "dificuldade"
                    ),

                "tipo":
                    question.get(
                        "tipo"
                    ),

                "indice_subjetividade":
                    question.get(
                        "indice_subjetividade"
                    ),

                "first_relevant_rank":
                    (
                        ""
                        if first_relevant_rank
                        is None
                        else first_relevant_rank
                    ),

                "hit_1":
                    int(hit1),

                "hit_3":
                    int(hit3),

                "hit_5":
                    int(hit5),

                "hit_10":
                    int(hit10),

                "reciprocal_rank_10":
                    reciprocal_rank,
            })

            if (
                i % 10 == 0
                or i == 130
            ):

                print(
                    f"{i}/130"
                )

    # ========================================================
    # VALIDAR TAMANHO
    # ========================================================

    expected_rankings = (
        130
        * 5
        * 10
    )

    expected_metrics = (
        130
        * 5
    )

    if (
        len(ranking_rows)
        != expected_rankings
    ):

        raise RuntimeError(
            "Número de rankings incorreto: "
            f"{len(ranking_rows)}"
        )

    if (
        len(metric_rows)
        != expected_metrics
    ):

        raise RuntimeError(
            "Número de métricas incorreto: "
            f"{len(metric_rows)}"
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    summary_rows = []

    for variant in VARIANTS:

        rows = [
            r
            for r in metric_rows
            if r[
                "variant"
            ] == variant
        ]

        n = len(rows)

        h1 = sum(
            r["hit_1"]
            for r in rows
        )

        h3 = sum(
            r["hit_3"]
            for r in rows
        )

        h5 = sum(
            r["hit_5"]
            for r in rows
        )

        h10 = sum(
            r["hit_10"]
            for r in rows
        )

        mrr = sum(
            r[
                "reciprocal_rank_10"
            ]
            for r in rows
        ) / n

        summary_rows.append({
            "variant":
                variant,

            "n_questions":
                n,

            "hit_1_count":
                h1,

            "hit_1_percent":
                100 * h1 / n,

            "hit_3_count":
                h3,

            "hit_3_percent":
                100 * h3 / n,

            "hit_5_count":
                h5,

            "hit_5_percent":
                100 * h5 / n,

            "hit_10_count":
                h10,

            "hit_10_percent":
                100 * h10 / n,

            "mrr_10":
                mrr,
        })

    # ========================================================
    # DELTAS AGREGADOS VS P0
    # ========================================================

    p0_summary = next(
        r
        for r in summary_rows
        if r[
            "variant"
        ] == "P0"
    )

    delta_rows = []

    for row in summary_rows:

        delta_rows.append({
            "variant":
                row[
                    "variant"
                ],

            "delta_hit_1_pp":
                (
                    row[
                        "hit_1_percent"
                    ]
                    -
                    p0_summary[
                        "hit_1_percent"
                    ]
                ),

            "delta_hit_3_pp":
                (
                    row[
                        "hit_3_percent"
                    ]
                    -
                    p0_summary[
                        "hit_3_percent"
                    ]
                ),

            "delta_hit_5_pp":
                (
                    row[
                        "hit_5_percent"
                    ]
                    -
                    p0_summary[
                        "hit_5_percent"
                    ]
                ),

            "delta_hit_10_pp":
                (
                    row[
                        "hit_10_percent"
                    ]
                    -
                    p0_summary[
                        "hit_10_percent"
                    ]
                ),

            "delta_mrr_10":
                (
                    row[
                        "mrr_10"
                    ]
                    -
                    p0_summary[
                        "mrr_10"
                    ]
                ),
        })

    # ========================================================
    # DELTAS POR QUESTÃO VS P0
    # ========================================================

    metrics_by_key = {
        (
            r["variant"],
            r["id_questao"]
        ): r
        for r in metric_rows
    }

    question_delta_rows = []

    for variant in [
        "P1",
        "P2",
        "P3",
        "P4",
    ]:

        for id_questao in range(
            1,
            131
        ):

            p0 = metrics_by_key[
                (
                    "P0",
                    id_questao
                )
            ]

            current = metrics_by_key[
                (
                    variant,
                    id_questao
                )
            ]

            p0_rank = (
                None
                if (
                    p0[
                        "first_relevant_rank"
                    ] == ""
                )
                else int(
                    p0[
                        "first_relevant_rank"
                    ]
                )
            )

            current_rank = (
                None
                if (
                    current[
                        "first_relevant_rank"
                    ] == ""
                )
                else int(
                    current[
                        "first_relevant_rank"
                    ]
                )
            )

            if (
                p0_rank is None
                and
                current_rank is None
            ):
                rank_change = (
                    "unchanged_miss"
                )

            elif (
                p0_rank is None
                and
                current_rank is not None
            ):
                rank_change = (
                    "new_hit"
                )

            elif (
                p0_rank is not None
                and
                current_rank is None
            ):
                rank_change = (
                    "lost_hit"
                )

            elif (
                current_rank
                < p0_rank
            ):
                rank_change = (
                    "improved"
                )

            elif (
                current_rank
                > p0_rank
            ):
                rank_change = (
                    "worsened"
                )

            else:
                rank_change = (
                    "same_rank"
                )

            question_delta_rows.append({
                "variant":
                    variant,

                "id_questao":
                    id_questao,

                "target_canonical":
                    current[
                        "target_canonical"
                    ],

                "p0_first_rank":
                    (
                        ""
                        if p0_rank is None
                        else p0_rank
                    ),

                "variant_first_rank":
                    (
                        ""
                        if current_rank is None
                        else current_rank
                    ),

                "rank_change":
                    rank_change,

                "delta_hit_1":
                    (
                        current[
                            "hit_1"
                        ]
                        -
                        p0[
                            "hit_1"
                        ]
                    ),

                "delta_hit_3":
                    (
                        current[
                            "hit_3"
                        ]
                        -
                        p0[
                            "hit_3"
                        ]
                    ),

                "delta_hit_5":
                    (
                        current[
                            "hit_5"
                        ]
                        -
                        p0[
                            "hit_5"
                        ]
                    ),

                "delta_hit_10":
                    (
                        current[
                            "hit_10"
                        ]
                        -
                        p0[
                            "hit_10"
                        ]
                    ),

                "delta_rr_10":
                    (
                        current[
                            "reciprocal_rank_10"
                        ]
                        -
                        p0[
                            "reciprocal_rank_10"
                        ]
                    ),
            })

    # ========================================================
    # CASE 11
    # ========================================================

    case11_rows = [
        r
        for r in ranking_rows
        if (
            r[
                "id_questao"
            ] == 11
        )
    ]

    # ========================================================
    # DOWNSTREAM TOP-5
    # ========================================================

    downstream_rows = [
        r
        for r in ranking_rows
        if (
            r[
                "id_questao"
            ]
            in downstream_ids
            and
            r[
                "rank"
            ] <= 5
        )
    ]

    expected_downstream = (
        32
        * 5
        * 5
    )

    if (
        len(downstream_rows)
        != expected_downstream
    ):

        raise RuntimeError(
            "Número inesperado de linhas "
            "downstream Top-5: "
            f"{len(downstream_rows)}"
        )

    # ========================================================
    # SALVAR
    # ========================================================

    write_csv(
        RANKINGS_FILE,
        ranking_rows,
        [
            "variant",
            "id_questao",
            "rank",
            "chunk_id",
            "distance",
            "target_raw",
            "target_canonical",
            "retrieved_canonical",
            "is_target",
            "source",
            "chapter_number",
            "section_number",
            "page",
            "dificuldade",
            "tipo",
            "indice_subjetividade",
        ]
    )

    write_csv(
        QUESTION_METRICS_FILE,
        metric_rows,
        [
            "variant",
            "id_questao",
            "target_canonical",
            "dificuldade",
            "tipo",
            "indice_subjetividade",
            "first_relevant_rank",
            "hit_1",
            "hit_3",
            "hit_5",
            "hit_10",
            "reciprocal_rank_10",
        ]
    )

    write_csv(
        SUMMARY_FILE,
        summary_rows,
        [
            "variant",
            "n_questions",
            "hit_1_count",
            "hit_1_percent",
            "hit_3_count",
            "hit_3_percent",
            "hit_5_count",
            "hit_5_percent",
            "hit_10_count",
            "hit_10_percent",
            "mrr_10",
        ]
    )

    write_csv(
        DELTA_FILE,
        delta_rows,
        [
            "variant",
            "delta_hit_1_pp",
            "delta_hit_3_pp",
            "delta_hit_5_pp",
            "delta_hit_10_pp",
            "delta_mrr_10",
        ]
    )

    write_csv(
        QUESTION_DELTA_FILE,
        question_delta_rows,
        [
            "variant",
            "id_questao",
            "target_canonical",
            "p0_first_rank",
            "variant_first_rank",
            "rank_change",
            "delta_hit_1",
            "delta_hit_3",
            "delta_hit_5",
            "delta_hit_10",
            "delta_rr_10",
        ]
    )

    write_csv(
        CASE11_FILE,
        case11_rows,
        [
            "variant",
            "id_questao",
            "rank",
            "chunk_id",
            "distance",
            "target_raw",
            "target_canonical",
            "retrieved_canonical",
            "is_target",
            "source",
            "chapter_number",
            "section_number",
            "page",
            "dificuldade",
            "tipo",
            "indice_subjetividade",
        ]
    )

    write_csv(
        DOWNSTREAM_TOP5_FILE,
        downstream_rows,
        [
            "variant",
            "id_questao",
            "rank",
            "chunk_id",
            "distance",
            "target_raw",
            "target_canonical",
            "retrieved_canonical",
            "is_target",
            "source",
            "chapter_number",
            "section_number",
            "page",
            "dificuldade",
            "tipo",
            "indice_subjetividade",
        ]
    )

    # ========================================================
    # AUDITORIA
    # ========================================================

    run_info = {
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

        "collection":
            COLLECTION_NAME,

        "top_k":
            TOP_K,

        "questions_per_variant":
            EXPECTED_QUESTIONS,

        "variants":
            VARIANTS,

        "total_queries":
            650,

        "total_ranking_rows":
            len(
                ranking_rows
            ),

        "downstream_cases":
            len(
                downstream_ids
            ),

        "downstream_top5_rows":
            len(
                downstream_rows
            ),

        "database_counts":
            db_counts,

        "question_file_hashes": {
            variant:
                sha256_file(
                    QUESTION_FILES[
                        variant
                    ]
                )
            for variant in VARIANTS
        },

        "p0_corpus_sha256":
            sha256_file(
                P0_CORPUS
            ),

        "downstream_cases_sha256":
            sha256_file(
                DOWNSTREAM_CASES
            ),
    }

    RUNS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with RUN_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            run_info,
            f,
            ensure_ascii=False,
            indent=2
        )

    # ========================================================
    # MOSTRAR RESULTADO
    # ========================================================

    print("\n" + "=" * 72)
    print(
        "RESULTADOS CONTROLADOS P0–P4"
    )
    print("=" * 72)

    for row in summary_rows:

        print(
            f"\n{row['variant']}"
        )

        print(
            "Hit@1:  "
            f"{row['hit_1_count']}/130 "
            f"({row['hit_1_percent']:.2f}%)"
        )

        print(
            "Hit@3:  "
            f"{row['hit_3_count']}/130 "
            f"({row['hit_3_percent']:.2f}%)"
        )

        print(
            "Hit@5:  "
            f"{row['hit_5_count']}/130 "
            f"({row['hit_5_percent']:.2f}%)"
        )

        print(
            "Hit@10: "
            f"{row['hit_10_count']}/130 "
            f"({row['hit_10_percent']:.2f}%)"
        )

        print(
            "MRR@10: "
            f"{row['mrr_10']:.4f}"
        )

    print("\n" + "=" * 72)
    print("ARQUIVOS GERADOS")
    print("=" * 72)

    print(RANKINGS_FILE)
    print(QUESTION_METRICS_FILE)
    print(SUMMARY_FILE)
    print(DELTA_FILE)
    print(QUESTION_DELTA_FILE)
    print(CASE11_FILE)
    print(DOWNSTREAM_TOP5_FILE)
    print(RUN_FILE)


if __name__ == "__main__":
    main()
import csv
import json
import platform
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

sys.path.insert(0, str(BASE_DIR))

from src.chapters import canonicalize_chunk


# ============================================================
# CONFIGURAÇÃO
# ============================================================

DB_PATH = Path(
    r"C:\PLN_EXPERIMENTOS\VECTOR_DB_P0_FRESH"
)

COLLECTION_NAME = "langchain"

MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"

TOP_K = 10


# ============================================================
# ENTRADAS
# ============================================================

QUESTIONS_FILE = (
    BASE_DIR
    / "data"
    / "reference"
    / "spamazon_qa_questions.jsonl"
)

ORIGINAL_QA_FILE = (
    BASE_DIR
    / "SPAmazon-QA.json"
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

RUNS_DIR = (
    BASE_DIR
    / "results"
    / "runs"
)

CASES_DIR = (
    BASE_DIR
    / "results"
    / "cases"
)

RANKINGS_FILE = (
    RAW_DIR
    / "p0_rankings.csv"
)

QUESTION_METRICS_FILE = (
    METRICS_DIR
    / "p0_question_metrics.csv"
)

SUMMARY_FILE = (
    METRICS_DIR
    / "p0_summary.csv"
)

HISTORICAL_COMPARISON_FILE = (
    METRICS_DIR
    / "p0_historical_comparison.csv"
)

CASE11_FILE = (
    CASES_DIR
    / "p0_case_11_top10.csv"
)

RUN_FILE = (
    RUNS_DIR
    / "p0_retrieval_run.json"
)


# ============================================================
# CARREGAMENTO
# ============================================================

def carregar_perguntas():

    perguntas = []

    with QUESTIONS_FILE.open(
        "r",
        encoding="utf-8"
    ) as f:

        for linha in f:
            perguntas.append(
                json.loads(linha)
            )

    perguntas.sort(
        key=lambda x: x["id_questao"]
    )

    return perguntas


def carregar_historico():

    """
    Recupera o booleano capitulo_recuperado
    registrado no SPAmazon-QA para
    AmazoniaExpert.IA.

    Esse campo é apenas histórico.
    Ele NÃO será usado para calcular
    as novas métricas.
    """

    with ORIGINAL_QA_FILE.open(
        "r",
        encoding="utf-8"
    ) as f:

        dados = json.load(f)

    historico = {}

    for registro in dados:

        qid = registro["id_questao"]

        valor = None

        for avaliacao in registro.get(
            "avaliacoes_modelos",
            []
        ):

            if (
                avaliacao.get(
                    "modelo_avaliado"
                )
                == "AmazoniaExpert.IA"
            ):

                valor = avaliacao.get(
                    "capitulo_recuperado"
                )

                break

        historico[qid] = valor

    return historico


# ============================================================
# SALVAR CSV
# ============================================================

def salvar_csv(
    caminho,
    linhas,
    campos
):

    caminho.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with caminho.open(
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
        writer.writerows(linhas)


# ============================================================
# EXECUÇÃO
# ============================================================

def main():

    print("=" * 70)
    print("RECUPERAÇÃO P0 — BASELINE AMAZONIAEXPERT.IA")
    print("=" * 70)

    # --------------------------------------------------------
    # Validar arquivos
    # --------------------------------------------------------

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"ChromaDB não encontrado:\n{DB_PATH}"
        )

    if not QUESTIONS_FILE.exists():
        raise FileNotFoundError(
            f"Perguntas não encontradas:\n"
            f"{QUESTIONS_FILE}"
        )

    # --------------------------------------------------------
    # Perguntas
    # --------------------------------------------------------

    perguntas = carregar_perguntas()

    historico = carregar_historico()

    if len(perguntas) != 130:
        raise RuntimeError(
            f"Esperadas 130 perguntas. "
            f"Encontradas: {len(perguntas)}"
        )

    print(
        f"\nPerguntas carregadas: "
        f"{len(perguntas)}"
    )

    # --------------------------------------------------------
    # Modelo de embeddings
    # --------------------------------------------------------

    print(
        "\nCarregando embeddings:"
    )

    print(MODEL_NAME)

    embeddings = HuggingFaceEmbeddings(
        model_name=MODEL_NAME
    )

    # --------------------------------------------------------
    # ChromaDB
    # --------------------------------------------------------

    print(
        "\nAbrindo ChromaDB P0..."
    )

    client = chromadb.PersistentClient(
        path=str(DB_PATH)
    )

    collection = client.get_collection(
        name=COLLECTION_NAME
    )

    total_chunks = collection.count()

    print(
        f"Chunks no banco: {total_chunks}"
    )

    if total_chunks != 6900:
        raise RuntimeError(
            f"Esperados 6900 chunks. "
            f"Banco contém {total_chunks}."
        )

    # ========================================================
    # RESULTADOS
    # ========================================================

    rankings = []

    metricas = []

    comparacao_historica = []

    case11_rows = []

    # ========================================================
    # CONSULTAS
    # ========================================================

    for numero, questao in enumerate(
        perguntas,
        start=1
    ):

        qid = questao["id_questao"]

        pergunta = questao["pergunta"]

        target = questao[
            "capitulo_alvo_id"
        ]

        print(
            f"[{numero:03d}/130] "
            f"Questão {qid:03d}"
        )

        # ----------------------------------------------------
        # P0:
        # nenhuma transformação linguística
        # ----------------------------------------------------

        query_text = pergunta

        # ----------------------------------------------------
        # Mesmo encoder do TCC
        # ----------------------------------------------------

        query_embedding = (
            embeddings.embed_query(
                query_text
            )
        )

        # ----------------------------------------------------
        # Busca Top-10
        # ----------------------------------------------------

        resultado = collection.query(
            query_embeddings=[
                query_embedding
            ],
            n_results=TOP_K,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

        ids = resultado["ids"][0]

        documentos = (
            resultado["documents"][0]
        )

        metadatas = (
            resultado["metadatas"][0]
        )

        distances = (
            resultado["distances"][0]
        )

        if len(ids) != TOP_K:

            raise RuntimeError(
                f"Questão {qid}: "
                f"esperados {TOP_K} resultados, "
                f"recebidos {len(ids)}."
            )

        ranks_corretos = []

        # ----------------------------------------------------
        # Cada posição do ranking
        # ----------------------------------------------------

        for rank, (
            chunk_id,
            document,
            metadata,
            distance,
        ) in enumerate(
            zip(
                ids,
                documentos,
                metadatas,
                distances,
            ),
            start=1,
        ):

            chapter_id = (
                canonicalize_chunk(
                    metadata
                )
            )

            hit = int(
                chapter_id == target
            )

            if hit:
                ranks_corretos.append(
                    rank
                )

            linha = {
                "question_id": qid,
                "variant": "P0",
                "rank": rank,
                "chunk_id": chunk_id,
                "chapter_original":
                    metadata.get(
                        "chapter_number"
                    ),
                "chapter_id":
                    chapter_id,
                "target_id":
                    target,
                "source":
                    metadata.get(
                        "source"
                    ),
                "page":
                    metadata.get(
                        "page"
                    ),
                "section_number":
                    metadata.get(
                        "section_number"
                    ),
                "distance":
                    distance,
                "hit":
                    hit,
            }

            rankings.append(
                linha
            )

            # Caso sentinela temporal
            if qid == 11:

                case11_rows.append(
                    {
                        **linha,
                        "question":
                            pergunta,
                        "document":
                            document,
                    }
                )

        # ====================================================
        # MÉTRICAS DA QUESTÃO
        # ====================================================

        primeira_posicao = (
            min(ranks_corretos)
            if ranks_corretos
            else None
        )

        hit1 = int(
            primeira_posicao is not None
            and primeira_posicao <= 1
        )

        hit3 = int(
            primeira_posicao is not None
            and primeira_posicao <= 3
        )

        hit5 = int(
            primeira_posicao is not None
            and primeira_posicao <= 5
        )

        hit10 = int(
            primeira_posicao is not None
            and primeira_posicao <= 10
        )

        rr10 = (
            1.0 / primeira_posicao
            if primeira_posicao
            is not None
            else 0.0
        )

        metricas.append(
            {
                "question_id":
                    qid,
                "variant":
                    "P0",
                "target_id":
                    target,
                "tipo":
                    questao["tipo"],
                "dificuldade":
                    questao[
                        "dificuldade"
                    ],
                "hit_at_1":
                    hit1,
                "hit_at_3":
                    hit3,
                "hit_at_5":
                    hit5,
                "hit_at_10":
                    hit10,
                "first_relevant_rank":
                    primeira_posicao,
                "rr_at_10":
                    rr10,
            }
        )

        # ====================================================
        # COMPARAÇÃO COM TCC
        # ====================================================

        historico_q = historico.get(
            qid
        )

        historico_bool = (
            None
            if historico_q is None
            else bool(historico_q)
        )

        novo_bool = bool(hit5)

        concorda = (
            None
            if historico_bool is None
            else (
                historico_bool
                == novo_bool
            )
        )

        comparacao_historica.append(
            {
                "question_id":
                    qid,
                "target_id":
                    target,
                "historical_capitulo_recuperado":
                    historico_bool,
                "p0_canonical_hit_at_5":
                    novo_bool,
                "agreement":
                    concorda,
            }
        )

    # ========================================================
    # VALIDAÇÃO DO RANKING
    # ========================================================

    expected_rows = (
        130 * TOP_K
    )

    if len(rankings) != expected_rows:

        raise RuntimeError(
            f"Esperadas {expected_rows} "
            f"linhas de ranking. "
            f"Obtidas {len(rankings)}."
        )

    # ========================================================
    # MÉTRICAS AGREGADAS
    # ========================================================

    total = len(metricas)

    hit1_total = sum(
        x["hit_at_1"]
        for x in metricas
    )

    hit3_total = sum(
        x["hit_at_3"]
        for x in metricas
    )

    hit5_total = sum(
        x["hit_at_5"]
        for x in metricas
    )

    hit10_total = sum(
        x["hit_at_10"]
        for x in metricas
    )

    mrr10 = sum(
        x["rr_at_10"]
        for x in metricas
    ) / total

    resumo = [
        {
            "variant": "P0",
            "questions": total,
            "hit_at_1_n": hit1_total,
            "hit_at_1": (
                hit1_total / total
            ),
            "hit_at_3_n": hit3_total,
            "hit_at_3": (
                hit3_total / total
            ),
            "hit_at_5_n": hit5_total,
            "hit_at_5": (
                hit5_total / total
            ),
            "hit_at_10_n":
                hit10_total,
            "hit_at_10":
                hit10_total / total,
            "mrr_at_10":
                mrr10,
        }
    ]

    # ========================================================
    # COMPARAÇÃO HISTÓRICA
    # ========================================================

    comparaveis = [
        x
        for x in comparacao_historica
        if x["agreement"]
        is not None
    ]

    concordancias = sum(
        bool(x["agreement"])
        for x in comparaveis
    )

    divergencias = [
        x["question_id"]
        for x in comparaveis
        if not x["agreement"]
    ]

    historico_true = sum(
        x[
            "historical_capitulo_recuperado"
        ]
        is True
        for x in comparaveis
    )

    historico_false = sum(
        x[
            "historical_capitulo_recuperado"
        ]
        is False
        for x in comparaveis
    )

    # ========================================================
    # SALVAR ARQUIVOS
    # ========================================================

    salvar_csv(
        RANKINGS_FILE,
        rankings,
        [
            "question_id",
            "variant",
            "rank",
            "chunk_id",
            "chapter_original",
            "chapter_id",
            "target_id",
            "source",
            "page",
            "section_number",
            "distance",
            "hit",
        ],
    )

    salvar_csv(
        QUESTION_METRICS_FILE,
        metricas,
        [
            "question_id",
            "variant",
            "target_id",
            "tipo",
            "dificuldade",
            "hit_at_1",
            "hit_at_3",
            "hit_at_5",
            "hit_at_10",
            "first_relevant_rank",
            "rr_at_10",
        ],
    )

    salvar_csv(
        SUMMARY_FILE,
        resumo,
        list(
            resumo[0].keys()
        ),
    )

    salvar_csv(
        HISTORICAL_COMPARISON_FILE,
        comparacao_historica,
        [
            "question_id",
            "target_id",
            "historical_capitulo_recuperado",
            "p0_canonical_hit_at_5",
            "agreement",
        ],
    )

    salvar_csv(
        CASE11_FILE,
        case11_rows,
        [
            "question_id",
            "variant",
            "rank",
            "chunk_id",
            "chapter_original",
            "chapter_id",
            "target_id",
            "source",
            "page",
            "section_number",
            "distance",
            "hit",
            "question",
            "document",
        ],
    )

    # ========================================================
    # REGISTRO DA EXECUÇÃO
    # ========================================================

    def versao_pacote(nome):

        try:
            return version(nome)

        except Exception:
            return None

    run_info = {
        "timestamp":
            datetime.now().isoformat(),
        "variant":
            "P0",
        "python":
            platform.python_version(),
        "chromadb":
            versao_pacote(
                "chromadb"
            ),
        "langchain_chroma":
            versao_pacote(
                "langchain-chroma"
            ),
        "langchain_huggingface":
            versao_pacote(
                "langchain-huggingface"
            ),
        "sentence_transformers":
            versao_pacote(
                "sentence-transformers"
            ),
        "embedding_model":
            MODEL_NAME,
        "collection":
            COLLECTION_NAME,
        "corpus_chunks":
            total_chunks,
        "questions":
            total,
        "top_k":
            TOP_K,
        "hit_at_1":
            hit1_total / total,
        "hit_at_3":
            hit3_total / total,
        "hit_at_5":
            hit5_total / total,
        "hit_at_10":
            hit10_total / total,
        "mrr_at_10":
            mrr10,
        "historical_true":
            historico_true,
        "historical_false":
            historico_false,
        "historical_agreements":
            concordancias,
        "historical_disagreements":
            len(divergencias),
        "historical_disagreement_ids":
            divergencias,
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
            indent=2,
        )

    # ========================================================
    # TERMINAL
    # ========================================================

    print("\n" + "=" * 70)
    print("RESULTADO P0")
    print("=" * 70)

    print(
        f"\nHit@1 : "
        f"{hit1_total}/{total} "
        f"({hit1_total / total:.2%})"
    )

    print(
        f"Hit@3 : "
        f"{hit3_total}/{total} "
        f"({hit3_total / total:.2%})"
    )

    print(
        f"Hit@5 : "
        f"{hit5_total}/{total} "
        f"({hit5_total / total:.2%})"
    )

    print(
        f"Hit@10: "
        f"{hit10_total}/{total} "
        f"({hit10_total / total:.2%})"
    )

    print(
        f"MRR@10: {mrr10:.4f}"
    )

    print("\n" + "=" * 70)
    print("COMPARAÇÃO COM O TCC")
    print("=" * 70)

    print(
        f"\nHistórico TRUE: "
        f"{historico_true}"
    )

    print(
        f"Histórico FALSE: "
        f"{historico_false}"
    )

    print(
        f"Concordâncias: "
        f"{concordancias}/"
        f"{len(comparaveis)}"
    )

    print(
        f"Divergências: "
        f"{len(divergencias)}"
    )

    print(
        "IDs divergentes:",
        divergencias,
    )

    # ========================================================
    # CASO 11
    # ========================================================

    print("\n" + "=" * 70)
    print("CASO 11 — RESTRIÇÃO TEMPORAL")
    print("=" * 70)

    for linha in case11_rows:

        marca = (
            " <-- CAPÍTULO-ALVO"
            if linha["hit"]
            else ""
        )

        print(
            f"\nRank "
            f"{linha['rank']}: "
            f"{linha['chapter_id']}"
            f"{marca}"
        )

        print(
            f"Source: "
            f"{linha['source']}"
        )

        print(
            f"Distância: "
            f"{linha['distance']}"
        )

    print("\n" + "=" * 70)
    print("ARQUIVOS GERADOS")
    print("=" * 70)

    print(RANKINGS_FILE)
    print(QUESTION_METRICS_FILE)
    print(SUMMARY_FILE)
    print(HISTORICAL_COMPARISON_FILE)
    print(CASE11_FILE)
    print(RUN_FILE)


if __name__ == "__main__":
    main()
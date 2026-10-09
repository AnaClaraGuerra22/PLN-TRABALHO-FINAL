import argparse
import hashlib
import json
import platform
from datetime import datetime
from importlib.metadata import version
from pathlib import Path

import pandas as pd
from langchain_community.llms import LlamaCpp
from langchain_core.prompts import PromptTemplate


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

CAMINHO_MODELO = Path(
    r"C:\TCCII\MODELO\ClimateChat.i1-Q4_K_M.gguf"
)

P0_CORPUS = (
    BASE_DIR
    / "data"
    / "reference"
    / "p0_chunks.jsonl"
)

CASES_FILE = (
    BASE_DIR
    / "data"
    / "reference"
    / "downstream_critical_cases.jsonl"
)

RETRIEVAL_FILE = (
    BASE_DIR
    / "results"
    / "cases"
    / "downstream_retrieval_top5.csv"
)

OUTPUT_FILE = (
    BASE_DIR
    / "results"
    / "raw"
    / "downstream_responses_rag.csv"
)

OUTPUT_JSONL = (
    BASE_DIR
    / "results"
    / "raw"
    / "downstream_responses_rag.jsonl"
)

RUN_FILE = (
    BASE_DIR
    / "results"
    / "runs"
    / "downstream_generation_run.json"
)

VARIANTS = [
    "P0",
    "P1",
    "P2",
    "P3",
    "P4",
]

EXPECTED_CASES = 32
EXPECTED_RETRIEVAL_ROWS = 800
EXPECTED_GENERATIONS = 160


# ============================================================
# PROMPT ORIGINAL DO AMAZONIAEXPERT.IA
# ============================================================

PROMPT_RAG = PromptTemplate(
    template="""<s>[INST] You are a highly qualified scientific assistant specializing in the sustainable development of the Amazon. 
Your task is to answer the question primarily based on the provided context from the Science Panel for the Amazon (SPA) reports. 

Strict Rules you MUST follow:
1. Direct Answer: Answer exactly what is asked. You may use your internal scientific expertise to complement the information, but do not contradict the context.
2. Conciseness: Keep your answer between 1 to 3 short paragraphs. 
3. No Filler Words: DO NOT use conversational fillers like "Based on the provided text...", "According to the context...", or "In conclusion...". State the facts directly.

Context extracted from SPA reports:
{context}

Question: {question}
Scientific Answer: [/INST]""",
    input_variables=[
        "context",
        "question",
    ],
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
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(bloco)

    return h.hexdigest()


def sha256_text(text):
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


# ============================================================
# CARREGAR CORPUS ORIGINAL P0
# ============================================================

def load_p0_chunks():

    print("=" * 72)
    print("CARREGANDO TEXTOS ORIGINAIS P0")
    print("=" * 72)

    lookup = {}

    with P0_CORPUS.open(
        "r",
        encoding="utf-8"
    ) as f:

        for line in f:

            record = json.loads(line)

            chunk_id = str(
                record["chunk_id"]
            )

            if chunk_id in lookup:
                raise RuntimeError(
                    f"Chunk duplicado: {chunk_id}"
                )

            lookup[chunk_id] = {
                "document":
                    record["document"],

                "metadata":
                    record["metadata"],
            }

    if len(lookup) != 6900:

        raise RuntimeError(
            "Esperados 6900 chunks em P0; "
            f"encontrados {len(lookup)}."
        )

    print(
        f"Chunks P0 carregados: {len(lookup)}"
    )

    return lookup


# ============================================================
# CARREGAR CASOS CRÍTICOS
# ============================================================

def load_cases():

    print("\n" + "=" * 72)
    print("CARREGANDO 32 CASOS CRÍTICOS")
    print("=" * 72)

    cases = {}

    with CASES_FILE.open(
        "r",
        encoding="utf-8"
    ) as f:

        for line in f:

            record = json.loads(line)

            qid = int(
                record["id_questao"]
            )

            if qid in cases:
                raise RuntimeError(
                    f"Questão duplicada: {qid}"
                )

            cases[qid] = record

    if len(cases) != EXPECTED_CASES:

        raise RuntimeError(
            f"Esperados {EXPECTED_CASES} casos; "
            f"encontrados {len(cases)}."
        )

    print(
        f"Casos críticos: {len(cases)}"
    )

    print(
        "IDs:"
    )

    print(
        sorted(cases)
    )

    return cases


# ============================================================
# CARREGAR TOP-5 CONGELADO
# ============================================================

def load_retrieval():

    print("\n" + "=" * 72)
    print("VALIDANDO TOP-5 CONGELADO")
    print("=" * 72)

    df = pd.read_csv(
        RETRIEVAL_FILE,
        encoding="utf-8-sig"
    )

    if len(df) != EXPECTED_RETRIEVAL_ROWS:

        raise RuntimeError(
            "Número inesperado de linhas: "
            f"{len(df)}. "
            f"Esperadas {EXPECTED_RETRIEVAL_ROWS}."
        )

    required = {
        "variant",
        "id_questao",
        "rank",
        "chunk_id",
    }

    missing = (
        required
        - set(df.columns)
    )

    if missing:

        raise RuntimeError(
            "Colunas ausentes: "
            f"{sorted(missing)}"
        )

    df["id_questao"] = (
        df["id_questao"]
        .astype(int)
    )

    df["rank"] = (
        df["rank"]
        .astype(int)
    )

    df["chunk_id"] = (
        df["chunk_id"]
        .astype(str)
    )

    # --------------------------------------------------------
    # Validar variantes
    # --------------------------------------------------------

    found_variants = sorted(
        df["variant"]
        .unique()
        .tolist()
    )

    if (
        found_variants
        != sorted(VARIANTS)
    ):

        raise RuntimeError(
            "Variantes inesperadas: "
            f"{found_variants}"
        )

    # --------------------------------------------------------
    # Cada questão/variante deve ter exatamente ranks 1..5
    # --------------------------------------------------------

    for (
        variant,
        qid
    ), group in df.groupby(
        [
            "variant",
            "id_questao",
        ]
    ):

        ranks = sorted(
            group["rank"]
            .tolist()
        )

        if ranks != [
            1, 2, 3, 4, 5
        ]:

            raise RuntimeError(
                f"{variant} / Q{qid}: "
                f"ranks inválidos: {ranks}"
            )

    combinations = (
        df[
            [
                "variant",
                "id_questao",
            ]
        ]
        .drop_duplicates()
    )

    if len(combinations) != EXPECTED_GENERATIONS:

        raise RuntimeError(
            "Esperadas 160 combinações "
            "questão-variante; "
            f"encontradas {len(combinations)}."
        )

    print(
        f"Linhas Top-5: {len(df)}"
    )

    print(
        "Combinações questão-variante: "
        f"{len(combinations)}"
    )

    print(
        "Top-5 congelado validado."
    )

    return df


# ============================================================
# VALIDAR INTEGRIDADE ENTRE OS ARQUIVOS
# ============================================================

def validate_integrity(
    p0_lookup,
    cases,
    retrieval,
):

    print("\n" + "=" * 72)
    print("AUDITORIA DE INTEGRIDADE")
    print("=" * 72)

    retrieval_ids = set(
        retrieval[
            "id_questao"
        ].unique()
    )

    case_ids = set(
        cases.keys()
    )

    if retrieval_ids != case_ids:

        raise RuntimeError(
            "IDs dos casos críticos e "
            "retrieval não coincidem.\n"
            f"Apenas cases: "
            f"{sorted(case_ids - retrieval_ids)}\n"
            f"Apenas retrieval: "
            f"{sorted(retrieval_ids - case_ids)}"
        )

    missing_chunks = []

    for chunk_id in (
        retrieval[
            "chunk_id"
        ].tolist()
    ):

        if chunk_id not in p0_lookup:
            missing_chunks.append(
                chunk_id
            )

    if missing_chunks:

        raise RuntimeError(
            "Chunks do Top-5 ausentes "
            "no corpus P0: "
            f"{missing_chunks[:10]}"
        )

    print(
        "32 IDs coincidem."
    )

    print(
        "Todos os 800 chunk IDs existem "
        "no corpus P0."
    )

    print(
        "Nenhuma nova recuperação será executada."
    )


# ============================================================
# MONTAR CONTEXTO ORIGINAL
# ============================================================

def build_context(
    subset,
    p0_lookup,
):

    subset = (
        subset
        .sort_values("rank")
    )

    texts = []

    chunk_ids = []
    sources = []
    pages = []
    chapters = []

    for _, row in subset.iterrows():

        chunk_id = str(
            row["chunk_id"]
        )

        ref = p0_lookup[
            chunk_id
        ]

        document = ref[
            "document"
        ]

        metadata = ref[
            "metadata"
        ]

        rank = int(
            row["rank"]
        )

        # EXATAMENTE como o script original do TCC:
        texts.append(
            f"[Trecho {rank}]: {document}"
        )

        chunk_ids.append(
            chunk_id
        )

        sources.append(
            str(
                metadata.get(
                    "source",
                    ""
                )
            )
        )

        pages.append(
            str(
                metadata.get(
                    "page",
                    ""
                )
            )
        )

        chapters.append(
            str(
                metadata.get(
                    "chapter_number",
                    ""
                )
            )
        )

    context = (
        "\n\n".join(
            texts
        )
    )

    return {
        "context":
            context,

        "chunk_ids":
            chunk_ids,

        "sources":
            sources,

        "pages":
            pages,

        "chapters":
            chapters,
    }


# ============================================================
# CARREGAR CHECKPOINT DE GERAÇÃO
# ============================================================

def load_existing_results():

    if not OUTPUT_FILE.exists():

        return pd.DataFrame()

    print(
        "\nArquivo de saída existente encontrado."
    )

    print(
        "O script continuará de onde parou."
    )

    df = pd.read_csv(
        OUTPUT_FILE,
        encoding="utf-8-sig"
    )

    return df


# ============================================================
# SALVAR RESULTADOS
# ============================================================

def save_results(rows):

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    df = pd.DataFrame(rows)

    df = df.sort_values(
        [
            "id_questao",
            "variant",
        ]
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    with OUTPUT_JSONL.open(
        "w",
        encoding="utf-8"
    ) as f:

        for record in (
            df.to_dict(
                orient="records"
            )
        ):

            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False
                )
                + "\n"
            )


# ============================================================
# MAIN
# ============================================================

def main(
    validate_only=False
):

    print("=" * 72)
    print(
        "GERAÇÃO DOWNSTREAM — "
        "AMAZONIAEXPERT.IA P0–P4"
    )
    print("=" * 72)

    print(
        "\nIMPORTANTE:"
    )

    print(
        "- somente geração RAG;"
    )

    print(
        "- nenhuma execução ClimateChat zero-shot;"
    )

    print(
        "- nenhuma nova recuperação vetorial;"
    )

    print(
        "- Top-5 já congelado;"
    )

    print(
        "- chunks enviados ao gerador "
        "sempre em texto ORIGINAL P0;"
    )

    print(
        "- pergunta enviada ao gerador "
        "sempre ORIGINAL."
    )

    # ========================================================
    # VALIDAR ARQUIVOS
    # ========================================================

    if not CAMINHO_MODELO.exists():

        raise FileNotFoundError(
            f"Modelo não encontrado:\n"
            f"{CAMINHO_MODELO}"
        )

    p0_lookup = (
        load_p0_chunks()
    )

    cases = (
        load_cases()
    )

    retrieval = (
        load_retrieval()
    )

    validate_integrity(
        p0_lookup,
        cases,
        retrieval,
    )

    # ========================================================
    # VALIDATE-ONLY
    # ========================================================

    if validate_only:

        print("\n" + "=" * 72)
        print(
            "VALIDAÇÃO CONCLUÍDA COM SUCESSO"
        )
        print("=" * 72)

        print(
            "Nenhuma resposta foi gerada."
        )

        return

    # ========================================================
    # CARREGAR CLIMATECHAT
    # ========================================================

    print("\n" + "=" * 72)
    print(
        "CARREGANDO CLIMATECHAT"
    )
    print("=" * 72)

    print(
        CAMINHO_MODELO
    )

    llm = LlamaCpp(
        model_path=str(
            CAMINHO_MODELO
        ),

        temperature=0.1,

        max_tokens=2048,

        n_ctx=8192,

        n_gpu_layers=0,

        repeat_penalty=1.15,

        top_p=0.9,

        stop=[
            "</s>",
            "Question:",
            "[INST]",
        ],

        verbose=False,
    )

    print(
        "ClimateChat carregado."
    )

    # ========================================================
    # RESUME
    # ========================================================

    existing = (
        load_existing_results()
    )

    if existing.empty:

        rows = []

        completed = set()

    else:

        rows = (
            existing
            .to_dict(
                orient="records"
            )
        )

        completed = {
            (
                int(row["id_questao"]),
                str(row["variant"]),
            )
            for row in rows
        }

        print(
            "Respostas já existentes: "
            f"{len(completed)}"
        )

    # ========================================================
    # GERAÇÃO
    # ========================================================

    total = (
        EXPECTED_GENERATIONS
    )

    generated_now = 0

    for qid in sorted(
        cases.keys()
    ):

        case = cases[
            qid
        ]

        pergunta_original = (
            case[
                "pergunta"
            ]
        )

        for variant in VARIANTS:

            key = (
                qid,
                variant,
            )

            if key in completed:

                print(
                    f"[SKIP] Q{qid} / "
                    f"{variant}"
                )

                continue

            subset = retrieval[
                (
                    retrieval[
                        "id_questao"
                    ] == qid
                )
                &
                (
                    retrieval[
                        "variant"
                    ] == variant
                )
            ]

            context_data = (
                build_context(
                    subset,
                    p0_lookup,
                )
            )

            contexto = (
                context_data[
                    "context"
                ]
            )

            prompt_final = (
                PROMPT_RAG.format(
                    context=contexto,
                    question=pergunta_original,
                )
            )

            current_number = (
                len(completed)
                + generated_now
                + 1
            )

            print(
                "\n"
                + "-" * 72
            )

            print(
                f"[{current_number}/{total}] "
                f"Q{qid} / {variant}"
            )

            print(
                pergunta_original[:100]
            )

            print(
                "Gerando resposta "
                "AmazoniaExpert.IA..."
            )

            resposta = (
                llm.invoke(
                    prompt_final
                )
                .strip()
            )

            if not resposta:

                raise RuntimeError(
                    f"Resposta vazia: "
                    f"Q{qid} / {variant}"
                )

            row = {
                "id_questao":
                    qid,

                "variant":
                    variant,

                "pergunta":
                    pergunta_original,

                "gabarito":
                    case[
                        "gabarito"
                    ],

                "capitulo_alvo":
                    case[
                        "capitulo_alvo"
                    ],

                "dificuldade":
                    case[
                        "dificuldade"
                    ],

                "tipo":
                    case[
                        "tipo"
                    ],

                "nota_historica":
                    case[
                        "nota_historica"
                    ],

                "capitulo_recuperado_historico":
                    case[
                        "capitulo_recuperado_historico"
                    ],

                "resposta_historica_amazoniaexpert":
                    case[
                        "resposta_historica_amazoniaexpert"
                    ],

                "resposta_rag":
                    resposta,

                "chunk_ids_top5":
                    " | ".join(
                        context_data[
                            "chunk_ids"
                        ]
                    ),

                "chapters_top5":
                    " | ".join(
                        context_data[
                            "chapters"
                        ]
                    ),

                "pages_top5":
                    " | ".join(
                        context_data[
                            "pages"
                        ]
                    ),

                "sources_top5":
                    " | ".join(
                        context_data[
                            "sources"
                        ]
                    ),

                "context_sha256":
                    sha256_text(
                        contexto
                    ),

                "prompt_sha256":
                    sha256_text(
                        prompt_final
                    ),
            }

            rows.append(
                row
            )

            generated_now += 1

            # --------------------------------------------
            # CHECKPOINT A CADA RESPOSTA
            # --------------------------------------------

            save_results(
                rows
            )

            print(
                "Resposta salva."
            )

    # ========================================================
    # VALIDAÇÃO FINAL
    # ========================================================

    final_df = pd.read_csv(
        OUTPUT_FILE,
        encoding="utf-8-sig"
    )

    final_keys = set(
        zip(
            final_df[
                "id_questao"
            ].astype(int),

            final_df[
                "variant"
            ].astype(str),
        )
    )

    if len(final_df) != EXPECTED_GENERATIONS:

        raise RuntimeError(
            "Número final de respostas "
            "inesperado: "
            f"{len(final_df)}"
        )

    if len(final_keys) != EXPECTED_GENERATIONS:

        raise RuntimeError(
            "Há combinações duplicadas "
            "ou ausentes no resultado."
        )

    empty = (
        final_df[
            "resposta_rag"
        ]
        .fillna("")
        .str.strip()
        .eq("")
        .sum()
    )

    if empty:

        raise RuntimeError(
            f"Há {empty} respostas vazias."
        )

    # ========================================================
    # AUDITORIA
    # ========================================================

    RUN_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    run_info = {
        "timestamp":
            datetime.now().isoformat(),

        "python":
            platform.python_version(),

        "llama_cpp_python":
            package_version(
                "llama-cpp-python"
            ),

        "langchain_community":
            package_version(
                "langchain-community"
            ),

        "model_path":
            str(
                CAMINHO_MODELO
            ),

        "model_filename":
            CAMINHO_MODELO.name,

        "generator":
            "ClimateChat.i1-Q4_K_M.gguf",

        "architecture":
            "AmazoniaExpert.IA RAG",

        "zero_shot_generated":
            False,

        "new_vector_search_performed":
            False,

        "retrieval_source":
            str(
                RETRIEVAL_FILE
            ),

        "retrieval_sha256":
            sha256_file(
                RETRIEVAL_FILE
            ),

        "p0_corpus_sha256":
            sha256_file(
                P0_CORPUS
            ),

        "critical_cases_sha256":
            sha256_file(
                CASES_FILE
            ),

        "n_cases":
            EXPECTED_CASES,

        "variants":
            VARIANTS,

        "n_responses":
            EXPECTED_GENERATIONS,

        "top_k_generation":
            5,

        "temperature":
            0.1,

        "max_tokens":
            2048,

        "n_ctx":
            8192,

        "n_gpu_layers":
            0,

        "repeat_penalty":
            1.15,

        "top_p":
            0.9,

        "stop":
            [
                "</s>",
                "Question:",
                "[INST]",
            ],

        "question_to_generator":
            "original",

        "context_text":
            "original P0 chunk text",

        "prompt_template":
            PROMPT_RAG.template,

        "output_csv":
            str(
                OUTPUT_FILE
            ),

        "output_jsonl":
            str(
                OUTPUT_JSONL
            ),
    }

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

    print("\n" + "=" * 72)
    print(
        "GERAÇÃO DOWNSTREAM CONCLUÍDA"
    )
    print("=" * 72)

    print(
        f"Casos: {EXPECTED_CASES}"
    )

    print(
        "Variantes por caso: 5"
    )

    print(
        "Respostas RAG: "
        f"{len(final_df)}"
    )

    print(
        "Respostas vazias: 0"
    )

    print(
        "\nCSV:"
    )

    print(
        OUTPUT_FILE
    )

    print(
        "\nJSONL:"
    )

    print(
        OUTPUT_JSONL
    )

    print(
        "\nAuditoria:"
    )

    print(
        RUN_FILE
    )


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help=(
            "Valida entradas e Top-5 "
            "sem carregar o ClimateChat."
        ),
    )

    args = parser.parse_args()

    main(
        validate_only=args.validate_only
    )
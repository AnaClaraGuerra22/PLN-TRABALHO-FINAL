import argparse
import hashlib
import json
import os
import platform
import re
import time
from datetime import datetime
from importlib.metadata import version
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

# Mesmo .env utilizado no código original do TCC.
CAMINHO_ENV = Path(
    r"C:\TCCII\UNSTRUCTURED\.env"
)

INPUT_CSV = (
    BASE_DIR
    / "results"
    / "raw"
    / "downstream_responses_rag.csv"
)

INPUT_JSONL = (
    BASE_DIR
    / "results"
    / "raw"
    / "downstream_responses_rag.jsonl"
)

GENERATION_RUN_FILE = (
    BASE_DIR
    / "results"
    / "runs"
    / "downstream_generation_run.json"
)

OUTPUT_CSV = (
    BASE_DIR
    / "results"
    / "raw"
    / "downstream_judge_evaluations.csv"
)

OUTPUT_JSONL = (
    BASE_DIR
    / "results"
    / "raw"
    / "downstream_judge_evaluations.jsonl"
)

RUN_FILE = (
    BASE_DIR
    / "results"
    / "runs"
    / "downstream_judge_run.json"
)

PREFLIGHT_FILE = (
    BASE_DIR
    / "results"
    / "runs"
    / "downstream_judge_preflight.json"
)

GENERATOR_MODEL_PATH = Path(
    r"C:\TCCII\MODELO\ClimateChat.i1-Q4_K_M.gguf"
)

GROQ_URL = (
    "https://api.groq.com/openai/v1/chat/completions"
)

# Prompt e estrutura de julgamento preservados do juiz_climatechatrag.py original do TCC.
# O modelo histórico Llama 3.3 70B deixou de estar disponível para esta conta;
# por isso a nova avaliação usa o substituto oficial atual openai/gpt-oss-120b.
LEGACY_JUDGE_MODEL = "llama-3.3-70b-versatile"
JUDGE_MODEL = "openai/gpt-oss-120b"
JUDGE_TEMPERATURE = 0.0
JUDGE_REASONING_EFFORT = "medium"

EXPECTED_CASES = 32
EXPECTED_CONTROLLED = 160
EXPECTED_TOTAL_ROWS = 192

EXPECTED_VARIANTS = [
    "P0",
    "P1",
    "P2",
    "P3",
    "P4",
]

EXPECTED_GENERATION_PROTOCOL = (
    "downstream-rag-fixed-seed-v2"
)

EXPECTED_GENERATION_SEED = 42

# Controle de robustez da nova execução.
MAX_RETRIES = 5

# O código original aguardava 60 s em HTTP 429.
RATE_LIMIT_WAIT_SECONDS = 60

# O código original aguardava 2 s entre avaliações.
INTER_CALL_SLEEP_SECONDS = 2

JUDGE_PROTOCOL_VERSION = (
    "judge-tcc-prompt-gptoss120b-dedup-v3"
)


# ============================================================
# PROMPT EXATO DO JUIZ UTILIZADO NO TCC
# ============================================================

# IMPORTANTE:
# Este texto foi copiado literalmente do arquivo original
# C:\TCCII\JUIZ\juiz_climatechatrag.py fornecido pela autora.
#
# Mantemos inclusive:
# - "Professor Doutor especialista na Amazônia";
# - o rótulo "2 [Macia]";
# - as chaves JSON "nota" e "justificativa";
# - uma única mensagem com role="user";
# - sem system prompt separado.
#
# Não corrigir o termo "Macia", pois isso mudaria o instrumento
# em relação ao código original do TCC.

def montar_prompt_original(
    pergunta,
    gabarito,
    resposta_ia,
):
    return f"""Você é um Professor Doutor especialista na Amazônia. 
Avalie a resposta de IA comparando com o Gabarito.

Escala Likert 1-5:
1 [Incorreta]: Errada ou irrelevante.
2 [Macia]: Omitiu pontos centrais.
3 [Parcial]: Incompleta ou rasa.
4 [Boa]: Correta com falhas mínimas.
5 [Excelente]: Perfeita e científica.

PERGUNTA: {pergunta}
GABARITO: {gabarito}
RESPOSTA DA IA: {resposta_ia}

IMPORTANTE: Responda APENAS no formato JSON exatamente como o exemplo:
{{"nota": 5, "justificativa": "A resposta cobre todos os pontos do gabarito."}}
"""


# ============================================================
# UTILIDADES
# ============================================================

def package_version(name):
    try:
        return version(name)
    except Exception:
        return None


def now_iso():
    return datetime.now().isoformat()


def sha256_text(text):
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def ensure_file(path, label):
    if not path.exists():
        raise FileNotFoundError(
            f"{label} não encontrado:\n{path}"
        )


def normalize_text(value):
    if pd.isna(value):
        return ""

    return str(value)


def build_judge_input_sha(
    question,
    reference,
    answer,
):
    """
    Hash apenas do conteúdo efetivamente relevante ao julgamento.

    Não inclui:
    - P0/P1/P2/P3/P4;
    - histórico/controlado;
    - nota histórica;
    - metadados de retrieval.

    Portanto, entradas textualmente idênticas são identificadas como
    a mesma tarefa de julgamento.
    """

    canonical = (
        normalize_text(question)
        + "\n<<<REFERENCE>>>\n"
        + normalize_text(reference)
        + "\n<<<ANSWER>>>\n"
        + normalize_text(answer)
    )

    return sha256_text(canonical)


def build_judge_prompt_sha(
    question,
    reference,
    answer,
):
    prompt = montar_prompt_original(
        question,
        reference,
        answer,
    )

    return sha256_text(prompt)


# ============================================================
# JSON — MESMA LÓGICA DO CÓDIGO ORIGINAL
# ============================================================

def extrair_json(texto):
    """
    Reproduz a estratégia do juiz_climatechatrag.py original:
    procura primeiro um objeto {...}; se não encontrar, tenta
    interpretar a resposta inteira como JSON.
    """

    try:
        match = re.search(
            r"\{.*\}",
            texto,
            re.DOTALL,
        )

        if match:
            return json.loads(
                match.group()
            )

        return json.loads(texto)

    except Exception:
        return None


def validar_veredito(
    dados,
    texto_resposta,
):
    if not isinstance(
        dados,
        dict,
    ):
        raise ValueError(
            "Resposta do juiz não pôde ser "
            "interpretada como objeto JSON."
        )

    if "nota" not in dados:
        raise ValueError(
            "Campo `nota` ausente no JSON do juiz."
        )

    if "justificativa" not in dados:
        raise ValueError(
            "Campo `justificativa` ausente "
            "no JSON do juiz."
        )

    nota_raw = dados["nota"]

    # O TCC usa escala INTEIRA 1-5.
    if isinstance(
        nota_raw,
        bool,
    ):
        raise ValueError(
            "Nota booleana é inválida."
        )

    if isinstance(
        nota_raw,
        int,
    ):
        nota = nota_raw

    elif (
        isinstance(
            nota_raw,
            float,
        )
        and nota_raw.is_integer()
    ):
        nota = int(nota_raw)

    elif (
        isinstance(
            nota_raw,
            str,
        )
        and nota_raw.strip().isdigit()
    ):
        nota = int(
            nota_raw.strip()
        )

    else:
        raise ValueError(
            "A nota retornada não é inteira."
        )

    if nota not in [
        1,
        2,
        3,
        4,
        5,
    ]:
        raise ValueError(
            "Nota fora da escala 1-5: "
            f"{nota}"
        )

    justificativa = str(
        dados["justificativa"]
    ).strip()

    if not justificativa:
        raise ValueError(
            "Justificativa vazia."
        )

    return {
        "nota": nota,
        "justificativa":
            justificativa,
        "raw_json":
            texto_resposta,
    }


# ============================================================
# VALIDAÇÃO DA GERAÇÃO DOWNSTREAM
# ============================================================

def load_generation_run():
    ensure_file(
        GENERATION_RUN_FILE,
        "Auditoria da geração downstream",
    )

    with GENERATION_RUN_FILE.open(
        "r",
        encoding="utf-8",
    ) as f:
        run = json.load(f)

    if (
        run.get(
            "protocol_version"
        )
        != EXPECTED_GENERATION_PROTOCOL
    ):
        raise RuntimeError(
            "Protocolo downstream inesperado: "
            f"{run.get('protocol_version')}"
        )

    if (
        int(
            run.get(
                "n_responses",
                -1,
            )
        )
        != EXPECTED_CONTROLLED
    ):
        raise RuntimeError(
            "A auditoria downstream não registra "
            "160 respostas."
        )

    if (
        int(
            run.get(
                "seed",
                -1,
            )
        )
        != EXPECTED_GENERATION_SEED
    ):
        raise RuntimeError(
            "A auditoria downstream não registra "
            "seed=42."
        )

    if (
        run.get(
            "new_vector_search_performed"
        )
        is not False
    ):
        raise RuntimeError(
            "A auditoria indica nova busca "
            "vetorial. Não prosseguir."
        )

    if (
        run.get(
            "zero_shot_generated"
        )
        is not False
    ):
        raise RuntimeError(
            "A auditoria indica geração "
            "zero-shot. Não prosseguir."
        )

    if (
        run.get(
            "question_to_generator"
        )
        != "original"
    ):
        raise RuntimeError(
            "A pergunta enviada ao gerador "
            "não está registrada como original."
        )

    if (
        run.get(
            "context_text"
        )
        != "original P0 chunk text"
    ):
        raise RuntimeError(
            "O contexto enviado ao gerador não "
            "está registrado como texto P0 original."
        )

    return run


def load_and_validate_controlled():
    print("=" * 76)
    print(
        "VALIDAÇÃO DA ENTRADA DO JUIZ LLM"
    )
    print("=" * 76)

    ensure_file(
        INPUT_CSV,
        "CSV de respostas downstream",
    )

    df = pd.read_csv(
        INPUT_CSV,
        encoding="utf-8-sig",
    )

    required = {
        "id_questao",
        "variant",
        "pergunta",
        "gabarito",
        "nota_historica",
        "resposta_historica_amazoniaexpert",
        "resposta_rag",
        "response_sha256",
        "generation_seed",
        "protocol_version",
    }

    missing = required - set(
        df.columns
    )

    if missing:
        raise RuntimeError(
            "Colunas ausentes no CSV downstream: "
            f"{sorted(missing)}"
        )

    if len(df) != EXPECTED_CONTROLLED:
        raise RuntimeError(
            f"Esperadas {EXPECTED_CONTROLLED} linhas; "
            f"encontradas {len(df)}."
        )

    df["id_questao"] = (
        df[
            "id_questao"
        ].astype(int)
    )

    df["variant"] = (
        df[
            "variant"
        ].astype(str)
    )

    if (
        df[
            "id_questao"
        ].nunique()
        != EXPECTED_CASES
    ):
        raise RuntimeError(
            "O CSV não contém exatamente "
            "32 questões."
        )

    variant_counts = (
        df[
            "variant"
        ]
        .value_counts()
        .to_dict()
    )

    expected_counts = {
        variant: EXPECTED_CASES
        for variant in EXPECTED_VARIANTS
    }

    if (
        variant_counts
        != expected_counts
    ):
        raise RuntimeError(
            "Contagem inesperada de variantes: "
            f"{variant_counts}"
        )

    duplicates = df.duplicated(
        subset=[
            "id_questao",
            "variant",
        ]
    ).sum()

    if duplicates:
        raise RuntimeError(
            f"Há {duplicates} combinações "
            "questão-variante duplicadas."
        )

    for col in [
        "pergunta",
        "gabarito",
        "resposta_rag",
        "resposta_historica_amazoniaexpert",
    ]:
        empty = (
            df[col]
            .fillna("")
            .astype(str)
            .str.strip()
            .eq("")
            .sum()
        )

        if empty:
            raise RuntimeError(
                f"A coluna {col} contém "
                f"{empty} valores vazios."
            )

    protocols = set(
        df[
            "protocol_version"
        ].astype(str)
    )

    if protocols != {
        EXPECTED_GENERATION_PROTOCOL
    }:
        raise RuntimeError(
            "Protocolos downstream misturados: "
            f"{protocols}"
        )

    seeds = set(
        pd.to_numeric(
            df[
                "generation_seed"
            ],
            errors="raise",
        ).astype(int)
    )

    if seeds != {
        EXPECTED_GENERATION_SEED
    }:
        raise RuntimeError(
            "Seeds downstream inesperadas: "
            f"{seeds}"
        )

    # Confere os hashes das 160 respostas geradas.
    bad_hashes = []

    for _, row in df.iterrows():
        actual = sha256_text(
            str(
                row[
                    "resposta_rag"
                ]
            )
        )

        expected = str(
            row[
                "response_sha256"
            ]
        )

        if actual != expected:
            bad_hashes.append(
                (
                    int(
                        row[
                            "id_questao"
                        ]
                    ),
                    str(
                        row[
                            "variant"
                        ]
                    ),
                )
            )

    if bad_hashes:
        raise RuntimeError(
            "Hashes de respostas não conferem: "
            f"{bad_hashes[:10]}"
        )

    # Confirma que os dados comuns da questão não mudam
    # entre P0-P4.
    invariant_cols = [
        "pergunta",
        "gabarito",
        "resposta_historica_amazoniaexpert",
        "nota_historica",
    ]

    for qid, group in df.groupby(
        "id_questao"
    ):
        for col in invariant_cols:
            values = (
                group[col]
                .fillna("<NA>")
                .astype(str)
                .unique()
            )

            if len(values) != 1:
                raise RuntimeError(
                    f"Q{qid}: coluna {col} "
                    "muda entre P0-P4."
                )

    print(
        "160 respostas controladas: OK"
    )
    print(
        "32 questões × 5 variantes: OK"
    )
    print(
        "Respostas vazias: 0"
    )
    print(
        "Combinações duplicadas: 0"
    )
    print(
        "Hashes das 160 respostas: OK"
    )
    print(
        "Seed downstream = 42: OK"
    )
    print(
        "Protocolo downstream = "
        f"{EXPECTED_GENERATION_PROTOCOL}: OK"
    )

    return df


# ============================================================
# CONSTRUIR AS 192 LINHAS DE AVALIAÇÃO
# ============================================================

def build_evaluation_rows(
    controlled_df,
):
    rows = []

    # --------------------------------------------------------
    # 160 respostas controladas P0-P4
    # --------------------------------------------------------

    for _, row in controlled_df.iterrows():
        question = normalize_text(
            row[
                "pergunta"
            ]
        )

        reference = normalize_text(
            row[
                "gabarito"
            ]
        )

        answer = normalize_text(
            row[
                "resposta_rag"
            ]
        )

        rows.append({
            "evaluation_scope":
                "controlled",
            "id_questao":
                int(
                    row[
                        "id_questao"
                    ]
                ),
            "variant":
                str(
                    row[
                        "variant"
                    ]
                ),
            "pergunta":
                question,
            "gabarito":
                reference,
            "resposta_avaliada":
                answer,
            "nota_historica":
                row[
                    "nota_historica"
                ],
            "source_response_sha256":
                sha256_text(
                    answer
                ),
            "judge_input_sha256":
                build_judge_input_sha(
                    question,
                    reference,
                    answer,
                ),
            "judge_prompt_sha256":
                build_judge_prompt_sha(
                    question,
                    reference,
                    answer,
                ),
            "generation_seed":
                EXPECTED_GENERATION_SEED,
            "generation_protocol":
                EXPECTED_GENERATION_PROTOCOL,
        })

    # --------------------------------------------------------
    # 32 respostas históricas do AmazoniaExpert.IA
    # --------------------------------------------------------

    historical = (
        controlled_df
        .sort_values(
            [
                "id_questao",
                "variant",
            ]
        )
        .drop_duplicates(
            subset=[
                "id_questao"
            ],
            keep="first",
        )
    )

    for _, row in historical.iterrows():
        question = normalize_text(
            row[
                "pergunta"
            ]
        )

        reference = normalize_text(
            row[
                "gabarito"
            ]
        )

        answer = normalize_text(
            row[
                "resposta_historica_amazoniaexpert"
            ]
        )

        rows.append({
            "evaluation_scope":
                "historical",
            "id_questao":
                int(
                    row[
                        "id_questao"
                    ]
                ),
            "variant":
                "HIST",
            "pergunta":
                question,
            "gabarito":
                reference,
            "resposta_avaliada":
                answer,
            "nota_historica":
                row[
                    "nota_historica"
                ],
            "source_response_sha256":
                sha256_text(
                    answer
                ),
            "judge_input_sha256":
                build_judge_input_sha(
                    question,
                    reference,
                    answer,
                ),
            "judge_prompt_sha256":
                build_judge_prompt_sha(
                    question,
                    reference,
                    answer,
                ),
            "generation_seed":
                None,
            "generation_protocol":
                "historical-tcc",
        })

    if (
        len(rows)
        != EXPECTED_TOTAL_ROWS
    ):
        raise RuntimeError(
            "Esperadas 192 linhas para julgamento; "
            f"criadas {len(rows)}."
        )

    df_eval = pd.DataFrame(
        rows
    )

    n_unique = int(
        df_eval[
            "judge_input_sha256"
        ].nunique()
    )

    print(
        "\n"
        + "=" * 76
    )
    print(
        "PLANO DE AVALIAÇÃO"
    )
    print("=" * 76)

    print(
        "Registros finais de avaliação: "
        f"{len(df_eval)}"
    )
    print(
        "  - controlados P0-P4: 160"
    )
    print(
        "  - históricos: 32"
    )
    print(
        "Entradas únicas para o Juiz LLM: "
        f"{n_unique}"
    )
    print(
        "Entradas duplicadas exatas serão avaliadas "
        "uma única vez e terão o mesmo veredito "
        "propagado para todas as linhas equivalentes."
    )

    return df_eval


# ============================================================
# PREFLIGHT / CONGELAMENTO
# ============================================================

def create_preflight(
    df_eval,
    generation_run,
):
    PREFLIGHT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # O hash abaixo caracteriza o instrumento exato:
    # prompt fixo sem os valores de pergunta/gabarito/resposta.
    prompt_template_literal = """Você é um Professor Doutor especialista na Amazônia. 
Avalie a resposta de IA comparando com o Gabarito.

Escala Likert 1-5:
1 [Incorreta]: Errada ou irrelevante.
2 [Macia]: Omitiu pontos centrais.
3 [Parcial]: Incompleta ou rasa.
4 [Boa]: Correta com falhas mínimas.
5 [Excelente]: Perfeita e científica.

PERGUNTA: {pergunta}
GABARITO: {gabarito}
RESPOSTA DA IA: {resposta_ia}

IMPORTANTE: Responda APENAS no formato JSON exatamente como o exemplo:
{{"nota": 5, "justificativa": "A resposta cobre todos os pontos do gabarito."}}
"""

    data = {
        "timestamp":
            now_iso(),
        "judge_protocol_version":
            JUDGE_PROTOCOL_VERSION,
        "judge_prompt_source":
            (
                r"C:\TCCII\JUIZ"
                r"\juiz_climatechatrag.py"
            ),
        "judge_prompt_fidelity":
            "literal reproduction supplied by author",
        "legacy_judge_model":
            LEGACY_JUDGE_MODEL,
        "judge_model":
            JUDGE_MODEL,
        "judge_model_change_reason":
            "Historical Groq judge unavailable to current account; official replacement used.",
        "judge_temperature":
            JUDGE_TEMPERATURE,
        "judge_reasoning_effort":
            JUDGE_REASONING_EFFORT,
        "groq_url":
            GROQ_URL,
        "message_roles":
            ["user"],
        "response_format":
            {
                "type":
                    "json_object"
            },
        "source_generation_protocol":
            generation_run.get(
                "protocol_version"
            ),
        "source_generation_seed":
            generation_run.get(
                "seed"
            ),
        "input_csv":
            str(
                INPUT_CSV
            ),
        "input_csv_sha256":
            sha256_file(
                INPUT_CSV
            ),
        "input_jsonl":
            (
                str(
                    INPUT_JSONL
                )
                if INPUT_JSONL.exists()
                else None
            ),
        "input_jsonl_sha256":
            (
                sha256_file(
                    INPUT_JSONL
                )
                if INPUT_JSONL.exists()
                else None
            ),
        "generation_run_file":
            str(
                GENERATION_RUN_FILE
            ),
        "generation_run_sha256":
            sha256_file(
                GENERATION_RUN_FILE
            ),
        "generator_model_path":
            (
                str(
                    GENERATOR_MODEL_PATH
                )
                if GENERATOR_MODEL_PATH.exists()
                else None
            ),
        "generator_model_sha256":
            (
                sha256_file(
                    GENERATOR_MODEL_PATH
                )
                if GENERATOR_MODEL_PATH.exists()
                else None
            ),
        "n_controlled":
            EXPECTED_CONTROLLED,
        "n_historical":
            EXPECTED_CASES,
        "n_evaluation_rows":
            int(
                len(
                    df_eval
                )
            ),
        "n_unique_judge_inputs":
            int(
                df_eval[
                    "judge_input_sha256"
                ].nunique()
            ),
        "likert_scale":
            [
                1,
                2,
                3,
                4,
                5,
            ],
        "deduplication_rule":
            (
                "Identical question + gabarito + answer "
                "=> one current judge call; verdict "
                "propagated to equivalent rows."
            ),
        "blind_fields_not_sent_to_judge":
            [
                "evaluation_scope",
                "variant",
                "nota_historica",
                "generation_seed",
                "generation_protocol",
                "retrieval metadata",
            ],
        "prompt_template":
            prompt_template_literal,
        "prompt_template_sha256":
            sha256_text(
                prompt_template_literal
            ),
    }

    with PREFLIGHT_FILE.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )

    return data


# ============================================================
# API KEY / GROQ
# ============================================================

def load_api_key():
    ensure_file(
        CAMINHO_ENV,
        ".env original do TCC",
    )

    load_dotenv(
        CAMINHO_ENV
    )

    api_key = os.getenv(
        "GROQ_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY não encontrada em:\n"
            f"{CAMINHO_ENV}"
        )

    return api_key


# ============================================================
# CHAMADA AO JUIZ — PAYLOAD DO TCC
# ============================================================

def avaliar_resposta(
    api_key,
    pergunta,
    gabarito,
    resposta_ia,
):
    """
    Reproduz o protocolo textual do TCC:
    - mesmo prompt;
    - mesma temperature;
    - mesma role=user;
    - mesmo response_format json_object.

    Desvio necessário:
    - o modelo histórico llama-3.3-70b-versatile não está disponível
      para a conta atual; usa-se openai/gpt-oss-120b como juiz atual.

    Diferenças operacionais deliberadas:
    - validação rígida de nota 1-5;
    - retries controlados;
    - nunca grava nota 0 como resultado experimental;
    - checkpoint e deduplicação de entradas idênticas.
    """

    resposta_str = str(
        resposta_ia
    )

    if (
        not resposta_str.strip()
        or resposta_str == "N/A"
        or pd.isna(
            resposta_ia
        )
        or resposta_str == "nan"
    ):
        # O código original retornava nota 1 neste caso.
        return {
            "nota":
                1,
            "justificativa":
                (
                    "Resposta não gerada ou "
                    "campo vazio."
                ),
            "raw_json":
                None,
            "http_status":
                None,
            "api_attempts":
                0,
        }

    prompt_completo = (
        montar_prompt_original(
            pergunta,
            gabarito,
            resposta_str,
        )
    )

    headers = {
        "Authorization":
            f"Bearer {api_key}",
        "Content-Type":
            "application/json",
    }

    # PAYLOAD equivalente ao código original do TCC.
    # Não adicionamos max_tokens, seed, system prompt etc.
    data = {
        "model":
            JUDGE_MODEL,
        "messages": [
            {
                "role":
                    "user",
                "content":
                    prompt_completo,
            }
        ],
        "temperature":
            JUDGE_TEMPERATURE,
        "response_format":
            {
                "type":
                    "json_object"
            },
        "reasoning_effort":
            JUDGE_REASONING_EFFORT,
    }

    last_error = None

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):
        try:
            response = requests.post(
                GROQ_URL,
                headers=headers,
                json=data,
                timeout=180,
            )

            if (
                response.status_code
                == 200
            ):
                resultado = (
                    response.json()
                )

                texto_resposta = (
                    resultado[
                        "choices"
                    ][0][
                        "message"
                    ][
                        "content"
                    ]
                )

                dados = extrair_json(
                    texto_resposta
                )

                veredito = validar_veredito(
                    dados,
                    texto_resposta,
                )

                veredito[
                    "http_status"
                ] = 200

                veredito[
                    "api_attempts"
                ] = attempt

                veredito[
                    "completion_id"
                ] = resultado.get(
                    "id"
                )

                veredito[
                    "model_returned"
                ] = resultado.get(
                    "model",
                    JUDGE_MODEL,
                )

                veredito[
                    "created"
                ] = resultado.get(
                    "created"
                )

                return veredito

            if (
                response.status_code
                == 429
            ):
                last_error = (
                    "HTTP 429: "
                    + response.text
                )

                print(
                    "  Cota/rate limit atingido. "
                    "Pausando 60 segundos..."
                )

                time.sleep(
                    RATE_LIMIT_WAIT_SECONDS
                )

                continue

            last_error = (
                f"HTTP {response.status_code}: "
                f"{response.text}"
            )

            print(
                "  Erro da API: "
                f"{response.status_code}"
            )

            if (
                attempt
                < MAX_RETRIES
            ):
                time.sleep(5)

        except Exception as exc:
            last_error = (
                f"{type(exc).__name__}: {exc}"
            )

            print(
                "  Erro técnico de conexão: "
                f"{last_error}"
            )

            if (
                attempt
                < MAX_RETRIES
            ):
                time.sleep(5)

    raise RuntimeError(
        "Falha ao obter um julgamento válido "
        f"após {MAX_RETRIES} tentativas.\n"
        f"Último erro: {last_error}"
    )


# ============================================================
# TESTE DE UMA ÚNICA AVALIAÇÃO
# ============================================================

def run_api_test(
    api_key,
    df_eval,
):
    print(
        "\n"
        + "=" * 76
    )
    print(
        "TESTE DO JUIZ LLM — Q9 / P0"
    )
    print("=" * 76)

    test_rows = df_eval[
        (
            df_eval[
                "evaluation_scope"
            ]
            == "controlled"
        )
        & (
            df_eval[
                "id_questao"
            ]
            == 9
        )
        & (
            df_eval[
                "variant"
            ]
            == "P0"
        )
    ]

    if len(test_rows) != 1:
        raise RuntimeError(
            "Não foi possível localizar "
            "Q9/P0 para o teste."
        )

    row = (
        test_rows.iloc[0]
    )

    print(
        "O juiz NÃO receberá o rótulo P0."
    )
    print(
        "Entradas enviadas: pergunta + "
        "gabarito + resposta."
    )

    result = avaliar_resposta(
        api_key,
        row[
            "pergunta"
        ],
        row[
            "gabarito"
        ],
        row[
            "resposta_avaliada"
        ],
    )

    print(
        "\nModelo solicitado:",
        JUDGE_MODEL,
    )

    print(
        "Modelo retornado:",
        result.get(
            "model_returned"
        ),
    )

    print(
        "HTTP:",
        result.get(
            "http_status"
        ),
    )

    print(
        "Nota Likert:",
        result[
            "nota"
        ],
    )

    print(
        "Justificativa:"
    )

    print(
        result[
            "justificativa"
        ]
    )

    print(
        "\nJSON bruto:"
    )

    print(
        result[
            "raw_json"
        ]
    )

    print(
        "\n"
        + "=" * 76
    )
    print(
        "TESTE DA API PASSOU"
    )
    print("=" * 76)

    print(
        "O juiz retornou JSON válido, "
        "nota inteira 1-5 e justificativa."
    )


# ============================================================
# CHECKPOINT / RESUME
# ============================================================

def load_existing_output():
    if not OUTPUT_CSV.exists():
        return pd.DataFrame()

    df = pd.read_csv(
        OUTPUT_CSV,
        encoding="utf-8-sig",
    )

    required = {
        "evaluation_scope",
        "id_questao",
        "variant",
        "judge_input_sha256",
        "nota_juiz_atual",
        "justificativa_juiz_atual",
        "judge_protocol_version",
    }

    missing = (
        required
        - set(
            df.columns
        )
    )

    if missing:
        raise RuntimeError(
            "Arquivo de julgamento existente "
            "não pertence ao protocolo atual. "
            f"Colunas ausentes: {sorted(missing)}"
        )

    protocols = set(
        df[
            "judge_protocol_version"
        ].astype(str)
    )

    if protocols != {
        JUDGE_PROTOCOL_VERSION
    }:
        raise RuntimeError(
            "Arquivo existente contém outro "
            "protocolo de juiz.\n"
            "Renomeie o arquivo antigo antes "
            "de iniciar esta versão."
        )

    duplicates = df.duplicated(
        subset=[
            "evaluation_scope",
            "id_questao",
            "variant",
        ]
    ).sum()

    if duplicates:
        raise RuntimeError(
            "Arquivo existente contém "
            f"{duplicates} linhas duplicadas."
        )

    return df


def save_output(
    df,
):
    OUTPUT_CSV.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = (
        df.sort_values(
            [
                "id_questao",
                "evaluation_scope",
                "variant",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    df.to_csv(
        OUTPUT_CSV,
        index=False,
        encoding="utf-8-sig",
    )

    with OUTPUT_JSONL.open(
        "w",
        encoding="utf-8",
    ) as f:
        for record in df.to_dict(
            orient="records"
        ):
            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    default=str,
                )
                + "\n"
            )


# ============================================================
# EXECUÇÃO COMPLETA DO JUIZ
# ============================================================

def run_full_judging(
    api_key,
    df_eval,
):
    existing = (
        load_existing_output()
    )

    # --------------------------------------------------------
    # Cache por entrada textual exata
    # --------------------------------------------------------

    cache = {}

    if not existing.empty:
        for _, row in existing.iterrows():
            input_hash = str(
                row[
                    "judge_input_sha256"
                ]
            )

            cache[
                input_hash
            ] = {
                "nota":
                    int(
                        row[
                            "nota_juiz_atual"
                        ]
                    ),
                "justificativa":
                    str(
                        row[
                            "justificativa_juiz_atual"
                        ]
                    ),
                "raw_json":
                    row.get(
                        "judge_raw_json",
                        None,
                    ),
                "http_status":
                    row.get(
                        "judge_http_status",
                        None,
                    ),
                "api_attempts":
                    row.get(
                        "judge_api_attempts",
                        None,
                    ),
                "completion_id":
                    row.get(
                        "judge_completion_id",
                        None,
                    ),
                "model_returned":
                    row.get(
                        "judge_model_returned",
                        JUDGE_MODEL,
                    ),
                "created":
                    row.get(
                        "judge_created",
                        None,
                    ),
            }

    completed_keys = set()

    if not existing.empty:
        completed_keys = set(
            zip(
                existing[
                    "evaluation_scope"
                ].astype(str),
                existing[
                    "id_questao"
                ].astype(int),
                existing[
                    "variant"
                ].astype(str),
            )
        )

    output_rows = (
        existing.to_dict(
            orient="records"
        )
        if not existing.empty
        else []
    )

    unique_total = int(
        df_eval[
            "judge_input_sha256"
        ].nunique()
    )

    print(
        "\n"
        + "=" * 76
    )
    print(
        "INICIANDO JULGAMENTO"
    )
    print("=" * 76)

    print(
        "Registros finais: "
        f"{EXPECTED_TOTAL_ROWS}"
    )

    print(
        "Entradas únicas: "
        f"{unique_total}"
    )

    print(
        "Máximo de chamadas reais à API: "
        f"{unique_total}"
    )

    print(
        "Rótulos P0-P4 e HIST não são "
        "mostrados ao juiz."
    )

    api_calls_now = 0
    reused_rows_now = 0

    ordered = (
        df_eval.sort_values(
            [
                "id_questao",
                "evaluation_scope",
                "variant",
            ]
        )
    )

    for _, row in ordered.iterrows():
        key = (
            str(
                row[
                    "evaluation_scope"
                ]
            ),
            int(
                row[
                    "id_questao"
                ]
            ),
            str(
                row[
                    "variant"
                ]
            ),
        )

        if key in completed_keys:
            print(
                "[SKIP] "
                f"{key[0]} / "
                f"Q{key[1]} / "
                f"{key[2]}"
            )
            continue

        input_hash = str(
            row[
                "judge_input_sha256"
            ]
        )

        if input_hash in cache:
            judgment = (
                cache[
                    input_hash
                ]
            )

            reused = True
            reused_rows_now += 1

            print(
                "[REUSE] "
                f"{row['evaluation_scope']} / "
                f"Q{row['id_questao']} / "
                f"{row['variant']} "
                "→ resposta idêntica já julgada"
            )

        else:
            print(
                "[API] "
                f"{row['evaluation_scope']} / "
                f"Q{row['id_questao']} / "
                f"{row['variant']}"
            )

            judgment = avaliar_resposta(
                api_key,
                row[
                    "pergunta"
                ],
                row[
                    "gabarito"
                ],
                row[
                    "resposta_avaliada"
                ],
            )

            cache[
                input_hash
            ] = judgment

            reused = False
            api_calls_now += 1

            print(
                "  Nota:",
                judgment[
                    "nota"
                ],
            )

            # Mesmo intervalo do código original.
            time.sleep(
                INTER_CALL_SLEEP_SECONDS
            )

        out = dict(
            row.to_dict()
        )

        out.update({
            "nota_juiz_atual":
                int(
                    judgment[
                        "nota"
                    ]
                ),
            "justificativa_juiz_atual":
                judgment[
                    "justificativa"
                ],
            "judge_model":
                JUDGE_MODEL,
            "judge_temperature":
                JUDGE_TEMPERATURE,
            "judge_protocol_version":
                JUDGE_PROTOCOL_VERSION,
            "judge_verdict_reused":
                reused,
            "judge_prompt_source":
                (
                    r"C:\TCCII\JUIZ"
                    r"\juiz_climatechatrag.py"
                ),
            "judge_http_status":
                judgment.get(
                    "http_status"
                ),
            "judge_api_attempts":
                judgment.get(
                    "api_attempts"
                ),
            "judge_completion_id":
                judgment.get(
                    "completion_id"
                ),
            "judge_model_returned":
                judgment.get(
                    "model_returned",
                    JUDGE_MODEL,
                ),
            "judge_created":
                judgment.get(
                    "created"
                ),
            "judge_raw_json":
                judgment.get(
                    "raw_json"
                ),
            "evaluated_at":
                now_iso(),
        })

        output_rows.append(
            out
        )

        # Checkpoint após CADA registro final.
        save_output(
            pd.DataFrame(
                output_rows
            )
        )

        completed_keys.add(
            key
        )

    # --------------------------------------------------------
    # AUDITORIA FINAL
    # --------------------------------------------------------

    final_df = pd.read_csv(
        OUTPUT_CSV,
        encoding="utf-8-sig",
    )

    if (
        len(final_df)
        != EXPECTED_TOTAL_ROWS
    ):
        raise RuntimeError(
            "Número final de registros inesperado: "
            f"{len(final_df)}"
        )

    unique_keys = (
        final_df[
            [
                "evaluation_scope",
                "id_questao",
                "variant",
            ]
        ]
        .drop_duplicates()
    )

    if (
        len(unique_keys)
        != EXPECTED_TOTAL_ROWS
    ):
        raise RuntimeError(
            "Há linhas duplicadas ou ausentes "
            "no julgamento final."
        )

    notes = set(
        pd.to_numeric(
            final_df[
                "nota_juiz_atual"
            ],
            errors="raise",
        ).astype(int)
    )

    if not notes.issubset(
        {
            1,
            2,
            3,
            4,
            5,
        }
    ):
        raise RuntimeError(
            "Notas fora da escala 1-5: "
            f"{sorted(notes)}"
        )

    empty_just = (
        final_df[
            "justificativa_juiz_atual"
        ]
        .fillna("")
        .astype(str)
        .str.strip()
        .eq("")
        .sum()
    )

    if empty_just:
        raise RuntimeError(
            "Há justificativas vazias: "
            f"{empty_just}"
        )

    # Controle determinístico do nosso dataset:
    # se pergunta + gabarito + resposta são idênticos,
    # o resultado final também deve ser idêntico.
    consistency = (
        final_df.groupby(
            "judge_input_sha256"
        )
        .agg(
            n_notes=(
                "nota_juiz_atual",
                "nunique",
            ),
            n_just=(
                "justificativa_juiz_atual",
                "nunique",
            ),
        )
    )

    bad = consistency[
        (
            consistency[
                "n_notes"
            ]
            != 1
        )
        |
        (
            consistency[
                "n_just"
            ]
            != 1
        )
    ]

    if len(bad):
        raise RuntimeError(
            "Entradas idênticas receberam "
            "vereditos finais diferentes."
        )

    # --------------------------------------------------------
    # AUDITORIA DA EXECUÇÃO DO JUIZ
    # --------------------------------------------------------

    RUN_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_info = {
        "timestamp":
            now_iso(),
        "judge_protocol_version":
            JUDGE_PROTOCOL_VERSION,
        "judge_prompt_source":
            (
                r"C:\TCCII\JUIZ"
                r"\juiz_climatechatrag.py"
            ),
        "judge_prompt_fidelity":
            "literal reproduction supplied by author",
        "python":
            platform.python_version(),
        "requests":
            package_version(
                "requests"
            ),
        "python_dotenv":
            package_version(
                "python-dotenv"
            ),
        "legacy_judge_model":
            LEGACY_JUDGE_MODEL,
        "judge_model":
            JUDGE_MODEL,
        "judge_model_change_reason":
            "Historical Groq judge unavailable to current account; official replacement used.",
        "reasoning_effort":
            JUDGE_REASONING_EFFORT,
        "temperature":
            JUDGE_TEMPERATURE,
        "message_roles":
            [
                "user"
            ],
        "response_format":
            {
                "type":
                    "json_object"
            },
        "likert_scale":
            [
                1,
                2,
                3,
                4,
                5,
            ],
        "n_final_evaluation_rows":
            int(
                len(
                    final_df
                )
            ),
        "n_controlled_rows":
            int(
                (
                    final_df[
                        "evaluation_scope"
                    ]
                    == "controlled"
                ).sum()
            ),
        "n_historical_rows":
            int(
                (
                    final_df[
                        "evaluation_scope"
                    ]
                    == "historical"
                ).sum()
            ),
        "n_unique_judge_inputs":
            int(
                final_df[
                    "judge_input_sha256"
                ].nunique()
            ),
        "n_reused_verdict_rows":
            int(
                final_df[
                    "judge_verdict_reused"
                ]
                .astype(str)
                .str.lower()
                .eq("true")
                .sum()
            ),
        "blind_evaluation":
            True,
        "fields_sent_to_judge":
            [
                "pergunta",
                "gabarito",
                "resposta_avaliada",
            ],
        "fields_not_sent_to_judge":
            [
                "variant",
                "evaluation_scope",
                "nota_historica",
                "retrieval metadata",
                "generation metadata",
            ],
        "deduplication_rule":
            (
                "Identical question + gabarito + answer "
                "share one current judge verdict."
            ),
        "source_input_csv":
            str(
                INPUT_CSV
            ),
        "source_input_csv_sha256":
            sha256_file(
                INPUT_CSV
            ),
        "source_generation_run":
            str(
                GENERATION_RUN_FILE
            ),
        "source_generation_run_sha256":
            sha256_file(
                GENERATION_RUN_FILE
            ),
        "output_csv":
            str(
                OUTPUT_CSV
            ),
        "output_csv_sha256":
            sha256_file(
                OUTPUT_CSV
            ),
        "output_jsonl":
            str(
                OUTPUT_JSONL
            ),
        "output_jsonl_sha256":
            sha256_file(
                OUTPUT_JSONL
            ),
        "api_calls_this_execution":
            api_calls_now,
        "reused_rows_this_execution":
            reused_rows_now,
    }

    with RUN_FILE.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            run_info,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(
        "\n"
        + "=" * 76
    )
    print(
        "JULGAMENTO CONCLUÍDO"
    )
    print("=" * 76)

    print(
        "Registros finais: "
        f"{len(final_df)}"
    )

    print(
        "Controlados: "
        f"{(
            final_df[
                'evaluation_scope'
            ]
            == 'controlled'
        ).sum()}"
    )

    print(
        "Históricos: "
        f"{(
            final_df[
                'evaluation_scope'
            ]
            == 'historical'
        ).sum()}"
    )

    print(
        "Entradas únicas: "
        f"{final_df['judge_input_sha256'].nunique()}"
    )

    print(
        "Escala: somente inteiros 1-5"
    )

    print(
        "Justificativas vazias: 0"
    )

    print(
        "\nCSV:"
    )
    print(
        OUTPUT_CSV
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


# ============================================================
# MAIN
# ============================================================

def main(
    validate_only=False,
    test_api=False,
):
    print("=" * 76)
    print(
        "JUIZ LLM — PROMPT DO TCC + JUIZ ATUAL "
        "P0–P4 + HISTÓRICO"
    )
    print("=" * 76)

    generation_run = (
        load_generation_run()
    )

    controlled_df = (
        load_and_validate_controlled()
    )

    df_eval = (
        build_evaluation_rows(
            controlled_df
        )
    )

    preflight = (
        create_preflight(
            df_eval,
            generation_run,
        )
    )

    print(
        "\nPreflight salvo em:"
    )
    print(
        PREFLIGHT_FILE
    )

    print(
        "\nSHA-256 do CSV de entrada:"
    )
    print(
        preflight[
            "input_csv_sha256"
        ]
    )

    if (
        preflight[
            "generator_model_sha256"
        ]
        is not None
    ):
        print(
            "\nSHA-256 do GGUF gerador:"
        )
        print(
            preflight[
                "generator_model_sha256"
            ]
        )

    print(
        "\nPrompt do Juiz:"
    )
    print(
        "Reprodução literal de "
        r"C:\TCCII\JUIZ\juiz_climatechatrag.py"
    )

    print(
        "\nModelo histórico do TCC:"
    )
    print(
        LEGACY_JUDGE_MODEL
    )

    print(
        "Modelo usado na nova avaliação:"
    )
    print(
        JUDGE_MODEL
    )

    print(
        "Reasoning effort congelado:"
    )
    print(
        JUDGE_REASONING_EFFORT
    )

    if validate_only:
        print(
            "\n"
            + "=" * 76
        )
        print(
            "VALIDAÇÃO CONCLUÍDA"
        )
        print("=" * 76)

        print(
            "Nenhuma chamada à API Groq "
            "foi realizada."
        )
        return

    api_key = (
        load_api_key()
    )

    if test_api:
        run_api_test(
            api_key,
            df_eval,
        )

        print(
            "\nNenhum arquivo final de "
            "julgamento foi criado pelo "
            "modo --test-api."
        )
        return

    run_full_judging(
        api_key,
        df_eval,
    )


if __name__ == "__main__":
    parser = (
        argparse.ArgumentParser()
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help=(
            "Valida os 160 resultados, monta "
            "as 192 linhas, calcula hashes e "
            "não chama a API."
        ),
    )

    parser.add_argument(
        "--test-api",
        action="store_true",
        help=(
            "Executa somente uma avaliação "
            "Q9/P0 com o prompt exato do TCC."
        ),
    )

    args = (
        parser.parse_args()
    )

    main(
        validate_only=
            args.validate_only,
        test_api=
            args.test_api,
    )

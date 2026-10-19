import hashlib
import json
import math
import platform
import warnings
from datetime import datetime
from importlib.metadata import version
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import friedmanchisquare, spearmanr, wilcoxon



BASE_DIR = Path(__file__).resolve().parents[1]

RAW_DIR = BASE_DIR / "results" / "raw"
METRICS_DIR = BASE_DIR / "results" / "metrics"
CASES_DIR = BASE_DIR / "results" / "cases"
TABLES_DIR = BASE_DIR / "results" / "tables"
FIGURES_DIR = BASE_DIR / "results" / "figures"
RUNS_DIR = BASE_DIR / "results" / "runs"

JUDGE_FILE = RAW_DIR / "downstream_judge_evaluations.csv"
QUESTION_METRICS_FILE = METRICS_DIR / "controlled_question_metrics.csv"
DOWNSTREAM_RETRIEVAL_FILE = CASES_DIR / "downstream_retrieval_top5.csv"
JUDGE_RUN_FILE = RUNS_DIR / "downstream_judge_run.json"

OUT_SUMMARY = METRICS_DIR / "downstream_summary.csv"
OUT_DISTRIBUTION = TABLES_DIR / "downstream_score_distribution.csv"
OUT_PAIRWISE = METRICS_DIR / "downstream_pairwise_vs_p0.csv"
OUT_GLOBAL_TESTS = METRICS_DIR / "downstream_global_tests.csv"

OUT_JUDGE_SENSITIVITY = METRICS_DIR / "judge_sensitivity_summary.csv"
OUT_JUDGE_SENSITIVITY_Q = METRICS_DIR / "judge_sensitivity_per_question.csv"

OUT_RETRIEVAL_REL = METRICS_DIR / "retrieval_answer_relationship.csv"
OUT_RETRIEVAL_CHANGE = METRICS_DIR / "retrieval_change_answer_change.csv"
OUT_RETRIEVAL_DELTA_CORR = METRICS_DIR / "retrieval_delta_answer_delta_correlations.csv"

OUT_KEY_CASES = TABLES_DIR / "downstream_key_cases.csv"

OUT_ANALYSIS_RUN = RUNS_DIR / "downstream_analysis_run.json"
OUT_ANALYSIS_SUMMARY = RUNS_DIR / "downstream_analysis_summary.txt"

FIG_LIKERT_PNG = FIGURES_DIR / "downstream_likert_distribution.png"
FIG_LIKERT_PDF = FIGURES_DIR / "downstream_likert_distribution.pdf"

FIG_DELTA_PNG = FIGURES_DIR / "downstream_delta_vs_p0.png"
FIG_DELTA_PDF = FIGURES_DIR / "downstream_delta_vs_p0.pdf"

FIG_JUDGE_PNG = FIGURES_DIR / "judge_sensitivity_matrix.png"
FIG_JUDGE_PDF = FIGURES_DIR / "judge_sensitivity_matrix.pdf"

FIG_HIT5_PNG = FIGURES_DIR / "retrieval_hit5_vs_judge.png"
FIG_HIT5_PDF = FIGURES_DIR / "retrieval_hit5_vs_judge.pdf"


VARIANTS = ["P0", "P1", "P2", "P3", "P4"]
COMPARISON_VARIANTS = ["P1", "P2", "P3", "P4"]
KEY_CASE_IDS = [11, 65, 83, 124]

EXPECTED_CONTROLLED = 160
EXPECTED_HISTORICAL = 32
EXPECTED_TOTAL = 192
EXPECTED_PER_VARIANT = 32
EXPECTED_UNIQUE_INPUTS = 154

ALPHA = 0.05


def require_file(path: Path, label: str):
    if not path.exists():
        raise FileNotFoundError(
            f"{label} não encontrado:\n{path}"
        )


def ensure_dirs():
    for directory in [
        METRICS_DIR,
        TABLES_DIR,
        FIGURES_DIR,
        RUNS_DIR,
    ]:
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )


def package_version(name: str):
    try:
        return version(name)
    except Exception:
        return None


def sha256_file(path: Path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def now_iso():
    return datetime.now().isoformat()


def holm_adjust(pvalues):
    """
    Correção de Holm-Bonferroni sem dependência de statsmodels.
    """
    pvalues = np.asarray(
        pvalues,
        dtype=float,
    )

    m = len(pvalues)

    if m == 0:
        return np.array(
            [],
            dtype=float,
        )

    order = np.argsort(
        pvalues
    )

    adjusted = np.empty(
        m,
        dtype=float,
    )

    running_max = 0.0

    for rank, idx in enumerate(
        order,
        start=1,
    ):
        candidate = (
            (m - rank + 1)
            * pvalues[idx]
        )

        running_max = max(
            running_max,
            candidate,
        )

        adjusted[idx] = min(
            1.0,
            running_max,
        )

    return adjusted


def safe_wilcoxon(x, y):
    """
    Wilcoxon pareado bicaudal.

    Se todas as diferenças forem zero, retorna estatística 0 e p=1.
    """
    x = pd.Series(
        x,
        dtype=float,
    )

    y = pd.Series(
        y,
        dtype=float,
    )

    mask = (
        x.notna()
        & y.notna()
    )

    x = x[mask]
    y = y[mask]

    differences = (
        x.to_numpy()
        - y.to_numpy()
    )

    if len(differences) == 0:
        return 0.0, 1.0

    if np.allclose(
        differences,
        0.0,
    ):
        return 0.0, 1.0

    result = wilcoxon(
        x,
        y,
        zero_method="wilcox",
        alternative="two-sided",
        method="auto",
    )

    return (
        float(
            result.statistic
        ),
        float(
            result.pvalue
        ),
    )


def safe_spearman(x, y):
    x = pd.Series(
        x,
        dtype=float,
    )

    y = pd.Series(
        y,
        dtype=float,
    )

    mask = (
        x.notna()
        & y.notna()
    )

    x = x[mask]
    y = y[mask]

    if len(x) < 3:
        return (
            np.nan,
            np.nan,
        )

    if (
        x.nunique()
        <= 1
        or y.nunique()
        <= 1
    ):
        return (
            np.nan,
            np.nan,
        )

    result = spearmanr(
        x,
        y,
    )

    return (
        float(
            result.statistic
        ),
        float(
            result.pvalue
        ),
    )


def first_rank_label(value):
    if pd.isna(value):
        return ">10"

    return str(
        int(value)
    )


def classify_note_delta(delta):
    if delta > 0:
        return "improved"

    if delta < 0:
        return "worsened"

    return "same"


def classify_hit5_transition(
    p0_hit,
    current_hit,
):
    if (
        p0_hit == 0
        and current_hit == 1
    ):
        return "entered_top5"

    if (
        p0_hit == 1
        and current_hit == 0
    ):
        return "left_top5"

    if (
        p0_hit == 1
        and current_hit == 1
    ):
        return "stayed_hit"

    return "stayed_miss"




def load_inputs():
    require_file(
        JUDGE_FILE,
        "Arquivo de avaliações do Juiz LLM",
    )

    require_file(
        QUESTION_METRICS_FILE,
        "Métricas controladas de retrieval",
    )

    require_file(
        DOWNSTREAM_RETRIEVAL_FILE,
        "Top-5 downstream congelado",
    )

    require_file(
        JUDGE_RUN_FILE,
        "Auditoria da execução do Juiz",
    )

    judge = pd.read_csv(
        JUDGE_FILE,
        encoding="utf-8-sig",
    )

    metrics = pd.read_csv(
        QUESTION_METRICS_FILE,
        encoding="utf-8-sig",
    )

    retrieval = pd.read_csv(
        DOWNSTREAM_RETRIEVAL_FILE,
        encoding="utf-8-sig",
    )

    with JUDGE_RUN_FILE.open(
        "r",
        encoding="utf-8",
    ) as f:
        judge_run = json.load(f)

    return (
        judge,
        metrics,
        retrieval,
        judge_run,
    )


def validate_inputs(
    judge,
    metrics,
    retrieval,
    judge_run,
):
    print(
        "=" * 78
    )
    print(
        "VALIDAÇÃO DOS DADOS DOWNSTREAM"
    )
    print(
        "=" * 78
    )

    required_judge = {
        "evaluation_scope",
        "id_questao",
        "variant",
        "nota_historica",
        "nota_juiz_atual",
        "judge_input_sha256",
        "justificativa_juiz_atual",
    }

    missing = (
        required_judge
        - set(
            judge.columns
        )
    )

    if missing:
        raise RuntimeError(
            "Colunas ausentes no arquivo do juiz: "
            f"{sorted(missing)}"
        )

    if len(judge) != EXPECTED_TOTAL:
        raise RuntimeError(
            f"Esperadas {EXPECTED_TOTAL} linhas no Juiz; "
            f"encontradas {len(judge)}."
        )

    controlled = judge[
        judge[
            "evaluation_scope"
        ]
        == "controlled"
    ].copy()

    historical = judge[
        judge[
            "evaluation_scope"
        ]
        == "historical"
    ].copy()

    if len(controlled) != EXPECTED_CONTROLLED:
        raise RuntimeError(
            "Número inesperado de avaliações controladas: "
            f"{len(controlled)}"
        )

    if len(historical) != EXPECTED_HISTORICAL:
        raise RuntimeError(
            "Número inesperado de avaliações históricas: "
            f"{len(historical)}"
        )

    counts = (
        controlled[
            "variant"
        ]
        .value_counts()
        .to_dict()
    )

    for variant in VARIANTS:
        if (
            counts.get(
                variant,
                0,
            )
            != EXPECTED_PER_VARIANT
        ):
            raise RuntimeError(
                f"{variant}: esperadas "
                f"{EXPECTED_PER_VARIANT} avaliações; "
                f"encontradas {counts.get(variant, 0)}."
            )

    duplicate_controlled = controlled.duplicated(
        subset=[
            "id_questao",
            "variant",
        ]
    ).sum()

    if duplicate_controlled:
        raise RuntimeError(
            "Há combinações questão-variante duplicadas "
            "nas avaliações controladas."
        )

    duplicate_historical = historical.duplicated(
        subset=[
            "id_questao",
        ]
    ).sum()

    if duplicate_historical:
        raise RuntimeError(
            "Há questões históricas duplicadas."
        )

    note_values = set(
        pd.to_numeric(
            judge[
                "nota_juiz_atual"
            ],
            errors="raise",
        )
        .astype(int)
        .unique()
    )

    if not note_values.issubset(
        {
            1,
            2,
            3,
            4,
            5,
        }
    ):
        raise RuntimeError(
            "Há notas atuais fora da escala 1-5: "
            f"{sorted(note_values)}"
        )

    empty_just = (
        judge[
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
            f"Há {empty_just} justificativas vazias."
        )

    unique_inputs = int(
        judge[
            "judge_input_sha256"
        ].nunique()
    )

    if (
        unique_inputs
        != EXPECTED_UNIQUE_INPUTS
    ):
        raise RuntimeError(
            "Quantidade inesperada de entradas únicas "
            f"do Juiz: {unique_inputs}"
        )

    if (
        int(
            judge_run.get(
                "n_final_evaluation_rows",
                -1,
            )
        )
        != EXPECTED_TOTAL
    ):
        raise RuntimeError(
            "downstream_judge_run.json não registra "
            "192 avaliações finais."
        )

    if (
        int(
            judge_run.get(
                "n_unique_judge_inputs",
                -1,
            )
        )
        != EXPECTED_UNIQUE_INPUTS
    ):
        raise RuntimeError(
            "downstream_judge_run.json não registra "
            "154 entradas únicas."
        )

    if (
        sha256_file(
            JUDGE_FILE
        )
        != judge_run.get(
            "output_csv_sha256"
        )
    ):
        raise RuntimeError(
            "SHA-256 do CSV de avaliações não confere "
            "com downstream_judge_run.json."
        )

    required_metrics = {
        "variant",
        "id_questao",
        "target_canonical",
        "first_relevant_rank",
        "hit_5",
        "reciprocal_rank_10",
    }

    missing_metrics = (
        required_metrics
        - set(
            metrics.columns
        )
    )

    if missing_metrics:
        raise RuntimeError(
            "Colunas ausentes nas métricas de retrieval: "
            f"{sorted(missing_metrics)}"
        )

    controlled_ids = set(
        controlled[
            "id_questao"
        ].astype(int)
    )

    metrics_critical = metrics[
        metrics[
            "id_questao"
        ].isin(
            controlled_ids
        )
    ].copy()

    if (
        len(
            metrics_critical
        )
        != EXPECTED_CONTROLLED
    ):
        raise RuntimeError(
            "Esperadas 160 linhas de métricas para "
            "os 32 casos críticos; encontradas "
            f"{len(metrics_critical)}."
        )

    required_retrieval = {
        "variant",
        "id_questao",
        "rank",
        "retrieved_canonical",
        "is_target",
        "target_canonical",
    }

    missing_retrieval = (
        required_retrieval
        - set(
            retrieval.columns
        )
    )

    if missing_retrieval:
        raise RuntimeError(
            "Colunas ausentes no Top-5 downstream: "
            f"{sorted(missing_retrieval)}"
        )

    if len(retrieval) != 800:
        raise RuntimeError(
            "Esperadas 800 linhas no Top-5 downstream; "
            f"encontradas {len(retrieval)}."
        )

    print(
        "192 avaliações finais: OK"
    )
    print(
        "160 controladas + 32 históricas: OK"
    )
    print(
        "32 avaliações por variante: OK"
    )
    print(
        "154 entradas únicas: OK"
    )
    print(
        "Notas somente em 1-5: OK"
    )
    print(
        "Justificativas vazias: 0"
    )
    print(
        "SHA-256 do CSV do Juiz: OK"
    )
    print(
        "160 métricas de retrieval dos casos críticos: OK"
    )
    print(
        "800 linhas do Top-5 downstream: OK"
    )

    return (
        controlled,
        historical,
        metrics_critical,
    )


# ============================================================
# RESUMO P0-P4
# ============================================================

def build_downstream_summary(
    controlled,
):
    rows = []

    for variant in VARIANTS:
        subset = controlled[
            controlled[
                "variant"
            ]
            == variant
        ].copy()

        notes = pd.to_numeric(
            subset[
                "nota_juiz_atual"
            ],
            errors="raise",
        )

        row = {
            "variant":
                variant,
            "n":
                int(
                    len(
                        subset
                    )
                ),
            "mean":
                float(
                    notes.mean()
                ),
            "median":
                float(
                    notes.median()
                ),
            "std":
                float(
                    notes.std(
                        ddof=1
                    )
                ),
            "min":
                int(
                    notes.min()
                ),
            "max":
                int(
                    notes.max()
                ),
        }

        for score in range(
            1,
            6,
        ):
            count = int(
                (
                    notes
                    == score
                ).sum()
            )

            row[
                f"score_{score}_count"
            ] = count

            row[
                f"score_{score}_percent"
            ] = (
                100.0
                * count
                / len(
                    notes
                )
            )

        rows.append(
            row
        )

    return pd.DataFrame(
        rows
    )


def build_score_distribution(
    controlled,
):
    rows = []

    for variant in VARIANTS:
        subset = controlled[
            controlled[
                "variant"
            ]
            == variant
        ]

        for score in range(
            1,
            6,
        ):
            count = int(
                (
                    subset[
                        "nota_juiz_atual"
                    ]
                    == score
                ).sum()
            )

            rows.append({
                "variant":
                    variant,
                "score":
                    score,
                "count":
                    count,
                "percent":
                    (
                        100.0
                        * count
                        / len(
                            subset
                        )
                    ),
            })

    return pd.DataFrame(
        rows
    )


# ============================================================
# COMPARAÇÕES PAREADAS VS P0
# ============================================================

def build_pairwise_vs_p0(
    controlled,
):
    wide = (
        controlled
        .pivot(
            index="id_questao",
            columns="variant",
            values="nota_juiz_atual",
        )
        .sort_index()
    )

    missing_variants = (
        set(
            VARIANTS
        )
        - set(
            wide.columns
        )
    )

    if missing_variants:
        raise RuntimeError(
            "Variantes ausentes no pivot de notas: "
            f"{sorted(missing_variants)}"
        )

    rows = []

    for variant in COMPARISON_VARIANTS:
        delta = (
            wide[
                variant
            ]
            - wide[
                "P0"
            ]
        )

        statistic, pvalue = (
            safe_wilcoxon(
                wide[
                    variant
                ],
                wide[
                    "P0"
                ],
            )
        )

        rows.append({
            "variant":
                variant,
            "n":
                int(
                    len(
                        delta
                    )
                ),
            "improved":
                int(
                    (
                        delta
                        > 0
                    ).sum()
                ),
            "same":
                int(
                    (
                        delta
                        == 0
                    ).sum()
                ),
            "worsened":
                int(
                    (
                        delta
                        < 0
                    ).sum()
                ),
            "delta_mean":
                float(
                    delta.mean()
                ),
            "delta_median":
                float(
                    delta.median()
                ),
            "delta_min":
                int(
                    delta.min()
                ),
            "delta_max":
                int(
                    delta.max()
                ),
            "wilcoxon_statistic":
                statistic,
            "p_raw":
                pvalue,
        })

    result = pd.DataFrame(
        rows
    )

    result[
        "p_holm_4"
    ] = holm_adjust(
        result[
            "p_raw"
        ].to_numpy()
    )

    result[
        "significant_raw_0_05"
    ] = (
        result[
            "p_raw"
        ]
        < ALPHA
    )

    result[
        "significant_holm_0_05"
    ] = (
        result[
            "p_holm_4"
        ]
        < ALPHA
    )

    return (
        result,
        wide,
    )


def build_global_tests(
    wide,
):
    friedman = friedmanchisquare(
        *[
            wide[
                variant
            ]
            for variant
            in VARIANTS
        ]
    )

    return pd.DataFrame([
        {
            "analysis":
                "P0-P4 paired downstream scores",
            "test":
                "Friedman",
            "statistic":
                float(
                    friedman.statistic
                ),
            "p_value":
                float(
                    friedman.pvalue
                ),
            "alpha":
                ALPHA,
            "significant_0_05":
                bool(
                    friedman.pvalue
                    < ALPHA
                ),
            "interpretation":
                (
                    "No global evidence of score differences across P0-P4"
                    if friedman.pvalue
                    >= ALPHA
                    else
                    "Global evidence of score differences across P0-P4"
                ),
        }
    ])




def build_judge_sensitivity(
    historical,
):
    data = historical[
        [
            "id_questao",
            "nota_historica",
            "nota_juiz_atual",
        ]
    ].copy()

    data[
        "nota_historica"
    ] = pd.to_numeric(
        data[
            "nota_historica"
        ],
        errors="raise",
    )

    data[
        "nota_juiz_atual"
    ] = pd.to_numeric(
        data[
            "nota_juiz_atual"
        ],
        errors="raise",
    )

    data[
        "delta_atual_menos_historico"
    ] = (
        data[
            "nota_juiz_atual"
        ]
        - data[
            "nota_historica"
        ]
    )

    data[
        "direction"
    ] = (
        data[
            "delta_atual_menos_historico"
        ]
        .apply(
            classify_note_delta
        )
    )

    statistic, pvalue = safe_wilcoxon(
        data[
            "nota_juiz_atual"
        ],
        data[
            "nota_historica"
        ],
    )

    delta_counts = (
        data[
            "delta_atual_menos_historico"
        ]
        .value_counts()
        .sort_index()
        .to_dict()
    )

    summary = pd.DataFrame([
        {
            "n":
                int(
                    len(
                        data
                    )
                ),
            "historical_mean":
                float(
                    data[
                        "nota_historica"
                    ].mean()
                ),
            "historical_median":
                float(
                    data[
                        "nota_historica"
                    ].median()
                ),
            "historical_std":
                float(
                    data[
                        "nota_historica"
                    ].std(
                        ddof=1
                    )
                ),
            "current_mean":
                float(
                    data[
                        "nota_juiz_atual"
                    ].mean()
                ),
            "current_median":
                float(
                    data[
                        "nota_juiz_atual"
                    ].median()
                ),
            "current_std":
                float(
                    data[
                        "nota_juiz_atual"
                    ].std(
                        ddof=1
                    )
                ),
            "mean_delta_current_minus_historical":
                float(
                    data[
                        "delta_atual_menos_historico"
                    ].mean()
                ),
            "median_delta_current_minus_historical":
                float(
                    data[
                        "delta_atual_menos_historico"
                    ].median()
                ),
            "current_higher":
                int(
                    (
                        data[
                            "delta_atual_menos_historico"
                        ]
                        > 0
                    ).sum()
                ),
            "same":
                int(
                    (
                        data[
                            "delta_atual_menos_historico"
                        ]
                        == 0
                    ).sum()
                ),
            "current_lower":
                int(
                    (
                        data[
                            "delta_atual_menos_historico"
                        ]
                        < 0
                    ).sum()
                ),
            "current_lower_percent":
                float(
                    100.0
                    * (
                        data[
                            "delta_atual_menos_historico"
                        ]
                        < 0
                    ).mean()
                ),
            "delta_minus_3_count":
                int(
                    delta_counts.get(
                        -3,
                        0,
                    )
                ),
            "delta_minus_2_count":
                int(
                    delta_counts.get(
                        -2,
                        0,
                    )
                ),
            "delta_minus_1_count":
                int(
                    delta_counts.get(
                        -1,
                        0,
                    )
                ),
            "delta_0_count":
                int(
                    delta_counts.get(
                        0,
                        0,
                    )
                ),
            "delta_plus_1_count":
                int(
                    delta_counts.get(
                        1,
                        0,
                    )
                ),
            "delta_plus_2_count":
                int(
                    delta_counts.get(
                        2,
                        0,
                    )
                ),
            "delta_plus_3_count":
                int(
                    delta_counts.get(
                        3,
                        0,
                    )
                ),
            "wilcoxon_statistic":
                statistic,
            "wilcoxon_p":
                pvalue,
            "significant_0_05":
                bool(
                    pvalue
                    < ALPHA
                ),
        }
    ])

    return (
        summary,
        data.sort_values(
            "id_questao"
        )
        .reset_index(
            drop=True
        ),
    )


# ============================================================
# RETRIEVAL × QUALIDADE DA RESPOSTA
# ============================================================

def merge_retrieval_scores(
    controlled,
    metrics_critical,
):
    judge_small = controlled[
        [
            "id_questao",
            "variant",
            "nota_juiz_atual",
        ]
    ].copy()

    merged = metrics_critical.merge(
        judge_small,
        on=[
            "id_questao",
            "variant",
        ],
        how="inner",
        validate="one_to_one",
    )

    if (
        len(
            merged
        )
        != EXPECTED_CONTROLLED
    ):
        raise RuntimeError(
            "Merge retrieval × juiz não resultou "
            "em 160 linhas."
        )

    return merged


def build_retrieval_answer_relationship(
    merged,
):
    rows = []

    # Resumo descritivo por Hit@5.
    for hit_value in [
        0,
        1,
    ]:
        subset = merged[
            merged[
                "hit_5"
            ]
            == hit_value
        ]

        rows.append({
            "analysis_type":
                "hit5_group",
            "group":
                (
                    "target_absent_top5"
                    if hit_value
                    == 0
                    else
                    "target_present_top5"
                ),
            "n":
                int(
                    len(
                        subset
                    )
                ),
            "mean_judge_score":
                float(
                    subset[
                        "nota_juiz_atual"
                    ].mean()
                ),
            "median_judge_score":
                float(
                    subset[
                        "nota_juiz_atual"
                    ].median()
                ),
            "std_judge_score":
                float(
                    subset[
                        "nota_juiz_atual"
                    ].std(
                        ddof=1
                    )
                ),
            "spearman_rho":
                np.nan,
            "spearman_p":
                np.nan,
        })

    rho, pvalue = safe_spearman(
        merged[
            "reciprocal_rank_10"
        ],
        merged[
            "nota_juiz_atual"
        ],
    )

    rows.append({
        "analysis_type":
            "spearman_rr10_vs_judge",
        "group":
            "all_160_controlled",
        "n":
            int(
                len(
                    merged
                )
            ),
        "mean_judge_score":
            float(
                merged[
                    "nota_juiz_atual"
                ].mean()
            ),
        "median_judge_score":
            float(
                merged[
                    "nota_juiz_atual"
                ].median()
            ),
        "std_judge_score":
            float(
                merged[
                    "nota_juiz_atual"
                ].std(
                    ddof=1
                )
            ),
        "spearman_rho":
            rho,
        "spearman_p":
            pvalue,
    })

    return pd.DataFrame(
        rows
    )


def build_retrieval_change_answer_change(
    merged,
):
    p0 = (
        merged[
            merged[
                "variant"
            ]
            == "P0"
        ]
        .set_index(
            "id_questao"
        )
        .sort_index()
    )

    rows_question = []

    for variant in COMPARISON_VARIANTS:
        current = (
            merged[
                merged[
                    "variant"
                ]
                == variant
            ]
            .set_index(
                "id_questao"
            )
            .sort_index()
        )

        if not current.index.equals(
            p0.index
        ):
            raise RuntimeError(
                f"IDs de {variant} não correspondem a P0."
            )

        for qid in p0.index:
            p0_hit = int(
                p0.loc[
                    qid,
                    "hit_5",
                ]
            )

            current_hit = int(
                current.loc[
                    qid,
                    "hit_5",
                ]
            )

            delta_note = float(
                current.loc[
                    qid,
                    "nota_juiz_atual",
                ]
                - p0.loc[
                    qid,
                    "nota_juiz_atual",
                ]
            )

            delta_rr = float(
                current.loc[
                    qid,
                    "reciprocal_rank_10",
                ]
                - p0.loc[
                    qid,
                    "reciprocal_rank_10",
                ]
            )

            rows_question.append({
                "id_questao":
                    int(
                        qid
                    ),
                "variant":
                    variant,
                "p0_hit_5":
                    p0_hit,
                "variant_hit_5":
                    current_hit,
                "hit5_transition":
                    classify_hit5_transition(
                        p0_hit,
                        current_hit,
                    ),
                "p0_first_rank":
                    (
                        p0.loc[
                            qid,
                            "first_relevant_rank",
                        ]
                    ),
                "variant_first_rank":
                    (
                        current.loc[
                            qid,
                            "first_relevant_rank",
                        ]
                    ),
                "p0_rr_10":
                    float(
                        p0.loc[
                            qid,
                            "reciprocal_rank_10",
                        ]
                    ),
                "variant_rr_10":
                    float(
                        current.loc[
                            qid,
                            "reciprocal_rank_10",
                        ]
                    ),
                "delta_rr_10":
                    delta_rr,
                "p0_judge_score":
                    int(
                        p0.loc[
                            qid,
                            "nota_juiz_atual",
                        ]
                    ),
                "variant_judge_score":
                    int(
                        current.loc[
                            qid,
                            "nota_juiz_atual",
                        ]
                    ),
                "delta_judge_score":
                    delta_note,
                "judge_direction":
                    classify_note_delta(
                        delta_note
                    ),
            })

    per_question = pd.DataFrame(
        rows_question
    )

    summary_rows = []

    transition_order = [
        "entered_top5",
        "left_top5",
        "stayed_hit",
        "stayed_miss",
    ]

    for transition in transition_order:
        subset = per_question[
            per_question[
                "hit5_transition"
            ]
            == transition
        ]

        if len(subset) == 0:
            continue

        summary_rows.append({
            "hit5_transition":
                transition,
            "n":
                int(
                    len(
                        subset
                    )
                ),
            "judge_improved":
                int(
                    (
                        subset[
                            "delta_judge_score"
                        ]
                        > 0
                    ).sum()
                ),
            "judge_same":
                int(
                    (
                        subset[
                            "delta_judge_score"
                        ]
                        == 0
                    ).sum()
                ),
            "judge_worsened":
                int(
                    (
                        subset[
                            "delta_judge_score"
                        ]
                        < 0
                    ).sum()
                ),
            "mean_delta_judge":
                float(
                    subset[
                        "delta_judge_score"
                    ].mean()
                ),
            "median_delta_judge":
                float(
                    subset[
                        "delta_judge_score"
                    ].median()
                ),
            "mean_delta_rr10":
                float(
                    subset[
                        "delta_rr_10"
                    ].mean()
                ),
        })

    summary = pd.DataFrame(
        summary_rows
    )

    return (
        summary,
        per_question,
    )


def build_delta_correlations(
    per_question,
):
    rows = []

    rho, pvalue = safe_spearman(
        per_question[
            "delta_rr_10"
        ],
        per_question[
            "delta_judge_score"
        ],
    )

    rows.append({
        "scope":
            "all_P1_to_P4_vs_P0",
        "variant":
            "ALL",
        "n":
            int(
                len(
                    per_question
                )
            ),
        "spearman_rho_delta_rr10_vs_delta_judge":
            rho,
        "p_value":
            pvalue,
        "exploratory":
            True,
    })

    for variant in COMPARISON_VARIANTS:
        subset = per_question[
            per_question[
                "variant"
            ]
            == variant
        ]

        rho, pvalue = safe_spearman(
            subset[
                "delta_rr_10"
            ],
            subset[
                "delta_judge_score"
            ],
        )

        rows.append({
            "scope":
                f"{variant}_vs_P0",
            "variant":
                variant,
            "n":
                int(
                    len(
                        subset
                    )
                ),
            "spearman_rho_delta_rr10_vs_delta_judge":
                rho,
            "p_value":
                pvalue,
            "exploratory":
                True,
        })

    return pd.DataFrame(
        rows
    )


# ============================================================
# CASOS-CHAVE Q11, Q65, Q83, Q124
# ============================================================

def build_key_cases(
    controlled,
    historical,
    metrics_critical,
    retrieval,
):
    historical_by_q = (
        historical
        .set_index(
            "id_questao"
        )
        .sort_index()
    )

    p0_scores = (
        controlled[
            controlled[
                "variant"
            ]
            == "P0"
        ]
        .set_index(
            "id_questao"
        )[
            "nota_juiz_atual"
        ]
    )

    p0_metrics = (
        metrics_critical[
            metrics_critical[
                "variant"
            ]
            == "P0"
        ]
        .set_index(
            "id_questao"
        )
    )

    rows = []

    for qid in KEY_CASE_IDS:
        for variant in VARIANTS:
            eval_row = controlled[
                (
                    controlled[
                        "id_questao"
                    ]
                    == qid
                )
                & (
                    controlled[
                        "variant"
                    ]
                    == variant
                )
            ]

            metric_row = metrics_critical[
                (
                    metrics_critical[
                        "id_questao"
                    ]
                    == qid
                )
                & (
                    metrics_critical[
                        "variant"
                    ]
                    == variant
                )
            ]

            top5 = (
                retrieval[
                    (
                        retrieval[
                            "id_questao"
                        ]
                        == qid
                    )
                    & (
                        retrieval[
                            "variant"
                        ]
                        == variant
                    )
                ]
                .sort_values(
                    "rank"
                )
            )

            if (
                len(
                    eval_row
                )
                != 1
                or len(
                    metric_row
                )
                != 1
                or len(
                    top5
                )
                != 5
            ):
                raise RuntimeError(
                    f"Dados incompletos para Q{qid}/{variant}."
                )

            eval_row = eval_row.iloc[0]
            metric_row = metric_row.iloc[0]

            retrieved_sequence = " | ".join(
                top5[
                    "retrieved_canonical"
                ].astype(str)
            )

            target_chunks_top5 = int(
                pd.to_numeric(
                    top5[
                        "is_target"
                    ],
                    errors="raise",
                ).sum()
            )

            hist_old = (
                historical_by_q.loc[
                    qid,
                    "nota_historica",
                ]
            )

            hist_current = (
                historical_by_q.loc[
                    qid,
                    "nota_juiz_atual",
                ]
            )

            rows.append({
                "id_questao":
                    qid,
                "variant":
                    variant,
                "target_canonical":
                    metric_row[
                        "target_canonical"
                    ],
                "first_relevant_rank":
                    first_rank_label(
                        metric_row[
                            "first_relevant_rank"
                        ]
                    ),
                "hit_5":
                    int(
                        metric_row[
                            "hit_5"
                        ]
                    ),
                "rr_10":
                    float(
                        metric_row[
                            "reciprocal_rank_10"
                        ]
                    ),
                "target_chunks_in_top5":
                    target_chunks_top5,
                "top5_retrieved_sequence":
                    retrieved_sequence,
                "judge_score":
                    int(
                        eval_row[
                            "nota_juiz_atual"
                        ]
                    ),
                "delta_judge_vs_p0":
                    int(
                        eval_row[
                            "nota_juiz_atual"
                        ]
                        - p0_scores.loc[
                            qid
                        ]
                    ),
                "delta_rr10_vs_p0":
                    float(
                        metric_row[
                            "reciprocal_rank_10"
                        ]
                        - p0_metrics.loc[
                            qid,
                            "reciprocal_rank_10",
                        ]
                    ),
                "historical_tcc_score":
                    int(
                        hist_old
                    ),
                "historical_response_current_judge_score":
                    int(
                        hist_current
                    ),
                "question":
                    eval_row[
                        "pergunta"
                    ],
                "judge_justification":
                    eval_row[
                        "justificativa_juiz_atual"
                    ],
            })

    return pd.DataFrame(
        rows
    )


# ============================================================
# FIGURAS
# ============================================================

def save_figure(
    fig,
    png_path,
    pdf_path,
):
    fig.tight_layout()

    fig.savefig(
        png_path,
        dpi=300,
        bbox_inches="tight",
    )

    fig.savefig(
        pdf_path,
        bbox_inches="tight",
    )

    plt.close(
        fig
    )


def plot_likert_distribution(
    distribution,
):
    pivot = (
        distribution
        .pivot(
            index="variant",
            columns="score",
            values="percent",
        )
        .reindex(
            VARIANTS
        )
        .fillna(
            0.0
        )
    )

    fig, ax = plt.subplots(
        figsize=(
            8.5,
            4.8,
        )
    )

    bottom = np.zeros(
        len(
            pivot
        )
    )

    for score in range(
        1,
        6,
    ):
        values = (
            pivot[
                score
            ].to_numpy()
        )

        ax.bar(
            pivot.index,
            values,
            bottom=bottom,
            label=f"Nota {score}",
        )

        bottom += values

    ax.set_xlabel(
        "Variante"
    )

    ax.set_ylabel(
        "Percentual de respostas (%)"
    )

    ax.set_title(
        "Distribuição das notas do Juiz LLM nos 32 casos críticos"
    )

    ax.set_ylim(
        0,
        100,
    )

    ax.legend(
        title="Likert",
        ncol=5,
        loc="upper center",
        bbox_to_anchor=(
            0.5,
            -0.15,
        ),
    )

    save_figure(
        fig,
        FIG_LIKERT_PNG,
        FIG_LIKERT_PDF,
    )


def plot_delta_vs_p0(
    pairwise,
):
    plot_df = (
        pairwise
        .set_index(
            "variant"
        )
        .reindex(
            COMPARISON_VARIANTS
        )
    )

    x = np.arange(
        len(
            COMPARISON_VARIANTS
        )
    )

    width = 0.25

    fig, ax = plt.subplots(
        figsize=(
            8.5,
            4.8,
        )
    )

    ax.bar(
        x - width,
        plot_df[
            "improved"
        ].to_numpy(),
        width,
        label="Melhorou",
    )

    ax.bar(
        x,
        plot_df[
            "same"
        ].to_numpy(),
        width,
        label="Empatou",
    )

    ax.bar(
        x + width,
        plot_df[
            "worsened"
        ].to_numpy(),
        width,
        label="Piorou",
    )

    ax.set_xticks(
        x
    )

    ax.set_xticklabels(
        COMPARISON_VARIANTS
    )

    ax.set_xlabel(
        "Variante comparada com P0"
    )

    ax.set_ylabel(
        "Número de questões"
    )

    ax.set_title(
        "Mudança da nota downstream em relação a P0"
    )

    ax.legend()

    save_figure(
        fig,
        FIG_DELTA_PNG,
        FIG_DELTA_PDF,
    )


def plot_judge_sensitivity(
    sensitivity_per_question,
):
    matrix = pd.crosstab(
        sensitivity_per_question[
            "nota_historica"
        ].astype(int),
        sensitivity_per_question[
            "nota_juiz_atual"
        ].astype(int),
    )

    matrix = matrix.reindex(
        index=range(
            1,
            6,
        ),
        columns=range(
            1,
            6,
        ),
        fill_value=0,
    )

    fig, ax = plt.subplots(
        figsize=(
            6.3,
            5.3,
        )
    )

    image = ax.imshow(
        matrix.to_numpy(),
        origin="lower",
        aspect="equal",
    )

    ax.set_xticks(
        range(
            5
        )
    )

    ax.set_xticklabels(
        range(
            1,
            6,
        )
    )

    ax.set_yticks(
        range(
            5
        )
    )

    ax.set_yticklabels(
        range(
            1,
            6,
        )
    )

    ax.set_xlabel(
        "Nota do juiz atual (GPT-OSS-120B)"
    )

    ax.set_ylabel(
        "Nota histórica do TCC"
    )

    ax.set_title(
        "Sensibilidade à substituição do Juiz LLM"
    )

    for i in range(
        matrix.shape[0]
    ):
        for j in range(
            matrix.shape[1]
        ):
            value = int(
                matrix.iloc[
                    i,
                    j,
                ]
            )

            ax.text(
                j,
                i,
                str(
                    value
                ),
                ha="center",
                va="center",
            )

    fig.colorbar(
        image,
        ax=ax,
        label="Número de respostas",
    )

    save_figure(
        fig,
        FIG_JUDGE_PNG,
        FIG_JUDGE_PDF,
    )


def plot_hit5_vs_judge(
    merged,
):
    absent = (
        merged[
            merged[
                "hit_5"
            ]
            == 0
        ][
            "nota_juiz_atual"
        ]
        .astype(float)
        .to_numpy()
    )

    present = (
        merged[
            merged[
                "hit_5"
            ]
            == 1
        ][
            "nota_juiz_atual"
        ]
        .astype(float)
        .to_numpy()
    )

    fig, ax = plt.subplots(
        figsize=(
            6.5,
            4.8,
        )
    )

    ax.boxplot(
        [
            absent,
            present,
        ],
        tick_labels=[
            "Alvo ausente no Top-5",
            "Alvo presente no Top-5",
        ],
    )

    ax.set_ylabel(
        "Nota do Juiz LLM"
    )

    ax.set_title(
        "Nota downstream segundo presença do capítulo-alvo no Top-5"
    )

    ax.set_ylim(
        0.5,
        5.5,
    )

    save_figure(
        fig,
        FIG_HIT5_PNG,
        FIG_HIT5_PDF,
    )


# ============================================================
# RESUMO TEXTUAL E AUDITORIA
# ============================================================

def build_text_summary(
    summary,
    pairwise,
    global_tests,
    judge_sensitivity,
    retrieval_rel,
    retrieval_change,
    delta_correlations,
):
    friedman_row = (
        global_tests.iloc[
            0
        ]
    )

    sensitivity = (
        judge_sensitivity.iloc[
            0
        ]
    )

    hit_absent = retrieval_rel[
        retrieval_rel[
            "group"
        ]
        == "target_absent_top5"
    ].iloc[0]

    hit_present = retrieval_rel[
        retrieval_rel[
            "group"
        ]
        == "target_present_top5"
    ].iloc[0]

    rr_row = retrieval_rel[
        retrieval_rel[
            "analysis_type"
        ]
        == "spearman_rr10_vs_judge"
    ].iloc[0]

    entered = retrieval_change[
        retrieval_change[
            "hit5_transition"
        ]
        == "entered_top5"
    ]

    left = retrieval_change[
        retrieval_change[
            "hit5_transition"
        ]
        == "left_top5"
    ]

    lines = []

    lines.append(
        "ANÁLISE DOWNSTREAM — RESUMO REPRODUZÍVEL"
    )
    lines.append(
        "=" * 60
    )
    lines.append(
        ""
    )

    lines.append(
        "1) Sensibilidade à substituição do Juiz LLM"
    )
    lines.append(
        f"- Média histórica (32 respostas): "
        f"{sensitivity['historical_mean']:.3f}"
    )
    lines.append(
        f"- Média atual nas mesmas respostas: "
        f"{sensitivity['current_mean']:.3f}"
    )
    lines.append(
        f"- Delta médio atual-histórico: "
        f"{sensitivity['mean_delta_current_minus_historical']:.3f}"
    )
    lines.append(
        f"- Atual menor: {int(sensitivity['current_lower'])}/32 "
        f"({sensitivity['current_lower_percent']:.1f}%)"
    )
    lines.append(
        f"- Wilcoxon p = {sensitivity['wilcoxon_p']:.8g}"
    )
    lines.append(
        ""
    )

    lines.append(
        "2) Notas P0-P4 nos 32 casos críticos"
    )

    for _, row in summary.iterrows():
        lines.append(
            f"- {row['variant']}: "
            f"média={row['mean']:.3f}, "
            f"mediana={row['median']:.1f}, "
            f"DP={row['std']:.3f}"
        )

    lines.append(
        f"- Friedman: estatística="
        f"{friedman_row['statistic']:.4f}, "
        f"p={friedman_row['p_value']:.6f}"
    )
    lines.append(
        ""
    )

    lines.append(
        "3) Comparações Pk vs P0"
    )

    for _, row in pairwise.iterrows():
        lines.append(
            f"- {row['variant']}: "
            f"melhorou={int(row['improved'])}, "
            f"igual={int(row['same'])}, "
            f"piorou={int(row['worsened'])}, "
            f"delta médio={row['delta_mean']:+.3f}, "
            f"p bruto={row['p_raw']:.6f}, "
            f"p Holm={row['p_holm_4']:.6f}"
        )

    lines.append(
        ""
    )

    lines.append(
        "4) Retrieval × nota"
    )
    lines.append(
        f"- Alvo ausente no Top-5: "
        f"n={int(hit_absent['n'])}, "
        f"média={hit_absent['mean_judge_score']:.3f}"
    )
    lines.append(
        f"- Alvo presente no Top-5: "
        f"n={int(hit_present['n'])}, "
        f"média={hit_present['mean_judge_score']:.3f}"
    )
    lines.append(
        f"- Spearman RR@10 × nota: "
        f"rho={rr_row['spearman_rho']:.4f}, "
        f"p={rr_row['spearman_p']:.6f}"
    )

    if len(
        entered
    ):
        row = entered.iloc[0]

        lines.append(
            f"- Entrada do alvo no Top-5: "
            f"n={int(row['n'])}, "
            f"melhorou={int(row['judge_improved'])}, "
            f"igual={int(row['judge_same'])}, "
            f"piorou={int(row['judge_worsened'])}"
        )

    if len(
        left
    ):
        row = left.iloc[0]

        lines.append(
            f"- Saída do alvo do Top-5: "
            f"n={int(row['n'])}, "
            f"melhorou={int(row['judge_improved'])}, "
            f"igual={int(row['judge_same'])}, "
            f"piorou={int(row['judge_worsened'])}"
        )

    lines.append(
        ""
    )

    lines.append(
        "5) Correlação exploratória das mudanças"
    )

    for _, row in delta_correlations.iterrows():
        rho = row[
            "spearman_rho_delta_rr10_vs_delta_judge"
        ]

        pvalue = row[
            "p_value"
        ]

        if pd.isna(
            rho
        ):
            lines.append(
                f"- {row['scope']}: correlação não definida "
                "(uma das variáveis é constante)."
            )
        else:
            lines.append(
                f"- {row['scope']}: "
                f"rho={rho:.4f}, "
                f"p={pvalue:.6f} "
                "(exploratório)"
            )

    lines.append(
        ""
    )

    lines.append(
        "Interpretação:"
    )
    lines.append(
        "- As notas atuais não substituem a média histórica global do TCC."
    )
    lines.append(
        "- O juiz atual foi sistematicamente mais severo nas mesmas 32 respostas históricas."
    )
    lines.append(
        "- As comparações downstream principais devem ser internas e pareadas entre P0-P4."
    )
    lines.append(
        "- Não houve diferença global significativa entre P0-P4 nos 32 casos críticos."
    )
    lines.append(
        "- Mudanças no retrieval não se propagaram de forma determinística para a qualidade da resposta."
    )
    lines.append(
        "- Os 32 casos são uma amostra crítica pré-selecionada, não uma estimativa global das 130 perguntas."
    )

    return "\n".join(
        lines
    )


def save_run_audit(
    input_hashes,
    output_paths,
    summary,
    pairwise,
    global_tests,
    judge_sensitivity,
    retrieval_rel,
):
    run = {
        "timestamp":
            now_iso(),
        "analysis_protocol":
            "downstream-analysis-v1",
        "python":
            platform.python_version(),
        "pandas":
            package_version(
                "pandas"
            ),
        "numpy":
            package_version(
                "numpy"
            ),
        "scipy":
            package_version(
                "scipy"
            ),
        "matplotlib":
            package_version(
                "matplotlib"
            ),
        "alpha":
            ALPHA,
        "variants":
            VARIANTS,
        "key_cases":
            KEY_CASE_IDS,
        "inputs_sha256":
            input_hashes,
        "validation": {
            "final_evaluation_rows":
                EXPECTED_TOTAL,
            "controlled_rows":
                EXPECTED_CONTROLLED,
            "historical_rows":
                EXPECTED_HISTORICAL,
            "unique_judge_inputs":
                EXPECTED_UNIQUE_INPUTS,
        },
        "headline_results": {
            "historical_mean_old_judge":
                float(
                    judge_sensitivity.iloc[
                        0
                    ][
                        "historical_mean"
                    ]
                ),
            "historical_mean_current_judge":
                float(
                    judge_sensitivity.iloc[
                        0
                    ][
                        "current_mean"
                    ]
                ),
            "judge_sensitivity_wilcoxon_p":
                float(
                    judge_sensitivity.iloc[
                        0
                    ][
                        "wilcoxon_p"
                    ]
                ),
            "friedman_p":
                float(
                    global_tests.iloc[
                        0
                    ][
                        "p_value"
                    ]
                ),
            "variant_means":
                {
                    row[
                        "variant"
                    ]:
                        float(
                            row[
                                "mean"
                            ]
                        )
                    for _, row
                    in summary.iterrows()
                },
            "pairwise_holm_p":
                {
                    row[
                        "variant"
                    ]:
                        float(
                            row[
                                "p_holm_4"
                            ]
                        )
                    for _, row
                    in pairwise.iterrows()
                },
            "rr10_judge_spearman_rho":
                float(
                    retrieval_rel[
                        retrieval_rel[
                            "analysis_type"
                        ]
                        == "spearman_rr10_vs_judge"
                    ].iloc[
                        0
                    ][
                        "spearman_rho"
                    ]
                ),
            "rr10_judge_spearman_p":
                float(
                    retrieval_rel[
                        retrieval_rel[
                            "analysis_type"
                        ]
                        == "spearman_rr10_vs_judge"
                    ].iloc[
                        0
                    ][
                        "spearman_p"
                    ]
                ),
        },
        "outputs":
            {},
    }

    for label, path in output_paths.items():
        run[
            "outputs"
        ][
            label
        ] = {
            "path":
                str(
                    path
                ),
            "sha256":
                (
                    sha256_file(
                        path
                    )
                    if path.exists()
                    else None
                ),
        }

    with OUT_ANALYSIS_RUN.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            run,
            f,
            ensure_ascii=False,
            indent=2,
        )


# ============================================================
# MAIN
# ============================================================

def main():
    ensure_dirs()

    (
        judge,
        metrics,
        retrieval,
        judge_run,
    ) = load_inputs()

    (
        controlled,
        historical,
        metrics_critical,
    ) = validate_inputs(
        judge,
        metrics,
        retrieval,
        judge_run,
    )

    print(
        "\n"
        + "=" * 78
    )
    print(
        "CALCULANDO ANÁLISES"
    )
    print(
        "=" * 78
    )

    summary = build_downstream_summary(
        controlled
    )

    distribution = build_score_distribution(
        controlled
    )

    pairwise, wide_scores = build_pairwise_vs_p0(
        controlled
    )

    global_tests = build_global_tests(
        wide_scores
    )

    (
        judge_sensitivity,
        judge_sensitivity_q,
    ) = build_judge_sensitivity(
        historical
    )

    merged = merge_retrieval_scores(
        controlled,
        metrics_critical,
    )

    retrieval_rel = build_retrieval_answer_relationship(
        merged
    )

    (
        retrieval_change,
        retrieval_change_q,
    ) = build_retrieval_change_answer_change(
        merged
    )

    delta_correlations = build_delta_correlations(
        retrieval_change_q
    )

    key_cases = build_key_cases(
        controlled,
        historical,
        metrics_critical,
        retrieval,
    )

    # --------------------------------------------------------
    # SALVAR TABELAS / MÉTRICAS
    # --------------------------------------------------------

    summary.to_csv(
        OUT_SUMMARY,
        index=False,
        encoding="utf-8-sig",
    )

    distribution.to_csv(
        OUT_DISTRIBUTION,
        index=False,
        encoding="utf-8-sig",
    )

    pairwise.to_csv(
        OUT_PAIRWISE,
        index=False,
        encoding="utf-8-sig",
    )

    global_tests.to_csv(
        OUT_GLOBAL_TESTS,
        index=False,
        encoding="utf-8-sig",
    )

    judge_sensitivity.to_csv(
        OUT_JUDGE_SENSITIVITY,
        index=False,
        encoding="utf-8-sig",
    )

    judge_sensitivity_q.to_csv(
        OUT_JUDGE_SENSITIVITY_Q,
        index=False,
        encoding="utf-8-sig",
    )

    retrieval_rel.to_csv(
        OUT_RETRIEVAL_REL,
        index=False,
        encoding="utf-8-sig",
    )

    retrieval_change.to_csv(
        OUT_RETRIEVAL_CHANGE,
        index=False,
        encoding="utf-8-sig",
    )

    delta_correlations.to_csv(
        OUT_RETRIEVAL_DELTA_CORR,
        index=False,
        encoding="utf-8-sig",
    )

    key_cases.to_csv(
        OUT_KEY_CASES,
        index=False,
        encoding="utf-8-sig",
    )

    # Arquivo por questão para auditoria das transições retrieval->nota.
    retrieval_change_q_file = (
        METRICS_DIR
        / "retrieval_change_answer_change_per_question.csv"
    )

    retrieval_change_q.to_csv(
        retrieval_change_q_file,
        index=False,
        encoding="utf-8-sig",
    )

    # --------------------------------------------------------
    # FIGURAS
    # --------------------------------------------------------

    plot_likert_distribution(
        distribution
    )

    plot_delta_vs_p0(
        pairwise
    )

    plot_judge_sensitivity(
        judge_sensitivity_q
    )

    plot_hit5_vs_judge(
        merged
    )

    # --------------------------------------------------------
    # RESUMO TEXTUAL
    # --------------------------------------------------------

    text_summary = build_text_summary(
        summary,
        pairwise,
        global_tests,
        judge_sensitivity,
        retrieval_rel,
        retrieval_change,
        delta_correlations,
    )

    OUT_ANALYSIS_SUMMARY.write_text(
        text_summary,
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # AUDITORIA FINAL
    # --------------------------------------------------------

    input_hashes = {
        "downstream_judge_evaluations_csv":
            sha256_file(
                JUDGE_FILE
            ),
        "controlled_question_metrics_csv":
            sha256_file(
                QUESTION_METRICS_FILE
            ),
        "downstream_retrieval_top5_csv":
            sha256_file(
                DOWNSTREAM_RETRIEVAL_FILE
            ),
        "downstream_judge_run_json":
            sha256_file(
                JUDGE_RUN_FILE
            ),
    }

    output_paths = {
        "downstream_summary_csv":
            OUT_SUMMARY,
        "downstream_score_distribution_csv":
            OUT_DISTRIBUTION,
        "downstream_pairwise_vs_p0_csv":
            OUT_PAIRWISE,
        "downstream_global_tests_csv":
            OUT_GLOBAL_TESTS,
        "judge_sensitivity_summary_csv":
            OUT_JUDGE_SENSITIVITY,
        "judge_sensitivity_per_question_csv":
            OUT_JUDGE_SENSITIVITY_Q,
        "retrieval_answer_relationship_csv":
            OUT_RETRIEVAL_REL,
        "retrieval_change_answer_change_csv":
            OUT_RETRIEVAL_CHANGE,
        "retrieval_change_per_question_csv":
            retrieval_change_q_file,
        "retrieval_delta_answer_delta_correlations_csv":
            OUT_RETRIEVAL_DELTA_CORR,
        "downstream_key_cases_csv":
            OUT_KEY_CASES,
        "downstream_analysis_summary_txt":
            OUT_ANALYSIS_SUMMARY,
        "likert_distribution_png":
            FIG_LIKERT_PNG,
        "likert_distribution_pdf":
            FIG_LIKERT_PDF,
        "delta_vs_p0_png":
            FIG_DELTA_PNG,
        "delta_vs_p0_pdf":
            FIG_DELTA_PDF,
        "judge_sensitivity_matrix_png":
            FIG_JUDGE_PNG,
        "judge_sensitivity_matrix_pdf":
            FIG_JUDGE_PDF,
        "retrieval_hit5_vs_judge_png":
            FIG_HIT5_PNG,
        "retrieval_hit5_vs_judge_pdf":
            FIG_HIT5_PDF,
    }

    save_run_audit(
        input_hashes,
        output_paths,
        summary,
        pairwise,
        global_tests,
        judge_sensitivity,
        retrieval_rel,
    )

    print(
        "\n"
        + text_summary
    )

    print(
        "\n"
        + "=" * 78
    )
    print(
        "ANÁLISE DOWNSTREAM CONCLUÍDA"
    )
    print(
        "=" * 78
    )

    print(
        "\nArquivos principais:"
    )

    for path in [
        OUT_SUMMARY,
        OUT_PAIRWISE,
        OUT_GLOBAL_TESTS,
        OUT_JUDGE_SENSITIVITY,
        OUT_RETRIEVAL_REL,
        OUT_RETRIEVAL_CHANGE,
        OUT_KEY_CASES,
        OUT_ANALYSIS_SUMMARY,
        OUT_ANALYSIS_RUN,
    ]:
        print(
            path
        )

    print(
        "\nFiguras:"
    )

    for path in [
        FIG_LIKERT_PDF,
        FIG_DELTA_PDF,
        FIG_JUDGE_PDF,
        FIG_HIT5_PDF,
    ]:
        print(
            path
        )


if __name__ == "__main__":
    main()

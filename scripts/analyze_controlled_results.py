import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import binomtest, wilcoxon


# ============================================================
# DIRETÓRIOS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[0]

# Quando o script estiver em <projeto>/scripts/, usa a raiz do projeto.
if BASE_DIR.name.lower() == "scripts":
    BASE_DIR = BASE_DIR.parent

METRICS_DIR = BASE_DIR / "results" / "metrics"
CASES_DIR = BASE_DIR / "results" / "cases"
TABLES_DIR = BASE_DIR / "results" / "tables"
FIGURES_DIR = BASE_DIR / "results" / "figures"
RUNS_DIR = BASE_DIR / "results" / "runs"

QUESTION_METRICS_FILE = METRICS_DIR / "controlled_question_metrics.csv"
QUESTION_DELTAS_FILE = METRICS_DIR / "controlled_question_deltas_vs_p0.csv"
DOWNSTREAM_TOP5_FILE = CASES_DIR / "downstream_retrieval_top5.csv"
CASE11_FILE = CASES_DIR / "controlled_case_11_top10.csv"

VARIANTS = ["P0", "P1", "P2", "P3", "P4"]
COMPARISON_VARIANTS = ["P1", "P2", "P3", "P4"]
HIT_METRICS = ["hit_1", "hit_3", "hit_5", "hit_10"]
METRIC_LABELS = {
    "hit_1": "Hit@1",
    "hit_3": "Hit@3",
    "hit_5": "Hit@5",
    "hit_10": "Hit@10",
    "mrr_10": "MRR@10",
}


# ============================================================
# UTILIDADES
# ============================================================

def require_file(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")


def ensure_dirs():
    for directory in [TABLES_DIR, FIGURES_DIR, RUNS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def holm_adjust(pvalues):
    """Correção de Holm-Bonferroni sem dependência de statsmodels."""
    pvalues = np.asarray(pvalues, dtype=float)
    m = len(pvalues)

    order = np.argsort(pvalues)
    adjusted = np.empty(m, dtype=float)

    running_max = 0.0
    for rank, idx in enumerate(order, start=1):
        candidate = (m - rank + 1) * pvalues[idx]
        running_max = max(running_max, candidate)
        adjusted[idx] = min(1.0, running_max)

    return adjusted


def fmt_percent(value):
    return f"{100.0 * value:.2f}%"


def fmt_float(value, digits=4):
    return f"{value:.{digits}f}"


def first_rank_label(value):
    if pd.isna(value):
        return ">10"
    return str(int(value))


# ============================================================
# VALIDAÇÃO DOS DADOS
# ============================================================

def load_and_validate():
    for path in [
        QUESTION_METRICS_FILE,
        QUESTION_DELTAS_FILE,
        DOWNSTREAM_TOP5_FILE,
        CASE11_FILE,
    ]:
        require_file(path)

    metrics = pd.read_csv(QUESTION_METRICS_FILE)
    deltas = pd.read_csv(QUESTION_DELTAS_FILE)
    downstream = pd.read_csv(DOWNSTREAM_TOP5_FILE)
    case11 = pd.read_csv(CASE11_FILE)

    if len(metrics) != 650:
        raise RuntimeError(
            f"Esperadas 650 linhas de métricas; encontradas {len(metrics)}."
        )

    expected_variants = set(VARIANTS)
    found_variants = set(metrics["variant"].unique())
    if found_variants != expected_variants:
        raise RuntimeError(
            f"Variantes inesperadas em métricas: {sorted(found_variants)}"
        )

    counts = metrics.groupby("variant")["id_questao"].nunique().to_dict()
    for variant in VARIANTS:
        if counts.get(variant) != 130:
            raise RuntimeError(
                f"{variant}: esperadas 130 perguntas; encontradas {counts.get(variant)}."
            )

    if len(deltas) != 520:
        raise RuntimeError(
            f"Esperadas 520 linhas de delta por questão; encontradas {len(deltas)}."
        )

    if len(downstream) != 800:
        raise RuntimeError(
            f"Esperadas 800 linhas downstream Top-5; encontradas {len(downstream)}."
        )

    downstream_ids = sorted(downstream["id_questao"].unique())
    if len(downstream_ids) != 32:
        raise RuntimeError(
            f"Esperados 32 casos downstream; encontrados {len(downstream_ids)}."
        )

    if len(case11) != 50:
        raise RuntimeError(
            f"Esperadas 50 linhas para Caso 11; encontradas {len(case11)}."
        )

    return metrics, deltas, downstream, case11, downstream_ids


# ============================================================
# RESUMOS DE MÉTRICAS
# ============================================================

def summarize_metrics(df, group_columns):
    rows = []

    for keys, group in df.groupby(group_columns, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)

        row = dict(zip(group_columns, keys))
        row["n"] = len(group)

        for metric in HIT_METRICS:
            count = int(group[metric].sum())
            row[f"{metric}_count"] = count
            row[f"{metric}_percent"] = 100.0 * count / len(group)

        row["mrr_10"] = group["reciprocal_rank_10"].mean()
        rows.append(row)

    result = pd.DataFrame(rows)

    variant_order = pd.CategoricalDtype(VARIANTS, ordered=True)
    if "variant" in result.columns:
        result["variant"] = result["variant"].astype(variant_order)
        sort_cols = [c for c in group_columns if c != "variant"] + ["variant"]
        result = result.sort_values(sort_cols).reset_index(drop=True)
        result["variant"] = result["variant"].astype(str)

    return result


# ============================================================
# MUDANÇAS DE RANK
# ============================================================

def rank_change_summary(deltas):
    categories = [
        "improved",
        "worsened",
        "same_rank",
        "new_hit",
        "lost_hit",
        "unchanged_miss",
    ]

    rows = []
    for variant in COMPARISON_VARIANTS:
        subset = deltas[deltas["variant"] == variant]
        counts = subset["rank_change"].value_counts().to_dict()

        row = {"variant": variant, "n": len(subset)}
        for category in categories:
            row[category] = int(counts.get(category, 0))
        rows.append(row)

    return pd.DataFrame(rows)


# ============================================================
# TESTES PAREADOS VS P0
# ============================================================

def paired_statistical_tests(metrics):
    p0 = (
        metrics[metrics["variant"] == "P0"]
        .set_index("id_questao")
        .sort_index()
    )

    rows = []

    for variant in COMPARISON_VARIANTS:
        current = (
            metrics[metrics["variant"] == variant]
            .set_index("id_questao")
            .sort_index()
        )

        if not current.index.equals(p0.index):
            raise RuntimeError(f"IDs de {variant} não correspondem a P0.")

        # Hit@k: teste exato de McNemar via binomial nos pares discordantes.
        for metric in HIT_METRICS:
            losses = int(((p0[metric] == 1) & (current[metric] == 0)).sum())
            gains = int(((p0[metric] == 0) & (current[metric] == 1)).sum())
            discordant = losses + gains

            if discordant == 0:
                pvalue = 1.0
            else:
                # Sob H0, cada discordância tem probabilidade 0,5 de cair
                # em cada direção. É equivalente ao McNemar exato bicaudal.
                pvalue = binomtest(
                    k=min(losses, gains),
                    n=discordant,
                    p=0.5,
                    alternative="two-sided",
                ).pvalue

            delta_pp = 100.0 * (
                current[metric].mean() - p0[metric].mean()
            )

            rows.append({
                "variant": variant,
                "metric": METRIC_LABELS[metric],
                "test": "McNemar exato",
                "p0_value": p0[metric].mean(),
                "variant_value": current[metric].mean(),
                "delta": delta_pp,
                "delta_unit": "pontos_percentuais",
                "losses_p0_to_variant": losses,
                "gains_p0_to_variant": gains,
                "n_discordant": discordant,
                "statistic": np.nan,
                "p_raw": float(pvalue),
            })

        # MRR@10: Wilcoxon pareado.
        p0_mrr = p0["reciprocal_rank_10"].astype(float)
        current_mrr = current["reciprocal_rank_10"].astype(float)
        diff = current_mrr - p0_mrr
        nonzero = int((diff != 0).sum())

        if nonzero == 0:
            statistic = 0.0
            pvalue = 1.0
        else:
            statistic, pvalue = wilcoxon(
                current_mrr,
                p0_mrr,
                zero_method="wilcox",
                alternative="two-sided",
                method="auto",
            )

        rows.append({
            "variant": variant,
            "metric": "MRR@10",
            "test": "Wilcoxon pareado",
            "p0_value": p0_mrr.mean(),
            "variant_value": current_mrr.mean(),
            "delta": current_mrr.mean() - p0_mrr.mean(),
            "delta_unit": "MRR",
            "losses_p0_to_variant": np.nan,
            "gains_p0_to_variant": np.nan,
            "n_discordant": nonzero,
            "statistic": float(statistic),
            "p_raw": float(pvalue),
        })

    result = pd.DataFrame(rows)

    # Correção conservadora considerando os 20 testes como uma única família.
    result["p_holm_all_20"] = holm_adjust(result["p_raw"].values)

    # Também registra correção dentro de cada métrica (4 comparações P1-P4).
    result["p_holm_within_metric"] = np.nan
    for metric_name, idx in result.groupby("metric").groups.items():
        idx = list(idx)
        adjusted = holm_adjust(result.loc[idx, "p_raw"].values)
        result.loc[idx, "p_holm_within_metric"] = adjusted

    result["significant_holm_all_20"] = result["p_holm_all_20"] < 0.05
    result["significant_holm_within_metric"] = (
        result["p_holm_within_metric"] < 0.05
    )

    return result


# ============================================================
# TABELA DE TRANSIÇÕES HIT@K
# ============================================================

def hit_transition_summary(metrics):
    p0 = (
        metrics[metrics["variant"] == "P0"]
        .set_index("id_questao")
        .sort_index()
    )

    rows = []
    for variant in COMPARISON_VARIANTS:
        current = (
            metrics[metrics["variant"] == variant]
            .set_index("id_questao")
            .sort_index()
        )

        for metric in HIT_METRICS:
            both_hit = int(((p0[metric] == 1) & (current[metric] == 1)).sum())
            loss = int(((p0[metric] == 1) & (current[metric] == 0)).sum())
            gain = int(((p0[metric] == 0) & (current[metric] == 1)).sum())
            both_miss = int(((p0[metric] == 0) & (current[metric] == 0)).sum())

            rows.append({
                "variant": variant,
                "metric": METRIC_LABELS[metric],
                "both_hit": both_hit,
                "loss": loss,
                "gain": gain,
                "both_miss": both_miss,
            })

    return pd.DataFrame(rows)


# ============================================================
# CASOS CRÍTICOS DOWNSTREAM
# ============================================================

def downstream_analysis(metrics, downstream_ids, deltas):
    subset = metrics[metrics["id_questao"].isin(downstream_ids)].copy()
    summary = summarize_metrics(subset, ["variant"])

    # Matriz: uma linha por caso e first relevant rank por variante.
    rank_matrix = subset.pivot(
        index="id_questao",
        columns="variant",
        values="first_relevant_rank",
    ).reset_index()

    rank_matrix = rank_matrix[["id_questao"] + VARIANTS]
    rank_matrix = rank_matrix.sort_values("id_questao")

    # Mudanças apenas nos 32 casos.
    critical_changes = deltas[deltas["id_questao"].isin(downstream_ids)].copy()
    critical_changes = critical_changes.sort_values(["id_questao", "variant"])

    return summary, rank_matrix, critical_changes


# ============================================================
# FIGURAS
# ============================================================

def save_figure(fig, basename):
    pdf_path = FIGURES_DIR / f"{basename}.pdf"
    png_path = FIGURES_DIR / f"{basename}.png"
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_global_hit(summary):
    x_labels = ["Hit@1", "Hit@3", "Hit@5", "Hit@10"]
    metrics = ["hit_1_percent", "hit_3_percent", "hit_5_percent", "hit_10_percent"]
    x = np.arange(len(x_labels))

    fig, ax = plt.subplots(figsize=(9, 5.5))

    for variant in VARIANTS:
        row = summary[summary["variant"] == variant].iloc[0]
        y = [row[m] for m in metrics]
        ax.plot(x, y, marker="o", linewidth=2, label=variant)

    ax.set_xticks(x)
    ax.set_xticklabels(x_labels)
    ax.set_ylabel("Taxa de acerto (%)")
    ax.set_xlabel("Métrica")
    ax.set_ylim(0, 100)
    ax.set_title("Desempenho global de recuperação por variante")
    ax.legend(title="Variante")
    ax.grid(axis="y", alpha=0.25)

    save_figure(fig, "controlled_hit_at_k_comparison")


def plot_global_mrr(summary):
    values = [
        summary.loc[summary["variant"] == variant, "mrr_10"].iloc[0]
        for variant in VARIANTS
    ]

    fig, ax = plt.subplots(figsize=(7.5, 5))
    bars = ax.bar(VARIANTS, values)
    ax.set_ylim(0, 1)
    ax.set_ylabel("MRR@10")
    ax.set_xlabel("Variante")
    ax.set_title("MRR@10 por variante")

    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.015,
            f"{value:.3f}",
            ha="center",
            va="bottom",
        )

    save_figure(fig, "controlled_mrr_comparison")


def plot_hit5_by_type(by_type):
    types = ["Direct", "Indirect"]
    x = np.arange(len(types))
    width = 0.15

    fig, ax = plt.subplots(figsize=(9, 5.5))

    offsets = np.linspace(-2 * width, 2 * width, len(VARIANTS))
    for offset, variant in zip(offsets, VARIANTS):
        subset = by_type[by_type["variant"] == variant].set_index("tipo")
        values = [subset.loc[t, "hit_5_percent"] for t in types]
        ax.bar(x + offset, values, width=width, label=variant)

    ax.set_xticks(x)
    ax.set_xticklabels(types)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Hit@5 (%)")
    ax.set_xlabel("Tipo de pergunta")
    ax.set_title("Hit@5 por tipo de pergunta")
    ax.legend(title="Variante")
    ax.grid(axis="y", alpha=0.25)

    save_figure(fig, "controlled_hit5_by_type")


def plot_hit5_by_difficulty(by_difficulty):
    difficulties = ["Easy", "Medium-Low", "Medium-High", "Hard"]
    x = np.arange(len(difficulties))
    width = 0.15

    fig, ax = plt.subplots(figsize=(10, 5.8))

    offsets = np.linspace(-2 * width, 2 * width, len(VARIANTS))
    for offset, variant in zip(offsets, VARIANTS):
        subset = by_difficulty[
            by_difficulty["variant"] == variant
        ].set_index("dificuldade")
        values = [subset.loc[d, "hit_5_percent"] for d in difficulties]
        ax.bar(x + offset, values, width=width, label=variant)

    ax.set_xticks(x)
    ax.set_xticklabels(difficulties)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Hit@5 (%)")
    ax.set_xlabel("Dificuldade")
    ax.set_title("Hit@5 por nível de dificuldade")
    ax.legend(title="Variante")
    ax.grid(axis="y", alpha=0.25)

    save_figure(fig, "controlled_hit5_by_difficulty")


def plot_downstream_hit(downstream_summary):
    x_labels = ["Hit@1", "Hit@3", "Hit@5", "Hit@10"]
    metrics = ["hit_1_percent", "hit_3_percent", "hit_5_percent", "hit_10_percent"]
    x = np.arange(len(x_labels))

    fig, ax = plt.subplots(figsize=(9, 5.5))

    for variant in VARIANTS:
        row = downstream_summary[
            downstream_summary["variant"] == variant
        ].iloc[0]
        y = [row[m] for m in metrics]
        ax.plot(x, y, marker="o", linewidth=2, label=variant)

    ax.set_xticks(x)
    ax.set_xticklabels(x_labels)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Taxa de acerto (%)")
    ax.set_xlabel("Métrica")
    ax.set_title("Recuperação nos 32 casos críticos downstream")
    ax.legend(title="Variante")
    ax.grid(axis="y", alpha=0.25)

    save_figure(fig, "downstream_critical_hit_at_k")


# ============================================================
# RELATÓRIO TEXTUAL AUTOMÁTICO
# ============================================================

def write_text_summary(
    global_summary,
    deltas,
    by_type,
    by_difficulty,
    rank_changes,
    downstream_summary,
    downstream_ranks,
    statistical_tests,
    case11,
):
    path = RUNS_DIR / "controlled_analysis_summary.txt"

    lines = []
    lines.append("ANÁLISE DO EXPERIMENTO CONTROLADO P0–P4")
    lines.append("=" * 72)
    lines.append("")

    lines.append("1. RESULTADOS GLOBAIS")
    lines.append("-" * 72)
    for variant in VARIANTS:
        row = global_summary[global_summary["variant"] == variant].iloc[0]
        lines.append(
            f"{variant}: "
            f"Hit@1={row['hit_1_percent']:.2f}% | "
            f"Hit@3={row['hit_3_percent']:.2f}% | "
            f"Hit@5={row['hit_5_percent']:.2f}% | "
            f"Hit@10={row['hit_10_percent']:.2f}% | "
            f"MRR@10={row['mrr_10']:.4f}"
        )

    lines.append("")
    lines.append("2. MUDANÇAS DE RANK VS P0")
    lines.append("-" * 72)
    for _, row in rank_changes.iterrows():
        lines.append(
            f"{row['variant']}: improved={row['improved']} | "
            f"worsened={row['worsened']} | same_rank={row['same_rank']} | "
            f"new_hit={row['new_hit']} | lost_hit={row['lost_hit']} | "
            f"unchanged_miss={row['unchanged_miss']}"
        )

    lines.append("")
    lines.append("3. CASOS CRÍTICOS DOWNSTREAM (N=32)")
    lines.append("-" * 72)
    for variant in VARIANTS:
        row = downstream_summary[
            downstream_summary["variant"] == variant
        ].iloc[0]
        lines.append(
            f"{variant}: "
            f"Hit@1={row['hit_1_percent']:.2f}% | "
            f"Hit@3={row['hit_3_percent']:.2f}% | "
            f"Hit@5={row['hit_5_percent']:.2f}% | "
            f"Hit@10={row['hit_10_percent']:.2f}% | "
            f"MRR@10={row['mrr_10']:.4f}"
        )

    lines.append("")
    lines.append("4. CASOS 65, 83 E 124")
    lines.append("-" * 72)
    for qid in [65, 83, 124]:
        row = downstream_ranks[downstream_ranks["id_questao"] == qid]
        if len(row) == 1:
            row = row.iloc[0]
            ranks = " | ".join(
                f"{v}={first_rank_label(row[v])}" for v in VARIANTS
            )
            lines.append(f"Q{qid}: {ranks}")

    lines.append("")
    lines.append("5. CASO 11")
    lines.append("-" * 72)
    for variant in VARIANTS:
        subset = case11[case11["variant"] == variant].sort_values("rank")
        sequence = ", ".join(subset["retrieved_canonical"].tolist())
        lines.append(f"{variant}: {sequence}")

    lines.append("")
    lines.append("6. TESTES ESTATÍSTICOS VS P0")
    lines.append("-" * 72)
    for _, row in statistical_tests.iterrows():
        lines.append(
            f"{row['variant']} / {row['metric']}: "
            f"p_raw={row['p_raw']:.6g} | "
            f"p_holm_all_20={row['p_holm_all_20']:.6g} | "
            f"p_holm_within_metric={row['p_holm_within_metric']:.6g}"
        )

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 72)
    print("ANÁLISE DOS RESULTADOS CONTROLADOS P0–P4")
    print("=" * 72)

    ensure_dirs()

    metrics, deltas, downstream, case11, downstream_ids = load_and_validate()

    print("Dados validados.")
    print(f"Métricas por pergunta: {len(metrics)}")
    print(f"Casos downstream: {len(downstream_ids)}")

    # --------------------------------------------------------
    # Tabelas descritivas
    # --------------------------------------------------------

    global_summary = summarize_metrics(metrics, ["variant"])
    by_type = summarize_metrics(metrics, ["variant", "tipo"])
    by_difficulty = summarize_metrics(metrics, ["variant", "dificuldade"])
    rank_changes = rank_change_summary(deltas)
    hit_transitions = hit_transition_summary(metrics)
    statistical_tests = paired_statistical_tests(metrics)

    downstream_summary, downstream_ranks, downstream_changes = downstream_analysis(
        metrics, downstream_ids, deltas
    )

    # --------------------------------------------------------
    # Deltas globais vs P0
    # --------------------------------------------------------

    p0 = global_summary[global_summary["variant"] == "P0"].iloc[0]
    delta_rows = []
    for variant in VARIANTS:
        row = global_summary[global_summary["variant"] == variant].iloc[0]
        delta_rows.append({
            "variant": variant,
            "delta_hit_1_pp": row["hit_1_percent"] - p0["hit_1_percent"],
            "delta_hit_3_pp": row["hit_3_percent"] - p0["hit_3_percent"],
            "delta_hit_5_pp": row["hit_5_percent"] - p0["hit_5_percent"],
            "delta_hit_10_pp": row["hit_10_percent"] - p0["hit_10_percent"],
            "delta_mrr_10": row["mrr_10"] - p0["mrr_10"],
        })
    global_deltas = pd.DataFrame(delta_rows)

    # --------------------------------------------------------
    # Salvar tabelas
    # --------------------------------------------------------

    outputs = {
        "controlled_results_global.csv": global_summary,
        "controlled_deltas_recomputed_vs_p0.csv": global_deltas,
        "controlled_results_by_type.csv": by_type,
        "controlled_results_by_difficulty.csv": by_difficulty,
        "controlled_rank_change_summary.csv": rank_changes,
        "controlled_hit_transition_summary.csv": hit_transitions,
        "controlled_statistical_tests_vs_p0.csv": statistical_tests,
        "downstream_critical_summary.csv": downstream_summary,
        "downstream_first_relevant_ranks.csv": downstream_ranks,
        "downstream_rank_changes.csv": downstream_changes,
    }

    for filename, dataframe in outputs.items():
        path = TABLES_DIR / filename
        dataframe.to_csv(path, index=False, encoding="utf-8-sig")

    # --------------------------------------------------------
    # Figuras
    # --------------------------------------------------------

    plot_global_hit(global_summary)
    plot_global_mrr(global_summary)
    plot_hit5_by_type(by_type)
    plot_hit5_by_difficulty(by_difficulty)
    plot_downstream_hit(downstream_summary)

    # --------------------------------------------------------
    # Relatório textual
    # --------------------------------------------------------

    report_path = write_text_summary(
        global_summary,
        deltas,
        by_type,
        by_difficulty,
        rank_changes,
        downstream_summary,
        downstream_ranks,
        statistical_tests,
        case11,
    )

    # --------------------------------------------------------
    # Console
    # --------------------------------------------------------

    print("\n" + "=" * 72)
    print("RESULTADOS GLOBAIS")
    print("=" * 72)

    display_cols = [
        "variant",
        "n",
        "hit_1_percent",
        "hit_3_percent",
        "hit_5_percent",
        "hit_10_percent",
        "mrr_10",
    ]
    print(global_summary[display_cols].to_string(index=False))

    print("\n" + "=" * 72)
    print("MUDANÇAS DE RANK VS P0")
    print("=" * 72)
    print(rank_changes.to_string(index=False))

    print("\n" + "=" * 72)
    print("CASOS CRÍTICOS DOWNSTREAM")
    print("=" * 72)
    print(downstream_summary[display_cols].to_string(index=False))

    print("\n" + "=" * 72)
    print("TESTES ESTATÍSTICOS VS P0")
    print("=" * 72)
    print(
        statistical_tests[
            [
                "variant",
                "metric",
                "test",
                "delta",
                "p_raw",
                "p_holm_all_20",
                "p_holm_within_metric",
            ]
        ].to_string(index=False)
    )

    print("\n" + "=" * 72)
    print("ARQUIVOS GERADOS")
    print("=" * 72)
    print(TABLES_DIR)
    print(FIGURES_DIR)
    print(report_path)


if __name__ == "__main__":
    main()

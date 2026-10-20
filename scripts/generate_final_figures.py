from pathlib import Path
import shutil
import tempfile

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

METRICS_DIR = BASE_DIR / "results" / "metrics"
TABLES_DIR = BASE_DIR / "results" / "tables"
FIGURES_DIR = BASE_DIR / "results" / "figures_final"

DOWNSTREAM_DISTRIBUTION_FILE = (
    TABLES_DIR / "downstream_score_distribution.csv"
)

DOWNSTREAM_PAIRWISE_FILE = (
    METRICS_DIR / "downstream_pairwise_vs_p0.csv"
)

JUDGE_SENSITIVITY_FILE = (
    METRICS_DIR / "judge_sensitivity_per_question.csv"
)

RETRIEVAL_RELATIONSHIP_FILE = (
    METRICS_DIR / "retrieval_answer_relationship.csv"
)

CONTROLLED_SUMMARY_FILE = (
    METRICS_DIR / "controlled_summary.csv"
)

# Saídas: os quatro primeiros nomes são exatamente os mesmos
# usados anteriormente, portanto este script substitui as figuras.
FIG_LIKERT = FIGURES_DIR / "fig01_downstream_likert"
FIG_DELTA = FIGURES_DIR / "fig02_downstream_delta"
FIG_JUDGE = FIGURES_DIR / "fig03_judge_sensitivity"
FIG_HIT5 = FIGURES_DIR / "fig04_hit5_vs_score"

# Figura adicional recomendada para o artigo.
FIG_RETRIEVAL_GLOBAL = FIGURES_DIR / "fig05_retrieval_global"


# ============================================================
# PALETA VISUAL PADRONIZADA
# ============================================================

# Azul principal e tons auxiliares.
BLUE_DARK = "#173F5F"
BLUE = "#2F6690"
BLUE_MID = "#5B8DB8"
BLUE_LIGHT = "#9DBDD6"
BLUE_PALE = "#D7E5F0"

# Cinzas.
GRAY_DARK = "#4C5964"
GRAY = "#7E8A94"
GRAY_LIGHT = "#BFC8CF"
GRAY_PALE = "#E5E9EC"

# Elementos neutros.
TEXT = "#25313B"
GRID = "#D8E0E6"
BACKGROUND = "#FFFFFF"

# Likert 1 -> 5:
# cinza claro -> azul escuro.
LIKERT_COLORS = [
    "#DDE2E6",
    "#B8C4CD",
    "#8FAABD",
    "#5F88A7",
    "#2F5F85",
]

# P0-P4 em tons azul/cinza, com contraste suficiente.
VARIANT_COLORS = {
    "P0": "#173F5F",
    "P1": "#60798B",
    "P2": "#9DBDD6",
    "P3": "#5B8DB8",
    "P4": "#2F6690",
}

VARIANTS = ["P0", "P1", "P2", "P3", "P4"]
COMPARISON_VARIANTS = ["P1", "P2", "P3", "P4"]


# ============================================================
# ESTILO GLOBAL
# ============================================================

def configure_style():
    """
    Define um estilo único para todas as figuras do projeto.

    A identidade visual usa apenas tons de azul e cinza,
    sem seaborn e sem estilos externos.
    """
    plt.rcParams.update({
        "figure.facecolor": BACKGROUND,
        "axes.facecolor": BACKGROUND,
        "savefig.facecolor": BACKGROUND,

        "font.family": "DejaVu Sans",
        "font.size": 10,

        "axes.titlesize": 12,
        "axes.titleweight": "semibold",
        "axes.labelsize": 10,
        "axes.labelcolor": TEXT,
        "axes.edgecolor": GRAY_LIGHT,
        "axes.linewidth": 0.8,

        "xtick.color": TEXT,
        "ytick.color": TEXT,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,

        "grid.color": GRID,
        "grid.linewidth": 0.7,
        "grid.alpha": 0.75,

        "legend.frameon": False,
        "legend.fontsize": 9,

        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def require_file(path: Path, label: str):
    if not path.exists():
        raise FileNotFoundError(
            f"{label} não encontrado:\n{path}"
        )


def save_figure(fig, base_path: Path):
    """
    Salva cada figura em PNG 300 dpi e PDF vetorial.

    Estratégia robusta para Windows/OneDrive:
    1. Matplotlib salva primeiro em um arquivo temporário local;
    2. o arquivo pronto é copiado para results/figures_final;
    3. os nomes são curtos e compostos apenas por caracteres ASCII.

    Isso evita o Errno 22 observado ao salvar diretamente sobre
    alguns arquivos antigos sincronizados pelo OneDrive.
    """
    FIGURES_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    fig.tight_layout()

    png_path = base_path.with_suffix(".png")
    pdf_path = base_path.with_suffix(".pdf")

    temp_paths = []

    try:
        # PNG temporário
        with tempfile.NamedTemporaryFile(
            suffix=".png",
            delete=False,
        ) as tmp_png:
            tmp_png_path = Path(tmp_png.name)

        temp_paths.append(tmp_png_path)

        fig.savefig(
            str(tmp_png_path),
            format="png",
            dpi=300,
            bbox_inches="tight",
            facecolor=BACKGROUND,
        )

        # PDF temporário
        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            delete=False,
        ) as tmp_pdf:
            tmp_pdf_path = Path(tmp_pdf.name)

        temp_paths.append(tmp_pdf_path)

        fig.savefig(
            str(tmp_pdf_path),
            format="pdf",
            bbox_inches="tight",
            facecolor=BACKGROUND,
        )

        # Copia os arquivos já finalizados para o OneDrive.
        shutil.copy2(
            tmp_png_path,
            png_path,
        )

        shutil.copy2(
            tmp_pdf_path,
            pdf_path,
        )

    except Exception as exc:
        raise RuntimeError(
            "Falha ao salvar/copiar a figura final.\n"
            f"PNG de destino: {png_path}\n"
            f"PDF de destino: {pdf_path}\n"
            f"Erro original: {type(exc).__name__}: {exc}"
        ) from exc

    finally:
        plt.close(fig)

        for temp_path in temp_paths:
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except Exception:
                pass

    print(f"[OK] {png_path}")
    print(f"[OK] {pdf_path}")


def clean_axes(ax, grid_axis="y"):
    """
    Remove poluição visual e mantém grade discreta.
    """
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.spines["left"].set_color(GRAY_LIGHT)
    ax.spines["bottom"].set_color(GRAY_LIGHT)

    if grid_axis == "y":
        ax.grid(
            axis="y",
            linestyle="-",
            zorder=0,
        )
        ax.grid(
            axis="x",
            visible=False,
        )
    elif grid_axis == "x":
        ax.grid(
            axis="x",
            linestyle="-",
            zorder=0,
        )
        ax.grid(
            axis="y",
            visible=False,
        )
    else:
        ax.grid(False)


# ============================================================
# 1. DISTRIBUIÇÃO LIKERT P0-P4
# ============================================================

def plot_downstream_likert():
    require_file(
        DOWNSTREAM_DISTRIBUTION_FILE,
        "Distribuição downstream",
    )

    df = pd.read_csv(
        DOWNSTREAM_DISTRIBUTION_FILE,
        encoding="utf-8-sig",
    )

    required = {
        "variant",
        "score",
        "percent",
    }

    missing = required - set(df.columns)

    if missing:
        raise RuntimeError(
            "Colunas ausentes em "
            f"{DOWNSTREAM_DISTRIBUTION_FILE.name}: "
            f"{sorted(missing)}"
        )

    pivot = (
        df
        .pivot(
            index="variant",
            columns="score",
            values="percent",
        )
        .reindex(VARIANTS)
        .fillna(0.0)
    )

    fig, ax = plt.subplots(
        figsize=(8.2, 4.8),
    )

    bottom = np.zeros(
        len(pivot),
    )

    for i, score in enumerate(range(1, 6)):
        values = pivot[score].to_numpy()

        bars = ax.bar(
            pivot.index,
            values,
            bottom=bottom,
            color=LIKERT_COLORS[i],
            edgecolor=BACKGROUND,
            linewidth=0.8,
            label=f"Nota {score}",
            zorder=3,
        )

        # Exibe apenas segmentos suficientemente grandes.
        for bar, value, base in zip(
            bars,
            values,
            bottom,
        ):
            if value >= 9:
                ax.text(
                    bar.get_x()
                    + bar.get_width() / 2,
                    base + value / 2,
                    f"{value:.0f}%",
                    ha="center",
                    va="center",
                    fontsize=8.5,
                    color=TEXT,
                )

        bottom += values

    ax.set_title(
        "Distribuição das notas do Juiz LLM nos casos críticos"
    )
    ax.set_xlabel(
        "Estratégia de pré-processamento"
    )
    ax.set_ylabel(
        "Percentual de respostas (%)"
    )
    ax.set_ylim(
        0,
        100,
    )

    ax.legend(
        title="Escala Likert",
        ncol=5,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.17),
    )

    clean_axes(
        ax,
        grid_axis="y",
    )

    save_figure(
        fig,
        FIG_LIKERT,
    )


# ============================================================
# 2. MELHOROU / EMPATOU / PIOROU VS P0
# ============================================================

def plot_downstream_delta():
    require_file(
        DOWNSTREAM_PAIRWISE_FILE,
        "Comparações downstream Pk vs P0",
    )

    df = pd.read_csv(
        DOWNSTREAM_PAIRWISE_FILE,
        encoding="utf-8-sig",
    )

    required = {
        "variant",
        "improved",
        "same",
        "worsened",
    }

    missing = required - set(df.columns)

    if missing:
        raise RuntimeError(
            "Colunas ausentes em "
            f"{DOWNSTREAM_PAIRWISE_FILE.name}: "
            f"{sorted(missing)}"
        )

    plot_df = (
        df
        .set_index("variant")
        .reindex(COMPARISON_VARIANTS)
    )

    x = np.arange(
        len(COMPARISON_VARIANTS),
    )

    width = 0.24

    fig, ax = plt.subplots(
        figsize=(8.2, 4.8),
    )

    bars_improved = ax.bar(
        x - width,
        plot_df["improved"].to_numpy(),
        width,
        color=BLUE,
        label="Melhorou",
        zorder=3,
    )

    bars_same = ax.bar(
        x,
        plot_df["same"].to_numpy(),
        width,
        color=GRAY_LIGHT,
        label="Permaneceu igual",
        zorder=3,
    )

    bars_worsened = ax.bar(
        x + width,
        plot_df["worsened"].to_numpy(),
        width,
        color=GRAY_DARK,
        label="Piorou",
        zorder=3,
    )

    for bars in [
        bars_improved,
        bars_same,
        bars_worsened,
    ]:
        ax.bar_label(
            bars,
            padding=3,
            fontsize=9,
            color=TEXT,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(
        COMPARISON_VARIANTS
    )

    ax.set_title(
        "Mudança da qualidade da resposta em relação a P0"
    )
    ax.set_xlabel(
        "Estratégia comparada com P0"
    )
    ax.set_ylabel(
        "Número de questões"
    )

    ymax = max(
        plot_df[
            [
                "improved",
                "same",
                "worsened",
            ]
        ]
        .to_numpy()
        .max()
        + 4,
        10,
    )

    ax.set_ylim(
        0,
        ymax,
    )

    ax.legend(
        ncol=3,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.17),
    )

    clean_axes(
        ax,
        grid_axis="y",
    )

    save_figure(
        fig,
        FIG_DELTA,
    )


# ============================================================
# 3. MATRIZ DE SENSIBILIDADE DO JUIZ
# ============================================================

def plot_judge_sensitivity():
    require_file(
        JUDGE_SENSITIVITY_FILE,
        "Sensibilidade por questão",
    )

    df = pd.read_csv(
        JUDGE_SENSITIVITY_FILE,
        encoding="utf-8-sig",
    )

    required = {
        "nota_historica",
        "nota_juiz_atual",
    }

    missing = required - set(df.columns)

    if missing:
        raise RuntimeError(
            "Colunas ausentes em "
            f"{JUDGE_SENSITIVITY_FILE.name}: "
            f"{sorted(missing)}"
        )

    matrix = pd.crosstab(
        df["nota_historica"].astype(int),
        df["nota_juiz_atual"].astype(int),
    )

    matrix = matrix.reindex(
        index=range(1, 6),
        columns=range(1, 6),
        fill_value=0,
    )

    # Colormap exclusivamente azul/cinza.
    cmap = LinearSegmentedColormap.from_list(
        "blue_gray",
        [
            "#F1F4F6",
            "#D7E5F0",
            "#9DBDD6",
            "#5B8DB8",
            "#2F6690",
            "#173F5F",
        ],
    )

    fig, ax = plt.subplots(
        figsize=(6.4, 5.4),
    )

    image = ax.imshow(
        matrix.to_numpy(),
        origin="lower",
        aspect="equal",
        cmap=cmap,
    )

    ax.set_xticks(
        range(5)
    )
    ax.set_xticklabels(
        range(1, 6)
    )

    ax.set_yticks(
        range(5)
    )
    ax.set_yticklabels(
        range(1, 6)
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

    max_value = max(
        int(matrix.to_numpy().max()),
        1,
    )

    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = int(
                matrix.iloc[i, j]
            )

            # Contraste automático do texto.
            color = (
                BACKGROUND
                if value >= max_value * 0.55
                else TEXT
            )

            ax.text(
                j,
                i,
                str(value),
                ha="center",
                va="center",
                fontsize=9.5,
                fontweight="semibold",
                color=color,
            )

    cbar = fig.colorbar(
        image,
        ax=ax,
        fraction=0.046,
        pad=0.04,
    )
    cbar.set_label(
        "Número de respostas"
    )
    cbar.outline.set_edgecolor(
        GRAY_LIGHT
    )

    clean_axes(
        ax,
        grid_axis=None,
    )

    save_figure(
        fig,
        FIG_JUDGE,
    )


# ============================================================
# 4. HIT@5 × NOTA DO JUIZ
# ============================================================

def plot_hit5_vs_judge():
    """
    O arquivo retrieval_answer_relationship.csv contém os
    resumos agregados por presença/ausência do alvo no Top-5.

    Como temos apenas as médias agregadas nesse arquivo, o gráfico
    final usa barras de média em vez de boxplot, evitando sugerir
    uma distribuição que não está presente nesse CSV.
    """
    require_file(
        RETRIEVAL_RELATIONSHIP_FILE,
        "Relação retrieval × nota",
    )

    df = pd.read_csv(
        RETRIEVAL_RELATIONSHIP_FILE,
        encoding="utf-8-sig",
    )

    required = {
        "analysis_type",
        "group",
        "n",
        "mean_judge_score",
    }

    missing = required - set(df.columns)

    if missing:
        raise RuntimeError(
            "Colunas ausentes em "
            f"{RETRIEVAL_RELATIONSHIP_FILE.name}: "
            f"{sorted(missing)}"
        )

    groups = df[
        df["analysis_type"] == "hit5_group"
    ].copy()

    order = [
        "target_absent_top5",
        "target_present_top5",
    ]

    groups = (
        groups
        .set_index("group")
        .reindex(order)
    )

    labels = [
        "Alvo ausente\nno Top-5",
        "Alvo presente\nno Top-5",
    ]

    values = (
        groups[
            "mean_judge_score"
        ]
        .to_numpy(dtype=float)
    )

    ns = (
        groups["n"]
        .to_numpy(dtype=int)
    )

    fig, ax = plt.subplots(
        figsize=(6.7, 4.7),
    )

    bars = ax.bar(
        labels,
        values,
        width=0.58,
        color=[
            GRAY_LIGHT,
            BLUE,
        ],
        zorder=3,
    )

    for bar, value, n in zip(
        bars,
        values,
        ns,
    ):
        ax.text(
            bar.get_x()
            + bar.get_width() / 2,
            value + 0.08,
            f"{value:.3f}\n(n={n})",
            ha="center",
            va="bottom",
            fontsize=9,
            color=TEXT,
        )

    ax.set_title(
        "Qualidade da resposta segundo presença do capítulo-alvo no Top-5"
    )
    ax.set_ylabel(
        "Nota média do Juiz LLM"
    )
    ax.set_xlabel(
        ""
    )

    ax.set_ylim(
        0,
        5,
    )
    ax.set_yticks(
        range(0, 6)
    )

    clean_axes(
        ax,
        grid_axis="y",
    )

    save_figure(
        fig,
        FIG_HIT5,
    )


# ============================================================
# 5. RESULTADO GLOBAL DE RETRIEVAL P0-P4
# ============================================================

def plot_controlled_retrieval_global():
    """
    Figura adicional para o artigo final.

    Mostra Hit@1, Hit@3, Hit@5 e Hit@10 em P0-P4.
    MRR@10 não entra na mesma figura porque está em escala distinta.
    """
    require_file(
        CONTROLLED_SUMMARY_FILE,
        "Resumo global de retrieval",
    )

    df = pd.read_csv(
        CONTROLLED_SUMMARY_FILE,
        encoding="utf-8-sig",
    )

    # Aceita nomes alternativos comuns.
    possible_columns = {
        "variant": [
            "variant",
            "variante",
        ],
        "hit_1": [
            "hit_1_percent",
            "hit_1",
            "hit1",
            "Hit@1",
        ],
        "hit_3": [
            "hit_3_percent",
            "hit_3",
            "hit3",
            "Hit@3",
        ],
        "hit_5": [
            "hit_5_percent",
            "hit_5",
            "hit5",
            "Hit@5",
        ],
        "hit_10": [
            "hit_10_percent",
            "hit_10",
            "hit10",
            "Hit@10",
        ],
    }

    resolved = {}

    for logical_name, candidates in possible_columns.items():
        found = [
            col
            for col in candidates
            if col in df.columns
        ]

        if not found:
            raise RuntimeError(
                "Não foi possível localizar a coluna "
                f"correspondente a {logical_name} em "
                f"{CONTROLLED_SUMMARY_FILE.name}. "
                f"Colunas disponíveis: {list(df.columns)}"
            )

        resolved[logical_name] = found[0]

    plot_df = df.copy()

    plot_df = (
        plot_df
        .set_index(
            resolved["variant"]
        )
        .reindex(VARIANTS)
    )

    metric_specs = [
        ("Hit@1", resolved["hit_1"]),
        ("Hit@3", resolved["hit_3"]),
        ("Hit@5", resolved["hit_5"]),
        ("Hit@10", resolved["hit_10"]),
    ]

    # controlled_summary.csv atual armazena os campos *_percent
    # diretamente em pontos percentuais (ex.: 79.23).
    # Para manter compatibilidade com versões antigas, só convertemos
    # por 100 quando todos os valores estiverem na escala 0-1.
    all_values = []

    for _, col in metric_specs:
        all_values.extend(
            pd.to_numeric(
                plot_df[col],
                errors="raise",
            ).tolist()
        )

    scale = 100.0 if max(all_values) <= 1.0 else 1.0

    x = np.arange(
        len(metric_specs)
    )

    width = 0.15

    offsets = (
        np.arange(
            len(VARIANTS)
        )
        - (
            len(VARIANTS)
            - 1
        )
        / 2
    ) * width

    fig, ax = plt.subplots(
        figsize=(9.2, 5.1),
    )

    for offset, variant in zip(
        offsets,
        VARIANTS,
    ):
        values = [
            float(
                plot_df.loc[
                    variant,
                    col,
                ]
            )
            * scale
            for _, col
            in metric_specs
        ]

        ax.bar(
            x + offset,
            values,
            width,
            color=VARIANT_COLORS[variant],
            label=variant,
            zorder=3,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(
        [
            label
            for label, _
            in metric_specs
        ]
    )

    ax.set_title(
        "Desempenho global de recuperação semântica"
    )
    ax.set_xlabel(
        "Métrica"
    )
    ax.set_ylabel(
        "Taxa de acerto (%)"
    )

    ax.set_ylim(
        0,
        100,
    )

    ax.legend(
        title="Variante",
        ncol=5,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.16),
    )

    clean_axes(
        ax,
        grid_axis="y",
    )

    save_figure(
        fig,
        FIG_RETRIEVAL_GLOBAL,
    )


# ============================================================
# MAIN
# ============================================================

def main():
    configure_style()

    print(
        "=" * 78
    )
    print(
        "GERAÇÃO PADRONIZADA DAS FIGURAS FINAIS"
    )
    print(
        "=" * 78
    )
    print(
        "Paleta: tons de azul e cinza"
    )
    print(
        f"Diretório de saída: {FIGURES_DIR}"
    )
    print()

    plot_downstream_likert()
    plot_downstream_delta()
    plot_judge_sensitivity()
    plot_hit5_vs_judge()

    # A figura global de retrieval é recomendada para o artigo.
    # Se controlled_summary.csv estiver disponível, ela também será gerada.
    if CONTROLLED_SUMMARY_FILE.exists():
        plot_controlled_retrieval_global()
    else:
        print(
            "[AVISO] controlled_summary.csv não encontrado; "
            "figura global de retrieval não foi gerada."
        )

    print()
    print(
        "=" * 78
    )
    print(
        "FIGURAS CONCLUÍDAS"
    )
    print(
        "=" * 78
    )
    print(
        "As figuras finais foram geradas em results/figures_final com paleta padronizada em azul e cinza."
    )


if __name__ == "__main__":
    main()

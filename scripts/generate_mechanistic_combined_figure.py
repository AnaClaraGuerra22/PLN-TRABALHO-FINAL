from pathlib import Path
import shutil
import tempfile

import matplotlib.pyplot as plt
import pandas as pd


# ============================================================
# CAMINHOS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

QUERY_FILE = (
    BASE_DIR
    / "results"
    / "raw"
    / "representation_shift_queries.csv"
)

CORRELATION_FILE = (
    BASE_DIR
    / "results"
    / "metrics"
    / "representation_retrieval_correlations.csv"
)

FIGURES_DIR = (
    BASE_DIR
    / "results"
    / "figures_final"
)

OUTPUT_BASE = (
    FIGURES_DIR
    / "fig08_representation_mechanism_combined"
)


# ============================================================
# CONFIGURAÇÃO VISUAL
# ============================================================

BLUE_DARK = "#173F5F"
BLUE = "#2F6690"
BLUE_MID = "#5B8DB8"
BLUE_LIGHT = "#9DBDD6"

GRAY_DARK = "#4C5964"
GRAY = "#7E8A94"
GRAY_LIGHT = "#BFC8CF"

TEXT_COLOR = "#25313B"
GRID_COLOR = "#D8E0E6"
BACKGROUND = "#FFFFFF"

VARIANTS = ["P1", "P2", "P3", "P4"]

VARIANT_COLORS = {
    "P1": GRAY_DARK,
    "P2": BLUE_LIGHT,
    "P3": BLUE_MID,
    "P4": BLUE_DARK,
}


def configure_style():
    plt.rcParams.update({
        "figure.facecolor": BACKGROUND,
        "axes.facecolor": BACKGROUND,
        "savefig.facecolor": BACKGROUND,
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.titleweight": "semibold",
        "axes.labelsize": 10,
        "axes.labelcolor": TEXT_COLOR,
        "axes.edgecolor": GRAY_LIGHT,
        "axes.linewidth": 0.8,
        "xtick.color": TEXT_COLOR,
        "ytick.color": TEXT_COLOR,
        "grid.color": GRID_COLOR,
        "grid.linewidth": 0.7,
        "grid.alpha": 0.75,
        "legend.frameon": False,
        "legend.fontsize": 8.5,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def save_figure_robust(fig, output_base: Path):
    """
    Salva primeiro em arquivos temporários locais e depois copia para
    o diretório sincronizado pelo OneDrive.
    """
    output_base.parent.mkdir(parents=True, exist_ok=True)

    png_path = output_base.with_suffix(".png")
    pdf_path = output_base.with_suffix(".pdf")

    temp_paths = []

    try:
        with tempfile.NamedTemporaryFile(
            suffix=".png",
            delete=False,
        ) as tmp_png:
            tmp_png_path = Path(tmp_png.name)

        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            delete=False,
        ) as tmp_pdf:
            tmp_pdf_path = Path(tmp_pdf.name)

        temp_paths.extend([
            tmp_png_path,
            tmp_pdf_path,
        ])

        fig.savefig(
            tmp_png_path,
            format="png",
            dpi=300,
            bbox_inches="tight",
            facecolor=BACKGROUND,
        )

        fig.savefig(
            tmp_pdf_path,
            format="pdf",
            bbox_inches="tight",
            facecolor=BACKGROUND,
        )

        shutil.copy2(
            tmp_png_path,
            png_path,
        )

        shutil.copy2(
            tmp_pdf_path,
            pdf_path,
        )

    finally:
        plt.close(fig)

        for path in temp_paths:
            try:
                if path.exists():
                    path.unlink()
            except Exception:
                pass

    print(f"[OK] {png_path}")
    print(f"[OK] {pdf_path}")


# ============================================================
# CARREGAMENTO E VALIDAÇÃO
# ============================================================

def load_data():
    if not QUERY_FILE.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado:\n{QUERY_FILE}"
        )

    if not CORRELATION_FILE.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado:\n{CORRELATION_FILE}"
        )

    df = pd.read_csv(
        QUERY_FILE,
        encoding="utf-8-sig",
    )

    corr = pd.read_csv(
        CORRELATION_FILE,
        encoding="utf-8-sig",
    )

    required_query_columns = {
        "id_questao",
        "variant",
        "embedding_drift",
        "top10_jaccard",
    }

    missing = (
        required_query_columns
        - set(df.columns)
    )

    if missing:
        raise RuntimeError(
            "Colunas ausentes em "
            "representation_shift_queries.csv: "
            f"{sorted(missing)}"
        )

    if len(df) != 520:
        raise RuntimeError(
            f"Esperadas 520 linhas; encontradas {len(df)}."
        )

    if set(df["variant"].unique()) != set(VARIANTS):
        raise RuntimeError(
            "Variantes inesperadas: "
            f"{sorted(df['variant'].unique())}"
        )

    counts = (
        df.groupby("variant")
        ["id_questao"]
        .nunique()
        .to_dict()
    )

    expected_counts = {
        variant: 130
        for variant
        in VARIANTS
    }

    if counts != expected_counts:
        raise RuntimeError(
            "Cada variante deveria possuir 130 perguntas.\n"
            f"Encontrado: {counts}"
        )

    required_corr_columns = {
        "family",
        "variant",
        "rho",
        "p_holm_4",
    }

    missing_corr = (
        required_corr_columns
        - set(corr.columns)
    )

    if missing_corr:
        raise RuntimeError(
            "Colunas ausentes em "
            "representation_retrieval_correlations.csv: "
            f"{sorted(missing_corr)}"
        )

    return df, corr


def get_p4_annotation(corr):
    row = corr[
        (
            corr["family"]
            == "drift_vs_top10_jaccard"
        )
        & (
            corr["variant"]
            == "P4"
        )
    ]

    if len(row) != 1:
        raise RuntimeError(
            "Não foi possível localizar exatamente uma "
            "correlação P4 para drift_vs_top10_jaccard."
        )

    row = row.iloc[0]

    rho = float(row["rho"])
    p_holm = float(row["p_holm_4"])

    if p_holm < 0.001:
        p_text = r"$p_{\mathrm{Holm}} < 0{,}001$"
    else:
        p_text = (
            rf"$p_{{\mathrm{{Holm}}}} = "
            f"{p_holm:.3f}$"
        )

    return rho, p_text


# ============================================================
# FIGURA
# ============================================================

def build_figure(df, corr):
    configure_style()

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(12.0, 4.6),
        gridspec_kw={
            "width_ratios": [0.95, 1.20],
            "wspace": 0.26,
        },
    )

    ax1, ax2 = axes

    # --------------------------------------------------------
    # PAINEL (a): distribuição da deriva
    # --------------------------------------------------------

    box_data = [
        df.loc[
            df["variant"] == variant,
            "embedding_drift",
        ].to_numpy()
        for variant
        in VARIANTS
    ]

    bp = ax1.boxplot(
        box_data,
        tick_labels=VARIANTS,
        patch_artist=True,
        widths=0.58,
        showfliers=True,
        medianprops={
            "color": TEXT_COLOR,
            "linewidth": 1.5,
        },
        whiskerprops={
            "color": GRAY_DARK,
            "linewidth": 1.0,
        },
        capprops={
            "color": GRAY_DARK,
            "linewidth": 1.0,
        },
        flierprops={
            "marker": "o",
            "markersize": 3.1,
            "markerfacecolor": BACKGROUND,
            "markeredgecolor": GRAY,
            "markeredgewidth": 0.8,
            "alpha": 0.85,
        },
    )

    for patch, variant in zip(
        bp["boxes"],
        VARIANTS,
    ):
        patch.set_facecolor(
            VARIANT_COLORS[variant]
        )
        patch.set_edgecolor(
            GRAY_DARK
        )
        patch.set_alpha(
            0.92
        )

    ax1.set_title(
        "Deriva da representação",
        pad=10,
    )

    ax1.set_xlabel(
        "Estratégia de pré-processamento"
    )

    ax1.set_ylabel(
        "Embedding drift\n"
        "(1 − similaridade cosseno)"
    )

    ax1.grid(
        axis="y",
        zorder=0,
    )

    ax1.grid(
        axis="x",
        visible=False,
    )

    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    ax1.text(
        0.01,
        0.99,
        "(a)",
        transform=ax1.transAxes,
        ha="left",
        va="top",
        fontsize=11,
        fontweight="bold",
        color=TEXT_COLOR,
    )

    # --------------------------------------------------------
    # PAINEL (b): deriva x estabilidade
    # --------------------------------------------------------

    for variant in VARIANTS:
        subset = df[
            df["variant"] == variant
        ]

        if variant == "P4":
            alpha = 0.72
            size = 27
            zorder = 4
        else:
            alpha = 0.34
            size = 22
            zorder = 2

        ax2.scatter(
            subset["embedding_drift"],
            subset["top10_jaccard"],
            s=size,
            alpha=alpha,
            color=VARIANT_COLORS[variant],
            label=variant,
            edgecolors="none",
            zorder=zorder,
        )

    rho_p4, p_text = get_p4_annotation(
        corr
    )

    annotation = (
        "P4 — Spearman\n"
        rf"$\rho = {rho_p4:.3f}$"
        "\n"
        f"{p_text}"
    )

    ax2.text(
        0.97,
        0.96,
        annotation,
        transform=ax2.transAxes,
        ha="right",
        va="top",
        fontsize=9,
        color=TEXT_COLOR,
        bbox={
            "boxstyle": "round,pad=0.35",
            "facecolor": BACKGROUND,
            "edgecolor": GRAY_LIGHT,
            "alpha": 0.94,
        },
        zorder=10,
    )

    ax2.set_title(
        "Deriva e estabilidade do Top-10",
        pad=10,
    )

    ax2.set_xlabel(
        "Embedding drift\n"
        "(1 − similaridade cosseno)"
    )

    ax2.set_ylabel(
        "Jaccard do Top-10\n"
        "(P0 × Pk)"
    )

    ax2.set_xlim(
        left=-0.01
    )

    ax2.set_ylim(
        -0.03,
        1.03,
    )

    ax2.grid(
        axis="both",
        zorder=0,
    )

    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    ax2.text(
        0.01,
        0.99,
        "(b)",
        transform=ax2.transAxes,
        ha="left",
        va="top",
        fontsize=11,
        fontweight="bold",
        color=TEXT_COLOR,
    )

    ax2.legend(
        title="Variante",
        ncol=4,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.20),
        columnspacing=1.15,
        handletextpad=0.35,
    )

    # --------------------------------------------------------
    # Título geral curto
    # --------------------------------------------------------

    fig.suptitle(
        "Efeito do pré-processamento sobre a representação "
        "e a estabilidade da recuperação",
        fontsize=13,
        fontweight="semibold",
        y=1.015,
    )

    fig.subplots_adjust(
        bottom=0.22,
        top=0.86,
    )

    return fig


def main():
    print("=" * 72)
    print("FIGURA MECANÍSTICA COMBINADA — RQ3")
    print("=" * 72)

    df, corr = load_data()

    print(
        f"[OK] representation_shift_queries.csv: "
        f"{len(df)} linhas"
    )

    print(
        "[OK] Variantes: "
        + ", ".join(VARIANTS)
    )

    fig = build_figure(
        df,
        corr,
    )

    save_figure_robust(
        fig,
        OUTPUT_BASE,
    )

    print("\nFigura final criada com sucesso.")


if __name__ == "__main__":
    main()

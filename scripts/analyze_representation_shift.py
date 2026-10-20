import argparse
import hashlib
import importlib.util
import inspect
import json
import math
import os
import platform
import re
import shutil
import tempfile
import time
from datetime import datetime
from importlib.metadata import version
from itertools import combinations
from pathlib import Path

# Evita downloads silenciosos: esta extensão deve reutilizar o encoder já usado.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import friedmanchisquare, spearmanr, wilcoxon
from sentence_transformers import SentenceTransformer

try:
    from transformers import logging as transformers_logging

    transformers_logging.set_verbosity_error()
except Exception:
    pass


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "data"
REFERENCE_DIR = DATA_DIR / "reference"
PROCESSED_DIR = DATA_DIR / "processed"

RESULTS_DIR = BASE_DIR / "results"
RAW_DIR = RESULTS_DIR / "raw"
METRICS_DIR = RESULTS_DIR / "metrics"
TABLES_DIR = RESULTS_DIR / "tables"
RUNS_DIR = RESULTS_DIR / "runs"
FIGURES_DIR = RESULTS_DIR / "figures_final"

SPAMAZON_FILE = BASE_DIR / "SPAmazon-QA.json"
CONTROLLED_RUN_FILE = RUNS_DIR / "controlled_retrieval_run.json"
QUESTION_METRICS_FILE = METRICS_DIR / "controlled_question_metrics.csv"

# O ranking completo já deve existir do experimento principal.
CONTROLLED_RANKINGS_DEFAULT = RAW_DIR / "controlled_rankings.csv"

P0_CORPUS_DEFAULT = REFERENCE_DIR / "p0_chunks.jsonl"
CORPUS_DEFAULTS = {
    "P0": P0_CORPUS_DEFAULT,
    "P1": PROCESSED_DIR / "p1_chunks.jsonl",
    "P2": PROCESSED_DIR / "p2_chunks.jsonl",
    "P3": PROCESSED_DIR / "p3_chunks.jsonl",
    "P4": PROCESSED_DIR / "p4_chunks.jsonl",
}

PREPROCESS_FILE = BASE_DIR / "src" / "preprocess.py"

MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
EXPECTED_EMBEDDING_DIMENSION = 768
EXPECTED_CHUNKS = 6900
EXPECTED_QUESTIONS = 130
EXPECTED_RANKING_ROWS = 6500
EXPECTED_TOP_K = 10

VARIANTS = ["P0", "P1", "P2", "P3", "P4"]
COMPARISON_VARIANTS = ["P1", "P2", "P3", "P4"]
KEY_CASE_IDS = [11, 58, 65, 83, 124]

EXPECTED_PREPROCESS_SHA256 = (
    "050AEC627D8DA62FAC2F0B8E364FDC9D3102368F1464B17240187E964ACA6610"
)

EXPECTED_CORPUS_SHA256 = {
    "P0": "1fce41571ca46ccca48c9aaf2fc07013aa7fe6bd215305350365eb451a73fae8",
    "P1": "0e1efcd0f921f08956529d89eb0ff267d221fbf494458c655e5e7e6eff1c3c6a",
    "P2": "48dc79cf004d56c5f25905532564fc8a0f4018f6c15fdbe241c2e6b2f8103447",
    "P3": "ae8b5ad596327372a3b5b6cf8e92a422db99ac45daae7e8f288e86e325302e99",
    "P4": "70fd5435015ba57aea468b8148190c1cc619e69796b8b33c6871cbb55ca62ded",
}

PROTOCOL_VERSION = "representation-shift-exploratory-v1"
ALPHA = 0.05

DEFAULT_BATCH_SIZE = 64
DEFAULT_DEVICE = "cpu"

# Saídas
OUT_QUERY_RAW = RAW_DIR / "representation_shift_queries.csv"
OUT_CHUNK_RAW = RAW_DIR / "representation_shift_chunks.csv"

OUT_SUMMARY = METRICS_DIR / "representation_shift_summary.csv"
OUT_TOKEN_SUMMARY = METRICS_DIR / "representation_tokenization_summary.csv"
OUT_RANKING_STABILITY = METRICS_DIR / "representation_ranking_stability.csv"
OUT_CORRELATIONS = METRICS_DIR / "representation_retrieval_correlations.csv"
OUT_STATS = METRICS_DIR / "representation_statistical_tests.csv"

OUT_KEY_CASES = TABLES_DIR / "representation_key_cases.csv"

OUT_RUN = RUNS_DIR / "representation_shift_run.json"
OUT_TEXT_SUMMARY = RUNS_DIR / "representation_shift_summary.txt"

FIG06 = FIGURES_DIR / "fig06_query_embedding_drift"
FIG07 = FIGURES_DIR / "fig07_ranking_stability"

# Paleta final do artigo/repositório
BLUE_DARK = "#173F5F"
BLUE = "#2F6690"
BLUE_MID = "#5B8DB8"
BLUE_LIGHT = "#9DBDD6"
GRAY_DARK = "#4C5964"
GRAY = "#7E8A94"
GRAY_LIGHT = "#BFC8CF"
GRAY_PALE = "#E5E9EC"
TEXT_COLOR = "#25313B"
GRID_COLOR = "#D8E0E6"
BACKGROUND = "#FFFFFF"

VARIANT_COLORS = {
    "P1": GRAY_DARK,
    "P2": BLUE_LIGHT,
    "P3": BLUE_MID,
    "P4": BLUE_DARK,
}


# ============================================================
# UTILIDADES GERAIS
# ============================================================

def now_iso():
    return datetime.now().astimezone().isoformat()


def package_version(package_name):
    try:
        return version(package_name)
    except Exception:
        return None


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def ensure_dirs():
    for directory in [
        RAW_DIR,
        METRICS_DIR,
        TABLES_DIR,
        RUNS_DIR,
        FIGURES_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)


def require_file(path: Path, label: str):
    if not path.exists():
        raise FileNotFoundError(
            f"{label} não encontrado:\n{path}"
        )
    if not path.is_file():
        raise RuntimeError(
            f"{label} existe, mas não é arquivo:\n{path}"
        )


def resolve_unique_file(default_path: Path, filename: str, label: str):
    """
    Usa o caminho padrão quando disponível.
    Caso contrário, procura exatamente o mesmo filename no projeto.
    """
    if default_path.exists():
        return default_path

    matches = [
        p for p in BASE_DIR.rglob(filename)
        if p.is_file()
    ]

    if len(matches) == 1:
        return matches[0]

    if len(matches) == 0:
        raise FileNotFoundError(
            f"{label} não encontrado.\n"
            f"Caminho esperado: {default_path}\n"
            f"Também não foi encontrado nenhum '{filename}' no projeto."
        )

    raise RuntimeError(
        f"Foram encontrados vários arquivos candidatos para {label}:\n"
        + "\n".join(str(p) for p in matches)
        + "\nMantenha apenas o artefato correto ou ajuste o caminho no script."
    )


def configure_plot_style():
    plt.rcParams.update({
        "figure.facecolor": BACKGROUND,
        "axes.facecolor": BACKGROUND,
        "savefig.facecolor": BACKGROUND,
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 12,
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
        "legend.fontsize": 9,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def save_figure_robust(fig, base_path: Path):
    """
    Salva primeiro em arquivo temporário local e só depois copia para o OneDrive,
    evitando o Errno 22 já observado na geração das figuras anteriores.
    """
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()

    png_path = base_path.with_suffix(".png")
    pdf_path = base_path.with_suffix(".pdf")

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

        temp_paths.extend([tmp_png_path, tmp_pdf_path])

        fig.savefig(
            str(tmp_png_path),
            format="png",
            dpi=300,
            bbox_inches="tight",
            facecolor=BACKGROUND,
        )
        fig.savefig(
            str(tmp_pdf_path),
            format="pdf",
            bbox_inches="tight",
            facecolor=BACKGROUND,
        )

        shutil.copy2(tmp_png_path, png_path)
        shutil.copy2(tmp_pdf_path, pdf_path)

    finally:
        plt.close(fig)
        for p in temp_paths:
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass

    print(f"[OK] {png_path}")
    print(f"[OK] {pdf_path}")


def holm_adjust(pvalues):
    """
    Holm-Bonferroni padrão para uma família totalmente observada.
    """
    pvalues = np.asarray(pvalues, dtype=float)
    m = len(pvalues)

    if m == 0:
        return np.array([], dtype=float)

    order = np.argsort(pvalues)
    adjusted = np.empty(m, dtype=float)

    running_max = 0.0

    for rank, idx in enumerate(order, start=1):
        candidate = (m - rank + 1) * pvalues[idx]
        running_max = max(running_max, candidate)
        adjusted[idx] = min(1.0, running_max)

    return adjusted


def holm_adjust_with_total_family(pvalues, total_family_size):
    """
    Correção de Holm preservando o tamanho total da família mesmo quando
    alguma correlação é indefinida por variância zero.

    Exemplo: família planejada de 4 variantes, mas P1 é indefinida.
    As 3 p-values válidas continuam corrigidas de forma conservadora
    considerando família total = 4.
    """
    pvalues = np.asarray(pvalues, dtype=float)

    if len(pvalues) == 0:
        return np.array([], dtype=float)

    order = np.argsort(pvalues)
    adjusted = np.empty(len(pvalues), dtype=float)
    running_max = 0.0

    for rank, idx in enumerate(order, start=1):
        multiplier = total_family_size - rank + 1
        candidate = multiplier * pvalues[idx]
        running_max = max(running_max, candidate)
        adjusted[idx] = min(1.0, running_max)

    return adjusted


def safe_spearman(x, y):
    x = pd.Series(x, dtype=float)
    y = pd.Series(y, dtype=float)

    mask = x.notna() & y.notna()
    x = x[mask]
    y = y[mask]

    if len(x) < 3:
        return np.nan, np.nan, len(x)

    if x.nunique() <= 1 or y.nunique() <= 1:
        return np.nan, np.nan, len(x)

    result = spearmanr(x, y)

    return (
        float(result.statistic),
        float(result.pvalue),
        int(len(x)),
    )


def safe_wilcoxon(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]

    if len(x) == 0:
        return 0.0, 1.0, 0

    diff = x - y

    if np.allclose(diff, 0.0):
        return 0.0, 1.0, len(x)

    result = wilcoxon(
        x,
        y,
        zero_method="wilcox",
        alternative="two-sided",
        method="auto",
    )

    return (
        float(result.statistic),
        float(result.pvalue),
        int(len(x)),
    )


# ============================================================
# CARREGAMENTO DE ARTEFATOS
# ============================================================

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"JSON inválido em {path}, linha {line_number}: {exc}"
                ) from exc
    return rows


def resolve_corpus_files():
    files = {}

    for variant in VARIANTS:
        default = CORPUS_DEFAULTS[variant]
        filename = default.name

        files[variant] = resolve_unique_file(
            default,
            filename,
            f"Corpus {variant}",
        )

    return files


def normalize_corpus_records(records, variant):
    normalized = []

    for i, obj in enumerate(records, start=1):
        if not isinstance(obj, dict):
            raise RuntimeError(
                f"{variant}: registro {i} do corpus não é objeto JSON."
            )

        chunk_id = obj.get("chunk_id")
        document = obj.get("document")

        if chunk_id is None:
            raise RuntimeError(
                f"{variant}: registro {i} sem 'chunk_id'."
            )

        if not isinstance(document, str) or not document.strip():
            raise RuntimeError(
                f"{variant}: chunk {chunk_id} sem texto em 'document'."
            )

        normalized.append({
            "chunk_id": str(chunk_id),
            "document": document,
            "metadata": obj.get("metadata", {}),
            "variant": variant,
        })

    return normalized


def load_and_validate_corpora(corpus_files):
    corpora = {}
    p0_ids = None

    print("\n[1/6] Validando corpora P0-P4...")

    for variant in VARIANTS:
        path = corpus_files[variant]

        actual_hash = sha256_file(path)
        expected_hash = EXPECTED_CORPUS_SHA256[variant]

        if actual_hash.lower() != expected_hash.lower():
            raise RuntimeError(
                f"{variant}: SHA-256 do corpus não corresponde ao artefato congelado.\n"
                f"Esperado: {expected_hash}\n"
                f"Atual:    {actual_hash}\n"
                f"Arquivo:  {path}"
            )

        records = normalize_corpus_records(
            load_jsonl(path),
            variant,
        )

        if len(records) != EXPECTED_CHUNKS:
            raise RuntimeError(
                f"{variant}: esperados {EXPECTED_CHUNKS} chunks; "
                f"encontrados {len(records)}."
            )

        ids = [r["chunk_id"] for r in records]

        if len(set(ids)) != EXPECTED_CHUNKS:
            raise RuntimeError(
                f"{variant}: IDs de chunks não são únicos."
            )

        if p0_ids is None:
            p0_ids = ids
        else:
            if set(ids) != set(p0_ids):
                raise RuntimeError(
                    f"{variant}: conjunto de chunk IDs difere de P0."
                )

        corpora[variant] = {
            r["chunk_id"]: r
            for r in records
        }

        print(
            f"  {variant}: {len(records)} chunks | SHA-256 OK"
        )

    print("  IDs P0-P4: conjuntos idênticos [OK]")

    return corpora, p0_ids


# ============================================================
# PERGUNTAS P0-P4
# ============================================================

QUESTION_ID_KEYS = [
    "id_questao",
    "question_id",
    "qid",
    "id",
]

QUESTION_TEXT_KEYS = [
    "query",
    "query_text",
    "processed_query",
    "query_processed",
    "pergunta_processada",
    "question_processed",
    "processed_question",
    "processed_text",
    "text",
    "pergunta",
    "question",
]


def extract_id(obj):
    if not isinstance(obj, dict):
        return None

    for key in QUESTION_ID_KEYS:
        if key in obj:
            value = obj[key]
            try:
                return int(value)
            except Exception:
                pass

    return None


def extract_question_text(obj):
    if not isinstance(obj, dict):
        return None

    for key in QUESTION_TEXT_KEYS:
        value = obj.get(key)
        if isinstance(value, str) and value.strip():
            return value

    # Estrutura original do SPAmazon-QA.
    conjunto = obj.get("conjunto_curado")
    if isinstance(conjunto, dict):
        value = conjunto.get("pergunta")
        if isinstance(value, str) and value.strip():
            return value

    # Busca recursiva controlada somente em dicionários.
    for value in obj.values():
        if isinstance(value, dict):
            found = extract_question_text(value)
            if found:
                return found

    return None


def load_records_generic(path: Path):
    suffix = path.suffix.lower()

    if suffix == ".jsonl":
        return load_jsonl(path)

    if suffix == ".json":
        data = load_json(path)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # tenta encontrar a primeira lista de registros
            for value in data.values():
                if isinstance(value, list):
                    return value
            return [data]

    if suffix == ".csv":
        return pd.read_csv(path).to_dict("records")

    # fallback: tenta JSONL e depois JSON.
    try:
        return load_jsonl(path)
    except Exception:
        data = load_json(path)
        if isinstance(data, list):
            return data
        return [data]


def normalize_question_records(records, variant):
    rows = []

    for obj in records:
        qid = extract_id(obj)
        text = extract_question_text(obj)

        if qid is None or text is None:
            continue

        rows.append({
            "id_questao": int(qid),
            "text": str(text),
            "variant": variant,
        })

    # remove duplicatas idênticas apenas se forem exatas
    df = pd.DataFrame(rows)

    if df.empty:
        raise RuntimeError(
            f"{variant}: não foi possível extrair perguntas do arquivo."
        )

    if df["id_questao"].duplicated().any():
        duplicated_ids = (
            df.loc[
                df["id_questao"].duplicated(keep=False),
                "id_questao",
            ]
            .tolist()
        )
        raise RuntimeError(
            f"{variant}: IDs de pergunta duplicados: {duplicated_ids[:10]}"
        )

    if len(df) != EXPECTED_QUESTIONS:
        raise RuntimeError(
            f"{variant}: esperadas {EXPECTED_QUESTIONS} perguntas; "
            f"extraídas {len(df)}."
        )

    return (
        df.sort_values("id_questao")
        .reset_index(drop=True)
    )


def find_question_files_by_hash(controlled_run):
    expected_hashes = controlled_run.get(
        "question_file_hashes",
        {},
    )

    if set(expected_hashes) != set(VARIANTS):
        return {}

    target_hash_to_variant = {
        h.lower(): variant
        for variant, h in expected_hashes.items()
    }

    found = {}

    # Primeiro tenta localizar arquivos candidatos dentro de data/.
    search_roots = [
        DATA_DIR,
    ]

    allowed_suffixes = {
        ".jsonl",
        ".json",
        ".csv",
        ".txt",
    }

    for root in search_roots:
        if not root.exists():
            continue

        for path in root.rglob("*"):
            if not path.is_file():
                continue

            if path.suffix.lower() not in allowed_suffixes:
                continue

            # Evita recalcular arquivos já resolvidos e ignora corpora conhecidos
            # quando todos os question hashes forem diferentes.
            file_hash = sha256_file(path).lower()

            variant = target_hash_to_variant.get(file_hash)

            if variant is not None:
                found[variant] = path

            if len(found) == len(VARIANTS):
                return found

    return found


def load_original_questions():
    require_file(
        SPAMAZON_FILE,
        "SPAmazon-QA.json",
    )

    data = load_json(SPAMAZON_FILE)

    if not isinstance(data, list):
        raise RuntimeError(
            "SPAmazon-QA.json deveria conter uma lista de questões."
        )

    rows = []

    for obj in data:
        qid = extract_id(obj)
        text = extract_question_text(obj)

        if qid is None or text is None:
            continue

        rows.append({
            "id_questao": int(qid),
            "text": text,
        })

    df = (
        pd.DataFrame(rows)
        .sort_values("id_questao")
        .reset_index(drop=True)
    )

    if len(df) != EXPECTED_QUESTIONS:
        raise RuntimeError(
            f"SPAmazon-QA: esperadas {EXPECTED_QUESTIONS} perguntas; "
            f"extraídas {len(df)}."
        )

    if df["id_questao"].nunique() != EXPECTED_QUESTIONS:
        raise RuntimeError(
            "SPAmazon-QA: IDs de perguntas não são únicos."
        )

    return df


def load_preprocess_module():
    require_file(
        PREPROCESS_FILE,
        "Implementação congelada src/preprocess.py",
    )

    actual_hash = sha256_file(PREPROCESS_FILE).upper()

    if actual_hash != EXPECTED_PREPROCESS_SHA256:
        raise RuntimeError(
            "src/preprocess.py não corresponde à implementação congelada.\n"
            f"Esperado: {EXPECTED_PREPROCESS_SHA256}\n"
            f"Atual:    {actual_hash}\n"
            "Não prossiga com a reconstrução das consultas."
        )

    spec = importlib.util.spec_from_file_location(
        "frozen_preprocess",
        PREPROCESS_FILE,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Não foi possível importar src/preprocess.py."
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def call_preprocessor(module, text, variant):
    """
    Adaptador defensivo. Só é usado se os arquivos de perguntas P0-P4
    originais não forem localizados pelos hashes registrados.

    O hash de src/preprocess.py é validado antes desta função.
    """
    if variant == "P0":
        # P0, por definição experimental, é a pergunta original.
        return text

    # 1) Mapa explícito PREPROCESSORS / PROCESSORS
    for map_name in [
        "PREPROCESSORS",
        "PROCESSORS",
        "VARIANT_FUNCTIONS",
    ]:
        mapping = getattr(module, map_name, None)
        if isinstance(mapping, dict):
            fn = (
                mapping.get(variant)
                or mapping.get(variant.lower())
            )
            if callable(fn):
                result = fn(text)
                if isinstance(result, str):
                    return result

    # 2) Funções específicas preprocess_p1, p1, process_p1...
    variant_lower = variant.lower()
    for name in [
        f"preprocess_{variant_lower}",
        f"process_{variant_lower}",
        f"transform_{variant_lower}",
        variant_lower,
    ]:
        fn = getattr(module, name, None)
        if callable(fn):
            result = fn(text)
            if isinstance(result, str):
                return result

    # 3) Funções gerais com assinaturas comuns
    general_names = [
        "preprocess_text",
        "preprocess",
        "apply_preprocessing",
        "process_text",
        "transform_text",
        "transform",
    ]

    call_patterns = [
        lambda fn: fn(text, variant),
        lambda fn: fn(text=text, variant=variant),
        lambda fn: fn(text, variant=variant),
        lambda fn: fn(text=text, strategy=variant),
        lambda fn: fn(text, strategy=variant),
        lambda fn: fn(text=text, mode=variant),
        lambda fn: fn(text, mode=variant),
    ]

    errors = []

    for name in general_names:
        fn = getattr(module, name, None)

        if not callable(fn):
            continue

        for call in call_patterns:
            try:
                result = call(fn)
                if isinstance(result, str):
                    return result
            except TypeError as exc:
                errors.append(f"{name}: {exc}")
                continue

    available_callables = sorted(
        name
        for name, value in vars(module).items()
        if callable(value)
        and not name.startswith("_")
    )

    raise RuntimeError(
        f"Não foi possível aplicar {variant} usando src/preprocess.py.\n"
        "Funções públicas encontradas: "
        f"{available_callables}\n"
        "Os arquivos de perguntas congeladas também não foram localizados "
        "pelos hashes do controlled_retrieval_run.json."
    )


def reconstruct_questions_from_frozen_preprocessor():
    original = load_original_questions()
    module = load_preprocess_module()

    result = {}

    for variant in VARIANTS:
        rows = []

        for row in original.itertuples(index=False):
            processed = call_preprocessor(
                module,
                row.text,
                variant,
            )

            if not isinstance(processed, str) or not processed.strip():
                raise RuntimeError(
                    f"{variant}/Q{row.id_questao}: pré-processamento "
                    "produziu texto vazio ou inválido."
                )

            rows.append({
                "id_questao": int(row.id_questao),
                "text": processed,
                "variant": variant,
            })

        result[variant] = pd.DataFrame(rows)

    return result


def load_and_validate_questions(controlled_run):
    print("\n[2/6] Localizando consultas P0-P4 congeladas...")

    found_files = find_question_files_by_hash(controlled_run)

    question_frames = {}
    source_info = {}

    if len(found_files) == len(VARIANTS):
        for variant in VARIANTS:
            path = found_files[variant]
            records = load_records_generic(path)
            df = normalize_question_records(
                records,
                variant,
            )

            expected_hash = controlled_run[
                "question_file_hashes"
            ][variant]

            actual_hash = sha256_file(path)

            if actual_hash.lower() != expected_hash.lower():
                raise RuntimeError(
                    f"{variant}: hash da consulta mudou durante a leitura."
                )

            question_frames[variant] = df
            source_info[variant] = {
                "mode": "frozen_file",
                "path": str(path),
                "sha256": actual_hash,
            }

            print(
                f"  {variant}: 130 perguntas | arquivo congelado por SHA-256 [OK]"
            )
    else:
        print(
            "  [AVISO] Nem todos os arquivos de consultas foram localizados "
            "pelos hashes registrados."
        )
        print(
            "  Reconstruindo P0-P4 exclusivamente com SPAmazon-QA.json + "
            "src/preprocess.py congelado."
        )

        question_frames = reconstruct_questions_from_frozen_preprocessor()

        preprocess_hash = sha256_file(PREPROCESS_FILE)

        for variant in VARIANTS:
            source_info[variant] = {
                "mode": "reconstructed_from_frozen_preprocessor",
                "path": str(PREPROCESS_FILE),
                "preprocess_sha256": preprocess_hash,
                "historical_question_file_sha256": (
                    controlled_run
                    .get("question_file_hashes", {})
                    .get(variant)
                ),
            }

            print(
                f"  {variant}: 130 perguntas reconstruídas [OK]"
            )

    ids_p0 = question_frames["P0"]["id_questao"].tolist()

    for variant in VARIANTS:
        ids = question_frames[variant]["id_questao"].tolist()

        if ids != ids_p0:
            raise RuntimeError(
                f"{variant}: IDs/ordem das perguntas diferem de P0."
            )

    # Confirma que P0 coincide literalmente com as perguntas originais.
    original = load_original_questions()

    if not (
        question_frames["P0"]["text"].tolist()
        == original["text"].tolist()
    ):
        raise RuntimeError(
            "As perguntas P0 não coincidem literalmente com "
            "SPAmazon-QA.json."
        )

    print("  IDs P0-P4: 130 e mesma ordem [OK]")
    print("  P0 == pergunta original do SPAmazon-QA [OK]")

    return question_frames, source_info


# ============================================================
# RANKINGS E MÉTRICAS
# ============================================================

def resolve_rankings_file():
    return resolve_unique_file(
        CONTROLLED_RANKINGS_DEFAULT,
        "controlled_rankings.csv",
        "Ranking controlado Top-10",
    )


def resolve_column(df, candidates, label):
    for col in candidates:
        if col in df.columns:
            return col

    raise RuntimeError(
        f"Não foi possível localizar a coluna '{label}'.\n"
        f"Candidatas: {candidates}\n"
        f"Colunas disponíveis: {list(df.columns)}"
    )


def load_and_validate_rankings(rankings_file):
    print("\n[3/6] Validando rankings controlados...")

    df = pd.read_csv(
        rankings_file,
        encoding="utf-8-sig",
    )

    if len(df) != EXPECTED_RANKING_ROWS:
        raise RuntimeError(
            f"Ranking: esperadas {EXPECTED_RANKING_ROWS} linhas; "
            f"encontradas {len(df)}."
        )

    variant_col = resolve_column(
        df,
        ["variant", "variante"],
        "variant",
    )
    qid_col = resolve_column(
        df,
        ["id_questao", "question_id", "qid"],
        "id_questao",
    )
    rank_col = resolve_column(
        df,
        ["rank", "position", "posicao"],
        "rank",
    )
    chunk_col = resolve_column(
        df,
        ["chunk_id", "id_chunk", "document_id"],
        "chunk_id",
    )

    normalized = df.rename(columns={
        variant_col: "variant",
        qid_col: "id_questao",
        rank_col: "rank",
        chunk_col: "chunk_id",
    }).copy()

    normalized["id_questao"] = pd.to_numeric(
        normalized["id_questao"],
        errors="raise",
    ).astype(int)

    normalized["rank"] = pd.to_numeric(
        normalized["rank"],
        errors="raise",
    ).astype(int)

    normalized["variant"] = normalized["variant"].astype(str)
    normalized["chunk_id"] = normalized["chunk_id"].astype(str)

    if set(normalized["variant"].unique()) != set(VARIANTS):
        raise RuntimeError(
            "Ranking contém variantes inesperadas: "
            f"{sorted(normalized['variant'].unique())}"
        )

    counts = (
        normalized
        .groupby(["variant", "id_questao"])
        .size()
    )

    if not (counts == EXPECTED_TOP_K).all():
        bad = counts[counts != EXPECTED_TOP_K]
        raise RuntimeError(
            "Nem todas as combinações questão-variante possuem Top-10.\n"
            f"Exemplos: {bad.head(10).to_dict()}"
        )

    expected_ranks = set(range(1, EXPECTED_TOP_K + 1))

    for (variant, qid), group in normalized.groupby(
        ["variant", "id_questao"]
    ):
        if set(group["rank"].tolist()) != expected_ranks:
            raise RuntimeError(
                f"{variant}/Q{qid}: ranks não são exatamente 1..10."
            )

    if (
        normalized
        .groupby("variant")["id_questao"]
        .nunique()
        .to_dict()
        != {variant: EXPECTED_QUESTIONS for variant in VARIANTS}
    ):
        raise RuntimeError(
            "Ranking não possui 130 perguntas em cada variante."
        )

    print(
        "  6.500 linhas | 5 variantes × 130 perguntas × Top-10 [OK]"
    )

    return normalized[
        [
            "variant",
            "id_questao",
            "rank",
            "chunk_id",
        ]
    ].copy()


def load_and_validate_question_metrics():
    require_file(
        QUESTION_METRICS_FILE,
        "controlled_question_metrics.csv",
    )

    df = pd.read_csv(
        QUESTION_METRICS_FILE,
        encoding="utf-8-sig",
    )

    required = {
        "variant",
        "id_questao",
        "first_relevant_rank",
        "hit_5",
        "reciprocal_rank_10",
    }

    missing = required - set(df.columns)

    if missing:
        raise RuntimeError(
            "Colunas ausentes em controlled_question_metrics.csv: "
            f"{sorted(missing)}"
        )

    if len(df) != 650:
        raise RuntimeError(
            "controlled_question_metrics.csv deveria ter 650 linhas."
        )

    return df


# ============================================================
# MODELO E TOKENIZER
# ============================================================

def load_model_local(device):
    print("\n[4/6] Carregando encoder/tokenizer localmente...")

    try:
        model = SentenceTransformer(
            MODEL_NAME,
            device=device,
            local_files_only=True,
        )
    except TypeError:
        # Compatibilidade defensiva: o ambiente histórico usa ST 5.3.0,
        # onde local_files_only está disponível. Este fallback existe apenas
        # para versões diferentes, mantendo HF_HUB_OFFLINE=1.
        model = SentenceTransformer(
            MODEL_NAME,
            device=device,
        )
    except Exception as exc:
        raise RuntimeError(
            f"Não foi possível carregar {MODEL_NAME} em modo offline.\n"
            "O modelo precisa estar presente no cache local, pois esta extensão "
            "não deve baixar um encoder diferente.\n"
            f"Erro: {exc}"
        ) from exc

    tokenizer = model.tokenizer

    embedding_dim = model.get_sentence_embedding_dimension()

    if int(embedding_dim) != EXPECTED_EMBEDDING_DIMENSION:
        raise RuntimeError(
            f"Dimensão inesperada: {embedding_dim}. "
            f"Esperado: {EXPECTED_EMBEDDING_DIMENSION}."
        )

    max_seq_length = int(model.max_seq_length)

    print(f"  Modelo: {MODEL_NAME}")
    print(f"  Dimensão: {embedding_dim}")
    print(f"  Tokenizer: {tokenizer.__class__.__name__}")
    print(f"  model.max_seq_length: {max_seq_length}")
    print(f"  Device: {device}")
    print("  Encoder/tokenizer: [OK]")

    return model, tokenizer, max_seq_length


# ============================================================
# PREFLIGHT
# ============================================================

def run_preflight(device):
    print("=" * 78)
    print("PREFLIGHT — EXTENSÃO MECANÍSTICA RQ3")
    print("=" * 78)
    print(f"Protocolo: {PROTOCOL_VERSION}")
    print("Nenhum embedding será calculado no modo --validate-only.")

    require_file(
        CONTROLLED_RUN_FILE,
        "controlled_retrieval_run.json",
    )

    controlled_run = load_json(
        CONTROLLED_RUN_FILE
    )

    if controlled_run.get("embedding_model") != MODEL_NAME:
        raise RuntimeError(
            "O modelo registrado no experimento principal não corresponde "
            f"a {MODEL_NAME}."
        )

    if int(
        controlled_run.get(
            "embedding_dimension",
            -1,
        )
    ) != EXPECTED_EMBEDDING_DIMENSION:
        raise RuntimeError(
            "Dimensionalidade registrada no experimento principal "
            "não corresponde a 768."
        )

    if int(
        controlled_run.get(
            "total_queries",
            -1,
        )
    ) != 650:
        raise RuntimeError(
            "controlled_retrieval_run.json não registra 650 consultas."
        )

    if int(
        controlled_run.get(
            "total_ranking_rows",
            -1,
        )
    ) != EXPECTED_RANKING_ROWS:
        raise RuntimeError(
            "controlled_retrieval_run.json não registra 6.500 posições."
        )

    corpus_files = resolve_corpus_files()

    corpora, chunk_order = load_and_validate_corpora(
        corpus_files
    )

    questions, question_source_info = load_and_validate_questions(
        controlled_run
    )

    rankings_file = resolve_rankings_file()

    rankings = load_and_validate_rankings(
        rankings_file
    )

    question_metrics = load_and_validate_question_metrics()

    print("\n[5/6] Validando IDs entre perguntas, rankings e métricas...")

    expected_ids = set(
        questions["P0"]["id_questao"].tolist()
    )

    ranking_ids = set(
        rankings["id_questao"].unique()
    )

    metric_ids = set(
        question_metrics["id_questao"].astype(int).unique()
    )

    if ranking_ids != expected_ids:
        raise RuntimeError(
            "IDs das perguntas no ranking diferem das consultas."
        )

    if metric_ids != expected_ids:
        raise RuntimeError(
            "IDs em controlled_question_metrics.csv diferem das consultas."
        )

    print("  130 IDs consistentes em perguntas/rankings/métricas [OK]")

    model, tokenizer, max_seq_length = load_model_local(
        device
    )

    print("\n[6/6] Ambiente...")
    print(f"  Python: {platform.python_version()}")
    print(
        "  sentence-transformers: "
        f"{package_version('sentence-transformers')}"
    )
    print(
        "  transformers: "
        f"{package_version('transformers')}"
    )
    print(f"  torch: {package_version('torch')}")
    print(f"  numpy: {package_version('numpy')}")
    print(f"  pandas: {package_version('pandas')}")
    print(f"  scipy: {package_version('scipy')}")

    preflight = {
        "controlled_run": controlled_run,
        "corpus_files": corpus_files,
        "corpora": corpora,
        "chunk_order": chunk_order,
        "questions": questions,
        "question_source_info": question_source_info,
        "rankings_file": rankings_file,
        "rankings": rankings,
        "question_metrics": question_metrics,
        "model": model,
        "tokenizer": tokenizer,
        "max_seq_length": max_seq_length,
    }

    print("\n" + "=" * 78)
    print("PREFLIGHT APROVADO")
    print("=" * 78)
    print("6.900 chunks em P0-P4: OK")
    print("IDs dos chunks idênticos: OK")
    print("130 perguntas P0-P4: OK")
    print("P0 igual às perguntas originais: OK")
    print("650 combinações questão-variante: OK")
    print("6.500 posições Top-10: OK")
    print("Encoder all-mpnet-base-v2: OK")
    print("Dimensão 768: OK")
    print(f"Tokenizer: {tokenizer.__class__.__name__}")
    print(f"Max sequence length: {max_seq_length}")
    print("\nA análise completa ainda NÃO foi executada.")

    return preflight


# ============================================================
# TOKENIZAÇÃO
# ============================================================

def word_count(text):
    return len(
        re.findall(
            r"\S+",
            text,
        )
    )


def tokenize_texts(
    texts,
    tokenizer,
    max_seq_length,
    batch_size,
):
    """
    Retorna a sequência real de subword IDs sem special tokens.
    A contagem efetiva considera os special tokens que o encoder adiciona.
    """
    special_tokens = int(
        tokenizer.num_special_tokens_to_add(
            pair=False
        )
    )

    token_ids_all = []
    info_rows = []

    for start in range(
        0,
        len(texts),
        batch_size,
    ):
        batch = texts[
            start:
            start + batch_size
        ]

        encoded = tokenizer(
            batch,
            add_special_tokens=False,
            truncation=False,
            padding=False,
            return_attention_mask=False,
            return_token_type_ids=False,
        )

        for text, ids in zip(
            batch,
            encoded["input_ids"],
        ):
            ids = list(ids)

            subword_count = len(ids)
            full_with_special = (
                subword_count
                + special_tokens
            )

            effective_count = min(
                full_with_special,
                max_seq_length,
            )

            truncated = (
                full_with_special
                > max_seq_length
            )

            wc = word_count(text)

            info_rows.append({
                "char_count": len(text),
                "word_count": wc,
                "subword_count": subword_count,
                "token_count_with_special": full_with_special,
                "token_count_effective": effective_count,
                "subword_per_word": (
                    subword_count / wc
                    if wc > 0
                    else np.nan
                ),
                "truncated": bool(truncated),
            })

            token_ids_all.append(ids)

    return token_ids_all, info_rows


# ============================================================
# EMBEDDINGS
# ============================================================

def encode_texts(
    model,
    texts,
    batch_size,
    label,
):
    print(
        f"  Codificando {label}: {len(texts)} textos..."
    )

    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=False,
    )

    embeddings = np.asarray(
        embeddings,
        dtype=np.float32,
    )

    if embeddings.shape != (
        len(texts),
        EXPECTED_EMBEDDING_DIMENSION,
    ):
        raise RuntimeError(
            f"{label}: shape inesperado de embeddings: "
            f"{embeddings.shape}"
        )

    return embeddings


def rowwise_embedding_metrics(
    p0_embeddings,
    pk_embeddings,
):
    dot = np.einsum(
        "ij,ij->i",
        p0_embeddings,
        pk_embeddings,
    )

    norm0 = np.linalg.norm(
        p0_embeddings,
        axis=1,
    )

    normk = np.linalg.norm(
        pk_embeddings,
        axis=1,
    )

    denom = norm0 * normk

    cosine = np.divide(
        dot,
        denom,
        out=np.zeros_like(
            dot,
            dtype=np.float32,
        ),
        where=denom != 0,
    )

    cosine = np.clip(
        cosine,
        -1.0,
        1.0,
    )

    drift = 1.0 - cosine

    l2 = np.linalg.norm(
        p0_embeddings
        - pk_embeddings,
        axis=1,
    )

    return cosine, drift, l2


# ============================================================
# ESTABILIDADE DO RANKING
# ============================================================

def build_top10_lookup(rankings):
    lookup = {}

    ordered = rankings.sort_values(
        [
            "variant",
            "id_questao",
            "rank",
        ]
    )

    for (
        variant,
        qid,
    ), group in ordered.groupby(
        [
            "variant",
            "id_questao",
        ]
    ):
        lookup[
            (
                str(variant),
                int(qid),
            )
        ] = group[
            "chunk_id"
        ].astype(str).tolist()

    return lookup


def top10_stability(
    top10_p0,
    top10_pk,
):
    set0 = set(top10_p0)
    setk = set(top10_pk)

    intersection = (
        set0
        & setk
    )

    union = (
        set0
        | setk
    )

    shared = len(intersection)

    overlap = shared / EXPECTED_TOP_K

    jaccard = (
        shared / len(union)
        if union
        else 1.0
    )

    return (
        shared,
        overlap,
        jaccard,
    )


def classify_hit5_transition(
    p0_hit,
    pk_hit,
):
    p0_hit = int(p0_hit)
    pk_hit = int(pk_hit)

    if p0_hit == 0 and pk_hit == 1:
        return "entered_top5"

    if p0_hit == 1 and pk_hit == 0:
        return "left_top5"

    if p0_hit == 1 and pk_hit == 1:
        return "stayed_hit"

    return "stayed_miss"


# ============================================================
# ANÁLISE DAS CONSULTAS
# ============================================================

def analyze_queries(
    preflight,
    batch_size,
):
    print("\n" + "=" * 78)
    print("ANÁLISE DAS 130 CONSULTAS")
    print("=" * 78)

    model = preflight["model"]
    tokenizer = preflight["tokenizer"]
    max_seq_length = preflight["max_seq_length"]
    questions = preflight["questions"]
    rankings = preflight["rankings"]
    metrics = preflight["question_metrics"]

    qids = questions[
        "P0"
    ][
        "id_questao"
    ].astype(int).tolist()

    p0_texts = questions[
        "P0"
    ][
        "text"
    ].tolist()

    p0_token_ids, p0_token_info = tokenize_texts(
        p0_texts,
        tokenizer,
        max_seq_length,
        batch_size,
    )

    p0_embeddings = encode_texts(
        model,
        p0_texts,
        batch_size,
        "consultas P0",
    )

    top10_lookup = build_top10_lookup(
        rankings
    )

    metric_lookup = (
        metrics
        .set_index(
            [
                "variant",
                "id_questao",
            ]
        )
        .sort_index()
    )

    rows = []

    for variant in COMPARISON_VARIANTS:
        print(f"\n[{variant}] Consultas")

        pk_df = questions[variant]
        pk_texts = pk_df["text"].tolist()

        pk_token_ids, pk_token_info = tokenize_texts(
            pk_texts,
            tokenizer,
            max_seq_length,
            batch_size,
        )

        pk_embeddings = encode_texts(
            model,
            pk_texts,
            batch_size,
            f"consultas {variant}",
        )

        cosine, drift, l2 = rowwise_embedding_metrics(
            p0_embeddings,
            pk_embeddings,
        )

        for idx, qid in enumerate(qids):
            p0_info = p0_token_info[idx]
            pk_info = pk_token_info[idx]

            p0_metric = metric_lookup.loc[
                (
                    "P0",
                    qid,
                )
            ]

            pk_metric = metric_lookup.loc[
                (
                    variant,
                    qid,
                )
            ]

            top0 = top10_lookup[
                (
                    "P0",
                    qid,
                )
            ]

            topk = top10_lookup[
                (
                    variant,
                    qid,
                )
            ]

            (
                shared,
                overlap,
                jaccard,
            ) = top10_stability(
                top0,
                topk,
            )

            p0_rank = p0_metric[
                "first_relevant_rank"
            ]
            pk_rank = pk_metric[
                "first_relevant_rank"
            ]

            p0_rank_capped = (
                11
                if pd.isna(p0_rank)
                else int(p0_rank)
            )

            pk_rank_capped = (
                11
                if pd.isna(pk_rank)
                else int(pk_rank)
            )

            p0_rr = float(
                p0_metric[
                    "reciprocal_rank_10"
                ]
            )
            pk_rr = float(
                pk_metric[
                    "reciprocal_rank_10"
                ]
            )

            p0_hit5 = int(
                p0_metric[
                    "hit_5"
                ]
            )
            pk_hit5 = int(
                pk_metric[
                    "hit_5"
                ]
            )

            token_delta = (
                pk_info[
                    "subword_count"
                ]
                - p0_info[
                    "subword_count"
                ]
            )

            token_change_rate = (
                abs(token_delta)
                / max(
                    p0_info[
                        "subword_count"
                    ],
                    1,
                )
            )

            rows.append({
                "id_questao":
                    qid,
                "variant":
                    variant,
                "question_p0":
                    p0_texts[idx],
                "question_pk":
                    pk_texts[idx],

                "p0_char_count":
                    p0_info["char_count"],
                "pk_char_count":
                    pk_info["char_count"],
                "char_delta":
                    (
                        pk_info["char_count"]
                        - p0_info["char_count"]
                    ),

                "p0_word_count":
                    p0_info["word_count"],
                "pk_word_count":
                    pk_info["word_count"],
                "word_delta":
                    (
                        pk_info["word_count"]
                        - p0_info["word_count"]
                    ),

                "p0_subword_count":
                    p0_info["subword_count"],
                "pk_subword_count":
                    pk_info["subword_count"],
                "subword_delta":
                    token_delta,
                "abs_subword_delta":
                    abs(token_delta),
                "subword_change_rate":
                    token_change_rate,

                "p0_token_count_effective":
                    p0_info[
                        "token_count_effective"
                    ],
                "pk_token_count_effective":
                    pk_info[
                        "token_count_effective"
                    ],

                "p0_subword_per_word":
                    p0_info[
                        "subword_per_word"
                    ],
                "pk_subword_per_word":
                    pk_info[
                        "subword_per_word"
                    ],

                "token_sequence_equal":
                    (
                        p0_token_ids[idx]
                        == pk_token_ids[idx]
                    ),

                "p0_truncated":
                    p0_info["truncated"],
                "pk_truncated":
                    pk_info["truncated"],

                "cosine_similarity_p0":
                    float(
                        cosine[idx]
                    ),
                "embedding_drift":
                    float(
                        drift[idx]
                    ),
                "l2_distance":
                    float(
                        l2[idx]
                    ),

                "top10_shared_count":
                    shared,
                "top10_overlap":
                    overlap,
                "top10_jaccard":
                    jaccard,

                "p0_first_relevant_rank":
                    (
                        np.nan
                        if pd.isna(p0_rank)
                        else int(p0_rank)
                    ),
                "pk_first_relevant_rank":
                    (
                        np.nan
                        if pd.isna(pk_rank)
                        else int(pk_rank)
                    ),
                "p0_first_rank_capped_11":
                    p0_rank_capped,
                "pk_first_rank_capped_11":
                    pk_rank_capped,
                "delta_first_rank_capped_11":
                    (
                        pk_rank_capped
                        - p0_rank_capped
                    ),

                "p0_rr_10":
                    p0_rr,
                "pk_rr_10":
                    pk_rr,
                "delta_rr_10":
                    (
                        pk_rr
                        - p0_rr
                    ),
                "abs_delta_rr_10":
                    abs(
                        pk_rr
                        - p0_rr
                    ),

                "p0_hit_5":
                    p0_hit5,
                "pk_hit_5":
                    pk_hit5,
                "hit5_transition":
                    classify_hit5_transition(
                        p0_hit5,
                        pk_hit5,
                    ),
            })

        del pk_embeddings

    result = pd.DataFrame(rows)

    if len(result) != 520:
        raise RuntimeError(
            f"Esperadas 520 observações de consulta; "
            f"obtidas {len(result)}."
        )

    return result


# ============================================================
# ANÁLISE DOS CHUNKS
# ============================================================

def analyze_chunks(
    preflight,
    batch_size,
):
    print("\n" + "=" * 78)
    print("ANÁLISE DOS 6.900 CHUNKS")
    print("=" * 78)
    print(
        "Esta etapa é descritiva e pode levar alguns minutos em CPU."
    )

    model = preflight["model"]
    tokenizer = preflight["tokenizer"]
    max_seq_length = preflight["max_seq_length"]
    corpora = preflight["corpora"]
    chunk_order = preflight["chunk_order"]

    p0_texts = [
        corpora[
            "P0"
        ][chunk_id][
            "document"
        ]
        for chunk_id
        in chunk_order
    ]

    p0_token_ids, p0_token_info = tokenize_texts(
        p0_texts,
        tokenizer,
        max_seq_length,
        batch_size,
    )

    p0_embeddings = encode_texts(
        model,
        p0_texts,
        batch_size,
        "chunks P0",
    )

    rows = []

    for variant in COMPARISON_VARIANTS:
        print(f"\n[{variant}] Chunks")

        pk_texts = [
            corpora[
                variant
            ][chunk_id][
                "document"
            ]
            for chunk_id
            in chunk_order
        ]

        pk_token_ids, pk_token_info = tokenize_texts(
            pk_texts,
            tokenizer,
            max_seq_length,
            batch_size,
        )

        pk_embeddings = encode_texts(
            model,
            pk_texts,
            batch_size,
            f"chunks {variant}",
        )

        cosine, drift, l2 = rowwise_embedding_metrics(
            p0_embeddings,
            pk_embeddings,
        )

        for idx, chunk_id in enumerate(
            chunk_order
        ):
            p0_info = p0_token_info[idx]
            pk_info = pk_token_info[idx]

            token_delta = (
                pk_info[
                    "subword_count"
                ]
                - p0_info[
                    "subword_count"
                ]
            )

            metadata = (
                corpora[
                    "P0"
                ][chunk_id]
                .get(
                    "metadata",
                    {},
                )
            )

            rows.append({
                "chunk_id":
                    chunk_id,
                "variant":
                    variant,
                "source":
                    metadata.get(
                        "source"
                    ),
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

                "p0_char_count":
                    p0_info[
                        "char_count"
                    ],
                "pk_char_count":
                    pk_info[
                        "char_count"
                    ],
                "char_delta":
                    (
                        pk_info[
                            "char_count"
                        ]
                        - p0_info[
                            "char_count"
                        ]
                    ),

                "p0_word_count":
                    p0_info[
                        "word_count"
                    ],
                "pk_word_count":
                    pk_info[
                        "word_count"
                    ],
                "word_delta":
                    (
                        pk_info[
                            "word_count"
                        ]
                        - p0_info[
                            "word_count"
                        ]
                    ),

                "p0_subword_count":
                    p0_info[
                        "subword_count"
                    ],
                "pk_subword_count":
                    pk_info[
                        "subword_count"
                    ],
                "subword_delta":
                    token_delta,
                "abs_subword_delta":
                    abs(
                        token_delta
                    ),
                "subword_change_rate":
                    (
                        abs(
                            token_delta
                        )
                        / max(
                            p0_info[
                                "subword_count"
                            ],
                            1,
                        )
                    ),

                "p0_token_count_effective":
                    p0_info[
                        "token_count_effective"
                    ],
                "pk_token_count_effective":
                    pk_info[
                        "token_count_effective"
                    ],

                "p0_subword_per_word":
                    p0_info[
                        "subword_per_word"
                    ],
                "pk_subword_per_word":
                    pk_info[
                        "subword_per_word"
                    ],

                "token_sequence_equal":
                    (
                        p0_token_ids[idx]
                        == pk_token_ids[idx]
                    ),

                "p0_truncated":
                    p0_info[
                        "truncated"
                    ],
                "pk_truncated":
                    pk_info[
                        "truncated"
                    ],

                "cosine_similarity_p0":
                    float(
                        cosine[idx]
                    ),
                "embedding_drift":
                    float(
                        drift[idx]
                    ),
                "l2_distance":
                    float(
                        l2[idx]
                    ),
            })

        del pk_embeddings

    result = pd.DataFrame(rows)

    if len(result) != 27600:
        raise RuntimeError(
            f"Esperadas 27.600 observações de chunks; "
            f"obtidas {len(result)}."
        )

    return result


# ============================================================
# RESUMOS
# ============================================================

def summarize_representation(
    query_df,
    chunk_df,
):
    rows = []

    for scope, df in [
        ("query", query_df),
        ("chunk", chunk_df),
    ]:
        for variant in COMPARISON_VARIANTS:
            subset = df[
                df["variant"]
                == variant
            ]

            drift = subset[
                "embedding_drift"
            ]

            cosine = subset[
                "cosine_similarity_p0"
            ]

            l2 = subset[
                "l2_distance"
            ]

            rows.append({
                "scope":
                    scope,
                "variant":
                    variant,
                "n":
                    int(
                        len(subset)
                    ),
                "cosine_mean":
                    float(
                        cosine.mean()
                    ),
                "cosine_median":
                    float(
                        cosine.median()
                    ),
                "cosine_std":
                    float(
                        cosine.std(
                            ddof=1
                        )
                    ),
                "drift_mean":
                    float(
                        drift.mean()
                    ),
                "drift_median":
                    float(
                        drift.median()
                    ),
                "drift_std":
                    float(
                        drift.std(
                            ddof=1
                        )
                    ),
                "drift_q25":
                    float(
                        drift.quantile(
                            0.25
                        )
                    ),
                "drift_q75":
                    float(
                        drift.quantile(
                            0.75
                        )
                    ),
                "drift_min":
                    float(
                        drift.min()
                    ),
                "drift_max":
                    float(
                        drift.max()
                    ),
                "l2_mean":
                    float(
                        l2.mean()
                    ),
                "l2_median":
                    float(
                        l2.median()
                    ),
                "token_sequence_equal_count":
                    int(
                        subset[
                            "token_sequence_equal"
                        ].sum()
                    ),
                "token_sequence_equal_percent":
                    float(
                        100.0
                        * subset[
                            "token_sequence_equal"
                        ].mean()
                    ),
                "pk_truncated_count":
                    int(
                        subset[
                            "pk_truncated"
                        ].sum()
                    ),
                "pk_truncated_percent":
                    float(
                        100.0
                        * subset[
                            "pk_truncated"
                        ].mean()
                    ),
            })

    return pd.DataFrame(rows)


def summarize_tokenization(
    query_df,
    chunk_df,
):
    rows = []

    for scope, df in [
        ("query", query_df),
        ("chunk", chunk_df),
    ]:
        for variant in COMPARISON_VARIANTS:
            subset = df[
                df[
                    "variant"
                ]
                == variant
            ]

            rows.append({
                "scope":
                    scope,
                "variant":
                    variant,
                "n":
                    int(
                        len(subset)
                    ),
                "p0_subword_mean":
                    float(
                        subset[
                            "p0_subword_count"
                        ].mean()
                    ),
                "pk_subword_mean":
                    float(
                        subset[
                            "pk_subword_count"
                        ].mean()
                    ),
                "subword_delta_mean":
                    float(
                        subset[
                            "subword_delta"
                        ].mean()
                    ),
                "subword_delta_median":
                    float(
                        subset[
                            "subword_delta"
                        ].median()
                    ),
                "abs_subword_delta_mean":
                    float(
                        subset[
                            "abs_subword_delta"
                        ].mean()
                    ),
                "subword_change_rate_mean":
                    float(
                        subset[
                            "subword_change_rate"
                        ].mean()
                    ),
                "p0_subword_per_word_mean":
                    float(
                        subset[
                            "p0_subword_per_word"
                        ].mean()
                    ),
                "pk_subword_per_word_mean":
                    float(
                        subset[
                            "pk_subword_per_word"
                        ].mean()
                    ),
                "token_sequence_changed_count":
                    int(
                        (
                            ~subset[
                                "token_sequence_equal"
                            ]
                        ).sum()
                    ),
                "token_sequence_changed_percent":
                    float(
                        100.0
                        * (
                            ~subset[
                                "token_sequence_equal"
                            ]
                        ).mean()
                    ),
                "p0_truncated_count":
                    int(
                        subset[
                            "p0_truncated"
                        ].sum()
                    ),
                "pk_truncated_count":
                    int(
                        subset[
                            "pk_truncated"
                        ].sum()
                    ),
            })

    return pd.DataFrame(rows)


def build_ranking_stability(
    query_df,
):
    columns = [
        "id_questao",
        "variant",
        "embedding_drift",
        "cosine_similarity_p0",
        "l2_distance",
        "top10_shared_count",
        "top10_overlap",
        "top10_jaccard",
        "p0_first_relevant_rank",
        "pk_first_relevant_rank",
        "delta_first_rank_capped_11",
        "p0_rr_10",
        "pk_rr_10",
        "delta_rr_10",
        "abs_delta_rr_10",
        "p0_hit_5",
        "pk_hit_5",
        "hit5_transition",
        "subword_delta",
        "abs_subword_delta",
        "subword_change_rate",
        "token_sequence_equal",
    ]

    return query_df[
        columns
    ].copy()


# ============================================================
# TESTES ESTATÍSTICOS
# ============================================================

def build_statistical_tests(
    query_df,
):
    wide = (
        query_df
        .pivot(
            index="id_questao",
            columns="variant",
            values="embedding_drift",
        )
        .reindex(
            columns=COMPARISON_VARIANTS
        )
        .sort_index()
    )

    if wide.isna().any().any():
        raise RuntimeError(
            "Há valores ausentes no pivot de embedding_drift."
        )

    friedman = friedmanchisquare(
        *[
            wide[variant]
            for variant
            in COMPARISON_VARIANTS
        ]
    )

    rows = [{
        "family":
            "embedding_drift_between_variants",
        "comparison":
            "P1-P4",
        "test":
            "Friedman",
        "n":
            int(
                len(wide)
            ),
        "statistic":
            float(
                friedman.statistic
            ),
        "p_raw":
            float(
                friedman.pvalue
            ),
        "p_holm":
            np.nan,
        "alpha":
            ALPHA,
        "significant":
            bool(
                friedman.pvalue
                < ALPHA
            ),
        "status":
            "executed",
    }]

    # O protocolo congelado prevê pós-hoc apenas se Friedman for significativo.
    if friedman.pvalue < ALPHA:
        pair_rows = []

        for a, b in combinations(
            COMPARISON_VARIANTS,
            2,
        ):
            statistic, pvalue, n = safe_wilcoxon(
                wide[a],
                wide[b],
            )

            pair_rows.append({
                "family":
                    "embedding_drift_pairwise",
                "comparison":
                    f"{a}_vs_{b}",
                "test":
                    "Wilcoxon pareado",
                "n":
                    n,
                "statistic":
                    statistic,
                "p_raw":
                    pvalue,
                "p_holm":
                    np.nan,
                "alpha":
                    ALPHA,
                "significant":
                    False,
                "status":
                    "executed",
            })

        adjusted = holm_adjust(
            [
                row[
                    "p_raw"
                ]
                for row
                in pair_rows
            ]
        )

        for row, p_holm in zip(
            pair_rows,
            adjusted,
        ):
            row["p_holm"] = float(
                p_holm
            )
            row["significant"] = bool(
                p_holm
                < ALPHA
            )

        rows.extend(
            pair_rows
        )
    else:
        for a, b in combinations(
            COMPARISON_VARIANTS,
            2,
        ):
            rows.append({
                "family":
                    "embedding_drift_pairwise",
                "comparison":
                    f"{a}_vs_{b}",
                "test":
                    "Wilcoxon pareado",
                "n":
                    int(
                        len(wide)
                    ),
                "statistic":
                    np.nan,
                "p_raw":
                    np.nan,
                "p_holm":
                    np.nan,
                "alpha":
                    ALPHA,
                "significant":
                    False,
                "status":
                    "not_run_global_friedman_not_significant",
            })

    return pd.DataFrame(rows)


def build_correlations(
    query_df,
):
    specs = [
        (
            "drift_vs_top10_jaccard",
            "embedding_drift",
            "top10_jaccard",
        ),
        (
            "drift_vs_abs_delta_rr10",
            "embedding_drift",
            "abs_delta_rr_10",
        ),
    ]

    all_rows = []

    for family, x_col, y_col in specs:
        family_rows = []
        valid_indices = []
        valid_pvalues = []

        for variant in COMPARISON_VARIANTS:
            subset = query_df[
                query_df[
                    "variant"
                ]
                == variant
            ]

            rho, pvalue, n = safe_spearman(
                subset[x_col],
                subset[y_col],
            )

            row = {
                "family":
                    family,
                "variant":
                    variant,
                "x":
                    x_col,
                "y":
                    y_col,
                "n":
                    n,
                "rho":
                    rho,
                "p_raw":
                    pvalue,
                "p_holm_4":
                    np.nan,
                "alpha":
                    ALPHA,
                "significant_holm":
                    False,
                "status":
                    (
                        "executed"
                        if np.isfinite(
                            pvalue
                        )
                        else
                        "undefined_zero_variance_or_insufficient_n"
                    ),
            }

            family_rows.append(
                row
            )

            if np.isfinite(
                pvalue
            ):
                valid_indices.append(
                    len(family_rows)
                    - 1
                )
                valid_pvalues.append(
                    pvalue
                )

        adjusted = holm_adjust_with_total_family(
            valid_pvalues,
            total_family_size=4,
        )

        for idx, p_holm in zip(
            valid_indices,
            adjusted,
        ):
            family_rows[idx][
                "p_holm_4"
            ] = float(
                p_holm
            )
            family_rows[idx][
                "significant_holm"
            ] = bool(
                p_holm
                < ALPHA
            )

        all_rows.extend(
            family_rows
        )

    return pd.DataFrame(
        all_rows
    )


# ============================================================
# CASOS-CHAVE
# ============================================================

def build_key_cases(
    query_df,
):
    subset = query_df[
        query_df[
            "id_questao"
        ].isin(
            KEY_CASE_IDS
        )
    ].copy()

    columns = [
        "id_questao",
        "variant",
        "question_p0",
        "token_sequence_equal",
        "p0_subword_count",
        "pk_subword_count",
        "subword_delta",
        "cosine_similarity_p0",
        "embedding_drift",
        "l2_distance",
        "top10_shared_count",
        "top10_jaccard",
        "p0_first_relevant_rank",
        "pk_first_relevant_rank",
        "p0_rr_10",
        "pk_rr_10",
        "delta_rr_10",
        "p0_hit_5",
        "pk_hit_5",
        "hit5_transition",
    ]

    return (
        subset[
            columns
        ]
        .sort_values(
            [
                "id_questao",
                "variant",
            ]
        )
        .reset_index(
            drop=True
        )
    )


# ============================================================
# FIGURAS
# ============================================================

def plot_query_embedding_drift(
    query_df,
):
    configure_plot_style()

    data = [
        query_df[
            query_df[
                "variant"
            ]
            == variant
        ][
            "embedding_drift"
        ].to_numpy()
        for variant
        in COMPARISON_VARIANTS
    ]

    fig, ax = plt.subplots(
        figsize=(
            8.0,
            4.8,
        )
    )

    bp = ax.boxplot(
        data,
        tick_labels=COMPARISON_VARIANTS,
        patch_artist=True,
        showfliers=True,
        medianprops={
            "color": TEXT_COLOR,
            "linewidth": 1.5,
        },
        whiskerprops={
            "color": GRAY_DARK,
        },
        capprops={
            "color": GRAY_DARK,
        },
        flierprops={
            "marker": "o",
            "markersize": 3,
            "markerfacecolor": BACKGROUND,
            "markeredgecolor": GRAY_DARK,
            "alpha": 0.6,
        },
    )

    for patch, variant in zip(
        bp["boxes"],
        COMPARISON_VARIANTS,
    ):
        patch.set_facecolor(
            VARIANT_COLORS[variant]
        )
        patch.set_edgecolor(
            GRAY_DARK
        )
        patch.set_alpha(
            0.9
        )

    ax.set_title(
        "Deriva da representação vetorial das consultas em relação a P0"
    )
    ax.set_xlabel(
        "Estratégia de pré-processamento"
    )
    ax.set_ylabel(
        "Embedding drift (1 − similaridade cosseno)"
    )

    ax.grid(
        axis="y",
        zorder=0,
    )
    ax.grid(
        axis="x",
        visible=False,
    )

    ax.spines[
        "top"
    ].set_visible(False)
    ax.spines[
        "right"
    ].set_visible(False)

    save_figure_robust(
        fig,
        FIG06,
    )


def plot_ranking_stability(
    query_df,
):
    configure_plot_style()

    fig, ax = plt.subplots(
        figsize=(
            8.0,
            5.0,
        )
    )

    for variant in COMPARISON_VARIANTS:
        subset = query_df[
            query_df[
                "variant"
            ]
            == variant
        ]

        ax.scatter(
            subset[
                "embedding_drift"
            ],
            subset[
                "top10_jaccard"
            ],
            s=28,
            alpha=0.68,
            color=VARIANT_COLORS[
                variant
            ],
            label=variant,
            edgecolors="none",
        )

    ax.set_title(
        "Deriva do embedding e estabilidade do Top-10"
    )
    ax.set_xlabel(
        "Embedding drift (1 − similaridade cosseno)"
    )
    ax.set_ylabel(
        "Jaccard entre Top-10 de P0 e Pk"
    )

    ax.set_ylim(
        -0.03,
        1.03,
    )

    ax.grid(
        axis="both",
        zorder=0,
    )

    ax.spines[
        "top"
    ].set_visible(False)
    ax.spines[
        "right"
    ].set_visible(False)

    ax.legend(
        title="Variante",
        ncol=4,
        loc="upper center",
        bbox_to_anchor=(
            0.5,
            -0.15,
        ),
    )

    save_figure_robust(
        fig,
        FIG07,
    )


# ============================================================
# RESUMO TEXTUAL
# ============================================================

def build_text_summary(
    representation_summary,
    token_summary,
    stats,
    correlations,
    query_df,
):
    lines = []

    lines.append(
        "EXTENSÃO MECANÍSTICA RQ3 — RESUMO REPRODUZÍVEL"
    )
    lines.append(
        "=" * 64
    )
    lines.append("")
    lines.append(
        f"Protocolo: {PROTOCOL_VERSION}"
    )
    lines.append(
        "Natureza: análise mecanística exploratória pós-resultados."
    )
    lines.append("")

    lines.append(
        "1) DERIVA DOS EMBEDDINGS — CONSULTAS"
    )

    query_summary = representation_summary[
        representation_summary[
            "scope"
        ]
        == "query"
    ]

    for _, row in query_summary.iterrows():
        lines.append(
            f"- {row['variant']}: "
            f"cos médio={row['cosine_mean']:.6f}; "
            f"drift médio={row['drift_mean']:.6f}; "
            f"drift mediano={row['drift_median']:.6f}; "
            f"tokens idênticos={row['token_sequence_equal_percent']:.1f}%"
        )

    lines.append("")

    lines.append(
        "2) TOKENIZAÇÃO — CONSULTAS"
    )

    token_query = token_summary[
        token_summary[
            "scope"
        ]
        == "query"
    ]

    for _, row in token_query.iterrows():
        lines.append(
            f"- {row['variant']}: "
            f"Δ subwords médio={row['subword_delta_mean']:+.3f}; "
            f"mudança média relativa={100*row['subword_change_rate_mean']:.2f}%; "
            f"sequência alterada={row['token_sequence_changed_percent']:.1f}%"
        )

    lines.append("")

    lines.append(
        "3) TESTE GLOBAL DE DERIVA"
    )

    friedman = stats[
        stats[
            "test"
        ]
        == "Friedman"
    ].iloc[0]

    lines.append(
        f"- Friedman: estatística={friedman['statistic']:.6f}; "
        f"p={friedman['p_raw']:.8g}"
    )

    lines.append("")

    lines.append(
        "4) DERIVA × ESTABILIDADE DO RETRIEVAL"
    )

    for family in [
        "drift_vs_top10_jaccard",
        "drift_vs_abs_delta_rr10",
    ]:
        lines.append(
            f"- Família: {family}"
        )

        subset = correlations[
            correlations[
                "family"
            ]
            == family
        ]

        for _, row in subset.iterrows():
            if pd.isna(
                row[
                    "rho"
                ]
            ):
                lines.append(
                    f"  {row['variant']}: correlação não definida "
                    "(variância zero ou N insuficiente)."
                )
            else:
                lines.append(
                    f"  {row['variant']}: "
                    f"rho={row['rho']:.4f}; "
                    f"p={row['p_raw']:.6g}; "
                    f"p_Holm={row['p_holm_4']:.6g}"
                )

    lines.append("")

    lines.append(
        "5) TRANSIÇÕES HIT@5"
    )

    transition = (
        query_df
        .groupby(
            [
                "variant",
                "hit5_transition",
            ]
        )
        .agg(
            n=(
                "id_questao",
                "size",
            ),
            mean_drift=(
                "embedding_drift",
                "mean",
            ),
        )
        .reset_index()
    )

    for row in transition.itertuples(
        index=False
    ):
        lines.append(
            f"- {row.variant} / {row.hit5_transition}: "
            f"n={row.n}; drift médio={row.mean_drift:.6f}"
        )

    lines.append("")
    lines.append(
        "INTERPRETAÇÃO: esta extensão é exploratória. "
        "Associações entre deriva e ranking não devem ser descritas "
        "automaticamente como relações causais."
    )

    return "\n".join(
        lines
    )


# ============================================================
# AUDITORIA FINAL
# ============================================================

def build_run_audit(
    preflight,
    args,
    query_df,
    chunk_df,
    representation_summary,
    token_summary,
    stats,
    correlations,
    elapsed_seconds,
):
    output_paths = [
        OUT_QUERY_RAW,
        OUT_CHUNK_RAW,
        OUT_SUMMARY,
        OUT_TOKEN_SUMMARY,
        OUT_RANKING_STABILITY,
        OUT_CORRELATIONS,
        OUT_STATS,
        OUT_KEY_CASES,
        OUT_TEXT_SUMMARY,
        FIG06.with_suffix(".png"),
        FIG06.with_suffix(".pdf"),
        FIG07.with_suffix(".png"),
        FIG07.with_suffix(".pdf"),
    ]

    corpus_hashes = {
        variant: sha256_file(
            resolve_corpus_files()[
                variant
            ]
        )
        for variant
        in VARIANTS
    }

    audit = {
        "timestamp":
            now_iso(),
        "protocol_version":
            PROTOCOL_VERSION,
        "analysis_nature":
            "post-result exploratory mechanistic analysis",
        "rq3":
            (
                "Em que medida as estratégias de pré-processamento alteram "
                "a tokenização e a representação vetorial produzida pelo "
                "all-mpnet-base-v2, e essas alterações estão associadas à "
                "estabilidade do ranking e ao desempenho de recuperação?"
            ),
        "model": {
            "name":
                MODEL_NAME,
            "embedding_dimension":
                EXPECTED_EMBEDDING_DIMENSION,
            "device":
                args.device,
            "batch_size":
                args.batch_size,
            "tokenizer_class":
                preflight[
                    "tokenizer"
                ].__class__.__name__,
            "max_seq_length":
                preflight[
                    "max_seq_length"
                ],
            "normalize_embeddings":
                False,
            "offline_mode":
                True,
        },
        "environment": {
            "python":
                platform.python_version(),
            "sentence_transformers":
                package_version(
                    "sentence-transformers"
                ),
            "transformers":
                package_version(
                    "transformers"
                ),
            "torch":
                package_version(
                    "torch"
                ),
            "numpy":
                package_version(
                    "numpy"
                ),
            "pandas":
                package_version(
                    "pandas"
                ),
            "scipy":
                package_version(
                    "scipy"
                ),
            "matplotlib":
                package_version(
                    "matplotlib"
                ),
        },
        "inputs": {
            "corpus_sha256":
                corpus_hashes,
            "question_sources":
                preflight[
                    "question_source_info"
                ],
            "controlled_rankings_path":
                str(
                    preflight[
                        "rankings_file"
                    ]
                ),
            "controlled_rankings_sha256":
                sha256_file(
                    preflight[
                        "rankings_file"
                    ]
                ),
            "question_metrics_path":
                str(
                    QUESTION_METRICS_FILE
                ),
            "question_metrics_sha256":
                sha256_file(
                    QUESTION_METRICS_FILE
                ),
            "controlled_retrieval_run_path":
                str(
                    CONTROLLED_RUN_FILE
                ),
            "controlled_retrieval_run_sha256":
                sha256_file(
                    CONTROLLED_RUN_FILE
                ),
            "preprocess_path":
                (
                    str(
                        PREPROCESS_FILE
                    )
                    if PREPROCESS_FILE.exists()
                    else None
                ),
            "preprocess_sha256":
                (
                    sha256_file(
                        PREPROCESS_FILE
                    )
                    if PREPROCESS_FILE.exists()
                    else None
                ),
        },
        "counts": {
            "query_comparisons":
                int(
                    len(
                        query_df
                    )
                ),
            "chunk_comparisons":
                int(
                    len(
                        chunk_df
                    )
                ),
            "questions":
                EXPECTED_QUESTIONS,
            "chunks":
                EXPECTED_CHUNKS,
            "comparison_variants":
                COMPARISON_VARIANTS,
        },
        "headline_results": {
            "query_mean_drift":
                {
                    row[
                        "variant"
                    ]:
                        float(
                            row[
                                "drift_mean"
                            ]
                        )
                    for _, row
                    in representation_summary[
                        representation_summary[
                            "scope"
                        ]
                        == "query"
                    ].iterrows()
                },
            "chunk_mean_drift":
                {
                    row[
                        "variant"
                    ]:
                        float(
                            row[
                                "drift_mean"
                            ]
                        )
                    for _, row
                    in representation_summary[
                        representation_summary[
                            "scope"
                        ]
                        == "chunk"
                    ].iterrows()
                },
            "query_token_sequence_equal_percent":
                {
                    row[
                        "variant"
                    ]:
                        float(
                            row[
                                "token_sequence_equal_percent"
                            ]
                        )
                    for _, row
                    in representation_summary[
                        representation_summary[
                            "scope"
                        ]
                        == "query"
                    ].iterrows()
                },
            "friedman_p":
                float(
                    stats.loc[
                        stats[
                            "test"
                        ]
                        == "Friedman",
                        "p_raw",
                    ].iloc[
                        0
                    ]
                ),
        },
        "elapsed_seconds":
            float(
                elapsed_seconds
            ),
        "outputs": {},
    }

    for path in output_paths:
        audit[
            "outputs"
        ][path.name] = {
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

    return audit


# ============================================================
# EXECUÇÃO COMPLETA
# ============================================================

def run_full_analysis(
    preflight,
    args,
):
    ensure_dirs()

    start = time.time()

    query_df = analyze_queries(
        preflight,
        args.batch_size,
    )

    chunk_df = analyze_chunks(
        preflight,
        args.batch_size,
    )

    print("\n" + "=" * 78)
    print("RESUMINDO E TESTANDO RESULTADOS")
    print("=" * 78)

    representation_summary = summarize_representation(
        query_df,
        chunk_df,
    )

    token_summary = summarize_tokenization(
        query_df,
        chunk_df,
    )

    ranking_stability = build_ranking_stability(
        query_df
    )

    stats = build_statistical_tests(
        query_df
    )

    correlations = build_correlations(
        query_df
    )

    key_cases = build_key_cases(
        query_df
    )

    # Salva dados e métricas.
    query_df.to_csv(
        OUT_QUERY_RAW,
        index=False,
        encoding="utf-8-sig",
    )

    chunk_df.to_csv(
        OUT_CHUNK_RAW,
        index=False,
        encoding="utf-8-sig",
    )

    representation_summary.to_csv(
        OUT_SUMMARY,
        index=False,
        encoding="utf-8-sig",
    )

    token_summary.to_csv(
        OUT_TOKEN_SUMMARY,
        index=False,
        encoding="utf-8-sig",
    )

    ranking_stability.to_csv(
        OUT_RANKING_STABILITY,
        index=False,
        encoding="utf-8-sig",
    )

    correlations.to_csv(
        OUT_CORRELATIONS,
        index=False,
        encoding="utf-8-sig",
    )

    stats.to_csv(
        OUT_STATS,
        index=False,
        encoding="utf-8-sig",
    )

    key_cases.to_csv(
        OUT_KEY_CASES,
        index=False,
        encoding="utf-8-sig",
    )

    # Figuras candidatas.
    plot_query_embedding_drift(
        query_df
    )

    plot_ranking_stability(
        query_df
    )

    text_summary = build_text_summary(
        representation_summary,
        token_summary,
        stats,
        correlations,
        query_df,
    )

    OUT_TEXT_SUMMARY.write_text(
        text_summary,
        encoding="utf-8",
    )

    elapsed = (
        time.time()
        - start
    )

    audit = build_run_audit(
        preflight,
        args,
        query_df,
        chunk_df,
        representation_summary,
        token_summary,
        stats,
        correlations,
        elapsed,
    )

    with OUT_RUN.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            audit,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print("\n" + text_summary)

    print("\n" + "=" * 78)
    print("EXTENSÃO MECANÍSTICA RQ3 CONCLUÍDA")
    print("=" * 78)
    print(
        f"Tempo total: {elapsed / 60.0:.1f} min"
    )
    print("\nArquivos principais:")
    for path in [
        OUT_QUERY_RAW,
        OUT_CHUNK_RAW,
        OUT_SUMMARY,
        OUT_TOKEN_SUMMARY,
        OUT_RANKING_STABILITY,
        OUT_CORRELATIONS,
        OUT_STATS,
        OUT_KEY_CASES,
        OUT_TEXT_SUMMARY,
        OUT_RUN,
        FIG06.with_suffix(".pdf"),
        FIG07.with_suffix(".pdf"),
    ]:
        print(path)


# ============================================================
# CLI
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Extensão mecanística exploratória RQ3: "
            "tokenização, deriva de embeddings e estabilidade do ranking."
        )
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help=(
            "Executa somente o preflight. "
            "Não calcula embeddings nem gera resultados."
        ),
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=(
            f"Batch size do SentenceTransformer "
            f"(default: {DEFAULT_BATCH_SIZE})."
        ),
    )

    parser.add_argument(
        "--device",
        default=DEFAULT_DEVICE,
        help=(
            "Device do SentenceTransformer. "
            f"Default: {DEFAULT_DEVICE}."
        ),
    )

    return parser.parse_args()


def main():
    args = parse_args()

    if args.batch_size < 1:
        raise ValueError(
            "--batch-size deve ser >= 1."
        )

    ensure_dirs()

    preflight = run_preflight(
        args.device
    )

    if args.validate_only:
        return

    print(
        "\nATENÇÃO: o preflight foi aprovado. "
        "A partir daqui serão calculados embeddings das "
        "130 consultas e dos 6.900 chunks em P0-P4."
    )

    run_full_analysis(
        preflight,
        args,
    )


if __name__ == "__main__":
    main()

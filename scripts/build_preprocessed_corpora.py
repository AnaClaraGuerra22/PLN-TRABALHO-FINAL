import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path


# ============================================================
# CAMINHOS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

sys.path.insert(
    0,
    str(BASE_DIR)
)

from src.chapters import canonicalize_chunk
from src.preprocess import preprocess


INPUT_FILE = (
    BASE_DIR
    / "data"
    / "reference"
    / "p0_chunks.jsonl"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "processed"
)

AUDIT_FILE = (
    BASE_DIR
    / "results"
    / "runs"
    / "preprocessed_corpora_audit.json"
)

STATS_FILE = (
    BASE_DIR
    / "results"
    / "tables"
    / "preprocessed_corpora_stats.csv"
)


VARIANTS = [
    "P1",
    "P2",
    "P3",
    "P4",
]


# ============================================================
# HASH
# ============================================================

def calcular_sha256(caminho: Path) -> str:

    sha = hashlib.sha256()

    with caminho.open("rb") as f:

        while True:

            bloco = f.read(
                1024 * 1024
            )

            if not bloco:
                break

            sha.update(bloco)

    return sha.hexdigest()


# ============================================================
# CARREGAR P0
# ============================================================

def carregar_p0():

    registros = []

    with INPUT_FILE.open(
        "r",
        encoding="utf-8"
    ) as f:

        for linha in f:

            registros.append(
                json.loads(linha)
            )

    return registros


# ============================================================
# EXECUÇÃO
# ============================================================

def main():

    print("=" * 72)
    print("GERAÇÃO DOS CORPORA PRÉ-PROCESSADOS — P1 A P4")
    print("=" * 72)

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"Corpus P0 não encontrado:\n"
            f"{INPUT_FILE}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    AUDIT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    STATS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # ========================================================
    # P0
    # ========================================================

    print("\nCarregando corpus P0...")

    registros_p0 = carregar_p0()

    total_p0 = len(
        registros_p0
    )

    ids_p0 = [
        r["chunk_id"]
        for r in registros_p0
    ]

    ids_p0_set = set(
        ids_p0
    )

    if total_p0 != 6900:

        raise RuntimeError(
            f"Esperados 6900 chunks no P0. "
            f"Encontrados: {total_p0}"
        )

    if len(ids_p0_set) != 6900:

        raise RuntimeError(
            "Os IDs do P0 não são únicos."
        )

    documentos_canonicos = set()

    for registro in registros_p0:

        documentos_canonicos.add(
            canonicalize_chunk(
                registro["metadata"]
            )
        )

    if len(documentos_canonicos) != 38:

        raise RuntimeError(
            "O P0 não contém os "
            "38 documentos esperados."
        )

    total_chars_p0 = sum(
        len(r["document"])
        for r in registros_p0
    )

    print(
        f"Chunks P0: {total_p0}"
    )

    print(
        "IDs únicos: "
        f"{len(ids_p0_set)}"
    )

    print(
        "Documentos canônicos: "
        f"{len(documentos_canonicos)}"
    )

    print(
        "Caracteres P0: "
        f"{total_chars_p0:,}"
    )

    # ========================================================
    # RESULTADOS DA AUDITORIA
    # ========================================================

    auditoria = {
        "source_file":
            str(INPUT_FILE),
        "source_chunks":
            total_p0,
        "source_unique_ids":
            len(ids_p0_set),
        "canonical_documents":
            len(documentos_canonicos),
        "variants": {},
    }

    estatisticas = []

    # ========================================================
    # VARIANTES
    # ========================================================

    for variant in VARIANTS:

        print("\n" + "=" * 72)

        print(
            f"PROCESSANDO {variant}"
        )

        print("=" * 72)

        output_file = (
            OUTPUT_DIR
            / f"{variant.lower()}_chunks.jsonl"
        )

        ids_saida = []

        documentos_saida = set()

        textos_vazios = 0

        textos_alterados = 0

        metadata_mismatches = 0

        total_chars_saida = 0

        chapter_counts = Counter()

        # ====================================================
        # GERAR CORPUS
        # ====================================================

        with output_file.open(
            "w",
            encoding="utf-8",
            newline="\n"
        ) as f_out:

            for indice, registro in enumerate(
                registros_p0,
                start=1
            ):

                chunk_id = (
                    registro["chunk_id"]
                )

                texto_original = (
                    registro["document"]
                )

                metadata = (
                    registro["metadata"]
                )

                texto_processado = preprocess(
                    texto_original,
                    variant
                )

                if not texto_processado.strip():

                    textos_vazios += 1

                if (
                    texto_processado
                    != texto_original
                ):

                    textos_alterados += 1

                canonical_id = (
                    canonicalize_chunk(
                        metadata
                    )
                )

                documentos_saida.add(
                    canonical_id
                )

                chapter_counts[
                    canonical_id
                ] += 1

                ids_saida.append(
                    chunk_id
                )

                total_chars_saida += len(
                    texto_processado
                )

                registro_saida = {
                    "chunk_id":
                        chunk_id,
                    "variant":
                        variant,
                    "document":
                        texto_processado,
                    "metadata":
                        metadata,
                }

                f_out.write(
                    json.dumps(
                        registro_saida,
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )

                f_out.write("\n")

                if indice % 500 == 0:

                    print(
                        f"  {indice}/6900"
                    )

        # ====================================================
        # VALIDAÇÕES
        # ====================================================

        ids_saida_set = set(
            ids_saida
        )

        if len(ids_saida) != 6900:

            raise RuntimeError(
                f"{variant}: quantidade "
                "incorreta de chunks."
            )

        if len(ids_saida_set) != 6900:

            raise RuntimeError(
                f"{variant}: IDs duplicados."
            )

        if ids_saida_set != ids_p0_set:

            faltando = (
                ids_p0_set
                - ids_saida_set
            )

            extras = (
                ids_saida_set
                - ids_p0_set
            )

            raise RuntimeError(
                f"{variant}: conjunto de IDs "
                "difere do P0.\n"
                f"Faltando: {len(faltando)}\n"
                f"Extras: {len(extras)}"
            )

        if textos_vazios != 0:

            raise RuntimeError(
                f"{variant}: "
                f"{textos_vazios} textos "
                "ficaram vazios."
            )

        if len(documentos_saida) != 38:

            raise RuntimeError(
                f"{variant}: esperado 38 "
                "documentos canônicos."
            )

        # ====================================================
        # VALIDAR METADADOS
        # ====================================================

        p0_por_id = {
            r["chunk_id"]:
                r["metadata"]
            for r in registros_p0
        }

        with output_file.open(
            "r",
            encoding="utf-8"
        ) as f_check:

            for linha in f_check:

                registro = json.loads(
                    linha
                )

                chunk_id = (
                    registro["chunk_id"]
                )

                if (
                    registro["metadata"]
                    != p0_por_id[
                        chunk_id
                    ]
                ):

                    metadata_mismatches += 1

        if metadata_mismatches != 0:

            raise RuntimeError(
                f"{variant}: foram "
                f"encontradas "
                f"{metadata_mismatches} "
                "alterações de metadata."
            )

        # ====================================================
        # ESTATÍSTICAS
        # ====================================================

        reducao_chars = (
            1
            - (
                total_chars_saida
                / total_chars_p0
            )
        ) * 100

        media_chars = (
            total_chars_saida
            / total_p0
        )

        hash_arquivo = calcular_sha256(
            output_file
        )

        auditoria["variants"][
            variant
        ] = {
            "output_file":
                str(output_file),
            "chunks":
                len(ids_saida),
            "unique_ids":
                len(ids_saida_set),
            "canonical_documents":
                len(documentos_saida),
            "empty_documents":
                textos_vazios,
            "changed_documents":
                textos_alterados,
            "metadata_mismatches":
                metadata_mismatches,
            "total_characters":
                total_chars_saida,
            "mean_characters_per_chunk":
                media_chars,
            "character_reduction_percent":
                reducao_chars,
            "sha256":
                hash_arquivo,
            "chapter_counts":
                dict(
                    sorted(
                        chapter_counts.items()
                    )
                ),
        }

        estatisticas.append(
            {
                "variant":
                    variant,
                "chunks":
                    len(ids_saida),
                "unique_ids":
                    len(ids_saida_set),
                "canonical_documents":
                    len(documentos_saida),
                "empty_documents":
                    textos_vazios,
                "changed_documents":
                    textos_alterados,
                "metadata_mismatches":
                    metadata_mismatches,
                "total_characters":
                    total_chars_saida,
                "mean_characters_per_chunk":
                    round(
                        media_chars,
                        2
                    ),
                "character_reduction_percent":
                    round(
                        reducao_chars,
                        2
                    ),
                "sha256":
                    hash_arquivo,
            }
        )

        # ====================================================
        # TERMINAL
        # ====================================================

        print(
            f"\n{variant} concluído."
        )

        print(
            f"Chunks: "
            f"{len(ids_saida)}"
        )

        print(
            f"IDs únicos: "
            f"{len(ids_saida_set)}"
        )

        print(
            f"Documentos: "
            f"{len(documentos_saida)}"
        )

        print(
            f"Textos vazios: "
            f"{textos_vazios}"
        )

        print(
            "Metadados alterados: "
            f"{metadata_mismatches}"
        )

        print(
            "Chunks com texto alterado: "
            f"{textos_alterados}"
        )

        print(
            "Redução de caracteres: "
            f"{reducao_chars:.2f}%"
        )

        print(
            f"SHA-256: "
            f"{hash_arquivo}"
        )

    # ========================================================
    # SALVAR AUDITORIA JSON
    # ========================================================

    with AUDIT_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            auditoria,
            f,
            ensure_ascii=False,
            indent=2,
        )

    # ========================================================
    # SALVAR TABELA
    # ========================================================

    campos = [
        "variant",
        "chunks",
        "unique_ids",
        "canonical_documents",
        "empty_documents",
        "changed_documents",
        "metadata_mismatches",
        "total_characters",
        "mean_characters_per_chunk",
        "character_reduction_percent",
        "sha256",
    ]

    with STATS_FILE.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=campos,
            delimiter=";",
        )

        writer.writeheader()

        writer.writerows(
            estatisticas
        )

    # ========================================================
    # FINAL
    # ========================================================

    print("\n" + "=" * 72)
    print("CORPORA P1–P4 GERADOS E VALIDADOS")
    print("=" * 72)

    print(
        "\nArquivos:"
    )

    for variant in VARIANTS:

        print(
            OUTPUT_DIR
            / f"{variant.lower()}_chunks.jsonl"
        )

    print(
        "\nAuditoria:"
    )

    print(AUDIT_FILE)

    print(
        "\nTabela de estatísticas:"
    )

    print(STATS_FILE)


if __name__ == "__main__":
    main()
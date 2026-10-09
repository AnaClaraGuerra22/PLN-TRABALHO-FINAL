import csv
import hashlib
import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]

sys.path.insert(
    0,
    str(BASE_DIR)
)

from src.preprocess import preprocess


INPUT_FILE = (
    BASE_DIR
    / "SPAmazon-QA.json"
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
    / "preprocessed_queries_audit.json"
)

STATS_FILE = (
    BASE_DIR
    / "results"
    / "tables"
    / "preprocessed_queries_stats.csv"
)

VARIANTS = [
    "P0",
    "P1",
    "P2",
    "P3",
    "P4",
]


def sha256_file(path):

    h = hashlib.sha256()

    with path.open(
        "rb"
    ) as f:

        for bloco in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b""
        ):
            h.update(bloco)

    return h.hexdigest()


def main():

    print("=" * 72)
    print(
        "GERAÇÃO DAS CONSULTAS P0–P4"
    )
    print("=" * 72)

    with INPUT_FILE.open(
        "r",
        encoding="utf-8"
    ) as f:

        dados = json.load(f)

    if len(dados) != 130:

        raise RuntimeError(
            f"Esperadas 130 perguntas; "
            f"encontradas {len(dados)}."
        )

    ids = [
        int(
            r["id_questao"]
        )
        for r in dados
    ]

    if len(set(ids)) != 130:

        raise RuntimeError(
            "IDs de perguntas duplicados."
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    resultados_auditoria = {}

    linhas_stats = []

    for variant in VARIANTS:

        print(
            "\n" + "=" * 72
        )

        print(
            f"PROCESSANDO {variant}"
        )

        print(
            "=" * 72
        )

        output_file = (
            OUTPUT_DIR
            / (
                variant.lower()
                + "_questions.jsonl"
            )
        )

        registros = []

        alteradas = 0

        caracteres_original = 0
        caracteres_processado = 0

        for registro in dados:

            meta = registro[
                "metadados_pergunta"
            ]

            qa = registro[
                "conjunto_curado"
            ]

            pergunta_original = qa[
                "pergunta"
            ]

            query = preprocess(
                pergunta_original,
                variant
            )

            if not query.strip():

                raise RuntimeError(
                    "Consulta vazia: "
                    f"ID {registro['id_questao']} "
                    f"em {variant}"
                )

            if (
                query
                != pergunta_original
            ):
                alteradas += 1

            caracteres_original += len(
                pergunta_original
            )

            caracteres_processado += len(
                query
            )

            registros.append({
                "id_questao":
                    int(
                        registro[
                            "id_questao"
                        ]
                    ),

                "variant":
                    variant,

                "query":
                    query,

                "pergunta_original":
                    pergunta_original,

                "capitulo_alvo":
                    meta.get(
                        "capitulo_alvo"
                    ),

                "dificuldade":
                    meta.get(
                        "dificuldade"
                    ),

                "tipo":
                    meta.get(
                        "tipo"
                    ),

                "modelo_gerador_qa":
                    meta.get(
                        "modelo_gerador_qa"
                    ),

                "indice_subjetividade":
                    meta.get(
                        "indice_subjetividade"
                    ),
            })

        registros.sort(
            key=lambda x:
            x["id_questao"]
        )

        with output_file.open(
            "w",
            encoding="utf-8"
        ) as f:

            for registro in registros:

                f.write(
                    json.dumps(
                        registro,
                        ensure_ascii=False
                    )
                    + "\n"
                )

        ids_saida = [
            r["id_questao"]
            for r in registros
        ]

        if ids_saida != sorted(ids):

            raise RuntimeError(
                f"{variant}: conjunto "
                "de IDs inesperado."
            )

        reducao = (
            (
                1
                - (
                    caracteres_processado
                    / caracteres_original
                )
            )
            * 100
        )

        hash_saida = sha256_file(
            output_file
        )

        resultados_auditoria[
            variant
        ] = {
            "questions":
                len(registros),

            "unique_ids":
                len(
                    set(ids_saida)
                ),

            "empty_queries":
                0,

            "changed_queries":
                alteradas,

            "original_characters":
                caracteres_original,

            "processed_characters":
                caracteres_processado,

            "character_reduction_percent":
                reducao,

            "sha256":
                hash_saida,

            "output_file":
                str(output_file),
        }

        linhas_stats.append({
            "variant":
                variant,

            "questions":
                len(registros),

            "changed_queries":
                alteradas,

            "character_reduction_percent":
                reducao,

            "sha256":
                hash_saida,
        })

        print(
            f"Perguntas: "
            f"{len(registros)}"
        )

        print(
            f"IDs únicos: "
            f"{len(set(ids_saida))}"
        )

        print(
            "Consultas vazias: 0"
        )

        print(
            "Consultas alteradas: "
            f"{alteradas}"
        )

        print(
            "Redução de caracteres: "
            f"{reducao:.2f}%"
        )

        print(
            f"SHA-256: {hash_saida}"
        )

    # ========================================================
    # AUDITORIA
    # ========================================================

    AUDIT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with AUDIT_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            {
                "source":
                    str(INPUT_FILE),

                "total_questions":
                    130,

                "variants":
                    resultados_auditoria,
            },
            f,
            ensure_ascii=False,
            indent=2
        )

    # ========================================================
    # TABELA
    # ========================================================

    STATS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with STATS_FILE.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "variant",
                "questions",
                "changed_queries",
                "character_reduction_percent",
                "sha256",
            ]
        )

        writer.writeheader()

        writer.writerows(
            linhas_stats
        )

    print(
        "\n" + "=" * 72
    )

    print(
        "CONSULTAS P0–P4 GERADAS E VALIDADAS"
    )

    print(
        "=" * 72
    )

    print(
        f"\nAuditoria:\n{AUDIT_FILE}"
    )

    print(
        f"\nEstatísticas:\n{STATS_FILE}"
    )


if __name__ == "__main__":
    main()
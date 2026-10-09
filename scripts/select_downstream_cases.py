import csv
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = BASE_DIR / "SPAmazon-QA.json"

OUTPUT_JSONL = (
    BASE_DIR
    / "data"
    / "reference"
    / "downstream_critical_cases.jsonl"
)

OUTPUT_CSV = (
    BASE_DIR
    / "results"
    / "tables"
    / "downstream_critical_cases.csv"
)

OUTPUT_AUDIT = (
    BASE_DIR
    / "results"
    / "runs"
    / "downstream_cases_selection.json"
)


def carregar_amazoniaexpert(avaliacoes):

    for avaliacao in avaliacoes:

        if (
            avaliacao.get("modelo_avaliado")
            == "AmazoniaExpert.IA"
        ):
            return avaliacao

    return None


def main():

    print("=" * 72)
    print("SELEÇÃO DOS CASOS CRÍTICOS DOWNSTREAM")
    print("=" * 72)

    with INPUT_FILE.open(
        "r",
        encoding="utf-8"
    ) as f:

        dados = json.load(f)

    if len(dados) != 130:

        raise RuntimeError(
            f"Esperadas 130 questões; "
            f"encontradas {len(dados)}."
        )

    casos = []

    ids_nota_baixa = set()
    ids_falha_retrieval = set()

    for registro in dados:

        id_questao = int(
            registro["id_questao"]
        )

        meta = registro[
            "metadados_pergunta"
        ]

        qa = registro[
            "conjunto_curado"
        ]

        avaliacao = carregar_amazoniaexpert(
            registro["avaliacoes_modelos"]
        )

        if avaliacao is None:

            raise RuntimeError(
                f"Questão {id_questao}: "
                "AmazoniaExpert.IA não encontrado."
            )

        juiz = avaliacao.get(
            "juiz_llm",
            {}
        )

        nota = juiz.get(
            "nota_likert"
        )

        justificativa = juiz.get(
            "justificativa_tecnica",
            ""
        )

        recuperado = avaliacao.get(
            "capitulo_recuperado"
        )

        nota_baixa = (
            nota in [1, 2, 3]
        )

        falha_retrieval = (
            recuperado is False
        )

        if nota_baixa:
            ids_nota_baixa.add(
                id_questao
            )

        if falha_retrieval:
            ids_falha_retrieval.add(
                id_questao
            )

        if not (
            nota_baixa
            or falha_retrieval
        ):
            continue

        criterios = []

        if nota_baixa:
            criterios.append(
                "nota_1_2_3"
            )

        if falha_retrieval:
            criterios.append(
                "falha_recuperacao_historica"
            )

        casos.append({
            "id_questao":
                id_questao,

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

            "pergunta":
                qa.get(
                    "pergunta"
                ),

            "gabarito":
                qa.get(
                    "resposta_esperada"
                ),

            "resposta_historica_amazoniaexpert":
                avaliacao.get(
                    "resposta_gerada"
                ),

            "nota_historica":
                nota,

            "justificativa_historica":
                justificativa,

            "capitulo_recuperado_historico":
                recuperado,

            "criterios_selecao":
                criterios,
        })

    casos.sort(
        key=lambda x: x[
            "id_questao"
        ]
    )

    ids_selecionados = {
        c["id_questao"]
        for c in casos
    }

    ids_intersecao = (
        ids_nota_baixa
        & ids_falha_retrieval
    )

    # ========================================================
    # JSONL
    # ========================================================

    OUTPUT_JSONL.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT_JSONL.open(
        "w",
        encoding="utf-8"
    ) as f:

        for caso in casos:

            f.write(
                json.dumps(
                    caso,
                    ensure_ascii=False
                )
                + "\n"
            )

    # ========================================================
    # CSV
    # ========================================================

    OUTPUT_CSV.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    campos = [
        "id_questao",
        "capitulo_alvo",
        "dificuldade",
        "tipo",
        "modelo_gerador_qa",
        "indice_subjetividade",
        "pergunta",
        "gabarito",
        "resposta_historica_amazoniaexpert",
        "nota_historica",
        "justificativa_historica",
        "capitulo_recuperado_historico",
        "criterios_selecao",
    ]

    with OUTPUT_CSV.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=campos
        )

        writer.writeheader()

        for caso in casos:

            linha = caso.copy()

            linha[
                "criterios_selecao"
            ] = "|".join(
                linha[
                    "criterios_selecao"
                ]
            )

            writer.writerow(
                linha
            )

    # ========================================================
    # AUDITORIA
    # ========================================================

    audit = {
        "total_spamazon_qa":
            len(dados),

        "regra_selecao":
            (
                "nota_historica_amazoniaexpert "
                "in [1,2,3] OR "
                "capitulo_recuperado_historico == false"
            ),

        "nota_1_2_3":
            len(ids_nota_baixa),

        "falha_recuperacao_historica":
            len(ids_falha_retrieval),

        "intersecao":
            len(ids_intersecao),

        "total_casos_unicos":
            len(ids_selecionados),

        "ids_nota_1_2_3":
            sorted(
                ids_nota_baixa
            ),

        "ids_falha_recuperacao":
            sorted(
                ids_falha_retrieval
            ),

        "ids_intersecao":
            sorted(
                ids_intersecao
            ),

        "ids_selecionados":
            sorted(
                ids_selecionados
            ),
    }

    OUTPUT_AUDIT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT_AUDIT.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            audit,
            f,
            ensure_ascii=False,
            indent=2
        )

    # ========================================================
    # RESULTADO
    # ========================================================

    print(
        f"\nNotas 1–3: "
        f"{len(ids_nota_baixa)}"
    )

    print(
        "Falhas históricas de recuperação: "
        f"{len(ids_falha_retrieval)}"
    )

    print(
        "Interseção: "
        f"{len(ids_intersecao)}"
    )

    print(
        "Casos críticos únicos: "
        f"{len(ids_selecionados)}"
    )

    print(
        "\nIDs com nota 1–3:"
    )
    print(
        sorted(ids_nota_baixa)
    )

    print(
        "\nIDs com falha de recuperação:"
    )
    print(
        sorted(ids_falha_retrieval)
    )

    print(
        "\nIDs presentes nas duas categorias:"
    )
    print(
        sorted(ids_intersecao)
    )

    print(
        "\nTodos os casos selecionados:"
    )
    print(
        sorted(ids_selecionados)
    )

    print(
        "\nArquivos:"
    )

    print(
        OUTPUT_JSONL
    )

    print(
        OUTPUT_CSV
    )

    print(
        OUTPUT_AUDIT
    )


if __name__ == "__main__":
    main()
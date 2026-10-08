import csv
import json
import sys
from pathlib import Path
from collections import Counter


# ============================================================
# CAMINHOS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(BASE_DIR))

from src.chapters import (
    canonicalize_chunk,
    canonicalize_target,
)


QA_FILE = BASE_DIR / "SPAmazon-QA.json"

P0_FILE = (
    BASE_DIR
    / "data"
    / "reference"
    / "p0_chunks.jsonl"
)

DERIVED_FILE = (
    BASE_DIR
    / "data"
    / "reference"
    / "spamazon_qa_questions.jsonl"
)

AUDIT_FILE = (
    BASE_DIR
    / "results"
    / "runs"
    / "spamazon_qa_validation.json"
)

TABLE_FILE = (
    BASE_DIR
    / "results"
    / "tables"
    / "questions_por_documento.csv"
)


# ============================================================
# CARREGAR DOCUMENTOS CANÔNICOS DO CORPUS
# ============================================================

def carregar_documentos_corpus():

    documentos = set()

    with P0_FILE.open(
        "r",
        encoding="utf-8"
    ) as f:

        for linha in f:

            registro = json.loads(linha)

            canonical_id = canonicalize_chunk(
                registro["metadata"]
            )

            documentos.add(canonical_id)

    return documentos


# ============================================================
# EXECUÇÃO
# ============================================================

def main():

    print("=" * 70)
    print("VALIDAÇÃO DO SPAmazon-QA")
    print("=" * 70)

    # --------------------------------------------------------
    # Arquivos
    # --------------------------------------------------------

    if not QA_FILE.exists():
        raise FileNotFoundError(
            f"SPAmazon-QA não encontrado:\n{QA_FILE}"
        )

    if not P0_FILE.exists():
        raise FileNotFoundError(
            f"Corpus P0 não encontrado:\n{P0_FILE}"
        )

    # --------------------------------------------------------
    # Corpus
    # --------------------------------------------------------

    corpus_ids = carregar_documentos_corpus()

    print(
        f"\nDocumentos canônicos no corpus: "
        f"{len(corpus_ids)}"
    )

    if len(corpus_ids) != 38:
        raise RuntimeError(
            f"Esperados 38 documentos no corpus, "
            f"mas encontrados {len(corpus_ids)}."
        )

    # --------------------------------------------------------
    # SPAmazon-QA
    # --------------------------------------------------------

    with QA_FILE.open(
        "r",
        encoding="utf-8"
    ) as f:

        dados = json.load(f)

    print(
        f"Perguntas encontradas: {len(dados)}"
    )

    if len(dados) != 130:
        raise RuntimeError(
            f"Esperadas 130 perguntas, "
            f"mas encontradas {len(dados)}."
        )

    # --------------------------------------------------------
    # Estruturas de auditoria
    # --------------------------------------------------------

    ids = []
    targets_originais = Counter()
    targets_canonicos = Counter()

    tipos = Counter()
    dificuldades = Counter()

    registros_derivados = []

    erros = []

    # --------------------------------------------------------
    # Validar cada questão
    # --------------------------------------------------------

    for registro in dados:

        question_id = registro.get(
            "id_questao"
        )

        ids.append(question_id)

        metadata = registro.get(
            "metadados_pergunta"
        ) or {}

        conjunto = registro.get(
            "conjunto_curado"
        ) or {}

        target_original = metadata.get(
            "capitulo_alvo"
        )

        pergunta = conjunto.get(
            "pergunta"
        )

        resposta_esperada = conjunto.get(
            "resposta_esperada"
        )

        tipo = metadata.get(
            "tipo"
        )

        dificuldade = metadata.get(
            "dificuldade"
        )

        subjetividade = metadata.get(
            "indice_subjetividade"
        )

        modelo_gerador = metadata.get(
            "modelo_gerador_qa"
        )

        # ----------------------------------------------------
        # Campos obrigatórios
        # ----------------------------------------------------

        if question_id is None:
            erros.append(
                "Questão sem id_questao."
            )
            continue

        if not pergunta:
            erros.append(
                f"Questão {question_id}: "
                "pergunta vazia."
            )

        if not target_original:
            erros.append(
                f"Questão {question_id}: "
                "capitulo_alvo ausente."
            )
            continue

        # ----------------------------------------------------
        # Canonicalização
        # ----------------------------------------------------

        try:

            target_id = canonicalize_target(
                target_original
            )

        except ValueError as e:

            erros.append(
                f"Questão {question_id}: {e}"
            )

            continue

        targets_originais[
            target_original
        ] += 1

        targets_canonicos[
            target_id
        ] += 1

        tipos[tipo] += 1
        dificuldades[dificuldade] += 1

        # ----------------------------------------------------
        # O alvo existe no corpus?
        # ----------------------------------------------------

        if target_id not in corpus_ids:

            erros.append(
                f"Questão {question_id}: "
                f"{target_original!r} -> "
                f"{target_id!r}, mas esse "
                "documento não existe no corpus."
            )

        # ----------------------------------------------------
        # Registro derivado
        # ----------------------------------------------------

        registros_derivados.append(
            {
                "id_questao": question_id,
                "pergunta": pergunta,
                "resposta_esperada":
                    resposta_esperada,
                "capitulo_alvo_original":
                    target_original,
                "capitulo_alvo_id":
                    target_id,
                "tipo": tipo,
                "dificuldade":
                    dificuldade,
                "indice_subjetividade":
                    subjetividade,
                "modelo_gerador_qa":
                    modelo_gerador,
            }
        )

    # ========================================================
    # VALIDAÇÕES GLOBAIS
    # ========================================================

    ids_unicos = set(ids)

    print("\n" + "=" * 70)
    print("ESTRUTURA DO BENCHMARK")
    print("=" * 70)

    print(
        f"IDs totais: {len(ids)}"
    )

    print(
        f"IDs únicos: {len(ids_unicos)}"
    )

    print(
        "Grafias distintas de "
        f"capitulo_alvo: "
        f"{len(targets_originais)}"
    )

    print(
        "Capítulos canônicos distintos: "
        f"{len(targets_canonicos)}"
    )

    if len(ids_unicos) != 130:
        erros.append(
            "Os 130 id_questao não são únicos."
        )

    if set(ids) != set(range(1, 131)):
        erros.append(
            "Os IDs não correspondem "
            "exatamente ao intervalo 1–130."
        )

    if len(targets_originais) != 39:
        erros.append(
            f"Esperadas 39 grafias de alvo; "
            f"foram encontradas "
            f"{len(targets_originais)}."
        )

    if len(targets_canonicos) != 38:
        erros.append(
            f"Esperados 38 alvos canônicos; "
            f"foram encontrados "
            f"{len(targets_canonicos)}."
        )

    # ========================================================
    # DISTRIBUIÇÕES
    # ========================================================

    print("\n" + "=" * 70)
    print("TIPO")
    print("=" * 70)

    for valor, quantidade in sorted(
        tipos.items()
    ):
        print(
            f"{valor:<20} {quantidade}"
        )

    print("\n" + "=" * 70)
    print("DIFICULDADE")
    print("=" * 70)

    for valor, quantidade in sorted(
        dificuldades.items()
    ):
        print(
            f"{valor:<20} {quantidade}"
        )

    # --------------------------------------------------------
    # Valores esperados
    # --------------------------------------------------------

    esperado_tipo = {
        "Direct": 53,
        "Indirect": 77,
    }

    esperado_dificuldade = {
        "Easy": 7,
        "Medium-Low": 28,
        "Medium-High": 16,
        "Hard": 79,
    }

    if dict(tipos) != esperado_tipo:
        erros.append(
            "Distribuição de tipo diferente "
            "da esperada."
        )

    if dict(dificuldades) != esperado_dificuldade:
        erros.append(
            "Distribuição de dificuldade "
            "diferente da esperada."
        )

    # ========================================================
    # ALVOS
    # ========================================================

    print("\n" + "=" * 70)
    print("PERGUNTAS POR DOCUMENTO CANÔNICO")
    print("=" * 70)

    for target, quantidade in sorted(
        targets_canonicos.items()
    ):
        print(
            f"{target:<25} "
            f"{quantidade:>3}"
        )

    # --------------------------------------------------------
    # Checagem especial dos Cross Chapters
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("CHECAGEM DOS CROSS CHAPTERS")
    print("=" * 70)

    print(
        "cross_chapter_1:",
        targets_canonicos[
            "cross_chapter_1"
        ],
        "perguntas"
    )

    print(
        "cross_chapter_2:",
        targets_canonicos[
            "cross_chapter_2"
        ],
        "perguntas"
    )

    print(
        "\nGrafias que resultaram em "
        "cross_chapter_2:"
    )

    for original, quantidade in sorted(
        targets_originais.items()
    ):

        try:
            canonical = canonicalize_target(
                original
            )
        except ValueError:
            continue

        if canonical == "cross_chapter_2":

            print(
                f"- {original}: "
                f"{quantidade}"
            )

    # ========================================================
    # INTERROMPER SE HOUVER ERROS
    # ========================================================

    if erros:

        print("\n" + "=" * 70)
        print("ERROS ENCONTRADOS")
        print("=" * 70)

        for erro in erros:
            print(f"- {erro}")

        raise RuntimeError(
            "A validação do SPAmazon-QA falhou."
        )

    # ========================================================
    # SALVAR JSONL DERIVADO
    # ========================================================

    DERIVED_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    registros_derivados.sort(
        key=lambda x: x["id_questao"]
    )

    with DERIVED_FILE.open(
        "w",
        encoding="utf-8",
        newline="\n"
    ) as f:

        for registro in registros_derivados:

            f.write(
                json.dumps(
                    registro,
                    ensure_ascii=False,
                    sort_keys=True
                )
            )

            f.write("\n")

    # ========================================================
    # SALVAR TABELA
    # ========================================================

    TABLE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with TABLE_FILE.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.writer(
            f,
            delimiter=";"
        )

        writer.writerow(
            [
                "id_canonico",
                "quantidade_perguntas",
            ]
        )

        for target, quantidade in sorted(
            targets_canonicos.items()
        ):

            writer.writerow(
                [
                    target,
                    quantidade,
                ]
            )

        writer.writerow(
            [
                "TOTAL",
                len(dados),
            ]
        )

    # ========================================================
    # AUDITORIA
    # ========================================================

    AUDIT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    auditoria = {
        "total_questions": len(dados),
        "unique_question_ids":
            len(ids_unicos),
        "raw_target_labels":
            len(targets_originais),
        "canonical_targets":
            len(targets_canonicos),
        "corpus_canonical_documents":
            len(corpus_ids),
        "type_distribution":
            dict(tipos),
        "difficulty_distribution":
            dict(dificuldades),
        "target_distribution":
            dict(
                sorted(
                    targets_canonicos.items()
                )
            ),
        "validation_errors": [],
    }

    with AUDIT_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            auditoria,
            f,
            ensure_ascii=False,
            indent=2
        )

    # ========================================================
    # SUCESSO
    # ========================================================

    print("\n" + "=" * 70)
    print("VALIDAÇÃO CONCLUÍDA")
    print("=" * 70)

    print(
        "\nOK: 130 perguntas válidas."
    )

    print(
        "OK: 130 IDs únicos."
    )

    print(
        "OK: 39 grafias de alvo "
        "convertidas em 38 documentos."
    )

    print(
        "OK: todos os capítulos-alvo "
        "existem no corpus P0."
    )

    print(
        "\nArquivo derivado:"
    )

    print(DERIVED_FILE)

    print(
        "\nTabela:"
    )

    print(TABLE_FILE)

    print(
        "\nAuditoria:"
    )

    print(AUDIT_FILE)


if __name__ == "__main__":
    main()
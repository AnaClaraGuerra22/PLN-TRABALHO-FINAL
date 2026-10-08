import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]

sys.path.insert(
    0,
    str(BASE_DIR)
)

from src.preprocess import preprocess


EXEMPLOS = [

    # Caso sentinela do TCC
    (
        "TEMPORALIDADE",
        "Name three major commodity or "
        "extractive activities that expanded "
        "in the Amazon since the 1970s."
    ),

    (
        "TEMPORALIDADE OPOSTA",
        "Name three major commodity or "
        "extractive activities in the Amazon "
        "before the 1970s."
    ),

    (
        "NEGAÇÃO",
        "Why does deforestation not produce "
        "the same effects in all regions?"
    ),

    (
        "COMPARAÇÃO",
        "Why is carbon loss greater than "
        "carbon uptake in some areas?"
    ),

    (
        "QUANTIDADE / SIGLAS",
        "How much CO2 was emitted between "
        "2010 and 2020?"
    ),

]


def main():

    for titulo, texto in EXEMPLOS:

        print("\n" + "=" * 80)
        print(titulo)
        print("=" * 80)

        for variant in [
            "P0",
            "P1",
            "P2",
            "P3",
            "P4",
        ]:

            resultado = preprocess(
                texto,
                variant,
            )

            print(
                f"\n{variant}:"
            )

            print(resultado)


if __name__ == "__main__":
    main()
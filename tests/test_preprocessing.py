import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

sys.path.insert(
    0,
    str(BASE_DIR)
)

from src.preprocess import preprocess


def test_p0_preserva_texto():

    text = "Amazon Since 1970."

    assert preprocess(
        text,
        "P0"
    ) == text


def test_p1_aplica_lowercase():

    text = "Amazon Since 1970."

    result = preprocess(
        text,
        "P1"
    )

    assert result == (
        "amazon since 1970."
    )



def test_temporalidade_preservada():

    text = (
        "Activities expanded "
        "since the 1970s and "
        "before the 1990s."
    )

    for variant in [
        "P2",
        "P3",
        "P4",
    ]:

        result = preprocess(
            text,
            variant
        )

        assert "since" in result
        assert "before" in result


def test_negacao_preservada():

    text = (
        "Deforestation does not "
        "produce the same effects "
        "in all regions."
    )

    for variant in [
        "P2",
        "P3",
        "P4",
    ]:

        result = preprocess(
            text,
            variant
        )

        assert "not" in result


def test_comparacao_preservada():

    text = (
        "Carbon loss is greater "
        "than carbon uptake."
    )

    for variant in [
        "P2",
        "P3",
        "P4",
    ]:

        result = preprocess(
            text,
            variant
        )

        assert "greater" in result
        assert "than" in result


def test_intervalo_numerico_preservado():

    text = (
        "CO2 emissions increased "
        "between 2010 and 2020."
    )

    for variant in [
        "P1",
        "P2",
        "P3",
        "P4",
    ]:

        result = preprocess(
            text,
            variant
        )

        assert "2010" in result
        assert "2020" in result
        assert "between" in result
        assert "and" in result


def test_p2_remove_stopwords():

    text = (
        "The forest is in the Amazon."
    )

    result = preprocess(
        text,
        "P2"
    )

    assert "the" not in result.split()


def test_p3_lematiza():

    text = (
        "activities expanded regions"
    )

    result = preprocess(
        text,
        "P3"
    )

    assert "activity" in result
    assert "expand" in result
    assert "region" in result


def test_p4_aplica_stemming():

    text = (
        "activities deforestation "
        "expanded"
    )

    result = preprocess(
        text,
        "P4"
    )

    assert "activ" in result
    assert "deforest" in result
    assert "expand" in result



def test_nenhuma_variante_produz_texto_vazio():

    text = (
        "Amazon biodiversity "
        "between 2010 and 2020."
    )

    for variant in [
        "P0",
        "P1",
        "P2",
        "P3",
        "P4",
    ]:

        result = preprocess(
            text,
            variant
        )

        assert result.strip()
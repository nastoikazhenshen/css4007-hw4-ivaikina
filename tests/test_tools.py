
from tools import lookup, calculate


def test_lookup_brightwater():
    result = lookup("Brightwater population 2025")
    ids = [item["id"] for item in result["matches"]]

    assert "NR-05" in ids
    assert "NR-16" in ids


def test_lookup_ossbridge():
    result = lookup("Ossbridge population")
    ids = [item["id"] for item in result["matches"]]

    assert "NR-01" in ids


def test_lookup_similar_names():
    result = lookup("Ossford population")
    ids = [item["id"] for item in result["matches"]]

    assert "NR-02" in ids


def test_lookup_archived():
    result = lookup("Tarnvale population")
    ids = [item["id"] for item in result["matches"]]

    assert "NR-03" in ids
    assert "NR-13" not in ids


def test_lookup_typo():
    result = lookup("Ossbrige")
    assert "error" in result
    assert "Ossbridge" in result["suggestions"]


def test_lookup_empty():
    result = lookup("")
    assert "error" in result


def test_calculate_multiplication():
    result = calculate("48317 * 1.0947")
    assert abs(result["result"] - 52892.6199) < 0.0001


def test_calculate_division():
    result = calculate("44675 / 921.4")
    assert abs(result["result"] - 48.48599956587801) < 0.0001


def test_calculate_zero():
    result = calculate("10 / 0")
    assert "error" in result


def test_calculate_import():
    result = calculate(
        "__import__('os').system('echo hi')"
    )
    assert "error" in result


def test_calculate_attribute():
    result = calculate("(1).__class__")
    assert "error" in result


def test_calculate_power():
    result = calculate("9**9**9")
    assert "error" in result


def test_calculate_invalid():
    result = calculate("hello")
    assert "error" in result

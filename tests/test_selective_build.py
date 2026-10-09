import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "selective_build.py"
SPEC = importlib.util.spec_from_file_location("selective_build", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_broadcom_only():
    result = MODULE.select_platforms(["platform/broadcom/sample.txt"])
    assert result["platforms"] == ["broadcom"]
    assert result["run_all"] is False


def test_mellanox_only():
    result = MODULE.select_platforms(["platform/mellanox/sample.txt"])
    assert result["platforms"] == ["mellanox"]
    assert result["run_all"] is False


def test_marvell_selects_both_architectures():
    result = MODULE.select_platforms(["platform/marvell-prestera/sample.txt"])
    assert result["platforms"] == ["marvell-prestera-arm64", "marvell-prestera-armhf"]


def test_vs_enables_tests():
    result = MODULE.select_platforms(["platform/vs/sample.txt"])
    assert result["platforms"] == ["vs"]
    assert result["run_vs_tests"] is True


def test_global_and_unknown_paths_run_all():
    for path in ("Makefile", "unknown/file.txt"):
        result = MODULE.select_platforms([path])
        assert result["run_all"] is True
        assert result["platforms"] == list(MODULE.ALL_PLATFORMS)


def test_all_mode_runs_everything():
    result = MODULE.select_platforms(["platform/mellanox/sample.txt"], mode="all")
    assert result["run_all"] is True
    assert result["platforms"] == list(MODULE.ALL_PLATFORMS)

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PYTHON_DIR = (
    PROJECT_ROOT
    / "automation"
    / "python"
)

# Make automation/python importable before importing
# our project modules.
sys.path.insert(
    0,
    str(PYTHON_DIR),
)


from ansible_runner import rollback_bgp_policy
from bgp_validator import validate_network
from change_loader import load_change
from path_validator import get_best_path

LEAF1 = "clab-bgp-automation-leaf1"
PREFIX = "10.10.2.1/32"


def run_change(
    change_file: str,
) -> subprocess.CompletedProcess:

    return subprocess.run(
        [
            sys.executable,
            str(
                PYTHON_DIR
                / "deployment_engine.py"
            ),
            "--change",
            change_file,
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture(autouse=True)
def restore_baseline():

    change = load_change(
        "changes/prefer_spine1.yml"
    )

    # Ensure every test starts from baseline.
    rollback_bgp_policy(change)

    yield

    # Ensure every test leaves the lab at baseline.
    rollback_bgp_policy(change)


def test_network_baseline():

    report = validate_network()

    assert (
        report["network_status"]
        == "PASS"
    )

    best_path = get_best_path(
        LEAF1,
        PREFIX,
    )

    assert best_path == "10.0.12.1"

def test_invalid_intent_triggers_rollback():

    result = run_change(
        "changes/test_invalid_intent.yml"
    )

    assert result.returncode != 0

    best_path = get_best_path(
        LEAF1,
        PREFIX,
    )

    assert best_path == "10.0.12.1"

    report = validate_network()

    assert (
        report["network_status"]
        == "PASS"
    )

def test_successful_change():

    result = run_change(
        "changes/prefer_spine1.yml"
    )

    assert result.returncode == 0, (
        result.stdout
        + result.stderr
    )

    best_path = get_best_path(
        LEAF1,
        PREFIX,
    )

    assert best_path == "10.0.11.1"
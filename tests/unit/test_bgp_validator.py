import sys
from pathlib import Path

PROJECT_ROOT = Path(
    __file__
).resolve().parents[2]

PYTHON_DIRECTORY = (
    PROJECT_ROOT
    / "automation"
    / "python"
)

sys.path.insert(
    0,
    str(PYTHON_DIRECTORY),
)


from bgp_validator import (
    validate_neighbors,
    validate_routes,
)


def test_established_neighbor_passes():

    summary = {
        "ipv4Unicast": {
            "peers": {
                "10.0.11.1": {
                    "state": "Established"
                }
            }
        }
    }

    results = validate_neighbors(
        ["10.0.11.1"],
        summary,
    )

    assert results[0]["status"] == "PASS"


def test_idle_neighbor_fails():

    summary = {
        "ipv4Unicast": {
            "peers": {
                "10.0.11.1": {
                    "state": "Idle"
                }
            }
        }
    }

    results = validate_neighbors(
        ["10.0.11.1"],
        summary,
    )

    assert results[0]["status"] == "FAIL"


def test_missing_neighbor_fails():

    summary = {
        "ipv4Unicast": {
            "peers": {}
        }
    }

    results = validate_neighbors(
        ["10.0.11.1"],
        summary,
    )

    assert results[0]["status"] == "FAIL"


def test_expected_route_passes():

    route_table = {
        "routes": {
            "10.10.2.1/32": [
                {
                    "valid": True
                }
            ]
        }
    }

    results = validate_routes(
        ["10.10.2.1/32"],
        route_table,
    )

    assert results[0]["status"] == "PASS"


def test_missing_route_fails():

    route_table = {
        "routes": {}
    }

    results = validate_routes(
        ["10.10.2.1/32"],
        route_table,
    )

    assert results[0]["status"] == "FAIL"
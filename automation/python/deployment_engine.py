import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from ansible_runner import (
    AnsibleExecutionError,
    deploy_bgp_policy,
    rollback_bgp_policy,
)
from bgp_validator import validate_network
from change_loader import load_change
from path_validator import get_best_path

REPORT_DIRECTORY = Path("reports")


def create_policy_commands(
    change: dict,
) -> list[str]:

    target = change["target"]
    policy = change["policy"]

    return [
        "configure terminal",

        f"route-map {policy['name']} permit 10",
        "set local-preference ",
        f"{policy['local_preference']}",

        f"router bgp {target['asn']}",
        "address-family ipv4 unicast",

        f"neighbor {policy['neighbor']} ",
        f"route-map {policy['name']} ",
        f"{policy['direction']}",

        "end",

        f"clear bgp {policy['neighbor']} soft ",
        f"{policy['direction']}",
    ]


def create_rollback_commands(
    change: dict,
) -> list[str]:

    target = change["target"]
    policy = change["policy"]
    rollback = change["rollback"]

    return [
        "configure terminal",

        f"router bgp {target['asn']}",
        "address-family ipv4 unicast",

        f"neighbor {policy['neighbor']} ",
        f"route-map {rollback['policy_name']} ",
        f"{policy['direction']}",

        "exit-address-family",

        f"no route-map {policy['name']} permit 10",

        "end",

        f"clear bgp {policy['neighbor']} soft ",
        f"{policy['direction']}",
    ]


def validate_intent(
    change: dict,
) -> tuple[bool, str | None]:

    target = change["target"]
    validation = change["validation"]

    actual_next_hop = get_best_path(
        target["container"],
        validation["prefix"],
    )

    expected_next_hop = (
        validation["expected_next_hop"]
    )

    passed = (
        actual_next_hop == expected_next_hop
    )

    return passed, actual_next_hop

def validate_rollback(
    change: dict,
) -> tuple[bool, dict]:

    target = change["target"]
    validation = change["validation"]
    rollback = change["rollback"]

    print(
        "Validating network after rollback..."
    )

    health = validate_network()

    actual_next_hop = get_best_path(
        target["container"],
        validation["prefix"],
    )

    expected_next_hop = (
        rollback["expected_next_hop"]
    )

    path_restored = (
        actual_next_hop == expected_next_hop
    )

    result = {
        "network_health":
            health["network_status"],

        "expected_next_hop":
            expected_next_hop,

        "actual_next_hop":
            actual_next_hop,

        "path_restored":
            path_restored,
    }

    passed = (
        health["network_status"] == "PASS"
        and path_restored
    )

    return passed, result

def save_report(
    change: dict,
    report: dict,
) -> Path:

    REPORT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = REPORT_DIRECTORY / (
        f"{change['id']}.json"
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            indent=2,
        )

    return path


def execute_change(
    change_file: str,
) -> bool:

    change = load_change(change_file)

    report = {
        "change_id": change["id"],
        "description": change["description"],
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "target": change["target"]["device"],
        "precheck": None,
        "deployment": None,
        "postcheck": None,
        "rollback": None,
        "result": None,
    }

    print("=" * 70)
    print(
        f"CHANGE {change['id']}: "
        f"{change['description']}"
    )
    print("=" * 70)

    # --------------------------------------------------
    # PRE-CHECK
    # --------------------------------------------------

    print("\n[1/4] Running pre-change validation")

    precheck = validate_network()

    report["precheck"] = (
        precheck["network_status"]
    )

    if precheck["network_status"] != "PASS":

        report["result"] = "BLOCKED"

        save_report(
            change,
            report,
        )

        print(
            "Pre-change validation FAILED."
        )
        print(
            "Deployment blocked."
        )

        return False

    print(
        "Pre-change validation PASSED."
    )

    # --------------------------------------------------
    # DEPLOY
    # --------------------------------------------------

    print("\n[2/4] Deploying policy")

    try:

        deploy_bgp_policy(change)

        report["deployment"] = "SUCCESS"

        report["deployment_engine"] = "ansible"

    except AnsibleExecutionError as exc:

        report["deployment"] = "FAILED"
        report["deployment_error"] = str(exc)

        print(
            f"Deployment failed: {exc}"
        )

        report["result"] = "FAILED"

        save_report(
            change,
            report,
        )

        return False

    print("Configuration deployed.")

    # Allow control plane to settle.
    time.sleep(2)

    # --------------------------------------------------
    # POST-CHECK
    # --------------------------------------------------

    print(
        "\n[3/4] Running post-change validation"
    )

    health = validate_network()

    intent_passed, actual_next_hop = (
        validate_intent(change)
    )

    report["postcheck"] = {
        "network_health":
            health["network_status"],
        "intent_passed":
            intent_passed,
        "expected_next_hop":
            change["validation"][
                "expected_next_hop"
            ],
        "actual_next_hop":
            actual_next_hop,
    }

    if (
        health["network_status"] == "PASS"
        and intent_passed
    ):

        report["result"] = "SUCCESS"

        report_path = save_report(
            change,
            report,
        )

        print(
            "Network health PASSED."
        )

        print(
            "Intent validation PASSED."
        )

        print(
            f"Best next-hop: {actual_next_hop}"
        )

        print("\nCHANGE SUCCESSFUL")
        print(
            f"Report: {report_path}"
        )

        return True

        # --------------------------------------------------
    # ROLLBACK
    # --------------------------------------------------

    print(
        "\nPost-validation FAILED."
    )

    print(
        "\n[4/4] Starting rollback"
    )

    try:

        rollback_bgp_policy(change)

        print(
            "Rollback configuration applied."
        )

        # Allow BGP to reconverge.
        time.sleep(3)

        rollback_passed, rollback_result = (
            validate_rollback(change)
        )

        report["rollback"] = {
            "execution": "SUCCESS",
            **rollback_result,
        }

        if rollback_passed:

            report["result"] = (
                "ROLLED_BACK"
            )

            print(
                "Rollback validation PASSED."
            )

        else:

            report["result"] = (
                "ROLLBACK_VALIDATION_FAILED"
            )

            print(
                "Rollback validation FAILED."
            )

    except AnsibleExecutionError as exc:

        report["rollback"] = {
            "execution": "FAILED",
            "error": str(exc),
        }

        report["result"] = (
            "ROLLBACK_FAILED"
        )

    report_path = save_report(
        change,
        report,
    )

    print(
        f"\nFinal result: "
        f"{report['result']}"
    )

    print(
        f"Report: {report_path}"
    )

    return False

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Production-style network "
            "change automation engine"
        )
    )

    parser.add_argument(
        "--change",
        required=True,
        help="YAML change request",
    )

    args = parser.parse_args()

    success = execute_change(
        args.change
    )

    raise SystemExit(
        0 if success else 1
    )


if __name__ == "__main__":
    main()
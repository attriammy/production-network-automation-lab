import subprocess

from bgp_validator import validate_network
from path_validator import get_best_path


LEAF1_CONTAINER = "clab-bgp-automation-leaf1"
TARGET_PREFIX = "10.10.2.1/32"
EXPECTED_NEXT_HOP = "10.0.11.1"


def run_vtysh_commands(
    container: str,
    commands: list[str],
) -> None:

    docker_command = [
        "sudo",
        "docker",
        "exec",
        container,
        "vtysh",
    ]

    for command in commands:
        docker_command.extend(
            ["-c", command]
        )

    subprocess.run(
        docker_command,
        check=True,
        text=True,
    )


def deploy_policy() -> None:

    commands = [
        "configure terminal",

        "route-map PREFER-SPINE1 permit 10",
        "set local-preference 200",

        "router bgp 65101",
        "address-family ipv4 unicast",
        "neighbor 10.0.11.1 route-map PREFER-SPINE1 in",

        "end",
        "clear bgp 10.0.11.1 soft in",
    ]

    run_vtysh_commands(
        LEAF1_CONTAINER,
        commands,
    )


def rollback_policy() -> None:

    print("Starting rollback...")

    commands = [
        "configure terminal",

        "router bgp 65101",
        "address-family ipv4 unicast",
        "neighbor 10.0.11.1 route-map ALLOW-ALL in",

        "exit-address-family",

        "no route-map PREFER-SPINE1 permit 10",

        "end",
        "clear bgp 10.0.11.1 soft in",
    ]

    run_vtysh_commands(
        LEAF1_CONTAINER,
        commands,
    )

    print("Rollback completed.")


def post_validate() -> bool:

    print("Running post-change network validation...")

    report = validate_network()

    if report["network_status"] != "PASS":
        print(
            "Post-check failed: "
            "network health is degraded."
        )
        return False

    best_path = get_best_path(
        LEAF1_CONTAINER,
        TARGET_PREFIX,
    )

    print(
        f"Best next-hop for "
        f"{TARGET_PREFIX}: {best_path}"
    )

    if best_path != EXPECTED_NEXT_HOP:
        print(
            f"Post-check failed: expected "
            f"{EXPECTED_NEXT_HOP}, got {best_path}"
        )
        return False

    print("Post-change validation passed.")

    return True


def deploy_local_preference():

    print("=" * 60)
    print("BGP POLICY DEPLOYMENT")
    print("=" * 60)

    print("\nRunning pre-change validation...")

    report = validate_network()

    if report["network_status"] != "PASS":
        raise RuntimeError(
            "Pre-check failed. Deployment blocked."
        )

    print("Pre-check passed.")

    print(
        "\nDeploying local-preference policy..."
    )

    try:
        deploy_policy()

    except subprocess.CalledProcessError as exc:
        print(
            f"Deployment command failed: {exc}"
        )

        rollback_policy()

        raise

    print("Configuration deployed.")

    if not post_validate():

        print(
            "\nPost-validation failed. "
            "Initiating rollback."
        )

        rollback_policy()

        raise RuntimeError(
            "Deployment failed and was rolled back."
        )

    print("\n" + "=" * 60)
    print("DEPLOYMENT SUCCESSFUL")
    print("=" * 60)


if __name__ == "__main__":
    deploy_local_preference()
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ANSIBLE_ROOT = (
    PROJECT_ROOT
    / "automation"
    / "ansible"
)

INVENTORY = (
    ANSIBLE_ROOT
    / "inventory"
    / "hosts.yml"
)


class AnsibleExecutionError(Exception):
    """Raised when an Ansible deployment fails."""

def rollback_bgp_policy(
    change: dict,
) -> str:

    target = change["target"]
    policy = change["policy"]
    rollback = change["rollback"]

    return run_playbook(
        "rollback_bgp_policy.yml",
        {
            "target_device":
                target["device"],

            "policy_name":
                policy["name"],

            "rollback_policy_name":
                rollback["policy_name"],

            "policy_neighbor":
                policy["neighbor"],

            "policy_direction":
                policy["direction"],
        },
    )

def deploy_bgp_policy(
    change: dict,
) -> str:

    target = change["target"]
    policy = change["policy"]

    return run_playbook(
        "deploy_bgp_policy.yml",
        {
            "target_device":
                target["device"],

            "policy_name":
                policy["name"],

            "policy_neighbor":
                policy["neighbor"],

            "local_preference":
                policy["local_preference"],

            "policy_direction":
                policy["direction"],
        },
    )

def run_playbook(
    playbook: str,
    extra_vars: dict,
) -> str:

    playbook_path = (
        ANSIBLE_ROOT
        / "playbooks"
        / playbook
    )

    command = [
        "ansible-playbook",
        "-i",
        str(INVENTORY),
        str(playbook_path),
    ]

    for key, value in extra_vars.items():

        command.extend(
            [
                "-e",
                f"{key}={value}",
            ]
        )

    try:

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
            cwd=str(ANSIBLE_ROOT),
        )

        return result.stdout

    except subprocess.TimeoutExpired as exc:

        raise AnsibleExecutionError(
            f"Ansible playbook timed out: "
            f"{playbook}"
        ) from exc

    except subprocess.CalledProcessError as exc:

        raise AnsibleExecutionError(
            f"Ansible playbook failed:\n"
            f"{exc.stdout}\n"
            f"{exc.stderr}"
        ) from exc
import subprocess


class DeviceCommandError(Exception):
    """Raised when execution against a device fails."""


def run_frr_command(
    container: str,
    command: str,
    timeout: int = 10,
) -> str:
    """Execute a single FRR show/operational command."""

    docker_command = [
        "sudo",
        "docker",
        "exec",
        container,
        "vtysh",
        "-c",
        command,
    ]

    try:
        result = subprocess.run(
            docker_command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
        )

        return result.stdout

    except subprocess.TimeoutExpired as exc:
        raise DeviceCommandError(
            f"{container}: command timed out: {command}"
        ) from exc

    except subprocess.CalledProcessError as exc:
        raise DeviceCommandError(
            f"{container}: command failed: "
            f"{exc.stderr}"
        ) from exc


def run_frr_commands(
    container: str,
    commands: list[str],
    timeout: int = 20,
) -> str:
    """Execute multiple vtysh commands in one session."""

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

    try:
        result = subprocess.run(
            docker_command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
        )

        return result.stdout

    except subprocess.TimeoutExpired as exc:
        raise DeviceCommandError(
            f"{container}: configuration timed out"
        ) from exc

    except subprocess.CalledProcessError as exc:
        raise DeviceCommandError(
            f"{container}: configuration failed: "
            f"{exc.stderr}"
        ) from exc
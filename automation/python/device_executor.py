import subprocess

class DeviceCommandError(Exception):
    """Exception raised for errors in the device command execution."""

def run_frr_command(container: str, command: str) -> str:
    """
    Run a command inside a FRR container.

    Args:
        container (str): The name of the FRR container.
        command (str): The command to run inside the container.

    Returns:
        str: The output of the command.

    Raises:
        DeviceCommandError: If the command execution fails.
    """
    docker_command = ["sudo","docker", "exec", container, "vtysh", "-c", command]
    try:
        result = subprocess.run(
            docker_command,
            capture_output=True,
            text=True,
            check=True,
            timeout=10  # Set a timeout of 10 seconds
        )
        return result.stdout
    
    except subprocess.TimeoutExpired as exc:
        raise DeviceCommandError(f"Command '{command}' in container '{container}' timed out after 10 seconds") from exc
    except subprocess.CalledProcessError as exc:
        raise DeviceCommandError(f"Error executing command '{command}' in container '{container}': {exc.stderr.strip()}") from exc


if __name__ == "__main__":
    output = run_frr_command("clab-bgp-automation-leaf1", "show ip bgp summary")
    print(output)
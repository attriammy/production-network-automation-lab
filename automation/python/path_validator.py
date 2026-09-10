import json

from device_executor import run_frr_command


def get_best_path(container: str, prefix: str) -> str | None:
    """
    Return the best BGP next-hop for a prefix.
    """

    output = run_frr_command(
        container,
        f"show ip bgp {prefix} json",
    )

    data = json.loads(output)

    paths = data.get("paths", [])

    for path in paths:
        if path.get("bestpath"):
            nexthops = path.get("nexthops", [])

            if nexthops:
                return nexthops[0].get("ip")

    return None


if __name__ == "__main__":

    best_path = get_best_path(
        "clab-bgp-automation-leaf1",
        "10.10.2.1/32",
    )

    print(f"Best next-hop: {best_path}")
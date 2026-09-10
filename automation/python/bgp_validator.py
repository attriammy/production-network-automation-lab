import json

from inventory_loader import load_inventory
from device_executor import (
    DeviceCommandError,
    run_frr_command,
)

INVENTORY_FILE = "inventory/devices.yml"


def get_bgp_summary(container: str) -> dict:
    """Return BGP summary as structured JSON."""

    output = run_frr_command(
        container,
        "show ip bgp summary json",
    )

    return json.loads(output)


def get_bgp_routes(container: str) -> dict:
    """Return BGP routing table as structured JSON."""

    output = run_frr_command(
        container,
        "show ip bgp json",
    )

    return json.loads(output)


def find_peer_data(summary: dict) -> dict:
    """
    Extract peer dictionary from FRR BGP summary JSON.
    """

    ipv4 = summary.get("ipv4Unicast", {})
    return ipv4.get("peers", {})


def validate_neighbors(
    expected_neighbors: list[str],
    summary: dict,
) -> list[dict]:

    peers = find_peer_data(summary)

    results = []

    for neighbor in expected_neighbors:

        peer = peers.get(neighbor)

        if peer is None:
            results.append(
                {
                    "neighbor": neighbor,
                    "status": "FAIL",
                    "reason": "Neighbor missing from BGP summary",
                }
            )
            continue

        state = peer.get("state")

        if state == "Established":
            results.append(
                {
                    "neighbor": neighbor,
                    "status": "PASS",
                    "reason": "Established",
                }
            )
        else:
            results.append(
                {
                    "neighbor": neighbor,
                    "status": "FAIL",
                    "reason": f"BGP state is {state}",
                }
            )

    return results


def validate_routes(
    expected_routes: list[str],
    route_table: dict,
) -> list[dict]:

    routes = route_table.get("routes", {})

    results = []

    for prefix in expected_routes:

        if prefix in routes:
            results.append(
                {
                    "prefix": prefix,
                    "status": "PASS",
                    "reason": "Route present",
                }
            )
        else:
            results.append(
                {
                    "prefix": prefix,
                    "status": "FAIL",
                    "reason": "Expected route missing",
                }
            )

    return results


def validate_device(
    name: str,
    device: dict,
) -> dict:

    container = device["container"]

    try:
        summary = get_bgp_summary(container)
        routes = get_bgp_routes(container)

    except (
        DeviceCommandError,
        json.JSONDecodeError,
    ) as exc:

        return {
            "device": name,
            "status": "FAIL",
            "error": str(exc),
            "neighbors": [],
            "routes": [],
        }

    neighbor_results = validate_neighbors(
        device.get("expected_neighbors", []),
        summary,
    )

    route_results = validate_routes(
        device.get("expected_routes", []),
        routes,
    )

    all_results = neighbor_results + route_results

    device_status = (
        "PASS"
        if all(
            result["status"] == "PASS"
            for result in all_results
        )
        else "FAIL"
    )

    return {
        "device": name,
        "status": device_status,
        "neighbors": neighbor_results,
        "routes": route_results,
    }


def validate_network() -> dict:

    inventory = load_inventory(INVENTORY_FILE)

    device_results = []

    for name, device in inventory.items():

        print(f"Validating {name}...")

        result = validate_device(
            name,
            device,
        )

        device_results.append(result)

    network_status = (
        "PASS"
        if all(
            device["status"] == "PASS"
            for device in device_results
        )
        else "FAIL"
    )

    return {
        "network_status": network_status,
        "devices": device_results,
    }


def print_report(report: dict):

    print("\n")
    print("=" * 70)
    print("NETWORK PRE-CHECK")
    print("=" * 70)

    for device in report["devices"]:

        print(
            f"\n{device['device'].upper()} "
            f"[{device['status']}]"
        )

        if "error" in device:
            print(
                f"  ERROR: {device['error']}"
            )
            continue

        for neighbor in device["neighbors"]:

            print(
                f"  BGP {neighbor['neighbor']:<15} "
                f"{neighbor['status']:<5} "
                f"{neighbor['reason']}"
            )

        for route in device["routes"]:

            print(
                f"  ROUTE {route['prefix']:<15} "
                f"{route['status']:<5} "
                f"{route['reason']}"
            )

    print("\n" + "=" * 70)

    print(
        f"NETWORK HEALTH: "
        f"{report['network_status']}"
    )

    if report["network_status"] == "PASS":
        print("DEPLOYMENT ALLOWED: YES")
    else:
        print("DEPLOYMENT ALLOWED: NO")

    print("=" * 70)


if __name__ == "__main__":

    report = validate_network()

    print_report(report)
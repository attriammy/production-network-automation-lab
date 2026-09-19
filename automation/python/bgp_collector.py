from device_executor import DeviceCommandError, run_frr_command
from inventory_loader import load_inventory

INVENTORY_FILE = "inventory/devices.yml"

def collect_bgp_summary():
    """ collect BGP summary from all devices in the inventory """

    inventory = load_inventory(INVENTORY_FILE)
    results = {}

    for name, device in inventory.items():
        print(f"Collecting BGP summary from {name}")
        try:
            output = run_frr_command(device["container"], "show ip bgp summary")
            results[name] = {
                "success": True,
                "output": output
            }

            print(f"[SUCESS] {name}")

        except DeviceCommandError as exc:
            results[name] = {
                "success": False,
                "error": str(exc)
            }
            print(f"[FAILED] {name}: {exc}")
    return results

if __name__ == "__main__":
    results = collect_bgp_summary()
    print("\n" + "=" * 60)
    print("BGP Collection Report")
    print("=" * 60)

    for device,result in results.items():
        print(f"\nDevice: {device}")
        if result["success"]:
            print(result["output"])
        else:
            print({result["error"]})
    
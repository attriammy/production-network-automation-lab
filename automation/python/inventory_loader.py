from pathlib import Path

import yaml


def load_inventory(file_path:str) -> dict:
    """
    Load inventory from a YAML file.

    Args:
        file_path (str): Path to the YAML file.

    Returns:
        dict: The loaded inventory.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if not data:
        raise ValueError("Inventory must contain a 'devices' section")
    return data["devices"]

if __name__ == "__main__":
    inventory = load_inventory("inventory/devices.yml")

    for name, device in inventory.items():
        print(f" {name}"
        f" AS {device['asn']}"
        f" role = {device['role']}")
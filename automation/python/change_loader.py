from pathlib import Path

import yaml


class ChangeValidationError(Exception):
    """Raised when a change request is invalid."""


REQUIRED_TARGET_FIELDS = {
    "device",
    "container",
    "asn",
}

REQUIRED_POLICY_FIELDS = {
    "name",
    "neighbor",
    "local_preference",
    "direction",
}

REQUIRED_VALIDATION_FIELDS = {
    "prefix",
    "expected_next_hop",
}

REQUIRED_ROLLBACK_FIELDS = {
    "policy_name",
    "expected_next_hop",
}

def _validate_required_fields(
    section_name: str,
    section: dict,
    required_fields: set[str],
) -> None:

    missing = required_fields - section.keys()

    if missing:
        raise ChangeValidationError(
            f"{section_name} missing fields: "
            f"{', '.join(sorted(missing))}"
        )


def load_change(file_path: str) -> dict:
    """Load and validate a network change request."""

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Change request not found: {file_path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = yaml.safe_load(file)

    if not data or "change" not in data:
        raise ChangeValidationError(
            "Change request must contain a 'change' section"
        )

    change = data["change"]

    for section in [
        "target",
        "policy",
        "validation",
        "rollback",
    ]:
        if section not in change:
            raise ChangeValidationError(
                f"Missing section: {section}"
            )

    _validate_required_fields(
        "target",
        change["target"],
        REQUIRED_TARGET_FIELDS,
    )

    _validate_required_fields(
        "policy",
        change["policy"],
        REQUIRED_POLICY_FIELDS,
    )

    _validate_required_fields(
        "validation",
        change["validation"],
        REQUIRED_VALIDATION_FIELDS,
    )

    _validate_required_fields(
        "rollback",
        change["rollback"],
        REQUIRED_ROLLBACK_FIELDS,
    )

    local_pref = change["policy"]["local_preference"]

    if not isinstance(local_pref, int):
        raise ChangeValidationError(
            "local_preference must be an integer"
        )

    if not 0 <= local_pref <= 4294967295:
        raise ChangeValidationError(
            "local_preference is outside valid range"
        )

    if change["policy"]["direction"] not in {
        "in",
        "out",
    }:
        raise ChangeValidationError(
            "direction must be 'in' or 'out'"
        )

    return change


if __name__ == "__main__":

    change = load_change(
        "changes/prefer_spine1.yml"
    )

    print(
        f"Loaded change "
        f"{change['id']}: "
        f"{change['description']}"
    )
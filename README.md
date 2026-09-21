# Production Network Automation Lab

A production-style network automation project demonstrating intent-driven BGP policy deployment, pre-change validation, automated configuration delivery, post-change operational verification, rollback, testing, and CI/CD using Python, Ansible, FRRouting, Containerlab, Docker, and GitHub Actions.

## 1. Problem Statement

Network configuration automation should not consider a change successful simply because configuration commands were accepted by a device.

A production network change must answer three separate questions:

1. Was the configuration successfully delivered?
2. Did the network remain healthy after the change?
3. Did the network reach the intended operational state?

This project implements an automated BGP policy deployment workflow that validates all three.

If the requested routing intent is not achieved, the automation automatically rolls back the configuration and verifies that the expected operational state has been restored.

---

## 2. Architecture

```text
                     ┌─────────────────────┐
                     │   Change Request    │
                     │       YAML          │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │ Python Deployment   │
                     │       Engine        │
                     └──────────┬──────────┘
                                │
                     Pre-change validation
                                │
                                ▼
                     ┌─────────────────────┐
                     │   BGP Validator     │
                     │ Neighbors + Routes  │
                     └──────────┬──────────┘
                                │
                          Healthy?
                          /      \
                        No        Yes
                        │          │
                     ABORT         ▼
                              ┌──────────────┐
                              │   Ansible    │
                              │   Delivery   │
                              └──────┬───────┘
                                     │
                                     ▼
                              ┌──────────────┐
                              │ FRR Network  │
                              │ Containerlab │
                              └──────┬───────┘
                                     │
                              Post-validation
                                     │
                                     ▼
                              ┌──────────────┐
                              │ Intent Check │
                              │ Best BGP Path│
                              └──────┬───────┘
                                     │
                               Intent met?
                               /        \
                             Yes         No
                              │           │
                           SUCCESS        ▼
                                     ┌──────────┐
                                     │ Rollback │
                                     └────┬─────┘
                                          │
                                   Validate rollback
                                          │
                                          ▼
                                     JSON Report
```

The main design principle is:

**Configuration success does not equal operational success.**

Ansible is responsible for deterministic configuration delivery.

Python is responsible for orchestration, network-state validation, intent verification, failure handling, and rollback decisions.

---

## 3. Lab Topology

The project uses a four-router FRRouting fabric running inside Docker containers and deployed using Containerlab.

```text
                         spine1
                        AS65001
                       /       \
              10.0.11.0/30   10.0.21.0/30
                    /             \
                   /               \
              leaf1               leaf2
             AS65101             AS65102
          Lo:10.10.1.1         Lo:10.10.2.1
                   \               /
                    \             /
              10.0.12.0/30   10.0.22.0/30
                       \       /
                        spine2
                       AS65002
```

Each leaf has redundant eBGP connectivity through both spines.

The test change modifies the BGP best path on `leaf1` for:

```text
10.10.2.1/32
```

---

## 4. BGP Policy Scenario

The baseline state is intentionally deterministic.

On `leaf1`:

```text
Path through spine1:
Next-hop       10.0.11.1
Local Pref     100

Path through spine2:
Next-hop       10.0.12.1
Local Pref     150
```

Therefore the normal best path is:

```text
leaf1 → spine2 → leaf2
```

The automated change applies a BGP policy to the spine1 neighbor:

```text
PREFER-SPINE1
local-preference 200
```

The expected state becomes:

```text
Path through spine1:
Local Pref     200

Path through spine2:
Local Pref     150
```

The new best path should therefore be:

```text
leaf1 → spine1 → leaf2
```

The automation does not assume that applying the route-map means the change succeeded.

It queries the BGP operational state and verifies that the actual next-hop changed to:

```text
10.0.11.1
```

---

## 5. Repository Structure

```text
production-network-automation-lab/
│
├── inventory/
│   └── devices.yml
│
├── changes/
│   ├── prefer_spine1.yml
│   └── test_invalid_intent.yml
│
├── topology/
│   ├── topology.clab.yaml
│   └── configs/
│       ├── leaf1/
│       ├── leaf2/
│       ├── spine1/
│       └── spine2/
│
├── automation/
│   ├── python/
│   │   ├── inventory_loader.py
│   │   ├── device_executor.py
│   │   ├── bgp_collector.py
│   │   ├── bgp_validator.py
│   │   ├── path_validator.py
│   │   ├── change_loader.py
│   │   ├── ansible_runner.py
│   │   └── deployment_engine.py
│   │
│   └── ansible/
│       ├── ansible.cfg
│       ├── inventory/
│       ├── playbooks/
│       └── roles/
│
├── tests/
│   ├── unit/
│   └── integration/
│
├── reports/
│
├── .github/
│   └── workflows/
│       └── network-automation-ci.yml
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 6. Change Request Model

Network changes are represented as declarative YAML rather than hard-coded inside Python.

Example:

```yaml
change:
  id: CHG-001

  description: Prefer spine1 for leaf2 loopback traffic

  target:
    device: leaf1
    container: clab-bgp-automation-leaf1
    asn: 65101

  policy:
    name: PREFER-SPINE1
    neighbor: 10.0.11.1
    local_preference: 200
    direction: in

  validation:
    prefix: 10.10.2.1/32
    expected_next_hop: 10.0.11.1

  rollback:
    policy_name: ALLOW-ALL
    expected_next_hop: 10.0.12.1
```

The change request describes:

* target device
* requested policy
* expected operational outcome
* rollback policy
* expected state after rollback

The deployment engine therefore operates on intent rather than embedding a specific network change in application logic.

---

## 7. Pre-Change Validation

Before configuration is changed, Python collects operational BGP state using FRR JSON output.

Validation includes:

* expected BGP neighbors exist
* required neighbors are Established
* expected routes are present
* device command execution succeeds
* JSON responses can be parsed
* overall network health passes

If any required invariant fails, deployment is blocked.

```text
Network unhealthy
       ↓
Pre-check FAIL
       ↓
Deployment blocked
```

This implements a fail-closed approach.

---

## 8. Configuration Delivery with Ansible

Python does not directly own configuration delivery.

The deployment engine invokes Ansible, which uses reusable roles to apply or remove BGP policy.

Responsibilities are intentionally separated:

```text
Python
 ├── orchestration
 ├── validation
 ├── decision making
 ├── intent verification
 └── rollback decision

Ansible
 ├── configuration delivery
 ├─
```

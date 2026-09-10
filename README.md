# Production Network Automation Lab

A hands-on network automation project designed to simulate
production-grade network configuration deployment.

## Goals

- Automate network configuration using Python and Ansible
- Build a real BGP topology using Containerlab and FRRouting
- Implement pre-change and post-change validation
- Implement canary deployment
- Implement automatic rollback
- Build CI/CD pipelines using GitHub Actions
- Simulate production network failures
- Practice network automation troubleshooting

## Planned Architecture

GitHub
  |
CI/CD Pipeline
  |
Python / Ansible
  |
Containerlab
  |
FRRouting Routers
  |
BGP Network

## Project Scenario

The project will automate BGP routing policy changes across
a simulated multi-device network.

The deployment workflow will include:

1. Pre-validation
2. Configuration generation
3. Canary deployment
4. Post-validation
5. Batch deployment
6. Automatic rollback on failure
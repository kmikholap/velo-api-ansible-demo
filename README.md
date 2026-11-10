# VeloCloud SD-WAN Ansible Automation Framework

Ansible collection for automating Arista VeloCloud SD-WAN Orchestrator (VCO) operations. Provides modules for edge provisioning with static WAN IP configuration and edge status reporting.

## Directory Structure

```
wellington-demo/
├── ansible.cfg                            # Ansible configuration
├── requirements.txt                       # Python dependencies
├── setup_env.sh                           # Virtual environment bootstrap
├── collections/ansible_collections/arista/velocloud/
│   ├── galaxy.yml
│   ├── plugins/
│   │   ├── module_utils/
│   │   │   └── vco_client.py              # VCO REST API client
│   │   └── modules/
│   │       ├── vco_facts.py               # Gather profiles/edges facts
│   │       ├── vco_edge_provision.py      # Provision edges + WAN config
│   │       ├── vco_edge_wan_config.py     # Standalone WAN interface config
│   │       └── vco_edge_status.py         # Edge status reporting
│   └── roles/provision_edges/             # Role for batch provisioning
├── inventory/
│   ├── hosts.yml                          # VCO as local-connection host
│   └── group_vars/velocloud/
│       ├── auth.yml.example               # Credentials template (copy to auth.yml)
│       └── edges.yml                      # Edge definitions
└── playbooks/
    ├── provision_edges.yml                # Provision and configure edges
    └── edge_status.yml                    # Query edge status
```

## Prerequisites

- Python 3.9+
- Access to a VeloCloud Orchestrator with an API token
- Network connectivity to the VCO from the machine running the playbooks

## Quick Start

### 1. Set Up the Environment

```bash
chmod +x setup_env.sh
./setup_env.sh
```

This creates a Python virtual environment and installs dependencies (`requests`, `ansible-core`, `pytest`).

### 2. Activate the Environment

```bash
source .venv/bin/activate
export ANSIBLE_COLLECTIONS_PATH="$(pwd)/collections"
```

### 3. Configure VCO Credentials

Copy the example auth file and fill in your VCO details:

```bash
cp inventory/group_vars/velocloud/auth.yml.example inventory/group_vars/velocloud/auth.yml
```

Edit `auth.yml` with your orchestrator URL, API token, and enterprise ID.

> **Note:** `auth.yml` is listed in `.gitignore` to prevent credentials from being committed.

### 4. Configure Edges (Provisioning Only)

Edit `inventory/group_vars/velocloud/edges.yml` to define the edges you want to provision. Each edge entry supports:

| Field                  | Required | Default              | Description                        |
|------------------------|----------|----------------------|------------------------------------|
| `name`                 | Yes      | —                    | Edge name in VCO                   |
| `model_number`         | No       | `edge6X0`            | Edge hardware model                |
| `profile_name`         | No       | `Quick Start Profile`| VCO configuration profile          |
| `description`          | No       | —                    | Edge description                   |
| `site`                 | No       | —                    | Site details (contact, address)    |
| `wan_interface`        | No       | `GE3`                | WAN interface to configure         |
| `wan_ip`               | No       | —                    | Static WAN IP address              |
| `wan_netmask`          | No       | —                    | WAN subnet mask                    |
| `wan_gateway`          | No       | —                    | WAN default gateway                |
| `send_activation_email`| No       | `true`               | Send activation email to site contact |
| `license_alias`        | No       | —                    | License tier (e.g., `POC`)         |
| `ha_enabled`           | No       | `false`              | Enable high availability           |

### 5. Run Playbooks

**Check edge status:**

```bash
ansible-playbook playbooks/edge_status.yml
```

**Provision edges:**

```bash
ansible-playbook playbooks/provision_edges.yml
```

## Ansible Modules Reference

### `arista.velocloud.vco_facts`

Gathers VeloCloud facts (profiles and/or edges) and populates `ansible_facts.velocloud`.

### `arista.velocloud.vco_edge_provision`

Provisions a new edge in the VCO. Optionally configures a static WAN IP on the specified interface and sends an activation email with the static IP included in the activation URL.

### `arista.velocloud.vco_edge_status`

Queries all edges in the enterprise and returns a status report including connection state, edge model, software version, and assigned profile.

### `arista.velocloud.vco_edge_wan_config`

Configures static WAN IP addressing on an existing edge's interface.

## API Call Flow — Edge Provisioning

1. `enterprise/getEnterpriseConfigurations` — resolve profile name to configuration ID
2. `edge/edgeProvision` — create edge, receive edge ID and activation key
3. `edge/getEdgeConfigurationStack` — retrieve edge-specific config module
4. Modify `deviceSettings.data.routedInterfaces` — set interface override + static addressing
5. `configuration/updateConfigurationModule` — push updated config (full object replacement)
6. VCO sends activation email to the site contact with the static IP in the activation URL

## Extending the Framework

To add new workflows:

1. Create a new module in `collections/ansible_collections/arista/velocloud/plugins/modules/`
2. Use `VcoClient` from `module_utils/vco_client.py` for API calls
3. Add a playbook in `playbooks/` referencing the new module

The `VcoClient` class wraps all VCO REST API calls (POST to `/portal/rest/<endpoint>` with token auth) and handles retries on rate limiting (HTTP 429).

#!/usr/bin/python

DOCUMENTATION = r"""
---
module: vco_edge_status
short_description: Report VeloCloud Edge status
description:
  - Retrieves all edges for the enterprise and reports their status,
    model, software version, and assigned profile.
options:
  orchestrator_url:
    description: VeloCloud Orchestrator URL
    required: true
    type: str
  api_token:
    description: API token for authentication
    required: true
    type: str
    no_log: true
  enterprise_id:
    description: Enterprise ID
    required: true
    type: int
  verify_ssl:
    description: Verify SSL certificates
    required: false
    type: bool
    default: true
"""

EXAMPLES = r"""
- name: Get all edge statuses
  arista.velocloud.vco_edge_status:
    orchestrator_url: "https://vco.example.com"
    api_token: "{{ vco_api_token }}"
    enterprise_id: 1982
  register: edge_status

- name: Show status table
  debug:
    msg: "{{ edge_status.msg }}"
"""

RETURN = r"""
edges:
  description: List of edge status records
  returned: success
  type: list
  elements: dict
  contains:
    id:
      type: int
    name:
      type: str
    edge_state:
      description: "CONNECTED, OFFLINE, DEGRADED, NEVER_ACTIVATED, DISABLED, EXPIRED"
      type: str
    activation_state:
      type: str
    model_number:
      type: str
    software_version:
      type: str
    build_number:
      type: str
    serial_number:
      type: str
    last_contact:
      type: str
    service_state:
      type: str
    profile:
      description: Assigned configuration profile name
      type: str
msg:
  description: Formatted status table
  returned: success
  type: str
edge_count:
  description: Total number of edges
  returned: success
  type: int
"""

from ansible.module_utils.basic import AnsibleModule

try:
    from ansible_collections.arista.velocloud.plugins.module_utils.vco_client import (
        VcoClient, VcoApiError,
    )
except ImportError:
    pass


def format_status_table(edges):
    if not edges:
        return "No edges found."

    headers = ["Name", "State", "Model", "SW Version", "Profile",
               "License", "Bandwidth", "Last Contact"]
    rows = []
    for e in edges:
        lic = e.get("license", {})
        rows.append([
            e["name"],
            e["edge_state"],
            e["model_number"],
            e["software_version"],
            e["profile"],
            lic.get("edition", "N/A"),
            lic.get("bandwidth_tier", "N/A"),
            e["last_contact"],
        ])

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val)))

    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
    lines = [fmt.format(*headers), fmt.format(*["-" * w for w in col_widths])]
    for row in rows:
        lines.append(fmt.format(*[str(v) for v in row]))

    return "\n".join(lines)


def run_module():
    module = AnsibleModule(
        argument_spec=dict(
            orchestrator_url=dict(type="str", required=True),
            api_token=dict(type="str", required=True, no_log=True),
            enterprise_id=dict(type="int", required=True),
            verify_ssl=dict(type="bool", default=True),
        ),
        supports_check_mode=True,
    )

    try:
        client = VcoClient(
            orchestrator_url=module.params["orchestrator_url"],
            api_token=module.params["api_token"],
            enterprise_id=module.params["enterprise_id"],
            verify_ssl=module.params["verify_ssl"],
        )

        raw_edges = client.get_enterprise_edges(
            with_fields=["configuration", "site", "licenses"]
        )

        edges = []
        for e in raw_edges:
            profile_name = ""
            config = e.get("configuration", {})
            enterprise_config = config.get("enterprise", {})
            if enterprise_config:
                profile_name = enterprise_config.get("name", "")

            license_info = {}
            licenses = e.get("licenses", [])
            if licenses:
                lic = licenses[0]
                license_info = {
                    "edition": lic.get("edition", ""),
                    "sku": lic.get("sku", ""),
                    "bandwidth_tier": lic.get("bandwidthTier", ""),
                    "term_months": lic.get("termMonths", ""),
                    "start": lic.get("start", ""),
                    "end": lic.get("end", ""),
                    "alias": lic.get("alias", ""),
                    "active": bool(lic.get("active", 0)),
                }

            edges.append({
                "id": e.get("id"),
                "name": e.get("name", ""),
                "edge_state": e.get("edgeState", ""),
                "activation_state": e.get("activationState", ""),
                "model_number": e.get("modelNumber", ""),
                "software_version": e.get("softwareVersion", ""),
                "build_number": e.get("buildNumber", ""),
                "serial_number": e.get("serialNumber", ""),
                "last_contact": e.get("lastContact", ""),
                "system_up_since": e.get("systemUpSince", ""),
                "service_state": e.get("serviceState", ""),
                "profile": profile_name,
                "license": license_info,
            })

        table = format_status_table(edges)

        module.exit_json(
            changed=False,
            edges=edges,
            edge_count=len(edges),
            msg=table,
        )

    except VcoApiError as e:
        module.fail_json(msg=str(e))
    except Exception as e:
        module.fail_json(msg=f"Unexpected error: {e}")


def main():
    run_module()


if __name__ == "__main__":
    main()

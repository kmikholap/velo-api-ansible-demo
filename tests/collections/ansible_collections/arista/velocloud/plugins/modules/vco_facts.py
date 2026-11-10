#!/usr/bin/python

DOCUMENTATION = r"""
---
module: vco_facts
short_description: Gather VeloCloud Orchestrator facts
description:
  - Gathers enterprise profiles and/or edge lists from the VeloCloud Orchestrator.
  - Useful for resolving profile names to IDs before provisioning.
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
  gather:
    description: List of fact types to gather
    required: false
    type: list
    elements: str
    default: ["profiles"]
    choices: ["profiles", "edges"]
  verify_ssl:
    description: Verify SSL certificates
    required: false
    type: bool
    default: true
"""

EXAMPLES = r"""
- name: Gather VeloCloud profiles
  arista.velocloud.vco_facts:
    orchestrator_url: "https://vco.example.com"
    api_token: "{{ vco_api_token }}"
    enterprise_id: 1982
    gather:
      - profiles
      - edges
"""

RETURN = r"""
ansible_facts:
  description: Facts gathered from VeloCloud Orchestrator
  returned: always
  type: dict
  contains:
    velocloud:
      description: VeloCloud facts namespace
      type: dict
      contains:
        profiles:
          description: List of configuration profiles
          type: list
        edges:
          description: List of edges (basic info)
          type: list
"""

from ansible.module_utils.basic import AnsibleModule

try:
    from ansible_collections.arista.velocloud.plugins.module_utils.vco_client import (
        VcoClient, VcoApiError,
    )
except ImportError:
    pass


def run_module():
    module = AnsibleModule(
        argument_spec=dict(
            orchestrator_url=dict(type="str", required=True),
            api_token=dict(type="str", required=True, no_log=True),
            enterprise_id=dict(type="int", required=True),
            gather=dict(type="list", elements="str", default=["profiles"]),
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

        facts = {}
        gather = module.params["gather"]

        if "profiles" in gather:
            configs = client.get_enterprise_configurations()
            facts["profiles"] = [
                {"id": c["id"], "name": c["name"],
                 "description": c.get("description", ""),
                 "edge_count": c.get("edgeCount", 0)}
                for c in configs
            ]

        if "edges" in gather:
            edges = client.get_enterprise_edges()
            facts["edges"] = [
                {"id": e["id"], "name": e["name"],
                 "edge_state": e.get("edgeState", ""),
                 "model_number": e.get("modelNumber", ""),
                 "activation_state": e.get("activationState", "")}
                for e in edges
            ]

        module.exit_json(
            changed=False,
            ansible_facts={"velocloud": facts},
        )

    except VcoApiError as e:
        module.fail_json(msg=str(e))
    except Exception as e:
        module.fail_json(msg=f"Unexpected error: {e}")


def main():
    run_module()


if __name__ == "__main__":
    main()

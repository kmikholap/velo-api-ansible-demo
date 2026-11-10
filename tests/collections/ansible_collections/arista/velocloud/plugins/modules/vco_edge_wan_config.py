#!/usr/bin/python

DOCUMENTATION = r"""
---
module: vco_edge_wan_config
short_description: Configure WAN interface static IP on a VeloCloud Edge
description:
  - Sets a WAN routed interface to static IP addressing on an existing edge.
  - Reads the edge-specific deviceSettings module, modifies the interface,
    and pushes the full updated configuration back.
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
  edge_id:
    description: Edge ID to configure
    required: true
    type: int
  interface_name:
    description: Routed interface name (e.g., GE3)
    required: false
    type: str
    default: "GE3"
  cidr_ip:
    description: Static IP address
    required: true
    type: str
  netmask:
    description: Subnet mask
    required: true
    type: str
  gateway:
    description: Default gateway
    required: true
    type: str
  verify_ssl:
    description: Verify SSL certificates
    required: false
    type: bool
    default: true
"""

EXAMPLES = r"""
- name: Configure static IP on edge WAN GE3
  arista.velocloud.vco_edge_wan_config:
    orchestrator_url: "https://vco.example.com"
    api_token: "{{ vco_api_token }}"
    enterprise_id: 1982
    edge_id: 1234
    interface_name: "GE3"
    cidr_ip: "203.0.113.10"
    netmask: "255.255.255.248"
    gateway: "203.0.113.9"
"""

RETURN = r"""
module_id:
  description: Configuration module ID that was updated
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


def run_module():
    module = AnsibleModule(
        argument_spec=dict(
            orchestrator_url=dict(type="str", required=True),
            api_token=dict(type="str", required=True, no_log=True),
            enterprise_id=dict(type="int", required=True),
            edge_id=dict(type="int", required=True),
            interface_name=dict(type="str", default="GE3"),
            cidr_ip=dict(type="str", required=True),
            netmask=dict(type="str", required=True),
            gateway=dict(type="str", required=True),
            verify_ssl=dict(type="bool", default=True),
        ),
        supports_check_mode=True,
    )

    if module.check_mode:
        module.exit_json(changed=True, msg="Would configure WAN interface")

    try:
        client = VcoClient(
            orchestrator_url=module.params["orchestrator_url"],
            api_token=module.params["api_token"],
            enterprise_id=module.params["enterprise_id"],
            verify_ssl=module.params["verify_ssl"],
        )

        result = client.configure_edge_wan_static(
            edge_id=module.params["edge_id"],
            interface_name=module.params["interface_name"],
            cidr_ip=module.params["cidr_ip"],
            netmask=module.params["netmask"],
            gateway=module.params["gateway"],
        )

        module.exit_json(
            changed=True,
            msg=f"Interface {module.params['interface_name']} configured with "
                f"static IP {module.params['cidr_ip']} on edge {module.params['edge_id']}",
        )

    except VcoApiError as e:
        module.fail_json(msg=str(e))
    except Exception as e:
        module.fail_json(msg=f"Unexpected error: {e}")


def main():
    run_module()


if __name__ == "__main__":
    main()

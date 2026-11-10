#!/usr/bin/python

DOCUMENTATION = r"""
---
module: vco_edge_provision
short_description: Provision a VeloCloud Edge
description:
  - Provisions a new Edge in the VeloCloud Orchestrator.
  - Optionally configures a WAN interface with a static IP address.
  - The activation email is automatically sent to the site contact email.
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
  name:
    description: Edge name
    required: true
    type: str
  model_number:
    description: >
      Edge model. Valid values include edge500, edge5X0, edge510,
      edge6X0, edge710, edge840, edge1000, edge3X00, virtual, etc.
    required: true
    type: str
  configuration_id:
    description: Configuration profile ID to assign to the edge
    required: true
    type: int
  site:
    description: >
      Site information dict. Include contactEmail to trigger activation email.
      Keys: contactName, contactEmail, streetAddress, city, state, country, postalCode.
    required: false
    type: dict
  serial_number:
    description: Edge serial number
    required: false
    type: str
  description:
    description: Edge description
    required: false
    type: str
  wan_interface:
    description: WAN interface name to configure with static IP
    required: false
    type: str
    default: "GE3"
  wan_ip:
    description: Static IP address for the WAN interface
    required: false
    type: str
  wan_netmask:
    description: Subnet mask for the WAN interface
    required: false
    type: str
  wan_gateway:
    description: Default gateway for the WAN interface
    required: false
    type: str
  verify_ssl:
    description: Verify SSL certificates
    required: false
    type: bool
    default: true
"""

EXAMPLES = r"""
- name: Provision edge with static WAN IP
  arista.velocloud.vco_edge_provision:
    orchestrator_url: "https://vco.example.com"
    api_token: "{{ vco_api_token }}"
    enterprise_id: 1982
    name: "BRANCH-01"
    model_number: "edge6X0"
    configuration_id: 42
    site:
      contactName: "John Smith"
      contactEmail: "jsmith@example.com"
      city: "Wellington"
      state: "FL"
      country: "US"
    wan_ip: "203.0.113.10"
    wan_netmask: "255.255.255.248"
    wan_gateway: "203.0.113.9"
"""

RETURN = r"""
edge_id:
  description: ID of the provisioned edge
  returned: success
  type: int
activation_key:
  description: Activation key for the edge
  returned: success
  type: str
wan_configured:
  description: Whether WAN static IP was configured
  returned: success
  type: bool
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
            name=dict(type="str", required=True),
            model_number=dict(type="str", required=True),
            configuration_id=dict(type="int", required=True),
            site=dict(type="dict", required=False, default=None),
            serial_number=dict(type="str", required=False, default=None),
            description=dict(type="str", required=False, default=None),
            wan_interface=dict(type="str", required=False, default="GE3"),
            wan_ip=dict(type="str", required=False, default=None),
            wan_netmask=dict(type="str", required=False, default=None),
            wan_gateway=dict(type="str", required=False, default=None),
            send_activation_email=dict(type="bool", default=True),
            license_alias=dict(type="str", required=False, default=None),
            ha_enabled=dict(type="bool", required=False, default=None),
            verify_ssl=dict(type="bool", default=True),
        ),
        supports_check_mode=True,
    )

    if module.check_mode:
        module.exit_json(changed=True, msg="Would provision edge")

    try:
        client = VcoClient(
            orchestrator_url=module.params["orchestrator_url"],
            api_token=module.params["api_token"],
            enterprise_id=module.params["enterprise_id"],
            verify_ssl=module.params["verify_ssl"],
        )

        result = client.provision_edge_full(
            name=module.params["name"],
            model_number=module.params["model_number"],
            configuration_id=module.params["configuration_id"],
            site=module.params["site"],
            wan_ip=module.params["wan_ip"],
            wan_netmask=module.params["wan_netmask"],
            wan_gateway=module.params["wan_gateway"],
            wan_interface=module.params["wan_interface"],
            serial_number=module.params["serial_number"],
            description=module.params["description"],
            send_activation_email=module.params["send_activation_email"],
            license_alias=module.params["license_alias"],
            ha_enabled=module.params["ha_enabled"],
        )

        already_exists = result.get("already_exists", False)
        changed = not already_exists

        if already_exists:
            msg = (f"Edge '{module.params['name']}' already exists "
                   f"(ID: {result['edge_id']}) — skipped")
        else:
            msg = (f"Edge '{module.params['name']}' provisioned "
                   f"(ID: {result['edge_id']}, "
                   f"Key: {result['activation_key']}, "
                   f"WAN: {result['wan_configured']}, "
                   f"Email: {result['email_sent']})")

        module.exit_json(
            changed=changed,
            edge_id=result["edge_id"],
            activation_key=result["activation_key"],
            wan_configured=result["wan_configured"],
            email_sent=result["email_sent"],
            already_exists=already_exists,
            msg=msg,
        )

    except VcoApiError as e:
        module.fail_json(msg=str(e))
    except Exception as e:
        module.fail_json(msg=f"Unexpected error: {e}")


def main():
    run_module()


if __name__ == "__main__":
    main()

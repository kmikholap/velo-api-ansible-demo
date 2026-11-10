import ipaddress
import time
import copy
import requests


class VcoApiError(Exception):
    def __init__(self, status_code, body, endpoint):
        self.status_code = status_code
        self.body = body
        self.endpoint = endpoint
        super().__init__(f"VCO API error {status_code} on {endpoint}: {body}")


class VcoClient:
    def __init__(self, orchestrator_url, api_token, enterprise_id,
                 verify_ssl=True, timeout=60):
        self.orchestrator_url = orchestrator_url.rstrip("/")
        self.base_url = self.orchestrator_url + "/portal/rest"
        self.enterprise_id = int(enterprise_id)
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Token {api_token}",
        })
        self.session.verify = verify_ssl

    def _post(self, endpoint, payload=None, max_retries=3):
        url = f"{self.base_url}/{endpoint}"
        if payload is None:
            payload = {}
        for attempt in range(max_retries):
            resp = self.session.post(url, json=payload, timeout=self.timeout)
            if resp.status_code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            if resp.status_code != 200:
                raise VcoApiError(resp.status_code, resp.text, endpoint)
            return resp.json()
        raise VcoApiError(429, "Rate limited after retries", endpoint)

    # --- Profile / configuration methods ---

    def get_enterprise_configurations(self):
        return self._post("enterprise/getEnterpriseConfigurations", {
            "enterpriseId": self.enterprise_id,
        })

    def get_configuration_modules(self, configuration_id, modules=None):
        payload = {
            "enterpriseId": self.enterprise_id,
            "configurationId": configuration_id,
        }
        if modules:
            payload["modules"] = modules
        return self._post("configuration/getConfigurationModules", payload)

    def get_profile_supported_models(self, configuration_id):
        modules = self.get_configuration_modules(
            configuration_id, modules=["deviceSettings"]
        )
        for m in modules:
            if m.get("name") == "deviceSettings":
                return list(m.get("data", {}).get("models", {}).keys())
        return []

    # --- Edge provisioning ---

    def edge_provision(self, name, model_number, configuration_id,
                       site=None, serial_number=None, description=None,
                       edge_license_id=None, ha_enabled=None):
        payload = {
            "enterpriseId": self.enterprise_id,
            "configurationId": configuration_id,
            "modelNumber": model_number,
            "name": name,
        }
        if site:
            payload["site"] = site
        if serial_number:
            payload["serialNumber"] = serial_number
        if description:
            payload["description"] = description
        if edge_license_id is not None:
            payload["edgeLicenseId"] = edge_license_id
        if ha_enabled is not None:
            payload["haEnabled"] = ha_enabled
        return self._post("edge/edgeProvision", payload)

    def get_enterprise_edge_licenses(self):
        edges = self.get_enterprise_edges(with_fields=["licenses"])
        seen = {}
        for e in edges:
            for lic in e.get("licenses", []):
                lid = lic.get("id")
                if lid and lid not in seen:
                    seen[lid] = {
                        "id": lid,
                        "alias": lic.get("alias", ""),
                        "edition": lic.get("edition", ""),
                        "bandwidth_tier": lic.get("bandwidthTier", ""),
                        "sku": lic.get("sku", ""),
                        "term_months": lic.get("termMonths", ""),
                    }
        return list(seen.values())

    def resolve_license_by_alias(self, alias):
        licenses = self.get_enterprise_edge_licenses()
        for lic in licenses:
            if alias.lower() in lic["alias"].lower():
                return lic["id"]
        alias_list = [l["alias"] for l in licenses]
        raise VcoApiError(
            0,
            f"License alias '{alias}' not found. "
            f"Available: {alias_list}",
            "resolve_license_by_alias"
        )

    # --- Edge query ---

    def get_enterprise_edges(self, with_fields=None):
        payload = {"enterpriseId": self.enterprise_id}
        if with_fields:
            payload["with"] = with_fields
        return self._post("enterprise/getEnterpriseEdges", payload)

    def get_edge(self, edge_id, with_fields=None):
        payload = {
            "enterpriseId": self.enterprise_id,
            "id": edge_id,
        }
        if with_fields:
            payload["with"] = with_fields
        return self._post("edge/getEdge", payload)

    def delete_edge(self, edge_id):
        return self._post("edge/deleteEdge", {
            "enterpriseId": self.enterprise_id,
            "id": edge_id,
        })

    # --- Edge configuration ---

    def get_edge_configuration_stack(self, edge_id):
        return self._post("edge/getEdgeConfigurationStack", {
            "enterpriseId": self.enterprise_id,
            "edgeId": edge_id,
        })

    def get_edge_configuration_modules(self, edge_id, modules=None):
        payload = {
            "enterpriseId": self.enterprise_id,
            "edgeId": edge_id,
        }
        if modules:
            payload["modules"] = modules
        return self._post("edge/getEdgeConfigurationModules", payload)

    def update_configuration_module(self, configuration_module_id, update_data):
        return self._post("configuration/updateConfigurationModule", {
            "enterpriseId": self.enterprise_id,
            "configurationModuleId": configuration_module_id,
            "_update": update_data,
        })

    # --- Activation email ---

    def get_edge_activation_email(self, edge_id):
        return self._post("edge/getEdgeActivationEmail", {
            "enterpriseId": self.enterprise_id,
            "id": edge_id,
            "ipVersion": ["IPv4", "IPv6"],
        })

    def send_activation_email(self, edge_id, to_email):
        template = self.get_edge_activation_email(edge_id)
        activation_url = template.get("content", {}).get(
            "activationURL", ""
        )

        edge = self.get_edge(edge_id)
        edge_name = edge.get("name", "")

        return self._post("edge/sendEdgeActivationEmail", {
            "enterpriseId": self.enterprise_id,
            "edgeId": edge_id,
            "name": edge_name,
            "to": to_email,
            "from": template.get("from", "no-reply@velocloud.net"),
            "replyTo": template.get("replyTo", "no-reply@velocloud.net"),
            "subject": template.get(
                "subject", f"Edge Activation for edge {edge_name}"
            ),
            "cc": "",
            "bcc": "",
            "content": {
                "activationURL": activation_url,
                "message": (
                    "If you experience any difficulty, "
                    "please contact your IT admin."
                ),
                "prompt": (
                    "To activate your VeloCloud Edge, "
                    "please follow these steps:"
                ),
                "salutation": "Dear customer,",
                "steps": [
                    "Connect your device to power and any Internet "
                    "cables or USB modems.",
                    "Find and connect to the Wi-Fi network that looks "
                    'like "velocloud-" followed by 3 more '
                    "letters/numbers (e.g. \"velocloud-01c\") and use "
                    '"vcsecret" as the password. If your device does '
                    "not have Wi-Fi, connect to it using an Ethernet "
                    "cable. Note: Wi-Fi supports only for IPv4, For "
                    "IPv6, please use the Ethernet cable.",
                    "Click the following link to activate your edge",
                ],
            },
        })

    # --- High-level helpers ---

    def _find_edge_specific_config(self, stack):
        for conf in stack:
            if "Edge Specific" in conf.get("name", ""):
                return conf
        return stack[0]

    def _get_model_interfaces(self, configuration_id, model_number):
        modules = self.get_configuration_modules(
            configuration_id, modules=["deviceSettings"]
        )
        for m in modules:
            if m.get("name") == "deviceSettings":
                models = m.get("data", {}).get("models", {})
                model_data = models.get(model_number, {})
                if model_data:
                    return copy.deepcopy(
                        model_data.get("routedInterfaces", [])
                    )
        return []

    def configure_edge_wan_static(self, edge_id, interface_name,
                                   cidr_ip, netmask, gateway,
                                   configuration_id=None, model_number=None):
        stack = self._get_edge_config_stack_with_retry(edge_id)
        edge_specific_config = self._find_edge_specific_config(stack)

        ds_module = None
        for mod in edge_specific_config.get("modules", []):
            if mod.get("name") == "deviceSettings":
                ds_module = mod
                break

        if ds_module is None:
            raise VcoApiError(
                0, "deviceSettings module not found in edge-specific config",
                "configure_edge_wan_static"
            )

        module_id = ds_module["id"]
        data = copy.deepcopy(ds_module.get("data", {}))

        existing_ri = data.get("routedInterfaces", [])
        if existing_ri:
            all_interfaces = copy.deepcopy(existing_ri)
        else:
            cfg_id = configuration_id
            m_num = model_number
            if not cfg_id or not m_num:
                profile_config = stack[-1] if len(stack) > 1 else None
                cfg_id = cfg_id or (
                    profile_config.get("id") if profile_config else None
                )
                edge = self.get_edge(edge_id)
                m_num = m_num or edge.get("modelNumber", "")
            all_interfaces = self._get_model_interfaces(cfg_id, m_num)
            if not all_interfaces:
                raise VcoApiError(
                    0,
                    f"Model '{m_num}' is not supported by the assigned "
                    f"profile (configurationId={cfg_id}). Cannot configure "
                    f"WAN interface. Assign a profile that includes this "
                    f"model or use a supported model.",
                    "configure_edge_wan_static"
                )

        prefix_len = ipaddress.IPv4Network(f"0.0.0.0/{netmask}").prefixlen

        interface_found = False
        for iface in all_interfaces:
            if iface.get("name") == interface_name:
                iface["override"] = True
                iface["addressing"] = {
                    "type": "STATIC",
                    "cidrIp": cidr_ip,
                    "cidrPrefix": prefix_len,
                    "netmask": netmask,
                    "gateway": gateway,
                }
                interface_found = True
            else:
                if iface.get("override") is None:
                    iface["override"] = False

        if not interface_found:
            raise VcoApiError(
                0,
                f"Interface {interface_name} not found in routedInterfaces",
                "configure_edge_wan_static"
            )

        data["routedInterfaces"] = all_interfaces

        if "lan" in data and "networks" in data["lan"]:
            data["lan"]["networks"] = [
                n for n in data["lan"]["networks"]
                if n.get("cidrIp") is not None
            ]

        return self.update_configuration_module(module_id, {
            "name": "deviceSettings",
            "data": data,
        })

    def find_edge_by_name(self, name):
        edges = self.get_enterprise_edges()
        for e in edges:
            if e.get("name") == name:
                return e
        return None

    def provision_edge_full(self, name, model_number, configuration_id,
                            site=None, wan_ip=None, wan_netmask=None,
                            wan_gateway=None, wan_interface="GE3",
                            serial_number=None, description=None,
                            send_activation_email=True,
                            license_alias=None, ha_enabled=None):
        existing = self.find_edge_by_name(name)
        if existing:
            return {
                "edge_id": existing["id"],
                "activation_key": existing.get("activationKey", ""),
                "wan_configured": False,
                "email_sent": False,
                "already_exists": True,
            }

        supported = self.get_profile_supported_models(configuration_id)
        if supported and model_number not in supported:
            raise VcoApiError(
                0,
                f"Model '{model_number}' is not supported by the assigned "
                f"profile (configurationId={configuration_id}). "
                f"Supported models: {', '.join(sorted(supported))}",
                "provision_edge_full"
            )

        edge_license_id = None
        if license_alias and license_alias.strip():
            edge_license_id = self.resolve_license_by_alias(license_alias)

        result = self.edge_provision(
            name=name,
            model_number=model_number,
            configuration_id=configuration_id,
            site=site,
            serial_number=serial_number,
            description=description,
            edge_license_id=edge_license_id,
            ha_enabled=ha_enabled,
        )

        edge_id = result["id"]
        activation_key = result["activationKey"]

        wan_configured = False
        if wan_ip and wan_ip.strip() and wan_netmask and wan_netmask.strip() \
                and wan_gateway and wan_gateway.strip():
            self.configure_edge_wan_static(
                edge_id=edge_id,
                interface_name=wan_interface,
                cidr_ip=wan_ip,
                netmask=wan_netmask,
                gateway=wan_gateway,
                configuration_id=configuration_id,
                model_number=model_number,
            )
            wan_configured = True

        email_sent = False
        contact_email = (site or {}).get("contactEmail", "")
        if send_activation_email and contact_email:
            self.send_activation_email(
                edge_id=edge_id,
                to_email=contact_email,
            )
            email_sent = True

        return {
            "edge_id": edge_id,
            "activation_key": activation_key,
            "wan_configured": wan_configured,
            "email_sent": email_sent,
            "already_exists": False,
        }

    def _get_edge_config_stack_with_retry(self, edge_id, max_attempts=4,
                                           delay=2):
        for attempt in range(max_attempts):
            stack = self.get_edge_configuration_stack(edge_id)
            if stack and any("Edge Specific" in c.get("name", "") for c in stack):
                edge_config = self._find_edge_specific_config(stack)
                for mod in edge_config.get("modules", []):
                    if mod.get("name") == "deviceSettings" and mod.get("data"):
                        return stack
            if attempt < max_attempts - 1:
                time.sleep(delay)
        return stack

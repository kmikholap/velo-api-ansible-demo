import time
import pytest


@pytest.fixture
def first_profile_id(vco_client):
    configs = vco_client.get_enterprise_configurations()
    assert len(configs) > 0, "Need at least one profile to provision edges"
    return configs[0]["id"]


@pytest.fixture
def unique_suffix():
    return str(int(time.time()))[-6:]


def test_provision_single_edge(vco_client, cleanup_edges, first_profile_id, unique_suffix):
    name = f"TEST-PROV-{unique_suffix}"
    result = vco_client.edge_provision(
        name=name,
        model_number="virtual",
        configuration_id=first_profile_id,
        description="Automated test edge",
    )
    assert "id" in result
    assert "activationKey" in result
    assert result["id"] > 0
    assert len(result["activationKey"]) > 0
    cleanup_edges.append(result["id"])
    print(f"  Provisioned edge ID={result['id']}, key={result['activationKey']}")


def test_provision_edge_with_site_email(vco_client, cleanup_edges, first_profile_id, unique_suffix):
    name = f"TEST-EMAIL-{unique_suffix}"
    result = vco_client.edge_provision(
        name=name,
        model_number="virtual",
        configuration_id=first_profile_id,
        site={
            "contactName": "Test User",
            "contactEmail": "test@example.com",
            "city": "TestCity",
            "country": "US",
        },
    )
    cleanup_edges.append(result["id"])

    edge = vco_client.get_edge(result["id"], with_fields=["site"])
    site = edge.get("site", {})
    assert site.get("contactEmail") == "test@example.com"


def test_provision_edge_with_wan_config(vco_client, cleanup_edges, first_profile_id, unique_suffix):
    name = f"TEST-WAN-{unique_suffix}"
    result = vco_client.provision_edge_full(
        name=name,
        model_number="virtual",
        configuration_id=first_profile_id,
        site={
            "contactName": "WAN Test",
            "contactEmail": "wan-test@example.com",
            "city": "TestCity",
            "country": "US",
        },
        wan_ip="10.99.99.10",
        wan_netmask="255.255.255.0",
        wan_gateway="10.99.99.1",
        wan_interface="GE3",
    )
    cleanup_edges.append(result["edge_id"])

    assert result["edge_id"] > 0
    assert len(result["activation_key"]) > 0
    assert result["wan_configured"] is True

    stack = vco_client.get_edge_configuration_stack(result["edge_id"])
    edge_config = None
    for conf in stack:
        if "Edge Specific" in conf.get("name", ""):
            edge_config = conf
            break
    assert edge_config is not None

    ds_module = None
    for mod in edge_config.get("modules", []):
        if mod.get("name") == "deviceSettings":
            ds_module = mod
            break

    assert ds_module is not None, "deviceSettings module not found"
    routed = ds_module.get("data", {}).get("routedInterfaces", [])
    ge3 = None
    for iface in routed:
        if iface.get("name") == "GE3":
            ge3 = iface
            break

    assert ge3 is not None, "GE3 interface not found"
    assert ge3.get("override") is True
    addressing = ge3.get("addressing", {})
    assert addressing.get("type") == "STATIC"
    assert addressing.get("cidrIp") == "10.99.99.10"
    assert addressing.get("netmask") == "255.255.255.0"
    assert addressing.get("gateway") == "10.99.99.1"
    print(f"  WAN config verified: {addressing}")

import pytest
from arista.velocloud.plugins.module_utils.vco_client import VcoApiError


def test_get_enterprise_configurations(vco_client):
    configs = vco_client.get_enterprise_configurations()
    assert isinstance(configs, list)
    assert len(configs) > 0, "Enterprise should have at least one profile"
    for c in configs:
        assert "id" in c
        assert "name" in c
        print(f"  Profile: {c['name']} (ID: {c['id']})")


def test_get_enterprise_edges(vco_client):
    edges = vco_client.get_enterprise_edges()
    assert isinstance(edges, list)
    for e in edges:
        assert "id" in e
        assert "name" in e
        assert "edgeState" in e
    print(f"  Found {len(edges)} edges")


def test_get_enterprise_edges_with_configuration(vco_client):
    edges = vco_client.get_enterprise_edges(with_fields=["configuration"])
    assert isinstance(edges, list)
    for e in edges:
        config = e.get("configuration", {})
        enterprise_config = config.get("enterprise", {})
        if enterprise_config:
            assert "name" in enterprise_config


def test_api_error_handling(vco_client):
    with pytest.raises(VcoApiError) as exc_info:
        vco_client._post("nonexistent/endpoint", {})
    assert exc_info.value.status_code != 200

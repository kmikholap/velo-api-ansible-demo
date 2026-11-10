VALID_EDGE_STATES = {
    "CONNECTED", "OFFLINE", "DEGRADED",
    "NEVER_ACTIVATED", "DISABLED", "EXPIRED",
}


def test_edge_status_returns_all_fields(vco_client):
    edges = vco_client.get_enterprise_edges(with_fields=["configuration"])
    for e in edges:
        assert "edgeState" in e, f"Edge {e.get('name')} missing edgeState"
        assert "modelNumber" in e, f"Edge {e.get('name')} missing modelNumber"
        assert "softwareVersion" in e, f"Edge {e.get('name')} missing softwareVersion"
        assert "name" in e


def test_edge_state_enum_values(vco_client):
    edges = vco_client.get_enterprise_edges()
    for e in edges:
        state = e.get("edgeState", "")
        assert state in VALID_EDGE_STATES, (
            f"Edge {e.get('name')} has unexpected state: {state}"
        )

import sys
import os
import pytest

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), "..", "collections", "ansible_collections"
))

from arista.velocloud.plugins.module_utils.vco_client import VcoClient

VCO_URL = os.environ["VCO_URL"]
VCO_TOKEN = os.environ["VCO_TOKEN"]
VCO_ENTERPRISE_ID = int(os.environ["VCO_ENTERPRISE_ID"])


@pytest.fixture(scope="session")
def vco_client():
    return VcoClient(
        orchestrator_url=VCO_URL,
        api_token=VCO_TOKEN,
        enterprise_id=VCO_ENTERPRISE_ID,
        verify_ssl=True,
    )


@pytest.fixture
def cleanup_edges(vco_client):
    edge_ids = []
    yield edge_ids
    for edge_id in edge_ids:
        try:
            vco_client.delete_edge(edge_id)
        except Exception:
            pass

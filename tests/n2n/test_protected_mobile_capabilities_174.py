"""Protected edge enrollment must not promise the refused legacy Ask workflow."""
import pytest

from bgp.federation.manager import FederationManager
from bgp.federation.service import FederationService


@pytest.mark.parametrize('protected', [False, True])
def test_advertised_ask_matches_selected_handler(tmp_path, monkeypatch, protected):
    monkeypatch.setenv('N2N_PROTECTED_OPERATIONS', '1' if protected else '0')
    service = FederationService(local_as=65001, router_id='4.4.4.4',
                                manager=FederationManager(base_dir=str(tmp_path)))
    advertised = service._edge_border_capabilities()
    handler = service._edge_border_handlers['n2n/edge/ask']
    assert (handler == service._protected_legacy_refusal) is protected
    assert advertised['capabilities']['text'] is (not protected)
    assert advertised['capabilities']['voice_text'] is (not protected)
    if protected:
        assert not any(advertised['capabilities'].values())
        assert advertised['model'] is None
        assert advertised['qualified_targets'] == []

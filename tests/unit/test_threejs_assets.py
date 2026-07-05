"""
Unit tests for assets.py's real-stencil resolution chain (spec.md FR-019,
FR-019a, FR-020, FR-021, User Story 5).

`assets._call_tool` (the single choke-point through which every
sketchfab-mcp call passes) is mocked here so these tests are deterministic
and independent of Sketchfab's live, ever-changing catalog contents
(research.md §5's rationale) — the real, unmocked integration (real search,
real per-model license verification, real download+embed, real
GLTFLoader.parse() in a headless browser) was manually verified end-to-end
during implementation using real Sketchfab credentials; see the "NetClaw
patch" comments in mcp-servers/sketchfab-mcp-server/index.ts for the real
bug (license field silently dropped) found and fixed along the way.
"""

import sys
from pathlib import Path
from unittest.mock import patch

skill_path = Path(__file__).parent.parent.parent / "workspace" / "skills" / "threejs-network-viz"
sys.path.insert(0, str(skill_path))

import assets  # noqa: E402
from topology_model import AssetKind, FallbackReason, ModelSource  # noqa: E402

_CC0_DETAILS = (
    '\n[Model] Test Model\nID: uid-cc0\nDownloadable: Yes\n'
    'License: {"uid": "7c23a1ba438d4306920229c12afcb5f9", "label": "CC0 Public Domain", "slug": "cc0"}\n'
    "Thumbnail: none\n"
)
_NON_CC0_DETAILS = (
    '\n[Model] Test Model\nID: uid-by\nDownloadable: Yes\n'
    'License: {"uid": "322a749bcfa841b29dff1e8a1bb74b0b", "label": "CC Attribution", "slug": "by"}\n'
    "Thumbnail: none\n"
)
_SEARCH_RESULT = "Found 2 models:\n\n[1] Test\nID: uid-cc0\nDownloadable: Yes\n\n[2] Test2\nID: uid-by\nDownloadable: Yes\n"


def setup_function():
    # Isolate each test from any real cache/user-asset directory contents.
    assets._CACHE_DIR = Path("/tmp/threejs-viz-test-cache")
    assets._USER_ASSET_DIR = Path("/tmp/threejs-viz-test-user-assets")
    import shutil

    shutil.rmtree(assets._CACHE_DIR, ignore_errors=True)
    shutil.rmtree(assets._USER_ASSET_DIR, ignore_errors=True)


def test_verify_cc0_license_accepts_exact_cc0_slug():
    with patch("assets._call_tool", return_value=_CC0_DETAILS):
        assert assets.verify_cc0_license("uid-cc0") is True


def test_verify_cc0_license_rejects_non_cc0_slug():
    with patch("assets._call_tool", return_value=_NON_CC0_DETAILS):
        assert assets.verify_cc0_license("uid-by") is False


def test_verify_cc0_license_rejects_when_license_field_missing():
    no_license_text = "\n[Model] Test\nID: uid-x\nDownloadable: Yes\nThumbnail: none\n"
    with patch("assets._call_tool", return_value=no_license_text):
        assert assets.verify_cc0_license("uid-x") is False


def test_download_and_embed_rejects_when_requested_format_unavailable():
    fallback_text = 'Downloaded model "X" in source format (requested glb was not available).\nSaved to: /tmp/x.source'
    with patch("assets._call_tool", return_value=fallback_text):
        assert assets.download_and_embed("uid-x") is None


def test_resolve_device_asset_defaults_to_procedural_when_not_real_stencil_mode():
    asset, fallback = assets.resolve_device_asset("r1", "router", real_stencil_mode=False)
    assert asset.kind == AssetKind.PROCEDURAL
    assert fallback is None


def test_resolve_device_asset_falls_back_when_no_candidate_is_cc0():
    with patch("assets._call_tool", return_value=_SEARCH_RESULT), patch.object(
        assets, "verify_cc0_license", return_value=False
    ):
        asset, fallback = assets.resolve_device_asset("r1", "router", real_stencil_mode=True)
    assert asset.kind == AssetKind.PROCEDURAL
    assert fallback is not None
    assert fallback.reason == FallbackReason.NO_CC0_CANDIDATE_FOUND
    assert fallback.hostname == "r1"


def test_resolve_device_asset_falls_back_with_source_unreachable_on_search_failure():
    with patch("assets._call_tool", side_effect=RuntimeError("network down")):
        asset, fallback = assets.resolve_device_asset("r1", "router", real_stencil_mode=True)
    assert asset.kind == AssetKind.PROCEDURAL
    assert fallback.reason == FallbackReason.SOURCE_UNREACHABLE


def test_resolve_device_asset_succeeds_with_verified_cc0_and_downloadable_candidate():
    download_text = 'Downloaded model "X" in glb format.\nSaved to: /tmp/threejs-viz-test-downloaded.glb'
    Path("/tmp/threejs-viz-test-downloaded.glb").write_bytes(b"glTFtestbytes")

    def fake_call_tool(tool_name, arguments):
        if tool_name == "sketchfab-search":
            return _SEARCH_RESULT
        if tool_name == "sketchfab-model-details":
            return _CC0_DETAILS
        if tool_name == "sketchfab-download":
            return download_text
        raise AssertionError(f"unexpected tool {tool_name}")

    with patch("assets._call_tool", side_effect=fake_call_tool):
        asset, fallback = assets.resolve_device_asset("r1", "router", real_stencil_mode=True)

    assert fallback is None
    assert asset.kind == AssetKind.REAL_MODEL
    assert asset.model_source == ModelSource.SKETCHFAB
    assert asset.model_license_slug == "cc0"
    assert asset.embedded_glb_base64 is not None

    # And the successful resolution was cached for reuse (check_cached_asset).
    cached, _ = assets.check_cached_asset("router"), None
    assert cached is not None
    assert cached.model_source == ModelSource.CACHE


def test_check_cached_asset_returns_none_when_nothing_cached_or_user_supplied():
    assert assets.check_cached_asset("router") is None


def test_user_supplied_asset_is_used_without_any_network_call():
    """This is the ONLY path by which a gated-marketplace-sourced asset can
    ever be used (FR-020) — placing a file by hand, never an automated
    fetch. Patching _call_tool to raise proves no network call happens."""
    assets._USER_ASSET_DIR.mkdir(parents=True, exist_ok=True)
    (assets._USER_ASSET_DIR / "firewall.glb").write_bytes(b"usersuppliedbytes")

    with patch("assets._call_tool", side_effect=AssertionError("must not call the network")):
        asset, fallback = assets.resolve_device_asset("fw1", "firewall", real_stencil_mode=True)

    assert fallback is None
    assert asset.kind == AssetKind.REAL_MODEL
    assert asset.model_source == ModelSource.USER_SUPPLIED

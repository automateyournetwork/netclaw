"""Unit tests for investigation admission policy (no network).

Run:  cd services/alert-receiver && python test_investigation_policy.py
"""
from __future__ import annotations

import importlib.util
from pathlib import Path


def _load():
    path = Path(__file__).with_name("server.py")
    spec = importlib.util.spec_from_file_location("alert_receiver_server", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    ar = _load()
    Alert = ar.Alert
    AlertLabel = ar.AlertLabel
    AlertAnnotation = ar.AlertAnnotation
    should = ar.should_auto_investigate

    def mk(name, severity="warning", status="firing", **labels):
        return Alert(
            status=status,
            labels=AlertLabel(
                alertname=name, instance="192.168.3.5", severity=severity, **labels
            ),
            annotations=AlertAnnotation(summary="t"),
            fingerprint="fp-test",
        )

    assert should(mk("SwitchInterfaceDown"))[0] is False
    assert should(mk("SwitchIdlePortsPresent", severity="info", investigate="false"))[0] is False
    assert should(mk("Something", severity="info"))[0] is False
    assert should(mk("SwitchLinkLost", investigate="true"))[0] is True
    assert should(mk("DeviceSnmpExporterDown", investigate="true"))[0] is True
    assert should(mk("WifiDegraded24GHz"))[0] is True
    assert should(mk("SwitchLinkLost", status="resolved", investigate="true"))[0] is False
    # explicit false wins even for warning
    assert should(mk("ImportantLooking", severity="critical", investigate="false"))[0] is False
    print("test_investigation_policy: OK")


if __name__ == "__main__":
    main()

"""Internal per-child composition, not an installed/qualified read capability.

Operator code must supply frozen metadata and the selected native policy module.
Use only inside collector._child's process/deadline boundary. No capability marker,
credential-file loader, command-line entry point or alternate transport is exposed.
"""
from contextlib import contextmanager
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


connection = _load('_spec200_adapter_connection', 'native_connection.py')
session = _load('_spec200_adapter_session', 'native_session.py')


class AdapterRefused(ValueError):
    pass


class FrozenCapture:
    """One child, one attempt, then detached parsing of those exact captured bytes.

    Construction does not load a testbed or connect. No model/tool may choose the
    document, hashes or server. A future operator adapter still needs actual SSH
    and policy qualification before exporting the collector capability marker.
    """
    def __init__(self, document, device_name, *, document_sha256, endpoint_sha256,
                 server, source_sha256):
        encoded = json.dumps(document, allow_nan=False)
        if len(encoded.encode()) > 65536 or connection.digest(document) != document_sha256:
            raise AdapterRefused('frozen_testbed_changed')
        self._document = encoded
        self._device = device_name
        self._document_sha256 = document_sha256
        self._endpoint_sha256 = endpoint_sha256
        self._server = server
        self._source_sha256 = source_sha256
        self._attempted = False
        self._captured = None

    @contextmanager
    def capture_context(self, device, command, *, timeout, evidence_directory):
        if self._attempted:
            raise AdapterRefused('attempt_already_started')
        self._attempted = True  # Refusal or uncertainty never permits retry.
        if device != self._device:
            raise AdapterRefused('frozen_device_mismatch')
        session.read.validate_read(self._server, command, source_sha256=self._source_sha256)
        prepared = connection.prepare_device(json.loads(self._document), device,
            document_sha256=self._document_sha256, endpoint_sha256=self._endpoint_sha256)
        with session.connected_capture(prepared, self._server, command, timeout=timeout,
                source_sha256=self._source_sha256,
                logfile=Path(evidence_directory)/'native-connection.log') as raw:
            yield raw  # Collector persists raw before this context exits.
        # Set only after clean preservation AND disconnect; never on an exception.
        self._captured = (device, command, hashlib.sha256(raw.encode()).digest())

    def parse_captured(self, device, command, *, output):
        if (not isinstance(output, str) or self._captured is None
                or self._captured != (device, command, hashlib.sha256(output.encode()).digest())):
            raise AdapterRefused('clean_capture_required')
        return session.read.parse_captured(command, output=output)

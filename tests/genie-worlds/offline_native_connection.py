"""Installed pyATS/Unicon preparation check with synthetic identities, no connect."""
import copy
import importlib.util
import os
from pathlib import Path
import socket
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('native_connection',ROOT/'scripts/genie-worlds/native_connection.py')
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)

with tempfile.TemporaryDirectory(dir=ROOT/'.spec200-local/tests') as temporary:
    pin=Path(temporary)/'known_hosts';pin.write_text('synthetic offline trust fixture\n');pin.chmod(0o600)
    document={'testbed':{'name':'synthetic','credentials':copy.deepcopy(native.CREDENTIALS)},
        'devices':{'router':{'os':'iosxe','platform':'iol','type':'router','connections':{
            'defaults':{'class':'unicon.Unicon'},'cli':{'protocol':'ssh','ip':'192.0.2.1','port':22,
                'ssh_options':native.SSH_PREFIX+str(pin)}}}}}
    from types import SimpleNamespace
    identity=native.policy.endpoint_identity('router',SimpleNamespace(os='iosxe',connections=document['devices']['router']['connections']))
    with patch.dict(os.environ,{key:'independent-synthetic-value' for key in [
            'SPEC200_PYATS_USERNAME','SPEC200_PYATS_PASSWORD','SPEC200_PYATS_ENABLE_PASSWORD']}), \
            patch.object(socket.socket,'connect',side_effect=AssertionError('network forbidden')) as network:
        prepared=native.prepare_device(document,'router',document_sha256=native.digest(document),
            endpoint_sha256=native.digest(identity))
        options=prepared.connection_options(5)
        assert options['init_exec_commands']==[] and options['init_config_commands']==[]
        assert options['reconnect'] is False and options['learn_os'] is False
        assert not prepared.device.is_connected()
        assert network.call_count==0
print('PASS: installed native dependency/source gate, pyATS loader, frozen endpoint/trust and options; zero socket connections; actual connect remains unqualified')

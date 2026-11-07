"""Transport policy for internal federation: local IPC or verified remote TLS."""
import ipaddress
import os
import ssl


def is_loopback(host):
    try:
        address=ipaddress.ip_address(host)
        return address.is_loopback or bool(getattr(address,'ipv4_mapped',None) and address.ipv4_mapped.is_loopback)
    except ValueError:
        return host == 'localhost'


def server_context(host):
    cert=os.environ.get('N2N_IN2N_TLS_CERT')
    key=os.environ.get('N2N_IN2N_TLS_KEY')
    if cert or key:
        if not cert or not key:raise ValueError('Set both N2N_IN2N_TLS_CERT and N2N_IN2N_TLS_KEY')
        ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version=ssl.TLSVersion.TLSv1_2
        ctx.load_cert_chain(cert,key)
        return ctx
    if not is_loopback(host):
        raise ValueError('Non-loopback iN2N requires TLS certificate and key')
    return None


def client_context(host):
    ca=os.environ.get('N2N_IN2N_CA_FILE')
    if is_loopback(host) and not ca and os.environ.get('N2N_IN2N_TLS','').lower() not in ('true','1'):
        return None
    ctx=ssl.create_default_context(cafile=ca)
    ctx.minimum_version=ssl.TLSVersion.TLSv1_2
    return ctx


def dial_options(service, host, port):
    """Shared by both launchers; reload the approved registry on every attempt."""
    if getattr(service, 'ha_runtime', None) is not None:
        raise ValueError('HA attachment endpoints come from the pinned cluster manifest')
    from .endpoint_registry import configured
    registry = configured(runtime=getattr(service, 'runtime', None))
    if registry is None:
        return host, port, {'ssl_context': client_context(host)}
    document = registry.load()
    entries = [e for e in document['entries'] if e['id'] == os.environ.get('N2N_BORDER_REGISTRY_ID')
               and e['direction'] == 'dial' and e['service'] == 'in2n']
    if len(entries) != 1:
        raise ValueError('strict member Border registration missing')
    entry = entries[0]
    return entry['routing_host'], entry['routing_port'], {
        'registration': entry, 'registry_revision': document['revision']}


def channel_binding(writer, *, strict=False):
    profile = writer.get_extra_info('tls_profile')
    if strict or profile == 'in2n-tls-exporter-v1':
        binding = writer.get_extra_info('tls_exporter')
        if (profile != 'in2n-tls-exporter-v1' or writer.get_extra_info('tls_version') != 'TLSv1.3'
                or not isinstance(binding, bytes) or len(binding) != 32):
            raise ValueError('strict iN2N TLS 1.3 exporter unavailable')
        return b'netclaw-in2n-tls-exporter-v1\0' + binding
    sslobj=writer.get_extra_info('ssl_object')
    if sslobj is not None:
        binding=sslobj.get_channel_binding('tls-unique')
        if not binding:raise ValueError('iN2N TLS channel binding unavailable')
        return b'netclaw-in2n-tls-unique\0'+binding
    peer=writer.get_extra_info('peername')
    if not peer or not is_loopback(peer[0]):
        raise ValueError('Non-loopback iN2N cleartext is refused')
    return b''

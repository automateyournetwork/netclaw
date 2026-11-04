"""Explicit installation-scoped lab attribution; no user/session authority."""
from contextlib import contextmanager
import uuid
from .protected_contract import exact, require, uuid_field


def validate_access(value):
    exact(value, 'mode')
    require(value['mode'] == 'open-lab', 'unsupported_access_mode')
    return value


def lab_principal(installation_id):
    uuid_field(installation_id)
    return {'issuer': 'open-lab',
            'subject': str(uuid.uuid5(uuid.UUID(installation_id), 'netclaw.open-lab.operator')),
            'display_name': 'Unauthenticated lab operator', 'roles': ['lab-operator']}


class OpenLabAccess:
    """Used only by an explicitly configured Border behind its private bridge."""
    open_lab = True

    def __init__(self, installation_id):
        self.installation_id = installation_id
        self.principal = lab_principal(installation_id)

    @contextmanager
    def authorize(self, context):
        require(context == {'access_mode': 'open-lab', 'installation_id': self.installation_id},
                'lab_context_refused', 403)
        yield dict(self.principal, roles=list(self.principal['roles']))

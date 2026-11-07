"""Freshness scope carried to the final, non-retrying effect handoff."""
from contextvars import ContextVar

from .config import check

CURRENT = ContextVar('netclaw_ha_effect', default=None)


class EffectScope:
    def __init__(self, kind, freshness):
        self.kind, self.freshness, self.active, self.handed_off = kind, freshness, True, False

    def check(self, kind):
        check(self.active and kind == self.kind and not self.handed_off, 'admission_scope_invalid', 403)
        self.freshness()

    def handoff(self, kind):
        self.check(kind)
        self.handed_off = True


def scope(kind):
    value = CURRENT.get()
    check(isinstance(value, EffectScope), 'ha_runtime_unqualified', 503)
    value.check(kind)
    return value

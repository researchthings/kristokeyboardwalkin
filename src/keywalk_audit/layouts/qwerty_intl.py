"""QWERTY US-International keyboard layout.

The US-International layout shares the QWERTY US physical key positions and
shift map. It diverges only in alt-graph and dead-key behavior, which does
not affect physical-key adjacency or shift-mirror equivalence and therefore
does not influence walk scoring or fingerprinting.
"""

from __future__ import annotations

from types import MappingProxyType

from keywalk_audit.layouts.base import Layout
from keywalk_audit.layouts.qwerty_us import QWERTY_US

QWERTY_INTL: Layout = Layout(
    name="qwerty_intl",
    char_to_pos=MappingProxyType(dict(QWERTY_US.char_to_pos)),
    shift_map=MappingProxyType(dict(QWERTY_US.shift_map)),
    row_offsets=MappingProxyType(dict(QWERTY_US.row_offsets)),
    finger_map=MappingProxyType(dict(QWERTY_US.finger_map)),
)

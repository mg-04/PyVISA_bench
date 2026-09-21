"""Shared plumbing for every instrument on the bench.

One base class wraps the PyVISA session so the instrument drivers only have to
care about SCPI strings, not connection bookkeeping.
"""

import pyvisa

_rm = None


def resource_manager():
    """Process-wide pyvisa-py ResourceManager (created on first use)."""
    global _rm
    if _rm is None:
        _rm = pyvisa.ResourceManager('@py')
    return _rm


def list_resources():
    """Every VISA resource string the backend can currently see."""
    return resource_manager().list_resources()


class Instrument:
    """Base class: lazy VISA connection, SCPI helpers, context manager.

    Subclasses set ``ALIAS``, ``DEFAULT_RESOURCE`` and ``DESCRIPTION``.
    Nothing touches the bus until the first read/write, so constructing an
    instrument (or a whole :class:`~bench.Bench`) is free.
    """

    ALIAS = None
    DEFAULT_RESOURCE = None
    DESCRIPTION = ''
    DEFAULT_TIMEOUT = 5000

    def __init__(self, resource=None, timeout=None):
        self.resource = resource or self.DEFAULT_RESOURCE
        if not self.resource:
            raise ValueError(
                f"{type(self).__name__} has no default resource string — "
                "pass resource='USB0::...::INSTR' or 'TCPIP::<ip>::INSTR'"
            )
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self._inst = None

    # -- connection ------------------------------------------------------

    @property
    def inst(self):
        """The open pyvisa resource, connecting on first access."""
        if self._inst is None:
            self.open()
        return self._inst

    def open(self):
        if self._inst is None:
            self._inst = resource_manager().open_resource(self.resource)
            self._inst.timeout = self.timeout
        return self

    def close(self):
        if self._inst is not None:
            self._inst.close()
            self._inst = None

    @property
    def is_open(self):
        return self._inst is not None

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    def __repr__(self):
        state = 'open' if self.is_open else 'not connected'
        return f'<{type(self).__name__} {self.resource} ({state})>'

    # -- raw SCPI --------------------------------------------------------

    def write(self, command):
        self.inst.write(command)

    def query(self, command):
        return self.inst.query(command)

    def query_raw(self, command):
        """Write a command, then read the raw (binary) response."""
        self.inst.write(command)
        return self.inst.read_raw()

    def query_float(self, command):
        return float(self.query(command))

    # -- common IEEE-488.2 commands --------------------------------------

    def idn(self):
        """Identification string, whitespace stripped."""
        return self.query('*IDN?').strip()

    def reset(self):
        """``*RST`` — return the instrument to its factory defaults."""
        self.write('*RST')

    def clear_status(self):
        self.write('*CLS')

    def wait_for_complete(self):
        """Block until the instrument finishes pending operations."""
        self.query('*OPC?')

    def ping(self):
        """Return ``(ok, detail)`` — ``detail`` is the IDN string or the error."""
        try:
            return True, self.idn()
        except Exception as exc:  # noqa: BLE001 — any VISA/USB failure means "down"
            return False, str(exc)

"""Power supply models.

All three share the :class:`~bench.categories.PowerSupply` interface — every
method takes ``channel`` as a keyword defaulting to 1 — so a call site works
unchanged whichever supply it's pointed at. What differs per model is only
how a channel gets selected and how measurements come back.
"""

from .categories import PowerSupply


class Keithley2280S(PowerSupply):
    """Keithley 2280S-32-6, single output.

    Answers ``MEAS:VOLT?`` with a compound ``<current>A,<voltage>V,<time>s``
    string, so one query returns everything — including a timestamp the other
    supplies don't report.
    """

    ALIAS = 'keithley'
    DEFAULT_RESOURCE = 'USB0::1510::8832::4558551::0::INSTR'
    DESCRIPTION = 'Keithley 2280S-32-6'
    CHANNELS = (1,)

    def measure_all(self, channel=1):
        self.select_channel(channel)
        parts = self.query('MEAS:VOLT?').strip().split(',')
        return {
            'current_a': float(parts[0].rstrip('A')),
            'voltage_v': float(parts[1].rstrip('V')),
            'timestamp_s': float(parts[2].rstrip('s')),
        }

    # -- protection (this model only) ----------------------------------------

    def set_ovp(self, volts):
        """Over-voltage protection threshold."""
        self.write(f'VOLT:PROT {volts}')

    def set_ocp(self, amps):
        """Over-current protection threshold."""
        self.write(f'CURR:PROT {amps}')


class KeysightEDU36311A(PowerSupply):
    """Keysight EDU36311A, 3 outputs, selected with ``INST:NSEL``."""

    ALIAS = 'keysight'
    DEFAULT_RESOURCE = 'USB0::10893::36609::CN64160195::0::INSTR'
    DESCRIPTION = 'Keysight EDU36311A (3 channels)'
    CHANNELS = (1, 2, 3)

    def select_channel(self, channel=1):
        self.check_channel(channel)
        self.write(f'INST:NSEL {channel}')

    def measure_all(self, channel=1):
        self.select_channel(channel)
        return {
            'current_a': self.query_float('MEAS:CURR?'),
            'voltage_v': self.query_float('MEAS:VOLT?'),
        }


class SiglentSPD3000(PowerSupply):
    """Siglent SPD3000-series, 3 outputs, selected with ``INST:SEL OUTn``.

    Measurements come back from a single compound ``MEAS:CURR?;VOLT?`` query,
    and the current limit is spelled ``CURRENT`` rather than ``CURR``.
    """

    ALIAS = 'spd'
    DEFAULT_RESOURCE = 'USB0::1155::30016::SPD3XHCD3R4649::0::INSTR'
    DESCRIPTION = 'Siglent SPD3000 (3 channels)'
    CHANNELS = (1, 2, 3)
    CURRENT_CMD = 'CURRENT'

    def select_channel(self, channel=1):
        self.check_channel(channel)
        self.write(f'INST:SEL OUT{channel}')

    def measure_all(self, channel=1):
        self.select_channel(channel)
        current_str, voltage_str = self.query('MEAS:CURR?;VOLT?').split(';')
        return {
            'current_a': float(current_str),
            'voltage_v': float(voltage_str),
        }

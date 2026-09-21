"""Oscilloscope models."""

import numpy as np

from .categories import Scope


def _scalar(raw, unit_chars):
    """Parse a Siglent reply like ``C4:PAVA FREQ,5.00E+02Hz`` into a float.

    Returns ``None`` when the scope reports no valid measurement (it answers
    with ``****`` if the signal doesn't support the measurement).
    """
    value = raw.split(',')[-1].strip().rstrip(unit_chars)
    if '*' in value:
        return None
    return float(value)


def _setting(raw, unit_chars):
    """Parse a settings reply like ``C4:VDIV 5.00E-01V`` into a float."""
    return float(raw.split(' ')[-1].strip().rstrip(unit_chars))


def parse_sample_rate(raw):
    """Parse a ``SARA?`` reply (``SARA 1.00GSa/s``) into samples per second."""
    value = raw.split(' ')[-1].strip().replace('Sa/s', '').strip()
    multipliers = {'G': 1e9, 'M': 1e6, 'k': 1e3, 'K': 1e3}
    if value and value[-1] in multipliers:
        return float(value[:-1]) * multipliers[value[-1]]
    return float(value)


class SiglentSDS1104XE(Scope):
    """Siglent SDS1104X-E, 4 analog channels."""

    ALIAS = 'sds1104x'
    DEFAULT_RESOURCE = 'TCPIP::172.24.58.184::INSTR'
    DESCRIPTION = 'Siglent SDS1104X-E'
    CHANNELS = (1, 2, 3, 4)

    #: Default cap on samples returned by :meth:`get_waveform`. A full
    #: capture is up to 14 M samples; as float64 that is ~112 MB per array,
    #: and the scaling arithmetic needs several at once. On a board with
    #: ~400 MB free that exhausts memory and the OOM killer starts taking
    #: processes — including your SSH session. Decimating the int8 data
    #: first keeps a full-span capture under a megabyte.
    MAX_POINTS = 200_000

    # -- acquisition control ---------------------------------------------

    def autoset(self):
        self.write('ASET')

    def run(self):
        self.write('RUN')

    def stop(self):
        self.write('STOP')

    # -- vertical / horizontal -------------------------------------------

    def enable_channel(self, channel, on=True):
        self.write(f'C{channel}:TRA {"ON" if on else "OFF"}')

    def set_vertical_scale(self, channel, volts_per_div):
        """e.g. ``set_vertical_scale(1, 0.5)`` -> 500 mV/div on channel 1."""
        self.write(f'C{channel}:VDIV {volts_per_div}')

    def get_vertical_scale(self, channel):
        return _setting(self.query(f'C{channel}:VDIV?'), 'V')

    def set_vertical_offset(self, channel, offset_volts):
        self.write(f'C{channel}:OFST {offset_volts}')

    def get_vertical_offset(self, channel):
        return _setting(self.query(f'C{channel}:OFST?'), 'V')

    def set_timebase(self, sec_per_div):
        """e.g. ``set_timebase(1e-3)`` -> 1 ms/div."""
        self.write(f'TDIV {sec_per_div}')

    def sample_rate(self):
        """Current acquisition sample rate, in samples per second."""
        return parse_sample_rate(self.query('SARA?'))

    # -- trigger -----------------------------------------------------------

    def set_trigger_source(self, channel):
        self.write(f'TRSE EDGE,SR,C{channel},HT,OFF')

    def set_trigger_level(self, channel, level_volts):
        self.write(f'C{channel}:TRLV {level_volts}')

    # -- scalar measurements ------------------------------------------------

    def measure_freq(self, channel=1):
        return _scalar(self.query(f'C{channel}:PAVA? FREQ'), 'Hz')

    def measure_period(self, channel=1):
        return _scalar(self.query(f'C{channel}:PAVA? PER'), 'S')

    def measure_pkpk(self, channel=1):
        return _scalar(self.query(f'C{channel}:PAVA? PKPK'), 'V')

    def measure_mean(self, channel=1):
        return _scalar(self.query(f'C{channel}:PAVA? MEAN'), 'V')

    # -- waveform capture ------------------------------------------------------

    def get_waveform(self, channel=1, points=None, max_points=None):
        """Capture a waveform, returning ``(time_s, voltage_v)`` numpy arrays.

        ``points`` truncates to the first N samples (a short window at the
        start of the capture). ``max_points`` instead keeps the whole time
        span and decimates to at most that many samples; it defaults to
        :attr:`MAX_POINTS`. Pass ``max_points=0`` for every sample.

        The decimation happens on the raw int8 data, before anything is
        expanded to float — see :attr:`MAX_POINTS` for why that matters.
        """
        raw = self.query_raw(f'C{channel}:WF? DAT2')

        # Strip the IEEE block header (#<ndigits><length>) before the payload.
        header = raw.find(b'#')
        num_digits = int(raw[header + 1:header + 2])
        data_len = int(raw[header + 2:header + 2 + num_digits])
        start = header + 2 + num_digits
        adc = np.frombuffer(raw[start:start + data_len], dtype=np.int8)

        # Trim and decimate while the data is still one byte per sample.
        if points:
            adc = adc[:points]
        limit = self.MAX_POINTS if max_points is None else max_points
        step = max(1, -(-len(adc) // limit)) if limit else 1
        adc = adc[::step]

        vdiv = self.get_vertical_scale(channel)
        offset = self.get_vertical_offset(channel)
        voltage = adc * (vdiv / 25.0) - offset

        time_axis = np.arange(len(adc)) * (step / self.sample_rate())

        return time_axis, voltage

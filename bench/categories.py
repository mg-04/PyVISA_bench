"""Category base classes: what a scope, a function generator and a supply
each promise, independent of who made them.

A category holds the behaviour that can be written once for every model —
composed measurements, readback dicts, file export. Anything that depends on
a manufacturer's SCPI dialect is left to the model class in ``scopes.py``,
``funcgens.py`` or ``supplies.py``.
"""

from .core import Instrument


class Scope(Instrument):
    """Common interface for oscilloscopes."""

    CATEGORY = 'scope'
    DEFAULT_TIMEOUT = 10000  # waveform transfers are slow

    # -- model-specific primitives ----------------------------------------

    def autoset(self):
        """Let the scope auto-adjust vertical, horizontal and trigger."""
        raise NotImplementedError

    def run(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def enable_channel(self, channel, on=True):
        raise NotImplementedError

    def set_vertical_scale(self, channel, volts_per_div):
        raise NotImplementedError

    def set_timebase(self, sec_per_div):
        raise NotImplementedError

    def measure_freq(self, channel=1):
        """Frequency in Hz, or ``None`` if the scope can't measure it."""
        raise NotImplementedError

    def measure_period(self, channel=1):
        raise NotImplementedError

    def measure_pkpk(self, channel=1):
        raise NotImplementedError

    def measure_mean(self, channel=1):
        raise NotImplementedError

    def get_waveform(self, channel=1, points=None):
        """Return ``(time_s, voltage_v)`` numpy arrays."""
        raise NotImplementedError

    # -- written once for every scope ---------------------------------------

    def measure_all(self, channel=1):
        """Every scalar measurement for one channel, as a dict."""
        return {
            'freq_hz': self.measure_freq(channel),
            'period_s': self.measure_period(channel),
            'vpp': self.measure_pkpk(channel),
            'mean_v': self.measure_mean(channel),
        }

    def save_waveform(self, channel=1, path='waveform.csv', points=None,
                      data=None):
        """Capture a waveform and write it to a two-column CSV.

        Pass ``data=(t, v)`` to write a capture you already have instead of
        pulling a fresh one off the scope.
        """
        import numpy as np

        t, v = data if data is not None else self.get_waveform(channel, points)
        np.savetxt(path, np.column_stack([t, v]),
                   delimiter=',', header='time_s,voltage_v', comments='')
        return path

    def plot_waveform(self, channel=1, path='waveform.png', points=None,
                      max_points=5000, data=None):
        """Capture a waveform and save a PNG of it. Returns ``(path, t, v)``.

        Pass ``data=(t, v)`` to plot a capture you already have instead of
        pulling a fresh one off the scope. The plot itself is decimated to
        ``max_points``, since matplotlib draws a long capture slowly and
        illegibly; the arrays returned are whatever was captured.
        """
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        t, v = data if data is not None else self.get_waveform(channel, points)
        step = max(1, len(t) // max_points) if max_points else 1

        plt.figure(figsize=(10, 4))
        plt.plot(t[::step] * 1e3, v[::step], lw=0.8)
        plt.xlabel('Time (ms)')
        plt.ylabel('Voltage (V)')
        title = f'Channel {channel} — {len(t)} points'
        plt.title(title if step == 1 else f'{title}, plotted 1 in {step}')
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(path, dpi=90)
        plt.close()
        return path, t, v


class FunctionGenerator(Instrument):
    """Common interface for function / waveform generators."""

    CATEGORY = 'funcgen'

    # -- model-specific primitives ----------------------------------------

    def output_on(self):
        raise NotImplementedError

    def output_off(self):
        raise NotImplementedError

    def output_state(self):
        raise NotImplementedError

    def set_sine(self, freq_hz, amplitude_vpp=1.0, offset_v=0.0):
        raise NotImplementedError

    def set_square(self, freq_hz, amplitude_vpp=1.0, offset_v=0.0):
        raise NotImplementedError

    def set_ramp(self, freq_hz, amplitude_vpp=1.0, offset_v=0.0):
        raise NotImplementedError

    def set_pulse(self, freq_hz, amplitude_vpp=1.0, offset_v=0.0):
        raise NotImplementedError

    def set_frequency(self, freq_hz):
        raise NotImplementedError

    def set_amplitude(self, vpp):
        raise NotImplementedError

    def set_offset(self, volts):
        raise NotImplementedError

    def get_frequency(self):
        raise NotImplementedError

    def get_amplitude(self):
        raise NotImplementedError

    def get_offset(self):
        raise NotImplementedError

    def get_waveform(self):
        raise NotImplementedError

    # -- written once for every generator -----------------------------------

    def settings(self):
        """Everything currently configured, as a dict."""
        return {
            'waveform': self.get_waveform(),
            'freq_hz': self.get_frequency(),
            'amplitude_vpp': self.get_amplitude(),
            'offset_v': self.get_offset(),
            'output_on': self.output_state(),
        }


class PowerSupply(Instrument):
    """Common interface for power supplies, single- or multi-output.

    Every method takes ``channel`` as a keyword defaulting to 1, so the same
    call works on a one-output Keithley and a three-output Keysight::

        supply.set_voltage(3.3)
        supply.set_voltage(3.3, channel=2)

    Asking a single-output supply for channel 2 raises ``ValueError`` rather
    than silently programming channel 1.

    Most of the SCPI here (``VOLT``, ``CURR``, ``OUTP``) is identical across
    all three supplies on this bench; models override only the bits that
    differ — how a channel is selected, and how measurements come back.
    """

    CATEGORY = 'supply'
    CHANNELS = (1,)
    CURRENT_CMD = 'CURR'  # the SPD3000 spells this 'CURRENT'

    # -- channel handling ----------------------------------------------------

    def check_channel(self, channel):
        """Raise ``ValueError`` if this supply has no such output."""
        if channel not in self.CHANNELS:
            if len(self.CHANNELS) == 1:
                raise ValueError(
                    f'{type(self).__name__} has one output (channel 1), got {channel!r}'
                )
            raise ValueError(
                f'{type(self).__name__} has channels '
                f'{", ".join(str(c) for c in self.CHANNELS)}, got {channel!r}'
            )
        return channel

    def select_channel(self, channel=1):
        """Make ``channel`` the active output. Validates; no-op if single-output."""
        self.check_channel(channel)

    # -- output control -------------------------------------------------------

    def output_on(self, channel=1):
        self.select_channel(channel)
        self.write('OUTP ON')

    def output_off(self, channel=1):
        self.select_channel(channel)
        self.write('OUTP OFF')

    def output_state(self, channel=1):
        self.select_channel(channel)
        return bool(int(self.query('OUTP?')))

    def all_off(self):
        """Turn every output off."""
        for channel in self.CHANNELS:
            self.output_off(channel)

    # -- setpoints -------------------------------------------------------------

    def set_voltage(self, volts, channel=1):
        self.select_channel(channel)
        self.write(f'VOLT {volts}')

    def set_current_limit(self, amps, channel=1):
        self.select_channel(channel)
        self.write(f'{self.CURRENT_CMD} {amps}')

    def get_voltage_setpoint(self, channel=1):
        self.select_channel(channel)
        return self.query_float('VOLT?')

    def get_current_limit(self, channel=1):
        self.select_channel(channel)
        return self.query_float(f'{self.CURRENT_CMD}?')

    def configure(self, volts, current_limit, channel=1):
        """Set a channel's voltage and current limit with the output off."""
        self.output_off(channel)
        self.set_current_limit(current_limit, channel)
        self.set_voltage(volts, channel)

    # -- measurements -----------------------------------------------------------

    def measure_all(self, channel=1):
        """Actual output as a dict: ``voltage_v``, ``current_a``.

        Models whose hardware reports more (the Keithley's timestamp) add keys.
        """
        raise NotImplementedError

    def measure_voltage(self, channel=1):
        return self.measure_all(channel)['voltage_v']

    def measure_current(self, channel=1):
        return self.measure_all(channel)['current_a']

"""One interface to every instrument on the bench, grouped by what it is.

Instruments are addressed as ``<category>.<model>`` — the category says what
kind of thing it is, the model says which machine::

    from bench import Bench

    with Bench() as b:
        b.funcgen.agilent.set_sine(500, amplitude_vpp=2.0)
        b.funcgen.agilent.output_on()

        print(b.scope.sds1104x.measure_all(4))
        b.supply.keysight.set_voltage(3.3, channel=1)

Every model in a category shares one interface, so swapping machines doesn't
mean rewriting call sites::

    for name in b.supply:              # 'keithley', 'keysight', 'spd'
        print(name, b.supply[name].measure_voltage())

Nothing touches the bus until you call a method on a model, so building a
``Bench`` is free. Drivers also work standalone::

    from bench import SiglentSDS1104XE
    with SiglentSDS1104XE() as scope:
        t, v = scope.get_waveform(4)

Run ``python -m bench --help`` for the command line equivalent.
"""

from .categories import FunctionGenerator, PowerSupply, Scope
from .core import Instrument, list_resources, resource_manager
from .discovery import discover, scan
from .funcgens import Agilent33220A
from .scopes import SiglentSDS1104XE
from .supplies import Keithley2280S, KeysightEDU36311A, SiglentSPD3000

__all__ = [
    'Bench',
    'Category',
    'REGISTRY',
    'Instrument',
    'Scope',
    'FunctionGenerator',
    'PowerSupply',
    'SiglentSDS1104XE',
    'Agilent33220A',
    'Keithley2280S',
    'KeysightEDU36311A',
    'SiglentSPD3000',
    'discover',
    'scan',
    'list_resources',
    'resource_manager',
    'open_instrument',
    'models',
]


#: ``category -> model -> (driver class, resource string)``. Adding a line
#: here is all it takes for a new instrument to show up in :class:`Bench`
#: and on the command line.
REGISTRY = {
    'scope': {
        'sds1104x': (SiglentSDS1104XE, SiglentSDS1104XE.DEFAULT_RESOURCE),
        'sds1104x_usb': (SiglentSDS1104XE,
                         'USB0::62700::60984::SDSMMEBQ4R5170::0::INSTR'),
    },
    'funcgen': {
        'agilent': (Agilent33220A, Agilent33220A.DEFAULT_RESOURCE),
    },
    'supply': {
        'keithley': (Keithley2280S, Keithley2280S.DEFAULT_RESOURCE),
        'keysight': (KeysightEDU36311A, KeysightEDU36311A.DEFAULT_RESOURCE),
        'spd': (SiglentSPD3000, SiglentSPD3000.DEFAULT_RESOURCE),
    },
}


def models():
    """Every instrument as a sorted list of ``'category.model'`` names."""
    return sorted(f'{c}.{m}' for c, entries in REGISTRY.items() for m in entries)


def split_name(name):
    """Split ``'supply.keithley'`` into ``('supply', 'keithley')``, validating both."""
    category, _, model = name.partition('.')
    if category not in REGISTRY:
        raise KeyError(
            f"unknown category '{category}' — known: {', '.join(sorted(REGISTRY))}"
        )
    if model not in REGISTRY[category]:
        known = ', '.join(f'{category}.{m}' for m in sorted(REGISTRY[category]))
        raise KeyError(f"unknown instrument '{name}' — known: {known}")
    return category, model


def open_instrument(name, resource=None, timeout=None):
    """Build the driver named ``'<category>.<model>'`` (not yet connected)."""
    category, model = split_name(name)
    cls, default_resource = REGISTRY[category][model]
    return cls(resource=resource or default_resource, timeout=timeout)


class Category:
    """The instruments of one kind — ``b.supply``, ``b.scope``, ``b.funcgen``.

    Reach a model by attribute (``b.supply.keithley``) or by key
    (``b.supply['keithley']``); iterate to get the model names. Each model is
    built once and cached, and connects only when you call something on it.
    """

    def __init__(self, name, resources=None):
        self.name = name
        self._resources = resources or {}
        self._cache = {}

    # -- access ------------------------------------------------------------

    def __getattr__(self, model):
        if model.startswith('_'):
            raise AttributeError(model)
        try:
            return self[model]
        except KeyError as exc:
            raise AttributeError(str(exc)) from None

    def __getitem__(self, model):
        if model not in REGISTRY[self.name]:
            known = ', '.join(sorted(REGISTRY[self.name]))
            raise KeyError(
                f"no {self.name} model '{model}' — known: {known}"
            )
        if model not in self._cache:
            full_name = f'{self.name}.{model}'
            self._cache[model] = open_instrument(
                full_name, self._resources.get(full_name)
            )
        return self._cache[model]

    def __iter__(self):
        return iter(sorted(REGISTRY[self.name]))

    def __len__(self):
        return len(REGISTRY[self.name])

    def __contains__(self, model):
        return model in REGISTRY[self.name]

    def __dir__(self):
        return sorted(set(super().__dir__()) | set(REGISTRY[self.name]))

    # -- lifecycle -----------------------------------------------------------

    @property
    def opened(self):
        """Models in this category holding an open VISA session."""
        return sorted(m for m, i in self._cache.items() if i.is_open)

    def close(self):
        for instrument in self._cache.values():
            try:
                instrument.close()
            except Exception:  # noqa: BLE001 — closing must never raise
                pass
        self._cache.clear()

    def __repr__(self):
        return f'<Category {self.name}: {", ".join(self)}>'


class Bench:
    """Every instrument, grouped by category.

    ``Bench().supply.keithley`` builds (and caches) that driver on first
    touch; closing the bench closes whatever was opened.

    Pass ``resources`` to point a name somewhere else::

        Bench(resources={'scope.sds1104x': 'TCPIP::172.24.58.99::INSTR'})
    """

    def __init__(self, resources=None):
        resources = resources or {}
        for name in resources:
            split_name(name)  # fail loudly on a typo'd override
        self._categories = {
            category: Category(category, resources) for category in REGISTRY
        }

    def __getattr__(self, name):
        categories = self.__dict__.get('_categories', {})
        if name in categories:
            return categories[name]
        raise AttributeError(
            f"{type(self).__name__} has no category '{name}' — "
            f"known: {', '.join(sorted(REGISTRY))}"
        )

    def __getitem__(self, name):
        """``b['supply.keithley']`` — the dotted name, as the CLI uses it."""
        category, model = split_name(name)
        return self._categories[category][model]

    def __iter__(self):
        return iter(sorted(self._categories))

    def __dir__(self):
        return sorted(set(super().__dir__()) | set(REGISTRY))

    @property
    def opened(self):
        """Dotted names of every instrument currently connected."""
        return sorted(
            f'{name}.{model}'
            for name, category in self._categories.items()
            for model in category.opened
        )

    def close(self):
        """Close every instrument this bench opened."""
        for category in self._categories.values():
            category.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    def __repr__(self):
        return f'<Bench opened={self.opened or "none"}>'

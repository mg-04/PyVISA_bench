"""Find out what's actually plugged in — the old ``diagnose.py``, tidied up."""

from .core import list_resources, resource_manager


def scan(timeout=3000):
    """Query ``*IDN?`` on every visible VISA resource.

    Returns a list of ``(resource, idn_or_none, error_or_none)`` tuples, so a
    silent instrument still shows up with the reason it didn't answer.
    """
    results = []
    rm = resource_manager()
    for resource in list_resources():
        try:
            inst = rm.open_resource(resource)
            inst.timeout = timeout
            try:
                results.append((resource, inst.query('*IDN?').strip(), None))
            finally:
                inst.close()
        except Exception as exc:  # noqa: BLE001 — report, don't abort the scan
            results.append((resource, None, str(exc)))
    return results


def discover(timeout=3000):
    """Print a scan of the bus. Returns the same list as :func:`scan`."""
    results = scan(timeout)
    if not results:
        print('No VISA resources found.')
        print('If an instrument is plugged in, check the udev rules — see README.md.')
        return results

    for resource, idn, error in results:
        print(f'{resource}\n    {idn if idn else f"ERROR: {error}"}')
    return results

"""Command line front end: ``python -m bench <command>``.

Instruments are named ``<category>.<model>``, e.g. ``supply.keithley``.
"""

import argparse
import ast
import inspect
import sys

from . import REGISTRY, models, open_instrument, split_name
from .discovery import discover


def _parse_arg(text):
    """Turn a CLI token into a Python value (``4`` -> int, ``on`` -> str)."""
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return text


def _split_args(tokens):
    """Split ``['3.3', 'channel=2']`` into positional args and keyword args."""
    args, kwargs = [], {}
    for token in tokens:
        name, sep, value = token.partition('=')
        if sep and name.isidentifier():
            kwargs[name] = _parse_arg(value)
        else:
            args.append(_parse_arg(token))
    return args, kwargs


def cmd_list(_args):
    """Show every instrument, grouped by category."""
    width = max(len(name) for name in models())
    for category in sorted(REGISTRY):
        print(f'{category}:')
        for model in sorted(REGISTRY[category]):
            cls, resource = REGISTRY[category][model]
            print(f'  {category + "." + model:<{width}}  {cls.DESCRIPTION}')
            print(f'  {"":<{width}}  {resource}')
    return 0


def cmd_scan(args):
    """Query *IDN? on everything the VISA backend can see."""
    discover(timeout=args.timeout)
    return 0


def cmd_check(args):
    """Ping instruments and report which ones answer."""
    names = args.names or models()
    failed = 0
    for name in names:
        instrument = open_instrument(name, timeout=args.timeout)
        ok, detail = instrument.ping()
        instrument.close()
        print(f'{"PASS" if ok else "FAIL"}  {name:<20} {detail}')
        failed += 0 if ok else 1
    return 1 if failed else 0


def cmd_methods(args):
    """List the methods available on one instrument."""
    category, model = split_name(args.name)
    cls = REGISTRY[category][model][0]
    for method_name, func in inspect.getmembers(cls, inspect.isfunction):
        if method_name.startswith('_'):
            continue
        signature = str(inspect.signature(func)).replace('self, ', '').replace('self', '')
        doc = (inspect.getdoc(func) or '').split('\n')[0]
        print(f'{method_name}{signature}')
        if doc:
            print(f'    {doc}')
    return 0


def cmd_call(args):
    """Call one method, e.g. ``call supply.keysight set_voltage 3.3 channel=1``."""
    instrument = open_instrument(args.name, timeout=args.timeout)
    try:
        method = getattr(instrument, args.method, None)
        if not callable(method) or args.method.startswith('_'):
            print(f"'{args.name}' has no method '{args.method}' — "
                  f'try: python -m bench methods {args.name}', file=sys.stderr)
            return 2
        call_args, call_kwargs = _split_args(args.params)
        result = method(*call_args, **call_kwargs)
        if result is not None:
            print(result)
        return 0
    finally:
        instrument.close()


def build_parser():
    parser = argparse.ArgumentParser(
        prog='python -m bench',
        description='Control the bench instruments from the command line. '
                    'Instruments are named <category>.<model>, e.g. supply.keithley.',
    )
    parser.add_argument('--timeout', type=int, default=None,
                        help='VISA timeout in ms (default: per-instrument)')
    sub = parser.add_subparsers(dest='command', required=True)

    sub.add_parser('list', help=cmd_list.__doc__).set_defaults(func=cmd_list)
    sub.add_parser('scan', help=cmd_scan.__doc__).set_defaults(func=cmd_scan)

    check = sub.add_parser('check', help=cmd_check.__doc__)
    check.add_argument('names', nargs='*', metavar='NAME',
                       help='instruments to ping (default: all)')
    check.set_defaults(func=cmd_check)

    methods = sub.add_parser('methods', help=cmd_methods.__doc__)
    methods.add_argument('name', metavar='NAME', choices=models())
    methods.set_defaults(func=cmd_methods)

    call = sub.add_parser('call', help=cmd_call.__doc__)
    call.add_argument('name', metavar='NAME', choices=models())
    call.add_argument('method')
    call.add_argument('params', nargs='*',
                      help='positional values and key=value pairs')
    call.set_defaults(func=cmd_call)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.timeout is None:
        args.timeout = 3000 if args.command in ('scan', 'check') else None
    try:
        return args.func(args)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # noqa: BLE001 — a bus failure is a CLI error, not a traceback
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1

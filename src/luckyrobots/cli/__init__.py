"""Top-level CLI for luckyrobots.

Entry point: ``luckyrobots`` (installed via pyproject.toml console_scripts).
Subcommands are registered lazily so optional dependencies are only
imported when the relevant subcommand is invoked.
"""

import click

from .inspect import inspect_main as inspect_main


@click.group()
def cli():
    """luckyrobots - Python API for LuckyEngine."""


try:
    from ..sysid.cli import sysid as _sysid_group

    cli.add_command(_sysid_group)
except ImportError:
    pass


@cli.command()
@click.argument("address")
def inspect(address: str):
    """Inspect a running LuckyEngine instance. ADDRESS is host:port."""
    host, _, port_s = address.partition(":")
    port = int(port_s) if port_s else 50051
    from .inspect import inspect_main

    raise SystemExit(inspect_main(host, port))


__all__ = ["cli", "inspect_main"]


if __name__ == "__main__":
    cli()

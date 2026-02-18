"""Top-level CLI for luckyrobots.

Entry point: ``luckyrobots`` (installed via pyproject.toml console_scripts).
Subcommands are registered lazily so optional dependencies are only
imported when the relevant subcommand is invoked.
"""

import click


@click.group()
def cli():
    """luckyrobots - Python API for LuckyEngine."""


try:
    from .sysid.cli import sysid as _sysid_group

    cli.add_command(_sysid_group)
except ImportError:
    pass


if __name__ == "__main__":
    cli()

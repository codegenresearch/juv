"""A wrapper around `uv` to launch ephemeral Jupyter notebooks."""

from __future__ import annotations

import sys
import os
from pathlib import Path
import click
import shutil

import rich


def assert_uv_available():
    if shutil.which("uv") is None:
        rich.print("Error: 'uv' command not found.", file=sys.stderr)
        rich.print("Please install 'uv' to run `juv`.", file=sys.stderr)
        rich.print(
            "For more information, visit: https://github.com/astral-sh/uv",
            file=sys.stderr,
        )
        sys.exit(1)


@click.group()
def cli():
    """A wrapper around uv to launch ephemeral Jupyter notebooks."""


@cli.command()
def version() -> None:
    """Display juv's version."""
    from ._version import __version__

    print(f"juv {__version__}")


@cli.command()
def info():
    """Display juv and uv versions."""
    from ._version import __version__ as juv_version

    import subprocess

    print(f"juv {juv_version}")
    uv_version = subprocess.run(["uv", "version"], capture_output=True, text=True)
    print(uv_version.stdout.strip())


@cli.command()
@click.argument("file", type=click.Path(exists=False), required=False)
@click.option("--python", type=click.STRING, required=False)
@click.option("--packages", "-p", type=click.STRING, multiple=True, help="Add package dependencies during initialization.")
def init(
    file: str | None,
    python: str | None,
    packages: tuple[str, ...],
) -> None:
    """Initialize a new notebook."""
    from ._init import init

    init(path=Path(file) if file else None, python=python, packages=packages)


@cli.command()
@click.argument("file", type=click.Path(exists=True), required=True)
@click.option("--requirements", "-r", type=click.Path(exists=True), required=False)
@click.argument("packages", nargs=-1)
def add(file: str, requirements: str | None, packages: tuple[str, ...]) -> None:
    """Add dependencies to the notebook."""
    from ._add import add

    add(path=Path(file), packages=packages, requirements=requirements)
    rich.print(f"Updated `[cyan]{Path(file).resolve().absolute()}[/cyan]`")


@cli.command()
@click.argument("file", type=click.Path(exists=True), required=True)
@click.option(
    "--jupyter",
    required=False,
    help="The Jupyter frontend to use. [env: JUV_JUPYTER=]",
)
@click.option("--with", "with_args", type=click.STRING, multiple=True)
@click.option("--python", type=click.STRING, required=False)
def run(
    file: str,
    jupyter: str | None,
    with_args: tuple[str, ...],
    python: str | None,
) -> None:
    """Launch a notebook or script."""

    from ._run import run

    run(
        path=Path(file),
        jupyter=jupyter,
        python=python,
        with_args=with_args,
    )


def upgrade_legacy_jupyter_command(args: list[str]) -> None:
    """Check legacy lab/notebook/nbclassic command usage and upgrade to 'run' with deprecation notice."""
    for i, arg in enumerate(args):
        if i == 0:
            continue
        if (
            arg.startswith(("lab", "notebook", "nbclassic"))
            and not args[i - 1].startswith("--")  # Make sure previous arg isn't a flag\n            and not arg.startswith("--")\n        ):\n            rich.print(\n                f"[bold]Warning:[/bold] The command '{arg}' is deprecated. "\n                f"Please use 'run' with `--jupyter={arg}` or set JUV_JUPYTER={arg}"\n            )\n            os.environ["JUV_JUPYTER"] = arg\n            args[i] = "run"\n\n\ndef main():\n    upgrade_legacy_jupyter_command(sys.argv)\n    cli()
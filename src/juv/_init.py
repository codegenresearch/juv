from __future__ import annotations

from pathlib import Path
import tempfile
import subprocess
import sys
import typing

import rich

from ._nbconvert import new_notebook, code_cell, write_ipynb


def new_notebook_with_inline_metadata(dir: Path, python: str | None = None) -> dict:
    """Create a new notebook with inline metadata.

    Parameters
    ----------
    dir : pathlib.Path
        Directory for `uv init` to run in.
    python : str, optional
        Python interpreter version to use.

    Returns
    -------
    dict
        New notebook with inline metadata.
    """
    with tempfile.NamedTemporaryFile(
        mode="w+",
        suffix=".py",
        delete=True,
        dir=dir,
    ) as f:
        cmd = ["uv", "init", "--quiet"]
        if python:
            cmd.extend(["--python", python])
        cmd.extend(["--script", f.name])

        subprocess.run(cmd)
        f.seek(0)
        contents = f.read().strip()
        notebook = new_notebook(cells=[code_cell(contents, hidden=True)])

    return notebook


def get_first_non_conflicting_untitled_ipynb(dir: Path) -> Path:
    """Find the first available UntitledX.ipynb file path in the given directory.

    Parameters
    ----------
    dir : pathlib.Path
        Directory to search for available UntitledX.ipynb files.

    Returns
    -------
    pathlib.Path
        Path to the first available UntitledX.ipynb file.

    Raises
    ------
    ValueError
        If no available UntitledX.ipynb file path is found within the first 100 attempts.
    """
    for i in range(100):
        path = dir / f"Untitled{i}.ipynb" if i else dir / "Untitled.ipynb"
        if not path.exists():
            return path

    raise ValueError("Could not find an available UntitledX.ipynb")


def init(
    path: Path | None = None,
    python: str | None = None,
    packages: typing.Sequence[str] = [],
) -> None:
    """Initialize a new notebook with optional Python version and packages.

    Parameters
    ----------
    path : pathlib.Path, optional
        Path to the notebook file to initialize.
    python : str, optional
        Python version to use for the notebook.
    packages : typing.Sequence[str], optional
        Packages to include in the notebook metadata.
    """
    if not path:
        path = get_first_non_conflicting_untitled_ipynb(Path.cwd())

    if path.suffix != ".ipynb":
        rich.print("File must have a `[cyan].ipynb[/cyan]` extension.", file=sys.stderr)
        sys.exit(1)

    notebook = new_notebook_with_inline_metadata(path.parent, python)
    write_ipynb(notebook, path)

    rich.print(f"Initialized notebook at `[cyan]{path.resolve().absolute()}[/cyan]`")

    if len(packages) > 0:
        from ._add import add
        add(path, packages, requirements=None)
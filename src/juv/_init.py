from __future__ import annotations

import sys
import typing
from pathlib import Path
import tempfile
import subprocess

import rich

from ._nbconvert import new_notebook, code_cell, write_ipynb


def new_notebook_with_inline_metadata(dir: Path, python: str | None = None) -> dict:
    """Create a new notebook with inline metadata.

    Initializes a new notebook by running `uv init` in the specified directory.
    Captures the output script and embeds it into a new Jupyter notebook with a hidden code cell.

    Parameters
    ----------
    dir : Path
        Directory where `uv init` will be executed.
    python : str, optional
        Version of the Python interpreter to use.

    Returns
    -------
    dict
        New notebook with a single code cell.
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
    """Find the first available Untitled notebook file in the specified directory.

    Parameters
    ----------
    dir : Path
        Directory to search for available Untitled notebook files.

    Returns
    -------
    Path
        Path to the first available Untitled notebook file.

    Raises
    ------
    ValueError
        If no available UntitledX.ipynb file is found.
    """
    base_path = dir / "Untitled.ipynb"
    if not base_path.exists():
        return base_path

    for i in range(1, 100):
        path = dir / f"Untitled{i}.ipynb"
        if not path.exists():
            return path

    raise ValueError("No available UntitledX.ipynb file found")


def init(
    path: Path | None = None,
    python: str | None = None,
    packages: typing.Sequence[str] = [],
) -> None:
    """Initialize a new notebook.

    Initializes a new Jupyter notebook with optional Python version and additional packages.
    If no path is provided, it creates a new file with a default name in the current working directory.

    Parameters
    ----------
    path : Path, optional
        Path to the notebook file. If not provided, a new file will be created.
    python : str, optional
        Version of the Python interpreter to use.
    packages : typing.Sequence[str], optional
        List of packages to add to the notebook.

    Raises
    ------
    SystemExit
        If the file does not have a `.ipynb` extension.
    """
    if not path:
        path = get_first_non_conflicting_untitled_ipynb(Path.cwd())

    if path.suffix != ".ipynb":
        rich.print("File must have a `[cyan].ipynb[/cyan]` extension.", file=sys.stderr)
        sys.exit(1)

    notebook = new_notebook_with_inline_metadata(path.parent, python)
    write_ipynb(notebook, path)

    if packages:
        from ._add import add
        add(path=path, packages=packages, requirements=None)

    rich.print(f"Initialized notebook at `[cyan]{path.resolve().absolute()}[/cyan]`")
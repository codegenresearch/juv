import pytest
from pathlib import Path
from unittest.mock import patch
import pathlib
import re
import os
from inline_snapshot import snapshot

import jupytext
from nbformat.v4.nbbase import new_code_cell, new_notebook

from click.testing import CliRunner, Result

from juv import cli, assert_uv_available
from juv._nbconvert import write_ipynb
from juv._pep723 import parse_inline_script_metadata
from juv._run import to_notebook, prepare_uvx_args, Runtime, Pep723Meta


def invoke(args: list[str], uv_python: str = "3.13") -> Result:
    return CliRunner().invoke(
        cli,
        args,
        env={**os.environ, "UV_PYTHON": uv_python},
    )


@pytest.fixture
def sample_script() -> str:
    return """
# /// script
# dependencies = ["numpy", "pandas"]
# requires-python = ">=3.8"
# ///

import numpy as np
import pandas as pd

print('Hello, world!')
"""


@pytest.fixture
def sample_notebook() -> dict:
    return {
        "cells": [
            {
                "cell_type": "code",
                "source": "# /// script\n# dependencies = [\"pandas\"]\n# ///\n\nimport pandas as pd\nprint('Hello, pandas!')",
            }
        ],
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def test_parse_pep723_meta(sample_script: str) -> None:
    meta = parse_inline_script_metadata(sample_script)
    assert meta == snapshot("""\
dependencies = ["numpy", "pandas"]
requires-python = ">=3.8"
""")


def test_parse_pep723_meta_no_meta() -> None:
    script_without_meta = "print('Hello, world!')"
    assert parse_inline_script_metadata(script_without_meta) is None


def filter_ids(output: str) -> str:
    return re.sub(r'"id": "[a-zA-Z0-9-]+"', '"id": "<ID>"', output)


def test_to_notebook_script(tmp_path: pathlib.Path):
    script = tmp_path / "script.py"
    script.write_text("""# /// script
# dependencies = ["numpy"]
# requires-python = ">=3.8"
# ///


import numpy as np

# %%
print('Hello, numpy!')
arr = np.array([1, 2, 3])""")

    meta, nb = to_notebook(script)
    output = jupytext.writes(nb, fmt="ipynb")
    output = filter_ids(output)

    assert (meta, output) == snapshot(
        (
            """\
dependencies = ["numpy"]
requires-python = ">=3.8"
""",
            """\
{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "<ID>",
   "metadata": {
    "jupyter": {
     "source_hidden": true
    }
   },
   "outputs": [],
   "source": [
    "# /// script\\n",
    "# dependencies = [\\"numpy\\"]\\n",
    "# requires-python = \\">=3.8\\"\\n",
    "# ///"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "<ID>",
   "metadata": {},
   "outputs": [],
   "source": [
    "import numpy as np"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "<ID>",
   "metadata": {},
   "outputs": [],
   "source": [
    "print('Hello, numpy!')\\n",
    "arr = np.array([1, 2, 3])"
   ]
  }
 ],
 "metadata": {
  "jupytext": {
   "cell_metadata_filter": "-all",
   "main_language": "python",
   "notebook_metadata_filter": "-all"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}\
""",
        )
    )


def test_assert_uv_available() -> None:
    with patch("shutil.which", return_value=None):
        with pytest.raises(SystemExit):
            assert_uv_available()


def test_python_override() -> None:
    assert prepare_uvx_args(
        target=Path("test.ipynb"),
        runtime=Runtime("nbclassic", None),
        pep723_meta=Pep723Meta(dependencies=["numpy"], requires_python="3.8"),
        with_args=["polars"],
        python="3.12",
    ) == snapshot(
        [
            "--from=jupyter-core",
            "--with=setuptools",
            "--with",
            "polars",
            "--python",
            "3.12",
            "--with=numpy",
            "--with=nbclassic",
            "jupyter",
            "nbclassic",
            "test.ipynb",
        ]
    )


def test_run_nbclassic() -> None:
    assert prepare_uvx_args(
        target=Path("test.ipynb"),
        runtime=Runtime("nbclassic", None),
        pep723_meta=Pep723Meta(dependencies=["numpy"], requires_python="3.8"),
        python=None,
        with_args=["polars"],
    ) == snapshot(
        [
            "--from=jupyter-core",
            "--with=setuptools",
            "--with",
            "polars",
            "--python=3.8",
            "--with=numpy",
            "--with=nbclassic",
            "jupyter",
            "nbclassic",
            "test.ipynb",
        ]
    )


def test_run_notebook() -> None:
    assert prepare_uvx_args(
        target=Path("test.ipynb"),
        runtime=Runtime("notebook", "6.4.0"),
        pep723_meta=Pep723Meta(dependencies=[], requires_python=None),
        with_args=[],
        python=None,
    ) == snapshot(
        [
            "--from=jupyter-core",
            "--with=setuptools",
            "--with=notebook==6.4.0",
            "jupyter",
            "notebook",
            "test.ipynb",
        ]
    )


def test_run_jlab() -> None:
    assert prepare_uvx_args(
        target=Path("test.ipynb"),
        runtime=Runtime("lab", None),
        pep723_meta=Pep723Meta(dependencies=["numpy"], requires_python="3.8"),
        python=None,
        with_args=["polars,altair"],
    ) == snapshot(
        [
            "--from=jupyter-core",
            "--with=setuptools",
            "--with",
            "polars,altair",
            "--python=3.8",
            "--with=numpy",
            "--with=jupyterlab",
            "jupyter",
            "lab",
            "test.ipynb",
        ]
    )


def filter_tempfile_ipynb(output: str) -> str:
    """Replace the temporary directory in the output with <TEMPDIR> for snapshotting."""
    pattern = r"`([^`\n]+\n?[^`\n]+/)([^/\n]+\.ipynb)`"
    replacement = r"`<TEMPDIR>/\2`"
    return re.sub(pattern, replacement, output)


def test_add_creates_inline_meta(tmp_path: pathlib.Path) -> None:
    nb = tmp_path / "foo.ipynb"
    write_ipynb(new_notebook(), nb)
    result = invoke(["add", str(nb), "polars==1", "anywidget"], uv_python="3.11")
    assert result.exit_code == 0
    assert filter_tempfile_ipynb(result.stdout) == snapshot("""\
Updated 
`<TEMPDIR>/foo.ipynb`
""")
    assert filter_ids(nb.read_text()) == snapshot("""\
{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "<ID>",
   "metadata": {
    "jupyter": {
     "source_hidden": true
    }
   },
   "outputs": [],
   "source": [
    "# /// script\\n",
    "# requires-python = \\">=3.11\\"\\n",
    "# dependencies = [\\n",
    "#     \\"anywidget\\",\\n",
    "#     \\"polars==1\\",\\n",
    "# ]\\n",
    "# ///"
   ]
  }
 ],
 "metadata": {},
 "nbformat": 4,
 "nbformat_minor": 5
}\
""")


def test_add_prepends_script_meta(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "empty.ipynb"
    write_ipynb(
        new_notebook(cells=[new_code_cell("print('Hello, world!')")]),
        path,
    )
    result = invoke(["add", str(path), "polars==1", "anywidget"], uv_python="3.10")
    assert result.exit_code == 0
    assert filter_tempfile_ipynb(result.stdout) == snapshot("""\
Updated 
`<TEMPDIR>/empty.ipynb`
""")
    assert filter_ids(path.read_text()) == snapshot("""\
{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "<ID>",
   "metadata": {
    "jupyter": {
     "source_hidden": true
    }
   },
   "outputs": [],
   "source": [
    "# /// script\\n",
    "# requires-python = \\">=3.10\\"\\n",
    "# dependencies = [\\n",
    "#     \\"anywidget\\",\\n",
    "#     \\"polars==1\\",\\n",
    "# ]\\n",
    "# ///"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "<ID>",
   "metadata": {},
   "outputs": [],
   "source": [
    "print('Hello, world!')"
   ]
  }
 ],
 "metadata": {},
 "nbformat": 4,
 "nbformat_minor": 5
}\
""")


def test_add_updates_existing_meta(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "empty.ipynb"
    nb = new_notebook(
        cells=[
            new_code_cell("""# /// script
# dependencies = ["numpy"]
# requires-python = ">=3.8"
# ///
import numpy as np
print('Hello, numpy!')"""),
        ]
    )
    write_ipynb(nb, path)
    result = invoke(["add", str(path), "polars==1", "anywidget"], uv_python="3.13")
    assert result.exit_code == 0
    assert filter_tempfile_ipynb(result.stdout) == snapshot("""\
Updated 
`<TEMPDIR>/empty.ipynb`
""")
    assert filter_ids(path.read_text()) == snapshot("""\
{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "<ID>",
   "metadata": {},
   "outputs": [],
   "source": [
    "# /// script\\n",
    "# dependencies = [\\n",
    "#     \\"anywidget\\",\\n",
    "#     \\"numpy\\",\\n",
    "#     \\"polars==1\\",\\n",
    "# ]\\n",
    "# requires-python = \\">=3.8\\"\\n",
    "# ///\\n",
    "import numpy as np\\n",
    "print('Hello, numpy!')"
   ]
  }
 ],
 "metadata": {},
 "nbformat": 4,
 "nbformat_minor": 5
}\
""")


def test_init_creates_notebook_with_inline_meta(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "empty.ipynb"
    result = invoke(["init", str(path)], uv_python="3.13")
    assert result.exit_code == 0
    assert filter_tempfile_ipynb(result.stdout) == snapshot("""\
Initialized notebook at 
`<TEMPDIR>/empty.ipynb`
""")
    assert filter_ids(path.read_text()) == snapshot("""\
{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "<ID>",
   "metadata": {
    "jupyter": {
     "source_hidden": true
    }
   },
   "outputs": [],
   "source": [
    "# /// script\\n",
    "# requires-python = \\">=3.13\\"\\n",
    "# dependencies = []\\n",
    "# ///"
   ]
  }
 ],
 "metadata": {},
 "nbformat": 4,
 "nbformat_minor": 5
}\
""")


def test_init_creates_notebook_with_specific_python_version(
    tmp_path: pathlib.Path,
) -> None:
    path = tmp_path / "empty.ipynb"
    result = invoke(["init", str(path), "--python=3.8"])
    assert result.exit_code == 0
    assert filter_tempfile_ipynb(result.stdout) == snapshot("""\
Initialized notebook at 
`<TEMPDIR>/empty.ipynb`
""")
    assert filter_ids(path.read_text()) == snapshot("""\
{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "<ID>",
   "metadata": {
    "jupyter": {
     "source_hidden": true
    }
   },
   "outputs": [],
   "source": [
    "# /// script\\n",
    "# requires-python = \\">=3.8\\"\\n",
    "# dependencies = []\\n",
    "# ///"
   ]
  }
 ],
 "metadata": {},
 "nbformat": 4,
 "nbformat_minor": 5
}\
""")


def test_init_with_deps(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    result = invoke(
        [
            "init",
            "--with",
            "rich,requests",
            "--with=polars==1",
            "--with=anywidget[dev]",
            "--with=numpy,pandas>=2",
        ]
    )
    print(result.stdout)
    assert result.exit_code == 0
    assert filter_tempfile_ipynb(result.stdout) == snapshot("""\
Initialized notebook at 
`<TEMPDIR>/Untitled.ipynb`
""")

    path = tmp_path / "Untitled.ipynb"
    assert filter_ids(path.read_text()) == snapshot("""\
{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "<ID>",
   "metadata": {
    "jupyter": {
     "source_hidden": true
    }
   },
   "outputs": [],
   "source": [
    "# /// script\\n",
    "# requires-python = \\">=3.13\\"\\n",
    "# dependencies = [\\n",
    "#     \\"anywidget[dev]\\",\\n",
    "#     \\"numpy\\",\\n",
    "#     \\"pandas>=2\\",\\n",
    "#     \\"polars==1\\",\\n",
    "#     \\"requests\\",\\n",
    "#     \\"rich\\",\\n",
    "# ]\\n",
    "# ///"
   ]
  }
 ],
 "metadata": {},
 "nbformat": 4,
 "nbformat_minor": 5
}\
""")

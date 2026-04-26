"""Build shim — injects open-image-skill.pth into the wheel's purelib root.

Why: pyproject.toml + setuptools data_files maps to the wheel's `data`
scheme (which lands in <prefix>/, NOT site-packages). For Python's site
initialization to pick up a .pth file, it must live in site-packages
itself. The cleanest portable way to ship a .pth into purelib via wheel
is to have build_py copy it into build/lib/, where setuptools then packs
it at the wheel root (= purelib on install).
"""

import os
import shutil

from setuptools import setup
from setuptools.command.build_py import build_py


class _BuildPyWithPth(build_py):
    """Copy open-image-skill.pth into build/lib/ so it lands in site-packages."""

    PTH_FILENAME = "open-image-skill.pth"

    def run(self):
        super().run()
        src = os.path.join(os.path.dirname(__file__) or ".", self.PTH_FILENAME)
        if os.path.exists(src):
            os.makedirs(self.build_lib, exist_ok=True)
            shutil.copy(src, os.path.join(self.build_lib, self.PTH_FILENAME))


setup(cmdclass={"build_py": _BuildPyWithPth})

# Copyright (c) 2024
#
# This file is part of OCEAN.
#
# OCEAN is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OCEAN is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with OCEAN.  If not, see <https://www.gnu.org/licenses/>.

"""The version of OCEAN shown in the user interface.

The version is the git tag of the release; it is never written in the code. When deploying, the
GitLab pipeline writes it to `OCEAN_VERSION` in `.env` (the tag for production, the commit for
the test server), because the servers have no git history. Elsewhere (running locally, docker)
it is read from git, and is `dev` if git is not available.
"""

# Standard library imports
import os
import subprocess

REPOSITORY_DIRECTORY = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# The value in .env_template, left in place if the deploy did not fill it in
PLACEHOLDER = "YOUR_VERSION"


def get_version() -> str:
    """The OCEAN version: `OCEAN_VERSION`, otherwise `git describe`, otherwise `dev`."""
    version = os.environ.get("OCEAN_VERSION", "").strip()
    if version and version != PLACEHOLDER:
        return version
    try:
        result = subprocess.run(["git", "describe", "--tags", "--always"], cwd=REPOSITORY_DIRECTORY,
                                capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "dev"

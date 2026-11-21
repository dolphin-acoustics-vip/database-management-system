import subprocess
from unittest.mock import patch

from ..app import version


def test_version_from_environment(monkeypatch):
    monkeypatch.setenv("OCEAN_VERSION", "v1.3.0")
    assert version.get_version() == "v1.3.0"


def test_version_placeholder_is_ignored(monkeypatch):
    monkeypatch.setenv("OCEAN_VERSION", version.PLACEHOLDER)
    with patch.object(subprocess, "run", side_effect=OSError):
        assert version.get_version() == "dev"


def test_version_from_git(monkeypatch):
    monkeypatch.delenv("OCEAN_VERSION", raising=False)
    result = subprocess.CompletedProcess([], 0, stdout="v1.2.1-2-g1677717\n")
    with patch.object(subprocess, "run", return_value=result):
        assert version.get_version() == "v1.2.1-2-g1677717"


def test_version_without_git(monkeypatch):
    monkeypatch.delenv("OCEAN_VERSION", raising=False)
    with patch.object(subprocess, "run", side_effect=OSError):
        assert version.get_version() == "dev"


def test_version_when_git_fails(monkeypatch):
    monkeypatch.delenv("OCEAN_VERSION", raising=False)
    result = subprocess.CompletedProcess([], 128, stdout="", stderr="fatal: not a git repository")
    with patch.object(subprocess, "run", return_value=result):
        assert version.get_version() == "dev"

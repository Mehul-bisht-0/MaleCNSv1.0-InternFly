from pathlib import Path

from internfly.config import _default_auto_start, _default_database_path


def test_local_defaults(monkeypatch) -> None:
    monkeypatch.delenv("VERCEL", raising=False)

    assert _default_database_path() == "internfly.db"
    assert _default_auto_start() is True


def test_vercel_defaults_use_writable_temporary_storage(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL", "1")

    assert Path(_default_database_path()).parent != Path.cwd()
    assert Path(_default_database_path()).name == "internfly.db"
    assert _default_auto_start() is False

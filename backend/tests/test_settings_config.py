import os
import subprocess
import sys
from pathlib import Path

from config.config import csv, database_from_url


def test_csv_parses_comma_separated_values():
    assert csv("localhost, 127.0.0.1,,example.com") == [
        "localhost",
        "127.0.0.1",
        "example.com",
    ]


def test_csv_accepts_list_values():
    assert csv(["localhost", " example.com "]) == ["localhost", "example.com"]


def test_database_from_url_defaults_to_project_sqlite(tmp_path):
    database = database_from_url("", base_dir=tmp_path)

    assert database["ENGINE"] == "django.db.backends.sqlite3"
    assert database["NAME"] == str(tmp_path / "db.sqlite3")


def test_database_from_url_parses_postgres_url():
    database = database_from_url(
        "postgres://user:pass@db:5432/app",
        base_dir=Path("/app/backend"),
        conn_max_age=120,
    )

    assert database["ENGINE"] == "django.db.backends.postgresql"
    assert database["NAME"] == "app"
    assert database["USER"] == "user"
    assert database["PASSWORD"] == "pass"
    assert database["HOST"] == "db"
    assert database["PORT"] == 5432
    assert database["CONN_MAX_AGE"] == 120


def test_database_from_url_can_require_postgres_ssl():
    database = database_from_url(
        "postgres://user:pass@db:5432/app",
        base_dir=Path("/app/backend"),
        ssl_require=True,
    )

    assert database["OPTIONS"]["sslmode"] == "require"


def test_production_settings_reject_default_secret_key():
    env = {
        **os.environ,
        "PYTHONPATH": "backend",
        "DEBUG": "False",
        "ALLOWED_HOSTS": "example.com",
    }

    result = subprocess.run(
        [sys.executable, "-c", "import config.settings"],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "SECRET_KEY must be set" in result.stderr


def test_production_settings_reject_example_secret_key():
    env = {
        **os.environ,
        "PYTHONPATH": "backend",
        "DEBUG": "False",
        "SECRET_KEY": "your-secret-key-change-this-in-production",
        "ALLOWED_HOSTS": "example.com",
        "DATABASE_URL": "postgres://user:pass@db:5432/app",
        "TASKS_BACKEND": "project.adapters.ProductionTaskBackend",
    }

    result = subprocess.run(
        [sys.executable, "-c", "import config.settings"],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "SECRET_KEY must be set" in result.stderr


def test_production_settings_require_external_database_url():
    env = {
        **os.environ,
        "PYTHONPATH": "backend",
        "DEBUG": "False",
        "SECRET_KEY": "prod-secret-key-with-many-unique-characters-1234567890",
        "ALLOWED_HOSTS": "example.com",
        "DATABASE_URL": "",
    }

    result = subprocess.run(
        [sys.executable, "-c", "import config.settings"],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "DATABASE_URL must be set" in result.stderr


def test_production_settings_reject_non_postgres_database_url():
    env = {
        **os.environ,
        "PYTHONPATH": "backend",
        "DEBUG": "False",
        "SECRET_KEY": "prod-secret-key-with-many-unique-characters-1234567890",
        "ALLOWED_HOSTS": "example.com",
        "DATABASE_URL": "sqlite:////tmp/production.sqlite3",
        "TASKS_BACKEND": "project.adapters.ProductionTaskBackend",
    }

    result = subprocess.run(
        [sys.executable, "-c", "import config.settings"],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "must point to PostgreSQL" in result.stderr


def test_production_settings_import_with_required_env():
    env = {
        **os.environ,
        "PYTHONPATH": "backend",
        "DEBUG": "False",
        "SECRET_KEY": "prod-secret-key-with-many-unique-characters-1234567890",
        "ALLOWED_HOSTS": "example.com",
        "DATABASE_URL": "postgres://user:pass@db:5432/app",
        "TASKS_BACKEND": "project.adapters.ProductionTaskBackend",
    }

    result = subprocess.run(
        [sys.executable, "-c", "import config.settings"],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_development_uses_immediate_task_backend_and_scheduler_is_disabled():
    import config.settings as settings

    assert settings.TASKS["default"]["BACKEND"] == (
        "django.tasks.backends.immediate.ImmediateBackend"
    )
    assert settings.TASKS["webhook"]["BACKEND"] == (
        "django.tasks.backends.immediate.ImmediateBackend"
    )
    assert settings.PERIODIC_SCHEDULER_ENABLED is False


def test_production_settings_reject_immediate_task_backend():
    env = {
        **os.environ,
        "PYTHONPATH": "backend",
        "DEBUG": "False",
        "SECRET_KEY": "prod-secret-key-with-many-unique-characters-1234567890",
        "ALLOWED_HOSTS": "example.com",
        "DATABASE_URL": "postgres://user:pass@db:5432/app",
        "TASKS_BACKEND": "django.tasks.backends.immediate.ImmediateBackend",
    }

    result = subprocess.run(
        [sys.executable, "-c", "import config.settings"],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "TASKS_BACKEND" in result.stderr


def test_realtime_opt_in_requires_optional_channels_dependency():
    env = {
        **os.environ,
        "PYTHONPATH": "backend",
        "REALTIME_ENABLED": "True",
    }

    result = subprocess.run(
        [sys.executable, "-c", "import config.settings"],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "optional Channels dependency" in result.stderr

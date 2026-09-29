from pathlib import Path


DEPLOY_DIR = Path(__file__).parents[1] / "deploy"


def test_pi_service_template_uses_fastapi_app():
    service = (DEPLOY_DIR / "financial-model.service.template").read_text()

    assert "src.api.main:app" in service
    assert "--host 0.0.0.0" in service
    assert "--port 8000" in service
    assert "Restart=on-failure" in service


def test_pi_installer_does_not_run_database_migrations():
    installer = (DEPLOY_DIR / "install_pi.sh").read_text()

    assert "alembic upgrade head" not in installer
    assert "financial_model.db" in installer
    assert "requirements-web.txt" in installer


def test_pi_deployment_documentation_requires_existing_database():
    readme = (DEPLOY_DIR / "README.md").read_text()

    assert "database/financial_model.db" in readme
    assert "does **not**" in readme.lower()
    assert "Sprint 4.9" in readme

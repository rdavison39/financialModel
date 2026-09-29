"""Tests for the Sprint 4.3 responsive web shell."""
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_web_root_redirects_to_portfolio():
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/portfolio"


def test_web_navigation_pages_render():
    pages = ("/portfolio/history", "/accounts", "/accounts/history", "/holdings/history", "/import")
    for path in pages:
        response = client.get(path)
        assert response.status_code == 200
        assert "Financial Model" in response.text
        assert "Portfolio History" in response.text
        assert "Account Management" in response.text


def test_web_page_has_mobile_viewport_and_stylesheet():
    response = client.get("/portfolio/history")
    assert 'name="viewport"' in response.text
    assert '/static/css/app.css' in response.text


def test_web_static_css_is_available():
    response = client.get("/static/css/app.css")
    assert response.status_code == 200
    assert "grid-template-columns" in response.text

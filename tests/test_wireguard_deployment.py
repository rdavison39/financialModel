from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WIREGUARD = ROOT / "deploy" / "wireguard"


def test_wireguard_templates_exist():
    assert (WIREGUARD / "README.md").is_file()
    assert (WIREGUARD / "server.conf.example").is_file()
    assert (WIREGUARD / "client.conf.example").is_file()
    assert (ROOT / "deploy" / "test_web_access.ps1").is_file()


def test_wireguard_templates_use_placeholders_not_real_keys():
    for name in ("server.conf.example", "client.conf.example"):
        text = (WIREGUARD / name).read_text(encoding="utf-8")
        assert "<" in text
        assert "PRIVATE_KEY" in text
        assert "PUBLIC_KEY" in text
        assert "-----BEGIN" not in text


def test_wireguard_templates_route_only_wireguard_network():
    server = (WIREGUARD / "server.conf.example").read_text(encoding="utf-8")
    client = (WIREGUARD / "client.conf.example").read_text(encoding="utf-8")

    assert "Address = 10.6.0.1/24" in server
    assert "AllowedIPs = 10.6.0.2/32" in server
    assert "Address = 10.6.0.2/32" in client
    assert "AllowedIPs = 10.6.0.0/24" in client
    assert "PersistentKeepalive = 25" in client


def test_wireguard_docs_do_not_recommend_public_fastapi_exposure():
    text = (WIREGUARD / "README.md").read_text(encoding="utf-8")
    assert "is **not** intended to be exposed directly to the public Internet" in text
    assert "Do not forward TCP `8000` from the Internet." in text


def test_windows_health_script_uses_health_endpoint():
    text = (ROOT / "deploy" / "test_web_access.ps1").read_text(encoding="utf-8")
    assert "/api/health" in text
    assert 'status -ne "ok"' in text

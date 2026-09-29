# Sprint 4.9A — Windows / WireGuard Validation

This directory contains the **pre-Pi** material for remote access.

The Raspberry Pi is not required for this stage.

## Goal

Validate the intended network architecture before the Pi is available:

```text
Remote iPhone / laptop
        |
     WireGuard
        |
   Home network
        |
 Raspberry Pi
        |
 FastAPI :8000
        |
   Services
        |
     SQLite
```

FastAPI port `8000` is an application port on the trusted LAN/WireGuard path. It is **not** intended to be exposed directly to the public Internet.

## Files

- `server.conf.example` — example WireGuard server configuration for the future Pi.
- `client.conf.example` — example remote-device configuration.
- `../test_web_access.ps1` — Windows-side test for the FastAPI health endpoint.

## Important

These files contain placeholders only.

Do **not** put real WireGuard private keys into source control.

Replace:

```text
<SERVER_PRIVATE_KEY>
<SERVER_PUBLIC_KEY>
<CLIENT_PRIVATE_KEY>
<CLIENT_PUBLIC_KEY>
<HOME_PUBLIC_IP_OR_DDNS>
```

with real values only in the actual WireGuard configuration when the Pi is available.

## 4.9A Windows test

With the FastAPI application running on Windows:

```powershell
.\deploy\test_web_access.ps1
```

This tests:

```text
http://127.0.0.1:8000/api/health
```

To test the application through a LAN address:

```powershell
.\deploy\test_web_access.ps1 -BaseUrl "http://192.168.1.50:8000"
```

Use the Windows machine's actual LAN address when running the test.

A successful result proves that FastAPI is responding over the selected network path. It does **not** prove WireGuard connectivity.

## Future Pi setup

When the Raspberry Pi is available:

1. Install the tested application on the Pi using the Sprint 4.8 deployment package.
2. Confirm `/api/health` locally on the Pi.
3. Configure the Pi as the WireGuard server using the server example as a starting point.
4. Create a real client key pair.
5. Configure the home router to forward **UDP 51820** to the Pi, if required by the chosen WireGuard topology.
6. Allow WireGuard traffic through the firewall.
7. Allow FastAPI TCP `8000` only from the trusted LAN and WireGuard networks.
8. Do not forward TCP `8000` from the Internet.
9. Connect the iPhone/laptop through WireGuard.
10. Test the Pi's WireGuard address with `/api/health`.
11. Test the web UI.
12. Only then consider 4.9 complete.

The actual Pi/router commands should be finalized against the Pi's real network interfaces, LAN subnet, WireGuard installation, and router configuration rather than guessed in advance.

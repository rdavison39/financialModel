# Sprint 4.8 — Raspberry Pi Deployment

This stage moves the **existing, already-tested backend** to the Raspberry Pi 5.

The target architecture is:

```text
Windows desktop / iPhone
          |
          | HTTP on LAN
          v
     Raspberry Pi 5
          |
       FastAPI
          |
     Existing services
          |
       SQLite
```

The Pi becomes the **single owner of the SQLite database**. Windows should not open
`database/financial_model.db` from a network share.

## Important

This deployment does **not**:

- change the database schema
- run Alembic migrations
- replace the Tkinter application
- modify the existing importers
- expose the API to the public Internet

The existing database is copied to the Pi and remains at:

```text
<application-directory>/database/financial_model.db
```

`src/database.py` resolves that path relative to the project root, so no database
configuration change is required.

## 1. Prepare the Pi

The Pi should be running a current Raspberry Pi OS installation and be connected to
the same LAN as the devices that will use the web application.

Create an application directory and copy the **entire tested project** to it.
For example:

```text
/home/ron/financialModel
```

The project must include:

```text
src/
database/
requirements.txt
requirements-web.txt
deploy/
```

Most importantly, copy the existing:

```text
database/financial_model.db
```

Do not create a new empty database.

## 2. Install the service

From the project directory on the Pi:

```bash
sudo ./deploy/install_pi.sh /home/ron/financialModel ron
```

Replace both arguments with the actual project directory and Linux user.

The installer:

1. Installs Python/venv prerequisites.
2. Creates `.venv` inside the project.
3. Installs the existing application requirements and web requirements.
4. Creates a systemd service.
5. Starts the FastAPI server automatically at boot.
6. Checks `/api/health` locally.

It deliberately does **not** run `alembic upgrade head`.

## 3. Test from the Pi

```bash
systemctl status financial-model.service
curl http://127.0.0.1:8000/api/health
```

Expected health response:

```json
{"status":"ok"}
```

## 4. Find the Pi's LAN address

```bash
hostname -I
```

Then from a computer or phone on the same LAN, open:

```text
http://<pi-ip>:8000/
```

For example:

```text
http://192.168.1.50:8000/
```

## 5. Test the complete web application

Verify on the Pi:

- Portfolio
- Portfolio History
- Account Management
- Account History
- Holdings History
- Import
- BMO import
- Nesbitt import
- `/api/health`

Also verify that the existing Windows Tkinter application still works against its
local Windows database. The Pi deployment should not alter that installation.

## 6. Useful service commands

Restart:

```bash
sudo systemctl restart financial-model.service
```

View status:

```bash
sudo systemctl status financial-model.service
```

View recent logs:

```bash
sudo journalctl -u financial-model.service -n 100 --no-pager
```

Follow logs:

```bash
sudo journalctl -u financial-model.service -f
```

Stop:

```bash
sudo systemctl stop financial-model.service
```

## Network/security boundary

Sprint 4.8 is intended for **local LAN access**. Do not forward TCP port 8000 from
the Internet to the Pi.

Remote access through the existing WireGuard VPN is Sprint 4.9.

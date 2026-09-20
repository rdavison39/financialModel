"""Persistent GUI settings for the Financial Model application."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


class UISettingsService:
    """Persist small amounts of per-screen GUI state outside the database."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or self._default_path()
        self._settings: dict[str, dict[str, Any]] = {}
        self._load()

    @staticmethod
    def _default_path() -> Path:
        if os.name == "nt":
            appdata = os.environ.get("APPDATA")
            if appdata:
                return Path(appdata) / "FinancialModel" / "ui_settings.json"
        config_home = os.environ.get("XDG_CONFIG_HOME")
        if config_home:
            return Path(config_home) / "financial_model" / "ui_settings.json"
        return Path.home() / ".financial_model" / "ui_settings.json"

    @staticmethod
    def _remove_date_settings(settings: dict[str, dict[str, Any]]) -> bool:
        """Remove transient date fields from persisted UI settings."""
        changed = False
        date_keys = {"start_date", "end_date", "from_date", "to_date"}
        for values in settings.values():
            for key in date_keys:
                if key in values:
                    del values[key]
                    changed = True
        return changed

    def _load(self) -> None:
        try:
            if not self.path.exists():
                return
            with self.path.open("r", encoding="utf-8") as handle:
                value = json.load(handle)
            if isinstance(value, dict):
                self._settings = {
                    str(screen): dict(values)
                    for screen, values in value.items()
                    if isinstance(values, dict)
                }
                # Dates are deliberately transient.  Remove any dates left
                # by an older version of the settings implementation.
                if self._remove_date_settings(self._settings):
                    self.save()
        except (OSError, ValueError, TypeError):
            self._settings = {}

    def get_screen(self, screen: str) -> dict[str, Any]:
        # Each GUI tab owns its own service instance.  Reload before reading
        # so one tab always sees settings written by another tab.
        self._load()
        return dict(self._settings.get(screen, {}))

    def update(self, screen: str, values: dict[str, Any]) -> None:
        # Each GUI tab owns its own service instance.  Reload first so a
        # write from one tab cannot overwrite settings saved by another tab.
        self._load()
        self._settings.setdefault(screen, {}).update(values)
        self._remove_date_settings(self._settings)
        self.save()

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(
                prefix="ui_settings_",
                suffix=".tmp",
                dir=str(self.path.parent),
                text=True,
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(self._settings, handle, indent=2, sort_keys=True)
                    handle.write("\n")
                os.replace(temp_name, self.path)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
        except OSError:
            # Preferences are optional and must never prevent the app from
            # starting or operating.
            return

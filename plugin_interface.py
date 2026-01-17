from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, List, Optional


@dataclass(frozen=True)
class PluginAction:
    """A single UI action exposed by a plugin (usually rendered as a menu action)."""

    text: str
    callback: Callable[..., Any]
    shortcut: Optional[str] = None
    status_tip: Optional[str] = None


class PluginInterface:
    """Base class for plugins.

    Backward compatible: if a plugin only implements `run(main_window)`, it still works.
    New style: plugins can expose multiple actions via `get_actions`.
    """

    name: str = "Unknown Plugin"
    version: str = "1.0"
    description: str = "No description."

    def on_load(self, main_window: Any) -> None:
        """Called when the plugin is loaded (optional)."""
        return None

    def on_unload(self, main_window: Any) -> None:
        """Called before the plugin is unloaded (optional)."""
        return None

    def get_actions(self, main_window: Any) -> List[PluginAction]:
        """Return UI actions provided by this plugin.

        Default behavior: expose a single "Run" action that calls `run`.
        """
        return [PluginAction(text="Run", callback=self.run)]

    def run(self, main_window: Any) -> None:
        """Fallback entrypoint for legacy/simple plugins."""
        raise NotImplementedError("Plugin must implement 'run' or override 'get_actions'.")

import importlib.util
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtGui import QAction

from plugin_interface import PluginInterface, PluginAction


@dataclass
class PluginLoadError:
    filename: str
    error: str


class PluginHost:
    """Loads plugins from a directory and exposes their actions to the UI."""

    def __init__(self, main_window: Any, plugin_dir: str = "plugins"):
        self.main_window = main_window
        # Resolve relative to app dir, not CWD. Humans love launching apps from random places.
        app_dir = Path(getattr(main_window, "APP_DIR", Path.cwd()))
        self.plugin_dir = (app_dir / plugin_dir).resolve()
        self.plugins: List[PluginInterface] = []
        self.load_errors: List[PluginLoadError] = []

    def ensure_dir(self) -> None:
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        init_py = self.plugin_dir / "__init__.py"
        if not init_py.exists():
            try:
                init_py.write_text("# plugins package\n", encoding="utf-8")
            except Exception:
                pass

    def _import_plugin(self, file_path: Path) -> Optional[PluginInterface]:
        module_name = f"plugin_{file_path.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, str(file_path))
            if spec is None or spec.loader is None:
                raise ImportError("Could not create import spec")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            if not hasattr(module, "Plugin"):
                raise AttributeError("Missing 'Plugin' class")

            plugin_instance = module.Plugin()
            # Allow legacy plugins that don't inherit PluginInterface.
            if not isinstance(plugin_instance, PluginInterface):
                # Wrap it into a minimal adapter.
                plugin_instance = self._LegacyAdapter(plugin_instance)

            return plugin_instance
        except Exception as e:
            self.load_errors.append(PluginLoadError(filename=file_path.name, error=str(e)))
            return None

    class _LegacyAdapter(PluginInterface):
        def __init__(self, legacy_obj: Any):
            self.legacy_obj = legacy_obj
            self.name = getattr(legacy_obj, "name", legacy_obj.__class__.__name__)
            self.version = getattr(legacy_obj, "version", "1.0")
            self.description = getattr(legacy_obj, "description", "No description.")

        def run(self, main_window: Any) -> None:
            return self.legacy_obj.run(main_window)

    def load(self, disabled_filenames: Optional[List[str]] = None) -> None:
        self.ensure_dir()
        self.plugins = []
        self.load_errors = []
        disabled = set(disabled_filenames or [])

        for file in sorted(self.plugin_dir.glob("*.py")):
            if file.name == "__init__.py":
                continue
            if file.name in disabled:
                continue
            plugin = self._import_plugin(file)
            if plugin is None:
                continue
            try:
                plugin.on_load(self.main_window)
            except Exception:
                # Plugin bugs shouldn't kill the host.
                pass
            self.plugins.append(plugin)

    def unload_all(self) -> None:
        for p in self.plugins:
            try:
                p.on_unload(self.main_window)
            except Exception:
                pass
        self.plugins = []

    def list_all_files(self) -> List[str]:
        self.ensure_dir()
        return [p.name for p in sorted(self.plugin_dir.glob("*.py")) if p.name != "__init__.py"]

    def build_menu(self, parent_menu) -> None:
        """Populate a QMenu with plugin actions."""
        parent_menu.clear()
        for plugin in self.plugins:
            sub = parent_menu.addMenu(f"{plugin.name}")
            try:
                actions = plugin.get_actions(self.main_window) or []
            except Exception:
                actions = [PluginAction(text="Run", callback=plugin.run)]

            for act in actions:
                qact = QAction(act.text, self.main_window)
                if act.shortcut:
                    qact.setShortcut(act.shortcut)
                if act.status_tip:
                    qact.setStatusTip(act.status_tip)

                def _call(cb, mw):
                    try:
                        # Support callbacks that accept 0 args or (main_window).
                        import inspect

                        sig = inspect.signature(cb)
                        if len(sig.parameters) == 0:
                            cb()
                        else:
                            cb(mw)
                    except Exception as e:
                        try:
                            mw.log(f"❌ Plugin error: {e}")
                        except Exception:
                            pass

                qact.triggered.connect(lambda _=False, cb=act.callback, mw=self.main_window: _call(cb, mw))
                sub.addAction(qact)

        if not self.plugins:
            empty = QAction("(No enabled plugins)", self.main_window)
            empty.setEnabled(False)
            parent_menu.addAction(empty)

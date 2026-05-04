import importlib.util
import sys
import types
from pathlib import Path


def test_app_bootstrap_adds_dashboard_dir_before_local_imports(monkeypatch):
    dashboard_dir = Path(__file__).resolve().parents[1]
    app_path = dashboard_dir / "app.py"
    module_names = ("app", "filters", "utils", "db", "views")
    saved_modules = {name: sys.modules.get(name) for name in module_names}

    def is_dashboard_path(path_entry: str) -> bool:
        if not path_entry:
            return False
        return Path(path_entry).resolve() == dashboard_dir

    monkeypatch.setattr(
        sys,
        "path",
        [entry for entry in sys.path if not is_dashboard_path(entry)],
    )

    for name in module_names:
        sys.modules.pop(name, None)

    try:
        spec = importlib.util.spec_from_file_location("case_dashboard_app_bootstrap", app_path)
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)

        spec.loader.exec_module(module)

        assert Path(sys.path[0]).resolve() == dashboard_dir
        assert dashboard_dir == module.DASHBOARD_DIR
    finally:
        for name in module_names:
            sys.modules.pop(name, None)
        for name, module in saved_modules.items():
            if module is not None:
                sys.modules[name] = module


def test_app_bootstrap_clears_stale_local_utils_module(monkeypatch):
    dashboard_dir = Path(__file__).resolve().parents[1]
    app_path = dashboard_dir / "app.py"
    module_names = ("app", "filters", "utils", "db", "views")
    saved_modules = {name: sys.modules.get(name) for name in module_names}
    stale_utils = types.ModuleType("utils")
    stale_utils.__file__ = str(dashboard_dir / "utils.py")

    sys.modules["utils"] = stale_utils

    try:
        spec = importlib.util.spec_from_file_location("case_dashboard_app_stale_utils", app_path)
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)

        spec.loader.exec_module(module)

        imported_utils = sys.modules["utils"]
        assert imported_utils is not stale_utils
        assert hasattr(imported_utils, "segment_label")
    finally:
        for name in module_names:
            sys.modules.pop(name, None)
        for name, module in saved_modules.items():
            if module is not None:
                sys.modules[name] = module

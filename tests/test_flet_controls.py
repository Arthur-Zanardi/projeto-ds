from __future__ import annotations

import ast
import importlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = ROOT / "main.py"


class FletStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = MAIN_PATH.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        cls.parents: dict[ast.AST, ast.AST] = {}
        for parent in ast.walk(cls.tree):
            for child in ast.iter_child_nodes(parent):
                cls.parents[child] = parent

    def test_deprecated_buttons_and_old_filepicker_patterns_are_absent(self) -> None:
        self.assertNotIn("ft.ElevatedButton", self.source)
        self.assertNotIn("ft.OutlinedButton", self.source)
        self.assertNotIn("ft.TextButton", self.source)
        self.assertNotIn("FilePicker(on_result", self.source)
        self.assertNotIn("overlay.append(file_picker)", self.source)

    def test_ft_button_does_not_use_text_keyword(self) -> None:
        for node in ast.walk(self.tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "Button":
                keywords = {keyword.arg for keyword in node.keywords}
                self.assertNotIn("text", keywords)

    def test_pick_files_is_awaited(self) -> None:
        pick_files_calls = []
        for node in ast.walk(self.tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "pick_files":
                pick_files_calls.append(node)

        self.assertTrue(pick_files_calls)
        for call in pick_files_calls:
            parent = self.parents.get(call)
            while parent is not None and not isinstance(parent, (ast.Await, ast.FunctionDef, ast.AsyncFunctionDef)):
                parent = self.parents.get(parent)
            self.assertIsInstance(parent, ast.Await)

    def test_google_polling_is_the_only_background_task(self) -> None:
        lines = [line for line in self.source.splitlines() if "page.run_task(" in line]

        self.assertEqual(lines, ['                page.run_task(poll_google, data["state"])'])


class FletControlConstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        try:
            cls.ft = importlib.import_module("flet")
            cls.app_main = importlib.import_module("main")
        except ModuleNotFoundError as exc:
            raise unittest.SkipTest(f"Flet is not installed in this Python: {exc}") from exc

    def test_button_helpers_construct_current_controls(self) -> None:
        ft = self.ft
        app_main = self.app_main

        controls = [
            app_main.primary_button("Save", icon=ft.Icons.SAVE, on_click=lambda e: None, palette=app_main.LIGHT),
            app_main.secondary_button("Choose", icon=ft.Icons.ADD, on_click=lambda e: None, palette=app_main.LIGHT),
            app_main.danger_button("Delete", icon=ft.Icons.DELETE, on_click=lambda e: None, palette=app_main.LIGHT),
            app_main.app_icon_button(icon=ft.Icons.SEND, tooltip="Send", on_click=lambda e: None, palette=app_main.LIGHT),
        ]

        self.assertEqual(controls[0].__class__.__name__, "Button")
        self.assertEqual(controls[1].__class__.__name__, "Button")
        self.assertEqual(controls[2].__class__.__name__, "Button")
        self.assertEqual(controls[3].__class__.__name__, "IconButton")
        self.assertEqual(controls[3].tooltip, "Send")

    def test_common_profile_controls_construct_without_type_error(self) -> None:
        ft = self.ft

        controls = [
            ft.Dropdown(label="Choice", options=[ft.dropdown.Option("a", "A")]),
            ft.Slider(min=0, max=1, divisions=10, value=0.5, label="{value}"),
            ft.Switch(label="Dark mode", value=False),
            ft.Checkbox(label="Visible", value=True),
            ft.TextField(label="Name"),
            ft.FilePicker(),
        ]

        self.assertEqual(len(controls), 6)


if __name__ == "__main__":
    unittest.main()

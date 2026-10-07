#!/usr/bin/env python3
"""Test bin/toggle-natural-scrolling against a fake PreferencePanesSupport."""
import importlib.machinery
import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[2] / "bin" / "toggle-natural-scrolling"


def load():
    loader = importlib.machinery.SourceFileLoader("toggle_natural_scrolling", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class FakeFramework:
    def __init__(self, natural):
        self.natural = natural
        self.calls = []

    def swipeScrollDirection(self):
        return self.natural

    def setSwipeScrollDirection(self, natural):
        self.calls.append(natural)
        self.natural = natural


class ToggleNaturalScrollingTest(unittest.TestCase):
    def test_turns_natural_scrolling_off_when_on(self):
        framework = FakeFramework(natural=True)

        result = load().toggle(framework)

        self.assertEqual((framework.calls, result), ([False], False))

    def test_turns_natural_scrolling_on_when_off(self):
        framework = FakeFramework(natural=False)

        result = load().toggle(framework)

        self.assertEqual((framework.calls, result), ([True], True))


if __name__ == "__main__":
    unittest.main()

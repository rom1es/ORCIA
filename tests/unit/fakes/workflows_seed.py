"""Test-only helper re-exporting `create_seeded_test_app()` (`<= 20 L`)."""

from __future__ import annotations

from tests.unit.fakes.test_app_helpers import create_seeded_test_app

__all__ = ["create_seeded_test_app"]

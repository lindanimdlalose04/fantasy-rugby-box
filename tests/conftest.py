"""Shared fixtures."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "network: needs the rugbydata store, skipped by default"
    )


def pytest_collection_modifyitems(config, items):
    """Network tests run only with --network, so the suite stays offline."""
    if config.getoption("--network"):
        return
    skip = pytest.mark.skip(reason="needs the store; pass --network to run")
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip)


def pytest_addoption(parser):
    parser.addoption(
        "--network", action="store_true", default=False,
        help="run the tests that read from the rugbydata store",
    )

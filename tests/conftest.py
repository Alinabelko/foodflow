"""
Shared pytest fixtures for FoodFlow e2e tests.

Each test gets an isolated DataManager pointing at a fresh tmp_path directory,
so real data/CSV files are never touched.

Seed helpers (seed_fridge, seed_people, etc.) live in tests/helpers.py
and are imported directly by test modules.
"""
import sys
import os
import pytest
from dotenv import load_dotenv

# Load .env from project root before any agent/OpenAI import
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ---------------------------------------------------------------------------
# Path bootstrap: ensure src/ is importable
# ---------------------------------------------------------------------------
SRC_DIR = os.path.join(os.path.dirname(__file__), "..", "src")
if os.path.abspath(SRC_DIR) not in sys.path:
    sys.path.insert(0, os.path.abspath(SRC_DIR))

# ---------------------------------------------------------------------------
# Also ensure tests/ dir itself is in path (for helpers.py import)
# ---------------------------------------------------------------------------
TESTS_DIR = os.path.dirname(__file__)
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

import data_manager as dm_module
from data_manager import DataManager
from agents.router_agent import RouterAgent


# ---------------------------------------------------------------------------
# Core fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def isolated_dm(tmp_path, monkeypatch):
    """
    Returns a DataManager whose DATA_DIR points to a fresh tmp_path.
    All CSV operations are isolated — no production data is touched.
    """
    monkeypatch.setattr(dm_module, "DATA_DIR", str(tmp_path))
    dm = DataManager()
    return dm


@pytest.fixture()
def agent(isolated_dm):
    """RouterAgent wired to the isolated DataManager."""
    return RouterAgent(isolated_dm)

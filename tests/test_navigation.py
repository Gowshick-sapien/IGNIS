"""Integration tests for Jinja2 template inheritance and navigation sidebar (Phase G2)."""

import pytest
from fastapi.testclient import TestClient
from src.cloud_dashboard.app import app

client = TestClient(app)


def test_navbar_presence_on_all_pages():
    pages = ["/experiments", "/reports", "/charts", "/scenarios"]
    for page in pages:
        res = client.get(page)
        assert res.status_code == 200, f"Failed on page {page}"
        assert "IGNIS CONTROL" in res.text, f"Navbar missing on {page}"
        assert "FOG RESEARCH PLATFORM" in res.text, f"Navbar missing on {page}"
        assert 'class="nav-link' in res.text, f"Nav links missing on {page}"


def test_navbar_active_highlighting():
    res_exp = client.get("/experiments")
    assert 'href="/experiments" class="nav-link active"' in res_exp.text

    res_rep = client.get("/reports")
    assert 'href="/reports" class="nav-link active"' in res_rep.text

    res_chart = client.get("/charts")
    assert 'href="/charts" class="nav-link active"' in res_chart.text

    res_scen = client.get("/scenarios")
    assert 'href="/scenarios" class="nav-link active"' in res_scen.text

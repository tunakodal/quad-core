
from pathlib import Path


def test_transparency_page_contract_is_present_and_contains_required_attribution():
    """
    ST-07 — Scenario 7: data source transparency page is accessible and displays
    required attribution information.

    System-level validation strategy used in this project:
    - The frontend is a separately served React application, so backend pytest
      infrastructure does not execute a browser-driven UI flow.
    - Instead, this test verifies the frontend source-of-truth contracts that
      make the transparency page user-accessible and informative:
        1. Route registration for the transparency page exists.
        2. The dedicated How It Works page exists.
        3. Required attribution/provider labels are present in the rendered page source.
        4. Transparency-related section headings are present and readable.

    This provides a stable regression guard for the requirement without introducing
    a separate frontend browser testing stack.
    """

    project_root = Path(__file__).resolve().parents[3]

    app_file = project_root / "src" / "App.jsx"
    how_it_works_file = project_root / "src" / "pages" / "HowItWorks.jsx"

    assert app_file.exists(), f"Frontend route file not found: {app_file}"
    assert how_it_works_file.exists(), f"Transparency page file not found: {how_it_works_file}"

    app_source = app_file.read_text(encoding="utf-8")
    how_source = how_it_works_file.read_text(encoding="utf-8")

    # Route accessibility contract
    assert 'path="/how-it-works"' in app_source
    assert "HowItWorks" in app_source

    # Visible page identity
    assert "How " in how_source
    assert "GUIDE" in how_source
    assert " Works" in how_source

    # Readable section structure
    assert "Point of Interest Database Overview" in how_source
    assert "Data Sources & External Services" in how_source
    assert "System Flow" in how_source

    # Required routing/map attribution
    assert "OSRM (Routing Engine)" in how_source
    assert "OpenStreetMap Data" in how_source

    # Required POI/content attribution
    assert "Wikipedia / MediaWiki REST API" in how_source
    assert "UNESCO References" in how_source

    # Supporting attribution descriptions should also be present
    assert "road networks" in how_source.lower()
    assert "geographic base data" in how_source.lower()
    assert "fetches poi descriptions" in how_source.lower()
    assert "heritage-related pois" in how_source.lower()


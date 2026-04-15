from pathlib import Path


def test_transparency_page_contract_is_present_and_contains_required_attribution():
    project_root = Path(__file__).resolve().parents[3]

    app_file = project_root / "src" / "App.jsx"
    how_it_works_file = project_root / "src" / "pages" / "HowItWorks.jsx"

    assert app_file.exists()
    assert how_it_works_file.exists()

    app_source = app_file.read_text(encoding="utf-8")
    how_source = how_it_works_file.read_text(encoding="utf-8")

    # Route
    assert 'path="/how-it-works"' in app_source
    assert "HowItWorks" in app_source

    # Title
    assert "How " in how_source
    assert "GUIDE" in how_source
    assert " Works" in how_source

    # Sections
    assert "Point of Interest Database" in how_source
    assert "System Flow" in how_source
    assert "Data Sources & External Services" in how_source

    # Remaining providers (only these!)
    assert "OSRM" in how_source
    assert "Leaflet" in how_source
    assert "OpenStreetMap" in how_source
    assert "Wikipedia" in how_source
    assert "Google Places API" in how_source
    assert "Google Text-to-Speech" in how_source

    # Optional (senin bıraktığın)
    assert "Claude" in how_source

    # Basic page sanity
    assert "Back to landing" in how_source
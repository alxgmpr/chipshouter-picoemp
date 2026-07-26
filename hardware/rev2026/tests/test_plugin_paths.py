import kicad_parse as kp


def test_kicad_happy_skills_resolves_to_existing_dir_with_bom():
    """The plugin-path helper must find a real skills dir containing a
    `bom` subdirectory (later tasks depend on skills like `bom`, `kicad`,
    etc. living under this path without hardcoding a plugin version)."""
    skills = kp.kicad_happy_skills()
    assert skills.is_dir()
    assert (skills / 'bom').is_dir()

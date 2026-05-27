# Canonical rashi names are the Aseema (AS) string values.
# Anuraga (AN) uses numeric option values (1-12) in its search form.

_TABLE = [
    ("Mesha", "1"),
    ("Vrushabha", "2"),
    ("Mithuna", "3"),
    ("Karkataka", "4"),
    ("Simha", "5"),
    ("Kanya", "6"),
    ("Thula", "7"),
    ("Vrishchika", "8"),
    ("Dhanu", "9"),
    ("Makara", "10"),
    ("Kumbha", "11"),
    ("Meena", "12"),
]

_AS_TO_AN_IDX = {as_val: an_idx for as_val, an_idx in _TABLE}
_AN_IDX_TO_AS = {an_idx: as_val for as_val, an_idx in _TABLE}

# AN profile pages show rashi as display text e.g. "Kataka (Cancer)".
# Map the first word of that display text back to the AS canonical name.
_AN_DISPLAY_FIRST_WORD = {
    "mesha": "Mesha",
    "vrishabha": "Vrushabha",
    "mithuna": "Mithuna",
    "kataka": "Karkataka",
    "simha": "Simha",
    "kanya": "Kanya",
    "tula": "Thula",
    "vrischika": "Vrishchika",
    "dhanu": "Dhanu",
    "makara": "Makara",
    "kumbha": "Kumbha",
    "meena": "Meena",
}


def to_as_rashi(rashi: str) -> str:
    """Convert any rashi string (AS canonical, AN index, or AN display text) to AS form."""
    if not rashi:
        return ""
    rashi = rashi.strip()
    # Already AS canonical?
    if rashi in _AS_TO_AN_IDX:
        return rashi
    # AN numeric index?
    if rashi in _AN_IDX_TO_AS:
        return _AN_IDX_TO_AS[rashi]
    # AN display text e.g. "Kataka (Cancer)" — match on first word
    first = rashi.split()[0].lower()
    return _AN_DISPLAY_FIRST_WORD.get(first, rashi)


def to_an_rashi(rashi: str) -> str:
    """Convert any rashi string to the AN numeric index (e.g. '4')."""
    if not rashi:
        return ""
    as_form = to_as_rashi(rashi)
    return _AS_TO_AN_IDX.get(as_form, rashi)

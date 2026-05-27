from config import DEFAULT_HEIGHT_MAX_CM, DEFAULT_HEIGHT_MIN_CM

# (cm, as_value, an_index)
# AN height indices start at 13 for 152cm; no AN option exists below that.
_HEIGHT_TABLE = [
    (152, "152cm", 13),
    (154, "154cm", 14),
    (157, "157cm", 15),
    (160, "160cm", 16),
    (162, "162cm", 17),
    (165, "165cm", 18),
    (167, "167cm", 19),
    (170, "170cm", 20),
    (172, "172cm", 21),
    (175, "175cm", 22),
    (177, "177cm", 23),
    (180, "180cm", 24),
    (182, "182cm", 25),
    (185, "185cm", 26),
    (187, "187cm", 27),
    (190, "190cm", 28),
    (193, "193cm", 29),
    (195, "195cm", 30),
    (198, "198cm", 31),
    (200, "200cm", 32),
    (203, "203cm", 33),
    (205, "205cm", 34),
    (208, "208cm", 35),
    (210, "210cm", 36),
]

# AS also has heights below 152cm; include them for AS-only lookups.
_AS_ONLY_BELOW = [
    (134, "134cm"),
    (137, "137cm"),
    (139, "139cm"),
    (142, "142cm"),
    (144, "144cm"),
    (147, "147cm"),
    (149, "149cm"),
]

_ALL_AS = [(cm, val) for cm, val, _ in _HEIGHT_TABLE]
_ALL_AS = [(cm, f"{cm}cm") for cm, _, _ in _HEIGHT_TABLE]
_ALL_AS_FULL = [(cm, f"{cm}cm") for cm, _, _ in _HEIGHT_TABLE] + _AS_ONLY_BELOW
_ALL_AS_FULL.sort(key=lambda x: x[0])

_CM_TO_AN = {cm: idx for cm, _, idx in _HEIGHT_TABLE}
_CM_TO_AS = {cm: val for cm, val, _ in _HEIGHT_TABLE}
for cm, val in _AS_ONLY_BELOW:
    _CM_TO_AS[cm] = val


def _nearest_idx(cm: int, table: list[tuple]) -> int:
    return min(range(len(table)), key=lambda i: abs(table[i][0] - cm))


def as_range(cm: int | None) -> tuple[str, str]:
    """Return (from_value, to_value) for AS search — one step below and above cm.
    Falls back to DEFAULT_HEIGHT_MIN_CM–DEFAULT_HEIGHT_MAX_CM when cm is None."""
    if cm is None:
        return f"{DEFAULT_HEIGHT_MIN_CM}cm", f"{DEFAULT_HEIGHT_MAX_CM}cm"
    idx = _nearest_idx(cm, _ALL_AS_FULL)
    lo = _ALL_AS_FULL[max(0, idx - 1)][1]
    hi = _ALL_AS_FULL[min(len(_ALL_AS_FULL) - 1, idx + 1)][1]
    return lo, hi


def an_range(cm: int | None) -> tuple[str, str]:
    """Return (from_index, to_index) for AN search — one step below and above cm.
    Falls back to DEFAULT_HEIGHT_MIN_CM–DEFAULT_HEIGHT_MAX_CM when cm is None."""
    if cm is None:
        an_table = [(c, i) for c, _, i in _HEIGHT_TABLE]
        lo = an_table[_nearest_idx(DEFAULT_HEIGHT_MIN_CM, an_table)][1]
        hi = an_table[_nearest_idx(DEFAULT_HEIGHT_MAX_CM, an_table)][1]
        return str(lo), str(hi)
    an_table = [(c, i) for c, _, i in _HEIGHT_TABLE]
    idx = _nearest_idx(cm, an_table)
    lo = an_table[max(0, idx - 1)][1]
    hi = an_table[min(len(an_table) - 1, idx + 1)][1]
    return str(lo), str(hi)

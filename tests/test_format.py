# -*- coding: utf-8 -*-
"""Unit tests for the pure formatting helpers (engine-free, extracted from the
read-side adapter)."""
from wgmod_research.adapter import format as f


class _KPI(object):
    def __init__(self, value=None, type=""):
        self.value = value
        self.type = type


class _Desc(object):
    def __init__(self, kpi):
        self.kpi = kpi


class _Action(object):
    def __init__(self, kpi=None):
        self._descriptor = _Desc(kpi if kpi is not None else [])


# --- roman ------------------------------------------------------------------

def test_roman_basic():
    assert f.roman(1) == "I"
    assert f.roman(10) == "X"
    assert f.roman(11) == "XI"


def test_roman_out_of_table_falls_back_to_digits():
    assert f.roman(12) == "12"


def test_roman_zero_and_none_and_negative_are_empty():
    assert f.roman(0) == ""
    assert f.roman(None) == ""
    assert f.roman(-3) == ""


# --- module_big_icon --------------------------------------------------------

def test_module_big_icon_swaps_to_big():
    src = "img://gui/maps/icons/modules/gun.png"
    assert f.module_big_icon(src) == "img://gui/maps/icons/modules/gunBig.png"


def test_module_big_icon_already_big_unchanged():
    src = "img://gui/maps/icons/modules/gunBig.png"
    assert f.module_big_icon(src) == src


def test_module_big_icon_non_module_unchanged():
    src = "img://gui/maps/icons/vehicle/foo.png"
    assert f.module_big_icon(src) == src


def test_module_big_icon_empty():
    assert f.module_big_icon("") == ""
    assert f.module_big_icon(None) == ""


# --- skilltree_icon ---------------------------------------------------------

def test_skilltree_icon_builds_large_url():
    assert f.skilltree_icon("major", "boo") == (
        "img://gui/maps/icons/skillTree/tree/perks/major/skills/large/boo.png")


def test_skilltree_icon_defaults_type_common():
    assert f.skilltree_icon("", "boo") == (
        "img://gui/maps/icons/skillTree/tree/perks/common/skills/large/boo.png")


def test_skilltree_icon_empty_name():
    assert f.skilltree_icon("major", "") == ""


# --- humanize ---------------------------------------------------------------

def test_humanize_splits_camel_case():
    assert f.humanize("invisibilityWhenShooting") == "Invisibility When Shooting"


def test_humanize_capitalizes_first():
    assert f.humanize("gun") == "Gun"


def test_humanize_empty():
    assert f.humanize("") == ""


# --- numeric formatters -----------------------------------------------------

def test_fmt_pct():
    assert f.fmt_pct(10.0) == "+10%"
    assert f.fmt_pct(-1.0) == "-1%"
    assert f.fmt_pct(0.0) == ""       # negligible -> empty
    assert f.fmt_pct(10.02) == "+10%"  # rounds clean
    assert f.fmt_pct(2.5) == "+2.5%"   # keeps a decimal


def test_fmt_signed():
    assert f.fmt_signed(3.0) == "+3"
    assert f.fmt_signed(-3.0) == "-3"
    assert f.fmt_signed(0.0) == ""
    assert f.fmt_signed(2.5) == "+2.5"


def test_fmt_signed_keeps_small_fractional_deltas():
    # 'add' KPIs are absolute quantities on wildly different scales: a top-reverse-
    # speed delta is +3, but a dispersion delta is -0.01. The old integer-rounding
    # swallowed the dispersion-scale ones to "" (their number vanished from the
    # tooltip, leaving only the qualitative sentence). Keep two decimals for sub-unit
    # deltas so the figure survives.
    assert f.fmt_signed(-0.01) == "-0.01"
    assert f.fmt_signed(-0.009999999776482582) == "-0.01"  # the live gunDispersion KPI
    assert f.fmt_signed(-0.02) == "-0.02"
    assert f.fmt_signed(0.1) == "+0.1"                     # no trailing zero
    assert f.fmt_signed(-0.5) == "-0.5"


def test_fmt_signed_only_true_zero_is_empty():
    # genuinely-negligible values (round to 0.00 even at two decimals) stay empty;
    # a real sub-unit delta does not.
    assert f.fmt_signed(0.0) == ""
    assert f.fmt_signed(0.001) == ""
    assert f.fmt_signed(-0.004) == ""
    assert f.fmt_signed(0.01) == "+0.01"


def test_fmt_num_unsigned_and_never_empty_for_zero():
    assert f.fmt_num(10.0) == "10"
    assert f.fmt_num(0.0) == "0"       # unlike fmt_pct/fmt_signed, keeps "0"
    assert f.fmt_num(2.5) == "2.5"


def test_fmt_num_keeps_small_fractional_magnitudes():
    # {value} fills carry absolute magnitudes too (skilltree_value's 'add' path),
    # which can be dispersion-scale hundredths. The old integer-rounding collapsed
    # those to "0", so a template read "...by 0" instead of "...by 0.01". Keep two
    # decimals (trailing zeros trimmed); a true ~zero still reads "0".
    assert f.fmt_num(0.01) == "0.01"
    assert f.fmt_num(0.1) == "0.1"
    assert f.fmt_num(0.001) == "0"


# --- KPI readers ------------------------------------------------------------

def test_kpi_objs_reads_descriptor_kpi():
    a = _Action([1, 2, 3])
    assert f.kpi_objs(a) == [1, 2, 3]


def test_kpi_objs_missing_descriptor_is_empty():
    assert f.kpi_objs(object()) == []


def test_kpi_prefix_mul_is_percent():
    assert f.kpi_prefix(_KPI(value=1.1, type="mul")) == "+10%"


def test_kpi_prefix_add_is_raw_delta():
    assert f.kpi_prefix(_KPI(value=3.0, type="add")) == "+3"


def test_kpi_prefix_non_mul_falls_back_to_signed():
    assert f.kpi_prefix(_KPI(value=-3.0, type="whatever")) == "-3"


def test_kpi_prefix_bool_and_nonnumeric_are_empty():
    assert f.kpi_prefix(_KPI(value=True, type="mul")) == ""
    assert f.kpi_prefix(_KPI(value="x", type="add")) == ""
    assert f.kpi_prefix(_KPI(value=None)) == ""


def test_kpi_prefix_negligible_mul_is_empty():
    assert f.kpi_prefix(_KPI(value=1.0, type="mul")) == ""


def test_skilltree_value_scans_first_usable_kpi():
    a = _Action([_KPI(value="x"), _KPI(value=1.2, type="mul")])
    assert f.skilltree_value(a) == "20"          # unsigned percent


def test_skilltree_value_add_magnitude():
    a = _Action([_KPI(value=-3.0, type="add")])
    assert f.skilltree_value(a) == "3"           # unsigned magnitude


def test_skilltree_value_none_usable_is_empty():
    a = _Action([_KPI(value="x"), _KPI(value=None)])
    assert f.skilltree_value(a) == ""


# --- enriched buff-line records ---------------------------------------------

def test_param_icon_name_remaps_known_kpi():
    assert f.param_icon_name("vehicleStrength") == "maxHealth"
    assert f.param_icon_name("nonHEShellDamage") == "avgDamage"
    assert f.param_icon_name("vehicleGunAimSpeed") == "aimingTime"


def test_param_icon_name_unknown_used_verbatim():
    # some KPI names are already a valid vehParams file (e.g. vehicleFireChance)
    assert f.param_icon_name("vehicleFireChance") == "vehicleFireChance"


def test_param_icon_name_empty():
    assert f.param_icon_name("") == ""
    assert f.param_icon_name(None) == ""


def test_strip_unit_drops_wrapping_parens():
    assert f.strip_unit("(HP)") == "HP"
    assert f.strip_unit("(km/h)") == "km/h"
    assert f.strip_unit(" (s) ") == "s"


def test_strip_unit_without_parens_unchanged():
    assert f.strip_unit("HP") == "HP"
    assert f.strip_unit("") == ""
    assert f.strip_unit(None) == ""


def test_kpi_record_field_order_and_pos_neg():
    sep = f.KPI_FIELD_SEP
    buff = f.kpi_record("img://x.png", False, "+10 HP", "to damage")
    assert buff == sep.join(["img://x.png", "pos", "+10 HP", "to damage"])
    nerf = f.kpi_record("img://y.png", True, "-0.10 s", "to aiming speed")
    assert nerf == sep.join(["img://y.png", "neg", "-0.10 s", "to aiming speed"])


def test_kpi_record_coerces_missing_fields_to_empty():
    sep = f.KPI_FIELD_SEP
    assert f.kpi_record("", False, "+25%", "") == sep.join(["", "pos", "+25%", ""])
    assert f.kpi_record(None, True, None, None) == sep.join(["", "neg", "", ""])

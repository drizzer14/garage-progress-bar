# -*- coding: utf-8 -*-
"""Unit tests for the Wulf command-argument parsers (engine-free, extracted from
the Gameface bridge)."""
from wgmod_research.bridge import wulf_args as w


class _WulfMap(object):
    """Stand-in for a Wulf-wrapped map: not a dict, but has .get(key)."""
    def __init__(self, d):
        self._d = d

    def get(self, key):
        return self._d.get(key)


# --- map_get ----------------------------------------------------------------

def test_map_get_from_dict():
    assert w.map_get({"x": 5}, "x") == 5


def test_map_get_from_wulf_map():
    assert w.map_get(_WulfMap({"y": 7}), "y") == 7


def test_map_get_missing_key():
    assert w.map_get({"x": 5}, "y") is None
    assert w.map_get(_WulfMap({"x": 5}), "y") is None


def test_map_get_scalar_is_none():
    assert w.map_get(42, "x") is None
    assert w.map_get(None, "x") is None


# --- cmd_int_arg ------------------------------------------------------------

def test_cmd_int_arg_dict_value():
    assert w.cmd_int_arg([{"value": 123}]) == 123


def test_cmd_int_arg_dict_id_fallback():
    assert w.cmd_int_arg([{"id": 456}]) == 456


def test_cmd_int_arg_wulf_map():
    assert w.cmd_int_arg([_WulfMap({"value": 789})]) == 789


def test_cmd_int_arg_bare_scalar():
    assert w.cmd_int_arg([321]) == 321


def test_cmd_int_arg_string_number_coerced():
    assert w.cmd_int_arg([{"value": "55"}]) == 55


def test_cmd_int_arg_empty_is_zero():
    assert w.cmd_int_arg([]) == 0
    assert w.cmd_int_arg(None) == 0


def test_cmd_int_arg_invalid_is_zero():
    assert w.cmd_int_arg([{"value": "nope"}]) == 0
    assert w.cmd_int_arg([{"value": None}]) == 0


# --- cmd_xy_arg -------------------------------------------------------------

def test_cmd_xy_arg_dict():
    assert w.cmd_xy_arg([{"x": 10, "y": 20}]) == (10, 20)


def test_cmd_xy_arg_wulf_map():
    assert w.cmd_xy_arg([_WulfMap({"x": 3, "y": 4})]) == (3, 4)


def test_cmd_xy_arg_missing_keys_default_zero():
    assert w.cmd_xy_arg([{"x": 10}]) == (10, 0)


def test_cmd_xy_arg_empty_is_origin():
    assert w.cmd_xy_arg([]) == (0, 0)
    assert w.cmd_xy_arg(None) == (0, 0)

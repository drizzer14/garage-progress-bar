# -*- coding: utf-8 -*-
"""Unit tests for `_compat._scrub_paths` -- strips absolute filesystem paths (drive
letter, install dir, username) out of exception-traceback text before it's logged, so
a player's python.log never leaks their machine layout."""
from wgmod_research import _compat as c


def test_scrub_windows_absolute_traceback_frame():
    line = (
        'File "C:\\Users\\Ivan\\Games\\WoT_EU\\mods\\2.3.1.2\\'
        'com.14th_ua.garageprogressbar_6.0.0.wotmod\\res\\scripts\\client\\'
        'wgmod_research\\bridge\\gameface_bridge.py", line 88'
    )
    result = c._scrub_paths(line)
    assert "C:" not in result
    assert "Ivan" not in result
    assert "WoT_EU" not in result
    assert "garageprogressbar" not in result
    assert 'scripts\\client\\wgmod_research\\bridge\\gameface_bridge.py' in result
    assert "line 88" in result


def test_scrub_forward_slash_wotmod_packed_variant():
    line = (
        'File "C:/Users/Ivan/Games/WoT_EU/mods/2.3.1.2/'
        'com.14th_ua.garageprogressbar_6.0.0.wotmod/res/scripts/client/'
        'wgmod_research/bridge/gameface_bridge.py", line 88'
    )
    result = c._scrub_paths(line)
    assert "C:" not in result
    assert "Ivan" not in result
    assert "WoT_EU" not in result
    assert 'scripts/client/wgmod_research/bridge/gameface_bridge.py' in result
    assert "line 88" in result


def test_scrub_non_client_absolute_path_has_no_client_anchor():
    line = 'File "C:\\Users\\Ivan\\Games\\WoT_EU\\res\\scripts\\common\\items.py", line 42'
    result = c._scrub_paths(line)
    assert "C:" not in result
    assert "Ivan" not in result
    assert "WoT_EU" not in result
    # No scripts/client anchor here -> falls back to bare filename.
    assert result == 'File "items.py", line 42'


def test_scrub_unc_absolute_traceback_frame():
    line = (
        'File "\\\\BUILD-HOST\\share\\WoT_EU\\mods\\2.3.1.2\\'
        'com.14th_ua.garageprogressbar_6.0.0.wotmod\\res\\scripts\\client\\'
        'wgmod_research\\bridge\\gameface_bridge.py", line 88'
    )
    result = c._scrub_paths(line)
    assert "BUILD-HOST" not in result
    assert 'scripts\\client\\wgmod_research\\bridge\\gameface_bridge.py' in result
    assert "line 88" in result


def test_scrub_posix_absolute_path():
    line = 'File "/home/ivan/wot/install/res/scripts/client/wgmod_research/builder.py", line 12'
    result = c._scrub_paths(line)
    assert "/home" not in result
    assert "ivan" not in result
    assert 'scripts/client/wgmod_research/builder.py' in result
    assert "line 12" in result


def test_scrub_multiline_traceback_scrubs_every_frame():
    text = (
        "Traceback (most recent call last):\n"
        '  File "C:\\Users\\Ivan\\Games\\WoT_EU\\mods\\2.3.1.2\\'
        'com.14th_ua.garageprogressbar_6.0.0.wotmod\\res\\scripts\\client\\'
        'wgmod_research\\bridge\\gameface_bridge.py", line 88, in refresh\n'
        "    push_model(vm)\n"
        '  File "C:\\Users\\Ivan\\Games\\WoT_EU\\mods\\2.3.1.2\\'
        'com.14th_ua.garageprogressbar_6.0.0.wotmod\\res\\scripts\\client\\'
        'wgmod_research\\domain\\builder.py", line 40, in build_model\n'
        "    raise ValueError('boom')\n"
        "ValueError: boom"
    )
    result = c._scrub_paths(text)
    assert "C:" not in result
    assert "Ivan" not in result
    assert "WoT_EU" not in result
    assert result.count('scripts\\client\\wgmod_research\\bridge\\gameface_bridge.py') == 1
    assert result.count('scripts\\client\\wgmod_research\\domain\\builder.py') == 1
    assert "line 88" in result
    assert "line 40" in result


def test_scrub_benign_line_without_path_is_unchanged():
    line = "ValueError: unexpected 'None' for research snapshot"
    assert c._scrub_paths(line) == line


def test_scrub_empty_text_passthrough():
    assert c._scrub_paths("") == ""
    assert c._scrub_paths(None) is None

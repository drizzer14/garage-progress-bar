# -*- coding: utf-8 -*-
"""PC-only reader for the tech-tree unlock subsystem (EU 2.3).

Extracted from engine_adapter.py (Tier 3g): reads the selected vehicle's unlock
graph (modules + next vehicles, incl. Tier XI) into [UnlockItem].
engine_adapter.build_snapshot() calls read_tech_unlocks (imported there under its old
private alias _read_tech_unlocks). Shares only the items-cache accessor with the other
readers, via adapter._read_common. Every read is guarded so one bad unlock row never
sinks the whole subsystem. Game symbols verified against the EU 2.3 decompiled client.
"""
from items import getTypeOfCompactDescr
from gui.shared.gui_items import GUI_ITEM_TYPE

from wgmod_research._compat import LOG_CURRENT_EXCEPTION
from wgmod_research.adapter import i18n
from wgmod_research.adapter._read_common import _items_cache
from wgmod_research.adapter.format import roman as _roman, module_big_icon as _module_big_icon
from wgmod_research.domain import types as t
from wgmod_research.domain.constants import Category


def _unlock_name(cache, int_cd):
    """Localized display name for an unlock id, or "" on any read failure (so one
    bad prerequisite never sinks the whole unlock row)."""
    try:
        return getattr(cache.items.getItemByCD(int_cd), "userName", "") or ""
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return ""


def read_tech_unlocks(veh, unlocks):
    """Tech-tree unlocks: modules + next vehicles (incl. Tier XI) via the
    vehicle's unlock graph. getUnlocksDescrs() yields (idx, xpCost, intCD, prereqs)."""
    try:
        cache = _items_cache()
        out = []
        for _idx, xp_cost, int_cd, prereqs in veh.getUnlocksDescrs():
            try:
                item_type = getTypeOfCompactDescr(int_cd)
                is_vehicle = item_type == GUI_ITEM_TYPE.VEHICLE
                item = cache.items.getItemByCD(int_cd)
                name = getattr(item, "userName", "") or ""
                # item.icon is the right art for both kinds, as img:// URLs:
                #  - module: the generic module-TYPE glyph (chassis/engine/tower/
                #    gun/radio under img://gui/maps/icons/modules/, 48x48) -- the
                #    same icons the in-battle info panel uses.
                #  - vehicle: the framed tech-tree-node icon (~160x100). NOT
                #    iconSmall -- that's the carousel contour strip, cropped
                #    edge-to-edge so it reads as "cut off".
                icon = getattr(item, "icon", "") or ""
                if not is_vehicle:
                    # Modules only: upgrade the 48x48 type glyph to its 80x80 `Big`
                    # sibling. Vehicle node art is a different, already-large asset.
                    icon = _module_big_icon(icon)
                # Tooltip caption: a next vehicle shows its tier ("Tier IX"); a
                # module shows its type ("Gun"/"Turret"/...). item.level on a
                # vehicle item is its tier. Both are localized to the client language
                # -- the tier word via i18n, the module type via the GUI item's own
                # already-localized `userType` (covers wheels/dual-gun/etc. too).
                if is_vehicle:
                    tier = int(getattr(item, "level", 0) or 0)
                    kind_label = i18n.tier_label(_roman(tier))
                else:
                    kind_label = getattr(item, "userType", "") or ""
            except Exception:
                LOG_CURRENT_EXCEPTION()
                is_vehicle, name, icon, kind_label = False, "", "", ""
            # Names of the prerequisite items not yet researched -> "Requires: ..."
            # in the tooltip. Only resolved when something is actually missing.
            missing = [p for p in prereqs if p not in unlocks]
            prereq_names = [nm for nm in (_unlock_name(cache, p) for p in missing) if nm]
            out.append(t.UnlockItem(
                int_cd=int_cd, name=name, icon=icon, xp_cost=int(xp_cost),
                kind=(Category.VEHICLE if is_vehicle else Category.MODULE),
                researched=(int_cd in unlocks),
                prereqs_met=(not missing),
                kind_label=kind_label, prereq_names=prereq_names))
        return out
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return []

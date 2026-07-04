# -*- coding: utf-8 -*-
"""Engine-free data types shared by the domain layer. 2/3 compatible.

EU 2.3 model (verified against the decompiled client source):
the selected vehicle's research is a single XP axis with two phases — tech-tree
research (modules + next vehicles, Tier XI included as an ordinary unlock), then
Field Modifications ("upgrades") once the vehicle is fully researched (elite).

Once a vehicle is elite and its field mods are done, EU 2.3 still has the global
**Elite Levels** system (internal codename "prestige", WG update 1.22.1): a
cosmetic 0..350 per-vehicle progression earned via combat XP, split into grade
bands (iron/bronze/silver/gold/enamel -> max). Certain tiers (the owner's tier XI)
additionally grant **milestone rewards** (2D styles / attachments) at specific
levels. So past COMPLETE the bar shows ELITE_REWARDS (tier-XI exclusive rewards,
while any remain) -> ELITE (the grade-band progression) -> COMPLETE (no prestige
data / fallback badge).
"""


class Mode(object):
    TECH_TREE = "tech_tree"     # not fully researched: modules + next vehicles
    FIELD_MODS = "field_mods"   # elite: remaining field-modification ("upgrade") steps
    SKILL_TREE = "skill_tree"   # tier-XI upgrade: branching skill tree, shown as an
                                # aggregate XP readout (remaining XP to fully upgrade)
    POTENTIAL_TIER_XI = "potential_tier_xi"  # opt-in: a tier-X tank with NO real tier XI,
                                # fully done -> a speculative bar tracking banked spendable
                                # XP toward a representative tier-XI cost (sits above ELITE)
    ELITE_REWARDS = "elite_rewards"  # tier XI w/ unearned milestone rewards: reward roadmap
    ELITE = "elite"             # elite + prestige: current grade-band progression
    COMPLETE = "complete"       # elite, no prestige data: "fully researched" badge
    HIDDEN = "hidden"           # the mode this vehicle resolved to is disabled by a user
                                # toggle -> hide the bar (bar_visible returns False)


class Tick(object):
    def __init__(self, xp_position, category, icon, name,
                 xp_gained, xp_required, affordable, completed, locked=False,
                 level=0, options=None, state="", action_id=0,
                 kind_label="", prereq_names=None, effect="", option_effects=None,
                 done=False, int_cd=0):
        self.xp_position = xp_position
        # vehicle | module (tech-tree unlock kind) | fieldmod. Drives the
        # per-tick glyph in the view (a bar is all-tech-tree or all-field-mods,
        # so within tech-tree this distinguishes the next-tank tick from modules).
        self.category = category
        self.icon = icon
        self.name = name
        self.xp_gained = xp_gained
        self.xp_required = xp_required
        self.affordable = affordable
        self.completed = completed
        # True = prerequisites not yet met, so this item can't be researched yet
        # even if affordable (only meaningful for tech-tree unlocks).
        self.locked = locked
        # Field-modification level (1..N) -> the roman numeral shown in the
        # hexagon glyph. 0 for non-field-mod ticks.
        self.level = level
        # The two selectable variants of this level's paired modification
        # (MultiModsItem), e.g. ["Anti-Reflective Optics Coating", "External
        # Vision System"] -> listed in the hover tooltip. Empty for levels with
        # no pair choice (features, role slots) and for tech-tree ticks.
        self.options = options or []
        # Elite-mode mark state: "achieved" | "next" | "upcoming" (empty for
        # tech-tree / field-mod ticks). Drives the grade-pip / reward-thumbnail
        # coloring in the ELITE and ELITE_REWARDS views.
        self.state = state
        # Identity carried for clickable ticks: the tech-tree unlock int_cd
        # (category 'vehicle'/'module') or the field-mod step_id (category
        # 'fieldmod'). 0 for ticks that aren't individually actionable
        # (skill-tree nodes, elite/reward marks).
        self.action_id = action_id
        # Tech-tree only: a short "kind" caption for the tooltip -- the module type
        # ("Gun"/"Turret"/"Engine"/"Chassis"/"Radio") or, for a next-vehicle
        # unlock, its tier ("Tier IX"). Empty for non-tech-tree ticks.
        self.kind_label = kind_label
        # Tech-tree only: names of the still-unresearched prerequisite items
        # blocking a locked unlock -> shown as "Requires: ..." in the tooltip.
        # Empty for unlocked / non-tech-tree ticks.
        self.prereq_names = prereq_names or []
        # Human-readable effect/bonus lines for the tooltip (field-mod KPI text,
        # e.g. "+1% to concealment"), newline-joined for multiple KPIs. Empty when
        # the action carries no labeled KPI (features, role slots, mechanic perks).
        self.effect = effect
        # Per-variant effect summaries for an A/B choice level, aligned with
        # `options` by index (each variant's buffs joined inline). Empty otherwise.
        self.option_effects = option_effects or []
        # Session "done" marker (adapter/recent.py): True on the synthetic first tick
        # for an item just researched via the bar -> the JS green-check + open-screen
        # click. False for every ordinary tick.
        self.done = done
        # The researched item's id, carried ONLY on a done marker so the (engine-bound)
        # bridge can look up its live credits buy price + ownership at marshal time.
        # 0 for ordinary ticks (they use action_id for the actionable id instead).
        self.int_cd = int_cd


class UnlockItem(object):
    """A tech-tree unlock (module or next vehicle, including a Tier XI vehicle)."""
    def __init__(self, int_cd, name, icon, xp_cost, kind, researched, prereqs_met,
                 kind_label="", prereq_names=None, xp_cost_effective=None, owned=False):
        self.int_cd = int_cd
        self.name = name
        self.icon = icon
        self.xp_cost = xp_cost
        # Effective (post-discount) XP cost. For a next-vehicle unlock the player holds
        # blueprint fragments for, this is the discounted price; modules and un-
        # discounted vehicles keep the raw cost. The techtree resolver prices/positions
        # each tick from this (defaulting to xp_cost when absent), so the bar reflects
        # what the player would actually pay. Modules MUST stay on raw cost (WG's
        # validator rejects a module unlocked at a differing cost).
        self.xp_cost_effective = xp_cost if xp_cost_effective is None else xp_cost_effective
        self.kind = kind                  # 'module' | 'vehicle'
        self.researched = researched
        # Owned = the module sits in the player's inventory (bought this session or
        # earlier). Modules only; vehicles keep the default False. Drives the self-
        # clearing of a "buy + mount" done marker once the module is purchased.
        self.owned = owned
        self.prereqs_met = prereqs_met
        # Display caption for the tooltip: module type ("Gun"/"Turret"/...) or the
        # next vehicle's tier ("Tier IX"). Empty if it couldn't be determined.
        self.kind_label = kind_label
        # Names of the still-unresearched prerequisite items (when prereqs_met is
        # False) -> the tooltip's "Requires: ..." line. Empty otherwise.
        self.prereq_names = prereq_names or []


class ProgressionStep(object):
    """A field-modification step (post-progression tree node, paid with XP)."""
    def __init__(self, step_id, name, icon, xp_cost, unlocked, level=0,
                 options=None, description="", option_effects=None, category="",
                 done=False):
        self.step_id = step_id
        self.name = name
        self.icon = icon
        self.xp_cost = xp_cost
        self.unlocked = unlocked          # already received/earned
        self.level = level                # field-mod level (1..N) -> roman numeral
        # Localized tooltip sub-heading for a tier-XI skill node (its Upgrades-screen
        # category, e.g. "Mechanic Upgrade" / "Special Upgrade"). Empty for field mods.
        self.category = category
        # variant names of the paired choice (MultiModsItem) at this level.
        self.options = options or []
        # Human-readable effect/bonus text (KPI lines, newline-joined), e.g.
        # "+1% to concealment". Empty when the action exposes no labeled KPI.
        self.description = description
        # Per-variant effect summaries, aligned with `options` by index: each is
        # that variant's own buffs joined inline (" · "). Empty for non-choice
        # steps. e.g. ["+5% to aiming speed · +3% to aiming circle size", ...].
        self.option_effects = option_effects or []
        # Session "done" marker (adapter/recent.py): True on the synthetic tier-XI
        # chip for a node just unlocked via the bar -> sorted first + open-screen
        # click. False for ordinary available-upgrade chips.
        self.done = done


class EliteGrade(object):
    """One prestige grade threshold (engine-free). `grade` is the complex-grade
    family id ('iron'/'bronze'/'silver'/'gold'/'enamel'/'prestige'/'undefined');
    `sub` is the sub-grade number 1..4 (-1 for the synthetic MAX grade). `level`
    is the prestige level at which this (sub-)grade is reached; `main` marks the
    major grade boundaries the game shows on its own scale."""
    def __init__(self, level, grade, sub, main=False):
        self.level = level
        self.grade = grade
        self.sub = sub
        self.main = main


class EliteReward(object):
    """One tier-exclusive milestone reward (engine-free). Granted at prestige
    `level`; `achieved` once earned; `icon` is an img:// thumbnail (may be empty
    if the art didn't resolve); `label` is the reward's user name; `type_label`
    is its category ('2D Style' etc.)."""
    def __init__(self, level, achieved, icon="", label="", type_label=""):
        self.level = level
        self.achieved = achieved
        self.icon = icon
        self.label = label
        self.type_label = type_label


class VehicleSnapshot(object):
    """Engine-free description of the selected vehicle's research state.

    The engine adapter produces this; the domain layer consumes only this.
    All XP fields are real ints (never None) and lists are in natural
    progression order.
    """
    def __init__(self, tier, is_elite, vehicle_xp, free_xp,
                 tech_unlocks=None, field_mod_steps=None,
                 fieldmods_done=0, fieldmods_total=0, vehicle_class="",
                 has_prestige=False, elite_level=0, elite_max_level=0,
                 elite_current_xp=0, elite_next_xp=0,
                 elite_grades=None, elite_rewards=None, elite_level_xp=None,
                 is_skill_tree=False, skilltree_total_xp=0,
                 skilltree_spent_xp=0, skilltree_done=0, skilltree_total=0,
                 skilltree_final_icon="", skilltree_final_name="",
                 skilltree_final_xp=0, skilltree_available=None,
                 skilltree_final_effect="", vehicle_int_cd=0,
                 avg_battle_xp=0, battle_count=0, account_avg_battle_xp=0,
                 reserve_mult=100, daily_double_factor=100, max_battle_xp=0):
        self.tier = tier                          # 1..11
        self.is_elite = is_elite                  # True = fully researched
        self.vehicle_xp = vehicle_xp              # unspent accumulated vehicle XP
        self.free_xp = free_xp                    # global free XP
        self.tech_unlocks = tech_unlocks or []    # [UnlockItem]
        self.field_mod_steps = field_mod_steps or []   # [ProgressionStep]
        # Researched / total field-mod LEVELS within the tier cap -> the header
        # counter (multi-mod choice slots are not counted).
        self.fieldmods_done = fieldmods_done
        self.fieldmods_total = fieldmods_total
        # vehicle class id ('mediumTank' etc.) for the elite badge in COMPLETE.
        self.vehicle_class = vehicle_class
        # --- Elite Levels (prestige) system; all default to "no prestige" so a
        # vehicle without prestige data falls back to the COMPLETE badge. ---
        self.has_prestige = has_prestige          # gate (elite + prestige enabled)
        self.elite_level = elite_level            # current elite level (0..max)
        self.elite_max_level = elite_max_level    # cap (350 in EU 2.3)
        self.elite_current_xp = elite_current_xp  # progress within current level
        self.elite_next_xp = elite_next_xp        # XP needed for the next level
        self.elite_grades = elite_grades or []    # [EliteGrade] sorted by level
        self.elite_rewards = elite_rewards or []  # [EliteReward] sorted by level
        # {level -> cumulative combat XP required to REACH that level}. Used to
        # show each milestone's XP "cost" in its tooltip. Empty if unavailable.
        self.elite_level_xp = elite_level_xp or {}
        # --- Tier-XI "vehicle skill tree" upgrade (branching post-progression).
        # The tree is non-linear, so the bar is a COUNT readout: axis = total
        # priced nodes, fill = nodes unlocked, with one tick per node and the
        # signature 'final' node flagged at the end. XP totals are kept for
        # reference but no longer drive the bar. ---
        self.is_skill_tree = is_skill_tree              # branching upgrade tree (id >= 10000)
        self.skilltree_total_xp = skilltree_total_xp    # full-upgrade cost (sum of ALL priced nodes); informational
        self.skilltree_spent_xp = skilltree_spent_xp    # XP invested (sum of RECEIVED node prices); informational
        self.skilltree_done = skilltree_done            # unlocked nodes
        self.skilltree_total = skilltree_total          # total priced nodes
        self.skilltree_final_icon = skilltree_final_icon  # img:// art of the 'final' node (end tick)
        self.skilltree_final_name = skilltree_final_name  # final node name (end-tick tooltip)
        self.skilltree_final_xp = skilltree_final_xp      # final node XP cost (end-tick tooltip)
        self.skilltree_final_effect = skilltree_final_effect  # final node buff text (end-tick tooltip)
        # Available frontier upgrade nodes (not received, prerequisites met) ->
        # the clickable "Upgrades Available:" chips. [ProgressionStep] (step_id,
        # name, icon, xp_cost). Empty for non-skill-tree vehicles.
        self.skilltree_available = skilltree_available or []
        # The selected vehicle's global compact-descriptor id. Used only to scope
        # session "done" markers (adapter/recent.py) per vehicle -- the domain
        # itself never reads it. 0 when unavailable.
        self.vehicle_int_cd = vehicle_int_cd
        # Historical average combat XP per RANDOM battle for this vehicle (the garage
        # "avg XP" figure). 0 when the tank has no random battles / unreadable. The
        # view divides an XP shortfall by this to estimate "battles remaining" in a
        # tooltip; the domain only carries it through to the model.
        self.avg_battle_xp = avg_battle_xp
        # --- Rest of the "battles remaining" estimate inputs, likewise carried straight
        # through to the model for the view's "≈ M-N battles" range (see WGModResearch.js
        # xpFracHtml). Neutral defaults leave the estimate at today's single-number form. ---
        self.battle_count = battle_count              # random battles behind avg_battle_xp
        self.account_avg_battle_xp = account_avg_battle_xp  # fallback divisor (under-sampled tank)
        self.reserve_mult = reserve_mult              # active XP-reserve multiplier, int % (100 = x1.0)
        self.daily_double_factor = daily_double_factor  # first-win-of-day factor, int % (100 = x1.0)
        self.max_battle_xp = max_battle_xp            # best single random battle -> range's optimistic bound


class ResearchProgressModel(object):
    """Output of build_model(). Fill is two stacked segments (vehicle XP, then
    free XP); the view draws fill_vehicle first and fill_free on top."""
    def __init__(self, mode, scale_min, scale_max,
                 fill_vehicle, fill_free, ticks,
                 fieldmods_done=0, fieldmods_total=0, vehicle_class="",
                 elite_level=0, elite_max_level=0, elite_grade="", elite_sub=0,
                 elite_current_icon="",
                 combat_xp=0, avail_upgrades=None, spendable_xp=0,
                 avg_battle_xp=0, battle_count=0, account_avg_battle_xp=0,
                 reserve_mult=100, daily_double_factor=100, max_battle_xp=0):
        self.mode = mode
        self.scale_min = scale_min
        self.scale_max = scale_max
        self.fill_vehicle = fill_vehicle       # first stacked segment (vehicle XP)
        self.fill_free = fill_free             # second stacked segment (free XP)
        # Total spendable XP (vehicle combat XP + global free XP), the same figure
        # the header readout shows. Surfaced as one model field (not per-tick, since
        # it's identical for every tick) so the view can compute per-item
        # affordability in EVERY mode -- including skill_tree, whose fill is a node
        # COUNT rather than an XP value.
        self.spendable_xp = spendable_xp
        self.ticks = ticks                     # [Tick], ordered by xp_position
        self.fieldmods_done = fieldmods_done   # researched/total field-mod levels
        self.fieldmods_total = fieldmods_total
        self.vehicle_class = vehicle_class     # for the elite badge in COMPLETE
        # --- ELITE / ELITE_REWARDS modes: the grade-band axis reuses
        # scale_min/scale_max + ticks + fill_vehicle (fill_free stays 0). ---
        self.elite_level = elite_level         # current elite level (for "N/350")
        self.elite_max_level = elite_max_level
        self.elite_grade = elite_grade         # complex-grade family id
        self.elite_sub = elite_sub             # current sub-grade (1..4)
        # Emblem URL for the grade currently REACHED (family+sub), shown in the
        # category-icon slot with the current level number over it, in BOTH elite
        # modes. "" below the first grade / no grades -> class+elite badge fallback.
        self.elite_current_icon = elite_current_icon
        self.combat_xp = combat_xp             # cumulative combat XP readout
        # SKILL_TREE mode: available frontier upgrade nodes (clickable chips).
        # [ProgressionStep] (step_id, name, icon, xp_cost). Empty in other modes.
        self.avail_upgrades = avail_upgrades or []
        # Historical average combat XP per random battle (from the snapshot). Carried
        # on every model so the view can estimate "battles remaining" beside an XP
        # shortfall in any mode's tooltip; 0 hides that estimate (no battles / unread).
        self.avg_battle_xp = avg_battle_xp
        # Rest of the estimate inputs (see VehicleSnapshot) -> the view's "≈ M-N battles"
        # range: battle count (sample-size / fallback gate), account-wide avg (fallback
        # divisor), and the optimistic-bound bonuses (int %, 100 = x1.0).
        self.battle_count = battle_count
        self.account_avg_battle_xp = account_avg_battle_xp
        self.reserve_mult = reserve_mult
        self.daily_double_factor = daily_double_factor
        self.max_battle_xp = max_battle_xp

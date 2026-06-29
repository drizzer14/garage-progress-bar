# -*- coding: utf-8 -*-
"""Engine-free data types shared by the domain layer. 2/3 compatible.

EU 2.3 model (verified in docs/superpowers/research/decompiled-findings.md):
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
data / fallback badge). The earlier "EU dropped elite/Paragons" note was wrong;
it conflated this with Lesta's separate RU "Paragon" mechanic.
"""


class Mode(object):
    TECH_TREE = "tech_tree"     # not fully researched: modules + next vehicles
    FIELD_MODS = "field_mods"   # elite: remaining field-modification ("upgrade") steps
    SKILL_TREE = "skill_tree"   # tier-XI upgrade: branching skill tree, shown as an
                                # aggregate XP readout (remaining XP to fully upgrade)
    ELITE_REWARDS = "elite_rewards"  # tier XI w/ unearned milestone rewards: reward roadmap
    ELITE = "elite"             # elite + prestige: current grade-band progression
    COMPLETE = "complete"       # elite, no prestige data: "fully researched" badge


class Tick(object):
    def __init__(self, xp_position, category, icon, name,
                 xp_gained, xp_required, affordable, completed, locked=False,
                 level=0, options=None, state=""):
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


class UnlockItem(object):
    """A tech-tree unlock (module or next vehicle, including a Tier XI vehicle)."""
    def __init__(self, int_cd, name, icon, xp_cost, kind, researched, prereqs_met):
        self.int_cd = int_cd
        self.name = name
        self.icon = icon
        self.xp_cost = xp_cost
        self.kind = kind                  # 'module' | 'vehicle'
        self.researched = researched
        self.prereqs_met = prereqs_met


class ProgressionStep(object):
    """A field-modification step (post-progression tree node, paid with XP)."""
    def __init__(self, step_id, name, icon, xp_cost, unlocked, level=0,
                 options=None):
        self.step_id = step_id
        self.name = name
        self.icon = icon
        self.xp_cost = xp_cost
        self.unlocked = unlocked          # already received/earned
        self.level = level                # field-mod level (1..N) -> roman numeral
        # variant names of the paired choice (MultiModsItem) at this level.
        self.options = options or []


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
                 skilltree_spent_xp=0, skilltree_done=0, skilltree_total=0):
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
        # --- Tier-XI "vehicle skill tree" upgrade (branching post-progression). A
        # skill-tree vehicle is shown as an aggregate, monotonic "% upgraded"
        # readout: the bar axis is the FIXED full-upgrade cost and the fill is the
        # cumulative XP already invested (it only grows as nodes are unlocked). ---
        self.is_skill_tree = is_skill_tree              # branching upgrade tree (id >= 10000)
        self.skilltree_total_xp = skilltree_total_xp    # fixed full-upgrade cost (sum of ALL priced nodes)
        self.skilltree_spent_xp = skilltree_spent_xp    # cumulative XP invested (sum of RECEIVED node prices)
        self.skilltree_done = skilltree_done            # unlocked nodes
        self.skilltree_total = skilltree_total          # total priced nodes


class ResearchProgressModel(object):
    """Output of build_model(). Fill is two stacked segments (vehicle XP, then
    free XP); the view draws fill_vehicle first and fill_free on top."""
    def __init__(self, mode, scale_min, scale_max,
                 fill_vehicle, fill_free, ticks,
                 fieldmods_done=0, fieldmods_total=0, vehicle_class="",
                 elite_level=0, elite_max_level=0, elite_grade="", elite_sub=0,
                 combat_xp=0):
        self.mode = mode
        self.scale_min = scale_min
        self.scale_max = scale_max
        self.fill_vehicle = fill_vehicle       # first stacked segment (vehicle XP)
        self.fill_free = fill_free             # second stacked segment (free XP)
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
        self.combat_xp = combat_xp             # cumulative combat XP readout

# -*- coding: utf-8 -*-
"""Wulf ViewModel definitions for the widget's data channel.

Extracted from gameface_bridge.py (which owns the listeners, refresh scheduling,
click handlers, and the push/marshal path) so the pure schema lives on its own. Three
models: TickVM (one bar tick), UpgradeVM (one tier-XI "available" chip), and ResearchVM
(the root model exposed as `wgResearch`, holding the scalar fields + the ticks/availUpgrades
arrays + the reverse-channel commands).

IMPORTANT -- the numeric property indices below are HAND-MAINTAINED and MUST match the
_addXProperty registration order: `_setNumber(i, v)` / `_setString(i, v)` address the
i-th registered property, so reordering or inserting a property without renumbering every
setter silently mismaps fields. The JS reader (WGModResearch.js) reads these by NAME, so
the names are the contract with the widget. PC-only (needs the live frameworks.wulf).
"""
from frameworks.wulf import ViewModel, Array


class TickVM(ViewModel):
    def __init__(self, properties=17, commands=0):
        super(TickVM, self).__init__(properties=properties, commands=commands)

    def _initialize(self):
        super(TickVM, self)._initialize()
        self._addNumberProperty("position", 0)   # 0
        self._addNumberProperty("xpRequired", 0)  # 1
        self._addStringProperty("category", "")  # 2
        self._addStringProperty("name", "")      # 3
        self._addBoolProperty("affordable", False)  # 4
        self._addBoolProperty("locked", False)   # 5
        self._addStringProperty("icon", "")      # 6 (img:// URL, may be empty)
        self._addNumberProperty("level", 0)      # 7 (field-mod level -> roman)
        self._addStringProperty("options", "")   # 8 (pair variants, \n-joined)
        self._addStringProperty("state", "")     # 9 (elite mark: achieved/next/upcoming)
        self._addNumberProperty("actionId", 0)   # 10 (tech-tree int_cd / field-mod step_id; 0 = not clickable)
        self._addStringProperty("kindLabel", "")  # 11 (tech-tree: "Gun"/"Tier IX" caption)
        self._addStringProperty("prereqNames", "")  # 12 (locked tech-tree: blockers, \n-joined)
        self._addStringProperty("effect", "")     # 13 (field-mod KPI bonus lines, \n-joined)
        self._addStringProperty("optionEffects", "")  # 14 (per-variant buffs, \n-joined, aligned w/ options)
        self._addBoolProperty("done", False)      # 15 (session "done" marker: green check + open-screen click)
        self._addNumberProperty("price", 0)       # 16 (done tick: credits buy price, 0 = hide footer)

    def setPosition(self, v):
        self._setNumber(0, v)

    def setXpRequired(self, v):
        self._setNumber(1, v)

    def setCategory(self, v):
        self._setString(2, v)

    def setName(self, v):
        self._setString(3, v)

    def setAffordable(self, v):
        self._setBool(4, v)

    def setLocked(self, v):
        self._setBool(5, v)

    def setIcon(self, v):
        self._setString(6, v)

    def setLevel(self, v):
        self._setNumber(7, v)

    def setOptions(self, v):
        self._setString(8, v)

    def setState(self, v):
        self._setString(9, v)

    def setActionId(self, v):
        self._setNumber(10, v)

    def setKindLabel(self, v):
        self._setString(11, v)

    def setPrereqNames(self, v):
        self._setString(12, v)

    def setEffect(self, v):
        self._setString(13, v)

    def setOptionEffects(self, v):
        self._setString(14, v)

    def setDone(self, v):
        self._setBool(15, v)

    def setPrice(self, v):
        self._setNumber(16, v)


class UpgradeVM(ViewModel):
    """One available tier-XI upgrade node -> a clickable 'Upgrades Available' chip."""
    def __init__(self, properties=7, commands=0):
        super(UpgradeVM, self).__init__(properties=properties, commands=commands)

    def _initialize(self):
        super(UpgradeVM, self)._initialize()
        self._addNumberProperty("actionId", 0)    # 0 (skill-tree step_id)
        self._addStringProperty("icon", "")        # 1 (img:// URL)
        self._addStringProperty("name", "")        # 2
        self._addNumberProperty("xpRequired", 0)   # 3
        self._addStringProperty("effect", "")      # 4 (perk KPI bonus lines, \n-joined)
        self._addStringProperty("category", "")    # 5 (localized node sub-heading caption)
        self._addBoolProperty("done", False)       # 6 (session "done" marker: green check + open-screen click)

    def setActionId(self, v):
        self._setNumber(0, v)

    def setIcon(self, v):
        self._setString(1, v)

    def setName(self, v):
        self._setString(2, v)

    def setXpRequired(self, v):
        self._setNumber(3, v)

    def setEffect(self, v):
        self._setString(4, v)

    def setCategory(self, v):
        self._setString(5, v)

    def setDone(self, v):
        self._setBool(6, v)


class ResearchVM(ViewModel):
    def __init__(self, properties=38, commands=8):
        super(ResearchVM, self).__init__(properties=properties, commands=commands)

    def _initialize(self):
        super(ResearchVM, self)._initialize()
        self._addStringProperty("mode", "")        # 0
        self._addNumberProperty("scaleMin", 0)     # 1
        self._addNumberProperty("scaleMax", 0)     # 2
        self._addNumberProperty("fillVehicle", 0)  # 3
        self._addNumberProperty("fillFree", 0)     # 4
        self._addArrayProperty("ticks", Array())   # 5
        self._addNumberProperty("fieldModsDone", 0)   # 6
        self._addNumberProperty("fieldModsTotal", 0)  # 7
        self._addStringProperty("vehicleClass", "")  # 8 (for elite badge)
        self._addNumberProperty("eliteLevel", 0)     # 9
        self._addNumberProperty("eliteMaxLevel", 0)  # 10
        self._addStringProperty("eliteGrade", "")    # 11 (grade family id)
        self._addNumberProperty("eliteSub", 0)       # 12 (current sub-grade 1..4)
        self._addNumberProperty("combatXp", 0)       # 13 (cumulative combat XP)
        self._addBoolProperty("visible", True)        # 14 (false hides the bar)
        self._addArrayProperty("availUpgrades", Array())  # 15 ([UpgradeVM] -> chips)
        self._addNumberProperty("spendableXp", 0)    # 16 (vehicle XP + free XP, for affordability)
        self._addBoolProperty("colorBlind", False)   # 17 (mirror WoT's color-blind mode)
        self._addNumberProperty("posX", 0)           # 18 (bar center-x px; 0 = auto/CSS default)
        self._addNumberProperty("posY", 0)           # 19 (bar top px; 0 = auto/CSS default)
        self._addStringProperty("eliteCurrentIcon", "")  # 20 (current-grade emblem for the category icon)
        self._addStringProperty("labels", "")        # 21 (JSON bundle of localized widget labels; see i18n.widget_labels)
        self._addNumberProperty("avgBattleXp", 0)    # 22 (this tank's avg combat XP/random battle; 0 hides the estimate)
        # --- Rest of the "battles remaining" estimate inputs (see WGModResearch.js
        # xpFracHtml): the range's divisor selection + optimistic-bound bonuses. ---
        self._addNumberProperty("battleCount", 0)          # 23 (this tank's random battle count; sample-size / fallback gate)
        self._addNumberProperty("accountAvgBattleXp", 0)   # 24 (account-wide avg XP; fallback divisor for an under-sampled tank)
        self._addNumberProperty("reserveMult", 100)        # 25 (active XP-reserve multiplier, % x100; 100 = x1.0)
        self._addNumberProperty("dailyDoubleFactor", 100)  # 26 (first-win-of-day factor, % x100; 100 = x1.0)
        self._addNumberProperty("maxBattleXp", 0)          # 27 (this tank's best single random battle; range's optimistic bound)
        self._addNumberProperty("posW", 0)   # 28 (viewport px a pinned posX/posY was captured at; 0 = unknown)
        self._addNumberProperty("posH", 0)   # 29 (viewport px a pinned posX/posY was captured at; 0 = unknown)
        self._addStringProperty("availModes", "")  # 30 (comma-joined Mode strings for the header mode switch; <2 -> no switch)
        self._addBoolProperty("ignoreFreeXp", False)  # 31 ("Ignore Free XP" setting: draw the combat-XP glyph, hide the free-XP tone)
        self._addNumberProperty("rev", 0)  # 32 (monotonic push counter; the JS poll re-renders when it changes -- cold-mount self-heal, see WGModResearch.js)
        self._addNumberProperty("scale", 0)  # 33 (bar scale index: 0 = Default, 1 = Large; the JS folds the .wg-large override class when 1)
        # XP-readout display controls (see WGModResearch.js). progressCurrent/Required are
        # the unified per-mode scalars (domain model); progressMode/showPercent are the
        # user settings. The widget derives the "%" as min(100, round(cur/req*100)) in JS.
        self._addNumberProperty("progressCurrent", 0)   # 34 (current XP figure for the readout)
        self._addNumberProperty("progressRequired", 0)  # 35 (required XP figure; <= 0 hides the "/" and "%")
        self._addNumberProperty("progressMode", 0)      # 36 (0 = Current, 1 = Current / Required)
        self._addBoolProperty("showPercent", False)     # 37 ("Show Progress %" setting)
        # Reverse channel: JS click handlers invoke these commands. Each returns a
        # command object that connect_commands() wires to a Python handler. Wulf
        # delivers the JS-supplied argument(s) to those handlers.
        self.researchUnlock = self._addCommand("researchUnlock")    # arg: tech-tree int_cd
        self.unlockFieldMod = self._addCommand("unlockFieldMod")    # arg: field-mod step_id
        self.openSkillTree = self._addCommand("openSkillTree")      # no arg
        self.openResearch = self._addCommand("openResearch")        # no arg (done VEHICLE marker click)
        self.openFieldMods = self._addCommand("openFieldMods")      # no arg (done field-mod marker click)
        self.buyMount = self._addCommand("buyMount")                # arg: module int_cd (done MODULE marker: buy + mount)
        self.setPosition = self._addCommand("setPosition")          # arg: {x, y[, w, h][, seed]} px (drag / seed); w/h = capture viewport
        # NB: "selectMode", NOT "setMode" -- setMode is the property-0 setter method below;
        # a same-named command attribute assigned here would shadow it.
        self.selectMode = self._addCommand("selectMode")            # arg: {value: Mode string} (header mode-switch click)

    def setMode(self, v):
        self._setString(0, v)

    def setScaleMin(self, v):
        self._setNumber(1, v)

    def setScaleMax(self, v):
        self._setNumber(2, v)

    def setFillVehicle(self, v):
        self._setNumber(3, v)

    def setFillFree(self, v):
        self._setNumber(4, v)

    def getTicks(self):
        return self._getArray(5)

    def setFieldModsDone(self, v):
        self._setNumber(6, v)

    def setFieldModsTotal(self, v):
        self._setNumber(7, v)

    def setVehicleClass(self, v):
        self._setString(8, v)

    def setEliteLevel(self, v):
        self._setNumber(9, v)

    def setEliteMaxLevel(self, v):
        self._setNumber(10, v)

    def setEliteGrade(self, v):
        self._setString(11, v)

    def setEliteSub(self, v):
        self._setNumber(12, v)

    def setEliteCurrentIcon(self, v):
        self._setString(20, v)

    def setLabels(self, v):
        self._setString(21, v)

    def setAvgBattleXp(self, v):
        self._setNumber(22, v)

    def setBattleCount(self, v):
        self._setNumber(23, v)

    def setAccountAvgBattleXp(self, v):
        self._setNumber(24, v)

    def setReserveMult(self, v):
        self._setNumber(25, v)

    def setDailyDoubleFactor(self, v):
        self._setNumber(26, v)

    def setMaxBattleXp(self, v):
        self._setNumber(27, v)

    def setCombatXp(self, v):
        self._setNumber(13, v)

    def setVisible(self, v):
        self._setBool(14, v)

    def getAvailUpgrades(self):
        return self._getArray(15)

    def setSpendableXp(self, v):
        self._setNumber(16, v)

    def setColorBlind(self, v):
        self._setBool(17, v)

    def setPosX(self, v):
        self._setNumber(18, v)

    def setPosY(self, v):
        self._setNumber(19, v)

    def setPosW(self, v):
        self._setNumber(28, v)

    def setPosH(self, v):
        self._setNumber(29, v)

    def setAvailModes(self, v):
        self._setString(30, v)

    def setIgnoreFreeXp(self, v):
        self._setBool(31, v)

    def setRev(self, v):
        self._setNumber(32, v)

    def setScale(self, v):
        self._setNumber(33, v)

    def setProgressCurrent(self, v):
        self._setNumber(34, v)

    def setProgressRequired(self, v):
        self._setNumber(35, v)

    def setProgressMode(self, v):
        self._setNumber(36, v)

    def setShowPercent(self, v):
        self._setBool(37, v)

    @staticmethod
    def getTicksType():
        return TickVM

    @staticmethod
    def getAvailUpgradesType():
        return UpgradeVM

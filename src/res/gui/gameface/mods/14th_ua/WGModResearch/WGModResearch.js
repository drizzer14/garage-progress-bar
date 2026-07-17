// WGMod research-progress widget. Injected into the hangar document by OpenWG.
// Reads our data model (exposed as `wgResearch` on the host sub-view's model)
// via ModelObserver, and renders a single-axis XP bar with stacked fill + ticks.
import { ModelObserver } from "../../libs/model.js";

// --- Wire contract with the Python side ------------------------------------
// These string VALUES are the Python<->JS contract; they MUST equal the Python
// enums verbatim. Python centralizes them (a typo there is a NameError), but the
// widget used to hard-code the same literals at ~30 sites, where a drift fails
// SILENTLY (a tick renders the wrong glyph, a click no-ops). Hoisted here so each
// value has ONE definition -- keep in lockstep with the enum noted on each block.
const MODE = {                                          // domain/types.py Mode
    TECH_TREE: "tech_tree", FIELD_MODS: "field_mods", SKILL_TREE: "skill_tree",
    POTENTIAL_TIER_XI: "potential_tier_xi",  // opt-in speculative bar (tier-X, no real XI)
    ELITE_REWARDS: "elite_rewards", ELITE: "elite", COMPLETE: "complete",
    HIDDEN: "hidden",   // bar isn't pushed at all for HIDDEN, so JS never sees it
};
const CAT = {                                           // domain/constants.py Category
    VEHICLE: "vehicle", MODULE: "module", FIELDMOD: "fieldmod",
    UPGRADE: "upgrade", ELITE: "elite", REWARD: "reward",
};
const CMD = {                                           // bridge/view_models.py commands
    RESEARCH_UNLOCK: "researchUnlock", UNLOCK_FIELD_MOD: "unlockFieldMod",
    OPEN_SKILL_TREE: "openSkillTree", OPEN_RESEARCH: "openResearch",
    OPEN_FIELD_MODS: "openFieldMods", BUY_MOUNT: "buyMount",
    SET_POSITION: "setPosition", SELECT_MODE: "selectMode",
};
const GRADE = {                                         // domain/constants.py GradeFamily
    IRON: "iron", BRONZE: "bronze", SILVER: "silver", GOLD: "gold",
    ENAMEL: "enamel", PRESTIGE: "prestige", UNDEFINED: "undefined",
};

const observer = ModelObserver("WGModResearch");

// Localized widget labels, sourced from the game's own resource strings and pushed
// from Python as a JSON bundle on the model's `labels` field (see adapter/i18n.py).
// Refreshed each render() so tooltip builders (which run later, on hover) read the
// current language. L(key, fallback) returns the localized string or the English
// fallback -- so a missing key never blanks a caption.
let LBL = {};
function refreshLabels(data) {
    try { LBL = JSON.parse((data && data.labels) || "{}") || {}; }
    catch (e) { LBL = {}; }
}
function L(key, fallback) {
    return (LBL && LBL[key]) || fallback;
}

// Category icon for the bar header -- the same art the in-game "Vehicle
// management" menu uses for each section. Keyed by bar mode.
const CAT_ICON = {
    [MODE.TECH_TREE]: "img://gui/maps/icons/hangar/vehicleMenu/large/research.png",
    [MODE.FIELD_MODS]: "img://gui/maps/icons/hangar/vehicleMenu/large/fieldModification.png",
    // Tier-XI vehicle skill tree -> the dedicated "Upgrades" vehicle-management
    // section glyph (white tank + node network), matching research/fieldMod above.
    [MODE.SKILL_TREE]: "img://gui/maps/icons/hangar/vehicleMenu/large/vehSkillTree.png",
    // Speculative "potential Tier XI" -> the Research section glyph (the bar tracks XP
    // toward a hypothetical tier-XI research goal, so the research art reads right).
    [MODE.POTENTIAL_TIER_XI]: "img://gui/maps/icons/hangar/vehicleMenu/large/research.png",
};

// NB: the potential-Tier-XI milestone tick's glyph / "Tier XI" caption / class-name
// title are stamped on the Python Tick in the bridge (_decorate_potential), NOT here --
// marshalled tick objects are read-only in this widget, so JS-side writes wouldn't take.

// Skill-tree (Tier-XI upgrades) mode replaces the right-side Total-XP readout with
// an "unlocked / total nodes" counter, fronted by the in-game Upgrades-screen
// counter glyph (the small chevron shown beside its own node counter).
const SKILL_COUNTER_ICON = "img://gui/maps/icons/skillTree/tree/counter.png";

// The game's own green checkmark (the library "GreenCheck" asset) -- used as the
// bottom-right badge on a session "done" marker so it reads as a native WoT glyph.
const DONE_ICON = "img://gui/maps/icons/library/GreenCheck_1.png";


// Total spendable XP for this vehicle's research = the vehicle's accumulated
// combat XP + the account-global free XP -- exactly how the in-game research
// screen totals it (techtree getVehTotalXP = freeXP + vehXP). Uses that screen's
// own "Total XP" row glyph (vehicle_hub/research_purchase/total_experience). The
// game also ships an `_elite` variant, but its art is drawn smaller + offset low
// in the same 16x16 canvas (no higher-res source), so it reads as lower quality;
// we use the clean base glyph in every mode instead.
const XP_ICON = "img://gui/maps/icons/vehicle_hub/research_purchase/total_experience.png";

// The plain combat-XP currency glyph (gray star) -- used ONLY by the elite-mode
// readout, which shows cumulative COMBAT XP (no free XP), unlike the other modes'
// combined Total-XP star above. Verified by viewing the PNG (its free-XP sibling
// freeXpIcon_23x22 confirms it's the standard combat/free pair).
const COMBAT_XP_ICON = "img://gui/maps/icons/library/xpIcon_23x22.png";

// "Ignore Free XP" setting (pushed on data.ignoreFreeXp, refreshed each render()). When
// on, the domain already zeroed free XP (fill/spendable/affordability), so the spendable
// figure is combat XP only -- and the currency glyph for it should be the plain combat-XP
// star, not the combined Total-XP star. Every spendable-XP presentation site draws
// xpCurrencyIcon() so the whole bar switches with one flag; the elite paths keep their
// own COMBAT_XP_ICON regardless (they were always combat-only).
let IGNORE_FREE_XP = false;
function xpCurrencyIcon() {
    return IGNORE_FREE_XP ? COMBAT_XP_ICON : XP_ICON;
}

// Credits glyph for the "done" tick footer (a researched item still costs credits to
// buy). Matches the top-right account-balance credits icon.
const CREDITS_ICON = "img://gui/maps/icons/library/CreditsIcon-3.png";

// Crossed-swords battle glyph for the "≈ N" battles-remaining estimate: the
// random-battle type icon (matching our random-battle avg-XP divisor). Language-neutral,
// like the shortfall figures. Verified against the client's gui packages (EU 2.3):
// gui/maps/icons/battleTypes/40x40/random.png exists (40x40 sibling set).
const BATTLE_ICON = "img://gui/maps/icons/battleTypes/40x40/random.png";

// Which art fills the elite grade badge (category-icon slot + below-bar ticks).
//   "tab"    -> the battle team-HP arrowhead/chevron grade badge ("tab" art) -- SHIPPED
//   "emblem" -> the hexagon grade emblem (also the automatic fallback when tab art is
//               unavailable for a grade, regardless of this setting)
// The tab set is .../prestige/tab/<family>/<size>/<grade>.png (size short|medium|
// long). NB the tab PNGs are OPAQUE in the game files -- their see-through look in
// battle is a game-applied style, not baked into the art.
const ELITE_CAT_ICON_STYLE = "tab";     // "tab" (shipped) | "emblem"
const ELITE_TAB_SIZE = "auto";          // "auto" (by digit count) | "short" | "medium" | "long"
const ELITE_TAB_SHOW_NUMBER = true;     // overlay the elite level number on the tab
// The terminal grade (elite lvl 350 / MAX) uses the prestige HEXAGON emblem inside
// the arrowhead instead of a number. Flip this to true to force the MAX badge on any
// vehicle for testing (no lvl-350 vehicle needed).
const ELITE_TAB_FORCE_MAX = false;

// Elite badge for the COMPLETE state: the in-game class+elite icon. veh class
// ids use '-' (AT-SPG); the icon files use '_' (AT_SPG_elite.png).
function eliteIcon(vehClass) {
    if (!vehClass) return "";
    return "img://gui/maps/icons/vehicleTypes/md/" +
        vehClass.replace(/-/g, "_") + "_elite.png";
}

// The ELITE grade badges (category icon + below-bar ticks) render the battle team-HP
// arrowhead "tab" grade badge by default (ELITE_CAT_ICON_STYLE above; see fillTabBadge),
// FALLING BACK to the in-game prestige HEXAGON EMBLEM when tab art doesn't resolve.
// The emblem is the exact badge the hangar carousel vehicle tooltip shows (game
// component PrestigeProgressSymbol: a single emblem PNG drawn once, no backing/glow/
// blend); its 72x72 art is solid (~245/255 alpha over the shape), so one draw reads
// opaque on the hangar -- no stacking trick needed. The grade URL arrives on the tick
// as t.icon (.../prestige/emblem/<size>/<family>/<sub>.png, or .../prestige.png for
// MAX); gradeTabUrl() rewrites it to the tab art. GRADE_COLOR tints the level numeral.
const GRADE_FAMILIES = {
    [GRADE.IRON]: 1, [GRADE.BRONZE]: 1, [GRADE.SILVER]: 1, [GRADE.GOLD]: 1, [GRADE.ENAMEL]: 1,
};
// Per-grade number tint -- the EXACT values from the game's own PrestigeProgressTab
// component CSS (.level color per grade). enamel reuses gold, as the game does.
const GRADE_COLOR = {
    [GRADE.IRON]: "#909ba1",
    [GRADE.BRONZE]: "#f18140",
    [GRADE.SILVER]: "#87b2ca",
    [GRADE.GOLD]: "#ecbe6e",
    [GRADE.ENAMEL]: "#ecbe6e",
};
function gradeFamily(emblemUrl) {
    // emblem URL is .../prestige/emblem/<size>/<family>/<sub>.png -- pull <family>.
    const m = /\/emblem\/\d+x\d+\/([a-z]+)\//.exec(emblemUrl || "");
    const fam = m ? m[1] : "";
    return GRADE_FAMILIES[fam] ? fam : "";
}
// Build the battle team-HP "tab" grade badge (arrowhead/chevron) URL from the
// current-grade emblem URL, which already carries family + sub-grade:
//   .../emblem/<size>/<family>/<sub>.png  ->  .../tab/<family>/<tabSize>/<sub>.png
// The MAX/prestige emblem (.../prestige.png, no family) maps to the single
// .../tab/prestige.png. Returns "" for a non-grade / empty URL (caller falls back).
// The tab arrowhead ships in short/medium/long widths, one per level digit-count
// (1/2/3 digits) so the numeral fills the body. "auto" picks by the level; an explicit
// ELITE_TAB_SIZE forces one.
function tabSizeFor(level) {
    if (ELITE_TAB_SIZE !== "auto") return ELITE_TAB_SIZE;
    const d = String(level | 0).length;
    return d >= 3 ? "long" : (d === 2 ? "medium" : "short");
}
// Size class that drives the centering margin. The MAX/prestige badge (hexagon baked
// in, no number) sits centered best in the 2-digit "medium" layout, so force it there
// regardless of the (3-digit) max level number.
function tabBadgeSize(emblemUrl, level, forceMax) {
    if (forceMax || /\/prestige\.png$/.test(emblemUrl || "")) return "medium";
    return tabSizeFor(level);
}
function gradeTabUrl(emblemUrl, size) {
    const u = emblemUrl || "";
    const m = /\/emblem\/\d+x\d+\/([a-z]+)\/(\d+)\.png/.exec(u);
    if (m) {
        return "img://gui/maps/icons/prestige/tab/" + m[1] + "/" + size + "/" + m[2] + ".png";
    }
    if (/\/prestige\.png$/.test(u)) {
        return "img://gui/maps/icons/prestige/tab/prestige.png";
    }
    return "";
}
// The level number is drawn the same way the tooltip's PrestigeProgressLabel does:
// a row of grade-colored emblemFont digit glyphs (NOT a CSS text number). The glyph
// art is itself colored per grade, so no CSS tint is applied. emblemFont has no
// `enamel` set -> fall back to gold (matches the amber tint enamel used previously).
function emblemFontFamily(family) {
    return family === GRADE.ENAMEL ? GRADE.GOLD : (family || GRADE.GOLD);
}
function emblemFontUrl(family, digit) {
    return "img://gui/maps/icons/prestige/emblemFont/16x33/" +
        emblemFontFamily(family) + "/" + digit + ".png";
}
// Per-digit class for an emblemFont glyph. The "1" glyph is narrower in the game art,
// so flag it for a tighter width. Shared by both emblem-number builders below.
function emblemDigitClass(ch) {
    return "wg-emblem-digit" + (ch === "1" ? " wg-emblem-digit-one" : "");
}

// The level number centered over the hexagon emblem: a flex row of emblemFont digit
// glyph divs (Gameface clips an <img>, so each glyph is a background-image div).
function emblemNumber(level, family) {
    const wrap = document.createElement("span");
    wrap.className = "wg-tick-emblem-num";
    const s = String(level);
    for (let i = 0; i < s.length; i++) {
        const d = document.createElement("span");
        d.className = emblemDigitClass(s[i]);
        d.style.backgroundImage = "url('" + emblemFontUrl(family, s[i]) + "')";
        wrap.appendChild(d);
    }
    return wrap;
}

// HTML-string form of emblemNumber() (the tooltip is built as an innerHTML string,
// not DOM): the grade-colored emblemFont digit glyphs for `level`. Each glyph is a
// background-image span (Gameface clips <img>).
function emblemNumberHtml(level, family) {
    const s = String(level | 0);
    let h = "";
    for (let i = 0; i < s.length; i++) {
        h += '<span class="' + emblemDigitClass(s[i]) + '" style="background-image:url(\'' +
            emblemFontUrl(family, s[i]) + '\')"></span>';
    }
    return h;
}
// Tooltip title-block icon for an elite GRADE tick: the grade emblem with the elite
// level painted over it in the grade-colored emblemFont -- exactly how the vehicle
// carousel's prestige tooltip shows it. MAX (prestige.png, no family) shows the
// hexagon alone, no number (matches the game + the category-icon badge).
function eliteTipIconHtml(url, level) {
    const fam = gradeFamily(url);
    const overlay = (fam && level > 0)
        ? '<span class="wg-tip-icon-num">' + emblemNumberHtml(level, fam) + "</span>" : "";
    return '<div class="wg-tip-icon wg-tip-icon-elite" style="background-image:url(\'' +
        url + '\')">' + overlay + "</div>";
}

// The elite level number as plain WoT-font text, matching how the garage carousel
// draws the level on its prestige "tab" badge (a PFDINMax numeral, NOT the
// grade-colored emblemFont image glyphs the big hexagon emblems use). Styled +
// positioned by .wg-tab-num in the CSS.
function tabNumber(level) {
    const s = document.createElement("span");
    s.className = "wg-tab-num";
    s.textContent = String(level | 0);
    return s;
}

// Build the arrowhead "tab" grade badge into `box` (which must carry the `wg-tab`
// class + a 36x16rem footprint): the mirrored arrowhead art plus, unless at MAX, the
// grade-tinted level numeral tucked into the well. `emblemUrl` is the grade emblem URL
// (.../prestige/emblem/...), `level` the elite level to show. Shared by the elite
// category icon and the below-bar grade ticks so both render identically. Returns
// false when there's no tab art for the URL (caller falls back to its own glyph).
function fillTabBadge(box, emblemUrl, level, forceMax) {
    while (box.firstChild) box.removeChild(box.firstChild);
    let tabUrl = gradeTabUrl(emblemUrl, tabSizeFor(level));
    if (!tabUrl) return false;
    // Terminal MAX grade: the prestige arrowhead carries the hexagon baked in -> no
    // number overlay. ELITE_TAB_FORCE_MAX previews it on any vehicle (cat icon only).
    const isMax = forceMax || /\/tab\/prestige\.png$/.test(tabUrl);
    if (isMax) tabUrl = "img://gui/maps/icons/prestige/tab/prestige.png";
    const art = document.createElement("span");
    art.className = "wg-tab-art";
    art.style.backgroundImage = "url('" + tabUrl + "')";
    box.appendChild(art);
    if (!isMax && ELITE_TAB_SHOW_NUMBER && level > 0) {
        const num = tabNumber(level);
        const c = GRADE_COLOR[gradeFamily(emblemUrl)];
        if (c) num.style.color = c;
        // Right-aligned in the well, so more padding = further left. The wider 3-digit
        // well needs a bigger nudge than the 1-/2-digit ones to sit as tight as the
        // carousel.
        num.style.paddingRight = (String(level | 0).length >= 3 ? 9 : 7) + "rem";
        box.appendChild(num);
    }
    return true;
}

const ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"];
function romanize(n) {
    n = n | 0;
    if (n > 0 && n < ROMAN.length) return ROMAN[n];
    return n > 0 ? String(n) : "";
}

// XP with thousand-separators. Defaults to WoT's native space separator (used in
// the tooltip); the header Total-XP counter passes "," for comma grouping.
function fmtXp(n, sep) {
    n = n | 0;
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, sep || " ");
}

function escapeHtml(s) {
    return String(s)
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// Display name for a tick. Field-mod names may be empty (the engine label
// lookup can miss); fall back to the localized field-mod category label (its roman
// numeral already rides the hexagon glyph, so it's not repeated here).
function tickName(t) {
    if (t.name) return t.name;
    if (t.category === CAT.FIELDMOD) return L("capFieldMod", "Field Modification");
    return "";
}

// A faint horizontal rule between tooltip sections (mirrors WG's native tooltip
// divider). joinSections() drops it between any two empty sections, so a divider
// only ever appears where two real sections meet.
function joinSections(sections) {
    return sections.filter(function (s) { return s; })
        .join('<div class="wg-tip-div"></div>');
}

// Split a Python-joined string into its non-empty parts. Multi-value model fields
// arrive "\n"-joined (variant buffs "\t"-joined); an empty/absent field -> []. NB
// callers that must stay index-aligned with a sibling list (optionEffects <->
// options) split raw instead and do NOT use this (filtering would misalign them).
function splitLines(s, sep) {
    return (s || "").split(sep || "\n").filter(function (x) { return x; });
}

// A small inline XP-currency glyph (background-image span -- Gameface clips <img>,
// but honors background-size:contain on a box). `url` is XP_ICON (total XP) or
// COMBAT_XP_ICON (vehicle/combat XP). Sits right after the figure it annotates. The
// combat-XP art carries more transparent padding, so it gets a size-bump modifier to
// read at the same visual size as the total-XP glyph (mirrors the header's own
// .wg-elite .wg-xp-ico override).
function xpIco(url) {
    const cls = url === COMBAT_XP_ICON ? "wg-tip-xp-ico wg-tip-xp-ico-combat"
        : url === BATTLE_ICON ? "wg-tip-xp-ico wg-tip-xp-ico-battle"
        : "wg-tip-xp-ico";
    return '<span class="' + cls + '" style="background-image:url(\'' + url + '\')"></span>';
}

// Compact XP readout: "<have> / <need> <glyph>" -- progress toward affording this
// item, replacing the older verbose cost + "Need N more"/"Ready" pair. `need` is the
// SAME quantity that gates the tick (cumulative bar position for ticks; the node cost
// for chips), so the fraction reaching full == the item being affordable. Tinted as a
// shortfall (warm red) until covered, currency-tan once it is.
//
// Headline = the item's COST (`need`) + its currency glyph, in slightly larger figures.
// Affordability is conveyed by the remaining sub-line below (absent once covered), not
// by the headline, so the headline stays a neutral cost readout.
//
// While short, that sub-line spells out the shortfall as language-neutral "-<n>"
// figures (no translatable "left"/"more" word). Each carries its OWN currency glyph +
// color (matching the bar's fills): the vehicle-only remaining (combat XP alone, free
// XP ignored) comes FIRST -- combat-XP glyph, near-white -- and the total remaining
// (free XP counts) follows in the headline's currency (total-XP + tan; combat + white
// for elite). The vehicle-only figure shows only when free XP actually moves the
// number. Once covered, the whole sub-line is omitted.
// Below this many random battles, a tank's own average XP is too noisy to trust as a
// divisor -> fall back to the account-wide average (see estDivisor).
const MIN_BATTLES_FOR_VEH_AVG = 5;

// Lifetime-average XP undersells ACTIVE play: the average is dragged down by mediocre /
// early games, while an engaged player earns well above it (good form, consumables, crew
// perks). Calibrate the divisor up by this empirical factor so the estimate tracks real
// pace. Trade-off: a purely average player earns ~their lifetime avg, so this reads a bit
// optimistic for them -- accepted, to better match how the bar's users actually grind.
const ESTIMATE_CALIBRATION = 1.5;

// Bundle the Python-pushed "battles remaining" inputs into one object threaded through
// the tooltip builders (avoids a long parameter tail). Multipliers arrive as ints x100
// (100 == x1.0); default to no-bonus so an unread value never widens the range wrongly.
function mkBattleEst(data) {
    return {
        avg: data.avgBattleXp | 0,                       // this tank's avg XP/random battle
        count: data.battleCount | 0,                     // its random battle count
        acctAvg: data.accountAvgBattleXp | 0,            // account-wide avg (fallback divisor)
        maxXp: data.maxBattleXp | 0,                     // this tank's best single battle (optimistic bound)
        reserveMult: (data.reserveMult | 0) || 100,      // active XP-reserve multiplier
        ddFactor: (data.dailyDoubleFactor | 0) || 100,   // first-win-of-day factor
    };
}

// The per-battle XP divisor for the estimate: trust this tank's own average only with
// enough battles behind it, else fall back to the account-wide average so a freshly
// bought tank still estimates. 0 (no divisor) suppresses the estimate upstream.
function estDivisor(est) {
    if (!est) return 0;
    if ((est.count | 0) >= MIN_BATTLES_FOR_VEH_AVG && (est.avg | 0) > 0) return est.avg | 0;
    return (est.acctAvg | 0) || (est.avg | 0);
}

function xpFracHtml(have, need, iconUrl, vehHave, est) {
    need = need | 0;
    if (need <= 0) return "";
    have = have | 0;
    const ico = xpIco(iconUrl || XP_ICON);   // headline currency (reused by total remaining)
    // Unaffordable ("not yet reachable") -> the cost itself is tinted the shortfall red,
    // the same signal it carried before the cost-only headline change.
    const cls = have < need ? "wg-tip-xp wg-tip-short" : "wg-tip-xp";
    let h = '<div class="' + cls + '">' + fmtXp(need) + ico + "</div>";
    // Two shortfalls: `left` counts free XP (drives affordability + the headline tint);
    // `vehLeft` is the combat-XP-only gap (free XP ignored). The item can be affordable
    // (left <= 0) while combat XP alone still falls short (vehLeft > 0) -- free XP covers
    // the rest. In that case the headline reads as "enough" (no red), but we STILL show
    // the combat "-<n>" figure + battles estimate, since only combat XP grows by playing.
    const left = need - have;
    const vehLeft = (vehHave !== undefined) ? (need - (vehHave | 0)) : left;
    if (left > 0 || vehLeft > 0) {
        let sub = "";
        // Combat XP (the vehicle's own XP alone) FIRST -- shown only when free XP
        // actually moves the number (otherwise identical to the total remaining). When
        // the total is already covered (left <= 0) but combat is short, `vehLeft > left`
        // holds automatically -- exactly the affordable-via-free-XP case.
        if (vehHave !== undefined && vehLeft > 0 && vehLeft > left) {
            sub += '<span class="wg-tip-rem-veh">-' + fmtXp(vehLeft) +
                xpIco(COMBAT_XP_ICON) + "</span>";
        }
        // Then the total remaining (free XP counts), in the headline's currency -- only
        // while the total is actually short (once covered it would read "-0"/negative).
        if (left > 0) {
            sub += '<span class="wg-tip-rem-tot">-' + fmtXp(left) + ico + "</span>";
        }
        // Battles-remaining estimate ("≈ M-N"): a RANGE of battles of playing THIS tank
        // to close the COMBAT-XP shortfall. Only combat XP grows by playing (free XP is a
        // shared account pool), so use the vehicle-only gap when we have it, else `have`
        // is already combat XP (the elite footer passes it with no vehHave). Both ends
        // divide the gap by a calibrated per-battle XP:
        //   - HIGH end (more battles) = your typical pace: the average * calibration.
        //   - LOW end (fewer battles) = your best-game pace: max(average, best-battle) *
        //     calibration, then the bonuses you have -- an active XP reserve (every
        //     battle) + the daily-double x2 on the first winning battle (if still up).
        // When the tank is under-sampled, estDivisor falls back to the account-wide avg.
        // Hidden when there's no divisor (no battles / unreadable) -> never divide by zero.
        const combatLeft = vehLeft;
        const base = estDivisor(est);
        if (base > 0 && combatLeft > 0) {
            const cal = ESTIMATE_CALIBRATION;
            const typical = base * cal;                          // average form (high end)
            const best = Math.max(base, est.maxXp | 0) * cal;    // best-game form (low end)
            const res = (est.reserveMult || 100) / 100;          // reserve multiplier (>= 1)
            const dd = (est.ddFactor || 100) / 100;              // daily-double factor (>= 1)
            const nMax = Math.ceil(combatLeft / typical);
            const first = best * res * dd;                       // best battle: best game + reserve + double
            const nMin = (combatLeft <= first)
                ? 1
                : 1 + Math.ceil((combatLeft - first) / (best * res));
            const label = (nMin < nMax) ? (fmtXp(nMin) + "–" + fmtXp(nMax)) : fmtXp(nMax);
            sub += '<span class="wg-tip-battles">&#8776; ' +
                label + xpIco(BATTLE_ICON) + "</span>";
        }
        h += '<div class="wg-tip-xp-rem">' + sub + "</div>";
    }
    return h;
}

// Credits buy-price line for a "done" tick (researched -> now costs credits to buy).
// Reuses the XP cost-line layout with the credits glyph; a 0/absent price shows
// nothing (matching xpFracHtml's early-return, so the done footer stays empty).
function creditsHtml(price) {
    price = price | 0;
    if (price <= 0) return "";
    return '<div class="wg-tip-xp wg-tip-credits">' + fmtXp(price) +
        xpIco(CREDITS_ICON) + "</div>";
}

// One buff/bonus row. The Python side packs each KPI line into a record
//   icon \x1f cls \x1f value \x1f desc      (cls = "pos" | "neg")
// so we render it like the game's native perk tooltip: the parameter icon, the
// signed value+unit colored green (buff) / red (nerf), then the dim stat phrase.
// A line WITHOUT the separators (any non-KPI body text) falls back to the plain
// tertiary row. All fields are escaped; the icon URL is only ever a background and
// is gated on the img:// prefix (same guard as tickIconHtml).
const BUFF_SEP = "\x1f";
function buffLineHtml(line, baseCls) {
    baseCls = baseCls || "wg-tip-effect";
    const f = (line || "").split(BUFF_SEP);
    if (f.length < 4) {
        return '<div class="' + baseCls + '">' + escapeHtml(line) + "</div>";
    }
    const icon = f[0], cls = f[1], value = f[2], desc = f[3];
    let h = '<div class="' + baseCls + ' wg-tip-buff">';
    if (icon && icon.indexOf("img://") === 0) {
        h += '<span class="wg-tip-buff-ico" style="background-image:url(\'' +
            icon + '\')"></span>';
    }
    if (value) {
        h += '<span class="wg-tip-buff-val ' +
            (cls === "neg" ? "wg-buff-neg" : "wg-buff-pos") + '">' +
            escapeHtml(value) + "</span>";
    }
    if (desc) {
        h += (value ? " " : "") +
            '<span class="wg-tip-buff-desc">' + escapeHtml(desc) + "</span>";
    }
    return h + "</div>";
}

// Effect/bonus lines (field-mod & skill-tree KPI text, e.g. "+1% to concealment"),
// one row per line. The Python side joins multiple KPIs with "\n"; each is an
// enriched record (see buffLineHtml). Empty string -> nothing rendered (features /
// mechanic perks carry no KPI text).
function effectHtml(effect) {
    const parts = splitLines(effect);
    let h = "";
    for (let i = 0; i < parts.length; i++) {
        h += buffLineHtml(parts[i]);
    }
    return h;
}

// The A/B choice block for a field-mod choice level: EACH selectable variant's
// name (title weight) with ALL its own buffs beneath it (tertiary) -- so both
// variants and every buff show, not just the base mod's. A localized "or" row sits
// between the variants (see .wg-tip-or). optEffects is aligned with opts by
// index (a variant with no readable KPI just omits the buff line).
function variantsHtml(opts, optEffects) {
    let h = '<div class="wg-tip-variants">';
    for (let i = 0; i < opts.length; i++) {
        // "pick one" separator between variants (localized; was a CSS ::after "or").
        if (i > 0) h += '<div class="wg-tip-or">' + escapeHtml(L("sepOr", "or")) + "</div>";
        h += '<div class="wg-tip-variant">';
        h += '<div class="wg-tip-variant-name">' + escapeHtml(opts[i]) + "</div>";
        // Each variant's buffs are TAB-separated (Python); render one enriched row
        // each (icon + colored value + phrase), keyed off the variant body class.
        const buffs = splitLines(optEffects[i], "\t");
        for (let j = 0; j < buffs.length; j++) {
            h += buffLineHtml(buffs[j], "wg-tip-variant-eff");
        }
        h += "</div>";
    }
    return h + "</div>";
}

// A background-image icon box for the tooltip title block (module/vehicle art,
// grade emblem, or skill-tree perk glyph -- all full img:// URLs).
function bgIconHtml(url, mod) {
    // `mod` is an optional category class (wg-tip-icon-veh / -reward) that overrides
    // the default 52rem square box so wide vehicle art and portrait reward art keep
    // their aspect instead of being forced square (see .wg-tip-icon-* in the CSS).
    return '<div class="wg-tip-icon' + (mod ? " " + mod : "") +
        '" style="background-image:url(\'' + url + '\')"></div>';
}

// Icon markup for a tick's tooltip title block. Field mods show their signature
// hexagon + roman numeral (matching the bar's own field-mod glyph), NOT a generic
// section icon. Everything else shows the item's img:// art (tech-tree module /
// vehicle glyph, grade emblem, skill-tree perk). A field-mod's t.icon is only a raw
// basename (not a URL), so it is never used as a background image. No usable art ->
// "" (text-only tooltip, header row omitted).
function tickIconHtml(t) {
    if (t.category === CAT.FIELDMOD) {
        return '<div class="wg-tip-icon wg-tip-hex"><span>' +
            escapeHtml(romanize(t.level)) + "</span></div>";
    }
    if (t.icon && t.icon.indexOf("img://") === 0) {
        // Vehicle-node art is wide (~160x100) -> wide-short box; module glyphs are
        // square but read too tall at the default 52 -> their own smaller box.
        var mod = t.category === CAT.VEHICLE ? "wg-tip-icon-veh"
            : t.category === CAT.MODULE ? "wg-tip-icon-mod" : "";
        return bgIconHtml(t.icon, mod);
    }
    return "";
}

// Small uppercase TYPE caption above the title ("Gun" / "Field Modification II" /
// "Upgrade" / "Elite Level N"), so every tooltip names what kind of item it is.
function capHtml(text) {
    return '<div class="wg-tip-caption">' + text + "</div>";
}

// Wrap the main text block (caption + title + description / variants) with the icon
// on the RIGHT, sized (via CSS) to the height of that text block. Returns the text
// unchanged when there's no icon to show.
function tipMain(iconHtml, titleHtml, bodyHtml) {
    var text = titleHtml + (bodyHtml || "");
    if (!iconHtml) return text;
    // Tag the block with the icon it carries so the CSS reserves a right-hand column
    // exactly as wide + tall as that icon (see .wg-tip-main-*). The icon is taken OUT
    // of flow (absolute, top-right) so .wg-tip-main is a plain BLOCK: Coherent sized a
    // flex row from the text's FIRST line only, AND it does NOT wrap text around a CSS
    // float (the icon just renders as a top block and the box collapses to min-width) --
    // a plain block reserved-column always grows to its full wrapped text. Order matters:
    // the hex/elite/category icons also carry the base "wg-tip-icon" class, so test the
    // specific ones first.
    var mod = iconHtml.indexOf("wg-tip-hex") >= 0 ? " wg-tip-main-hex"
        : iconHtml.indexOf("wg-tip-icon-elite") >= 0 ? " wg-tip-main-elite"
        : iconHtml.indexOf("wg-tip-icon-veh") >= 0 ? " wg-tip-main-veh"
        : iconHtml.indexOf("wg-tip-icon-reward") >= 0 ? " wg-tip-main-reward"
        : iconHtml.indexOf("wg-tip-icon-mod") >= 0 ? " wg-tip-main-mod"
        : " wg-tip-main-icon";
    return '<div class="wg-tip-main' + mod + '"><div class="wg-tip-text">' + text +
        "</div>" + iconHtml + "</div>";
}

// Green "done" badge: the game's own GreenCheck asset as a background image, pinned
// to the glyph's bottom-right corner (see .wg-done-badge). A real element rather than
// a pseudo, since the field-mod hex already uses ::before.
function doneBadge() {
    const b = document.createElement("div");
    b.className = "wg-done-badge";
    b.style.backgroundImage = "url('" + DONE_ICON + "')";
    return b;
}

// Compact glyph for a "done" tick: a fixed-size, non-clipped, left-inset container
// holding the item's art (field-mod hexagon or tech-tree icon) plus the corner check.
// Unlike the shared glyph branches, this container never clips the badge and keeps it
// beside the icon regardless of the icon's aspect. Positioning lives in CSS
// (.wg-done-glyph): inset from the left edge so it stays inside the .wg-hot overlay.
function doneGlyph(t) {
    const g = document.createElement("div");
    g.className = "wg-done-glyph";
    if (t.category === CAT.FIELDMOD) {
        g.className += " wg-done-glyph-hex";
        const hex = document.createElement("div");
        hex.className = "wg-tick-hex";
        const num = document.createElement("span");
        num.textContent = romanize(t.level);
        hex.appendChild(num);
        g.appendChild(hex);
    } else if (t.icon) {
        const ico = document.createElement("div");
        ico.className = "wg-done-ico";
        ico.style.backgroundImage = "url('" + t.icon + "')";
        g.appendChild(ico);
    }
    g.appendChild(doneBadge());
    return g;
}

// Tooltip body for a tick, built as ordered sections joined by dividers for clear
// hierarchy: MAIN (text block [type caption + title + effect / choice variants] +
// right-side icon) -> FOOTER ("have / need XP", or the prerequisite line when
// locked). A field-mod choice level puts its selectable variants (each with its
// buffs) in place of a single title.
function tooltipHtml(t, spendableXp, fillVehicle, est, frontier) {
    const opts = splitLines(t.options);
    const optEffects = (t.optionEffects || "").split("\n");   // raw: index-aligned with opts
    let title = "", body = "", foot = "";
    if (t.category === CAT.FIELDMOD) {
        const cap = capHtml(escapeHtml(L("capFieldMod", "Field Modification")));
        if (opts.length) {
            // Choice level -> the selectable variants ARE the content (with buffs).
            title = cap;
            body = variantsHtml(opts, optEffects);
        } else {
            const name = tickName(t);
            const nm = name ? '<div class="wg-tip-name">' + escapeHtml(name) + "</div>" : "";
            title = cap + nm;
            body = effectHtml(t.effect);
        }
    } else {
        // Type caption: tech-tree kind ("Gun"/"Turret"/.../"Tier IX"), else "Upgrade"
        // for tier-XI skill-tree nodes (which carry no kindLabel).
        const cap = t.kindLabel ? capHtml(escapeHtml(t.kindLabel))
            : t.category === CAT.UPGRADE ? capHtml(escapeHtml(L("headerSkillTree", "Upgrades"))) : "";
        const name = tickName(t);
        const nm = name ? '<div class="wg-tip-name">' + escapeHtml(name) + "</div>" : "";
        title = cap + nm;
        body = effectHtml(t.effect);
    }
    if (t.done) {
        // Session "done" marker: already researched -> show the credits buy price
        // (hidden once owned; 0 renders nothing), styled like the XP cost line.
        foot = creditsHtml(t.price);
    } else if (frontier && t.category === CAT.UPGRADE && t.icon && t.xpRequired) {
        // Skill-tree final (capstone) tick, and ONLY when it's the purchasable frontier
        // (the capstone-only state: every prior node unlocked, this is the lone
        // available upgrade). Only this tick carries a name + real XP cost (domain
        // skilltree.py) in every state, but it's genuinely locked until the frontier --
        // so show name + cost only then, not the generic "Prerequisites not met". Uses
        // t.xpRequired (the real cost), not t.position (a node index); no fillVehicle.
        // When it's NOT the frontier, fall through to the t.locked requirements branch.
        foot = xpFracHtml(spendableXp, t.xpRequired, xpCurrencyIcon(), undefined, est);
    } else if (t.locked) {
        // Name the blocking prerequisites when known, else the generic line.
        const reqs = splitLines(t.prereqNames);
        foot = reqs.length
            ? '<div class="wg-tip-status">' + escapeHtml(L("requires", "Required:")) + " " +
                reqs.map(escapeHtml).join(", ") + "</div>"
            : '<div class="wg-tip-status">' +
                escapeHtml(L("prereqNotMet", "Prerequisites not met")) + "</div>";
    } else {
        foot = xpFracHtml(spendableXp, t.position, xpCurrencyIcon(), fillVehicle, est);
    }
    // Text block + its icon are ONE unit (no divider between them); the divider only
    // separates that unit from the footer (cost / prerequisite).
    return joinSections([tipMain(tickIconHtml(t), title, body), foot]);
}

function setCatIcon(el, url) {
    // Drop any overlaid child (the elite grade-band emblem level-number) so a mode
    // switch never leaves a stale number over another mode's category glyph.
    while (el.firstChild) el.removeChild(el.firstChild);
    if (url) {
        el.style.backgroundImage = "url('" + url + "')";
        el.style.display = "block";
    } else {
        el.style.backgroundImage = "";
        el.style.display = "none";
    }
}

function setUpgrades(el, done, total) {
    if (total > 0) {
        el.textContent = done + "/" + total;
        el.style.display = "block";
    } else {
        el.textContent = "";
        el.style.display = "none";
    }
}

// Right-side readout of the TOTAL spendable XP (vehicle combat XP + global free
// XP), with the native experience glyph to the right of the figure. Shown in
// every mode -- available XP stays meaningful even once the tank is researched.
function setXp(root, vehXp, freeXp) {
    root.querySelector(".wg-xp-ico").style.backgroundImage =
        "url('" + xpCurrencyIcon() + "')";
    root.querySelector(".wg-xp-val").textContent =
        fmtXp((vehXp || 0) + (freeXp || 0), ",");
}

// The second right-side readout pair (.wg-xp2-*) is used ONLY by skill_tree mode to
// show total spendable XP alongside the node counter; every other mode has a single
// figure, so hide the extra pair there (it persists across renders/modes).
function hideXp2(root) {
    root.querySelector(".wg-xp2-val").style.display = "none";
    root.querySelector(".wg-xp2-ico").style.display = "none";
}

// wulf exposes nested viewmodels / array elements wrapped as { value: ... }.
function unwrap(x) {
    return x && x.value !== undefined ? x.value : x;
}

// Invoke a reverse-channel command on our ResearchVM (exposed as `wgResearch` on
// the host model). Wulf surfaces a ViewModel command as a callable on the model;
// whether it lives on the wrapped proxy or its unwrapped value can differ across
// builds, so try both. `arg` is omitted for the no-arg command (openSkillTree).
function invokeCommand(name, arg) {
    try {
        const vm = observer.model && observer.model.wgResearch;
        let host = null;
        if (vm && typeof vm[name] === "function") host = vm;
        else {
            const inner = unwrap(vm);
            if (inner && typeof inner[name] === "function") host = inner;
        }
        if (!host) { console.error("[wgmod] command missing: " + name); return; }
        // Wulf commands take a single MAP argument (a raw scalar is rejected by
        // Gameface as "not a map"). A scalar id is wrapped as {value: id}; an arg
        // that's already a map (e.g. setPosition's {x, y}) is passed through as-is; a
        // no-arg command (openSkillTree/openResearch/openFieldMods) still passes an
        // empty MAP for the same symmetry -- the Python handlers take *args and ignore it.
        if (arg === undefined || arg === null) host[name]({});
        else if (typeof arg === "object") host[name](arg);
        else host[name]({ value: arg });
    } catch (e) {
        console.error("[wgmod] invokeCommand failed: " + name, e);
    }
}

// The bar's TRACK rect defines the 0..100% pct basis (a tick's .left comes from pct()
// over the ticks layer, which is left:0/right:0 of the track). The .wg-hot overlay
// extends PAST the bar's left edge (so a left-overhanging done marker stays hoverable),
// so cursor->% hit-testing must measure against the ticks layer, NOT hotEl -- else
// every tick's % would shift by the overlay's extra left width. Falls back to hotEl.
function barRect(hotEl) {
    const p = hotEl.parentNode;
    const ticks = p && p.querySelector && p.querySelector(".wg-ticks");
    return (ticks && ticks.getBoundingClientRect()) || hotEl.getBoundingClientRect();
}

// Nearest CLICKABLE tick to a cursor x (from hotEl._wgClickMeta), gated by a small
// proximity window so a click on the bare bar between ticks doesn't fire an action.
// Imprecise hits are additionally backstopped by WG's confirm dialog (Python side).
const CLICK_HIT_PCT = 4;
// Nearest entry in a [{left%, ...}] list to a cursor x, measured against the bar TRACK
// (barRect), which defines the 0..100% basis. Returns {best, dist} (best null for an
// empty list). Shared by the click resolver (clickMeta, gated by CLICK_HIT_PCT) and the
// tick-hover fallback (tickMeta, gated per mode) so both agree on "which tick is nearest".
function nearestByX(meta, hotEl, clientX, rect) {
    if (!meta || !meta.length) return { best: null, dist: 1e9 };
    // `rect` (the bar TRACK rect) may be passed in so a single mousemove reads it ONCE
    // and shares it across the cursor-affordance + tooltip hit-tests (a forced layout
    // read per call otherwise); falls back to reading it here for other callers.
    rect = rect || barRect(hotEl);
    const w = (rect && rect.width) || hotEl.clientWidth || 1;
    const left = rect ? rect.left : 0;
    const curPct = ((clientX - left) / w) * 100;
    let best = null, bestD = 1e9;
    for (let i = 0; i < meta.length; i++) {
        const d = Math.abs(meta[i].left - curPct);
        if (d < bestD) { bestD = d; best = meta[i]; }
    }
    return { best: best, dist: bestD };
}
function nearestClick(hotEl, clientX, rect) {
    const r = nearestByX(hotEl._wgClickMeta, hotEl, clientX, rect);
    return r.best && r.dist <= CLICK_HIT_PCT ? r.best : null;
}

function getRoot() {
    return document.getElementById("wgmod-root");
}

function ensureRoot() {
    let root = getRoot();
    if (!root) {
        root = document.createElement("div");
        root.id = "wgmod-root";
        root.innerHTML =
            '<div class="wg-head">' +
            '<div class="wg-cat-icon"></div>' +
            '<div class="wg-head-left">' +
            '<div class="wg-label"></div>' +
            '<div class="wg-upgrades"></div>' +
            // The mode-switch title: the NEXT available mode, dimmed, to the right of the
            // current title. Visual only; hover/click are routed through the .wg-head-hot
            // layer (see bindHeadHot / renderModeSwitch).
            '<div class="wg-switch"></div>' +
            "</div>" +
            '<div class="wg-xp">' +
            '<span class="wg-xp-val"></span>' +
            '<span class="wg-xp-ico"></span>' +
            '<span class="wg-xp2-val"></span>' +
            '<span class="wg-xp2-ico"></span>' +
            "</div>" +
            "</div>" +
            '<div class="wg-track">' +
            '<div class="wg-fill wg-fill-veh"></div>' +
            '<div class="wg-fill wg-fill-free"></div>' +
            '<div class="wg-ticks"></div>' +
            '<div class="wg-cur"></div>' +
            '<div class="wg-hot"></div>' +
            '<div class="wg-tooltip"></div>' +
            "</div>" +
            '<div class="wg-next"></div>';
        document.body.appendChild(root);
    }
    return root;
}

function arrLen(a) {
    if (!a) return 0;
    if (typeof a.length === "number") return a.length;
    if (typeof a.count === "number") return a.count;
    return 0;
}

// Element i of a wulf array-or-plain-array, unwrapped. A plain JS array indexes
// directly; a wulf Array exposes elements via .get(i). Pairs with arrLen().
function arrGet(a, i) {
    return unwrap(a[i] !== undefined ? a[i] : a.get && a.get(i));
}

// Tier-XI "Next available:" row below the bar: a caption + one clickable chip per
// available frontier node (perk icon, hover tooltip with name + XP cost, click to
// unlock). Hidden when nothing is available. The signature FINAL upgrade stays on
// the bar itself (its rightmost end tick), separate from this row.
//
// The chips are VISUAL ONLY (pointer-events:none -- in this Coherent build, elements
// nested under the pointer-events:none root don't reliably receive events even with
// pointer-events:auto). Interaction is routed through the .wg-hot overlay (the one
// proven-interactive layer, which spans this row's area): we register each chip's
// element + command + tooltip in hotEl._wgChips, and ensureHover() hit-tests them by
// bounding rect for hover (toggling the chip's own .wg-chip-tip) and click.
function renderNextAvailable(nextEl, arr, hotEl, spendableXp, est) {
    nextEl.innerHTML = "";
    const chips = [];
    const n = arrLen(arr);
    if (n) {
        // (No "Next available:" caption -- the chips speak for themselves and the label
        // had no localized game equivalent.)
        for (let i = 0; i < n; i++) {
            const u = arrGet(arr, i);
            if (!u) continue;
            const xp = u.xpRequired | 0;
            // Match the Upgrades screen: minor (10k) -> circle; major
            // (>=20k: 20k/25k) -> diamond. Frame + perk glyph layered.
            const chip = document.createElement("div");
            chip.className = "wg-chip " + (xp >= 20000 ? "wg-chip-major" : "wg-chip-minor");
            if (u.done) chip.className += " wg-done";   // session marker: green check + open-screen click
            fillChipGlyph(chip, u.icon);
            const tip = document.createElement("div");
            tip.className = "wg-chip-tip";
            // Type caption = the node's own Upgrades-screen sub-heading ("Mechanic
            // Upgrade" / "Special Upgrade", localized from Python); falls back to the
            // generic word. Then name + buffs; the node's perk art (img:// URL) as the
            // right-side icon, matching the chip glyph. Icon-less nodes -> text-only.
            const cName = u.name
                ? '<div class="wg-tip-name">' + escapeHtml(u.name) + "</div>" : "";
            // Node sub-heading if the game gave one, else the localized "Upgrades"
            // section label (never the bare English word).
            const cCap = u.category || L("headerSkillTree", "Upgrades");
            const cTitle = capHtml(escapeHtml(cCap)) + cName;
            const cBody = effectHtml(u.effect);
            const cIcon = (u.icon && u.icon.indexOf("img://") === 0) ? bgIconHtml(u.icon) : "";
            // Done marker -> already unlocked, no cost/footer; else per-node cost
            // (frontier nodes unlock independently). No fillVehicle arg: `xp` here is
            // a node COUNT-cost, not a two-currency XP figure, so a "-<n>" vehicle
            // remaining sub-line would be bogus.
            const cFoot = u.done
                ? ""
                : xpFracHtml(spendableXp, xp, xpCurrencyIcon(), undefined, est);
            // Text block + icon as one unit (no divider between them); divider before cost.
            tip.innerHTML = joinSections([tipMain(cIcon, cTitle, cBody), cFoot]);
            chip.appendChild(tip);
            if (u.done) chip.appendChild(doneBadge());   // green check, bottom-right
            nextEl.appendChild(chip);
            // Gate clickability on affordability, like the bar's ticks: an
            // unaffordable frontier node isn't unlockable, so give it a null cmd
            // (the click handler no-ops on null). Done markers open the screen.
            chips.push(u.done
                ? { el: chip, tip: tip, cmd: CMD.OPEN_SKILL_TREE, arg: undefined }
                : { el: chip, tip: tip,
                    cmd: (spendableXp >= xp) ? CMD.UNLOCK_FIELD_MOD : null,
                    arg: u.actionId });
        }
        nextEl.style.display = "flex";
    } else {
        nextEl.style.display = "none";
    }
    if (hotEl) hotEl._wgChips = chips;
}

// Build the framed perk glyph (frame ring + centered perk icon) into `box`, matching
// the Upgrades screen. Shared by the Next-available chips and the bar's skill-tree
// final-upgrade tick. The frame shape (circle=minor / diamond=major) comes from the
// box's own wg-chip-minor/-major class (CSS), so callers set that on `box`.
function fillChipGlyph(box, iconUrl) {
    const frame = document.createElement("div");
    frame.className = "wg-chip-frame";
    const ico = document.createElement("div");
    ico.className = "wg-chip-ico";
    if (iconUrl) ico.style.backgroundImage = "url('" + iconUrl + "')";
    box.appendChild(frame);
    box.appendChild(ico);
}

// Signature of the available-upgrade set, so render() can skip rebuilding identical
// chips (a rebuild destroys the hovered chip's tooltip element).
function upgradesSig(arr, spendableXp) {
    const n = arrLen(arr);
    // spendableXp is folded in so the chips rebuild when affordability flips; it's
    // stable between unlock actions, so this doesn't cause per-push rebuild flicker.
    let s = n + "@" + (spendableXp | 0) + ":";
    for (let i = 0; i < n; i++) {
        const u = arrGet(arr, i);
        if (u) s += (u.actionId | 0) + "," + (u.xpRequired | 0) + "," + (u.done ? 1 : 0) + ";";
    }
    return s;
}

// The chip (in hotEl._wgChips) whose on-screen box contains the cursor, or null.
function chipAt(hotEl, clientX, clientY) {
    const chips = hotEl._wgChips;
    if (!chips || !chips.length) return null;
    for (let i = 0; i < chips.length; i++) {
        const r = chips[i].el.getBoundingClientRect();
        if (r && clientX >= r.left && clientX <= r.right &&
            clientY >= r.top && clientY <= r.bottom) return chips[i];
    }
    return null;
}

// Toggle the framed chip tooltip for the hovered chip, clearing any
// previously-active one. Driven from the .wg-hot handler, not CSS :hover.
function setActiveChip(hotEl, chip) {
    const prev = hotEl._wgActiveChip;
    if (prev && prev !== chip) {
        prev.tip.style.display = "none";
    }
    if (chip) {
        chip.tip.style.display = "block";
        clampTip(chip.tip);   // keep it within the bar width / flip above near the bottom
    }
    hotEl._wgActiveChip = chip || null;
}

// --- De-crowding: stack overlapping tick glyphs into vertical lanes ----------
// The glyphs hung below the bar (tech-tree module/vehicle icons, field-mod
// hexes, elite emblems/thumbnails) sit at their tick's XP position. When two
// positions fall close together the glyphs pile on top of each other and become
// unreadable / hard to click. We greedily assign each crowded glyph a vertical
// LANE and drop it a row (with a thin stem back to its tick) so every glyph stays
// legible. Lane 0 is the normal spot, so a bar with no crowding is unchanged, and
// hover/click stay purely x-based (unaffected by the vertical offset).
const TICKS_WIDTH_REM = 516;   // .wg-ticks span (root 520rem minus the track's 2rem borders)
const LANE_STEP_REM = 30;      // vertical drop per extra lane -- clears a ~24-30rem glyph
const MAX_LANES = 2;           // cap the stagger at two rows (lane 0 + one dropped row)
// Baseline below-track drop for the tick tooltip -- mirrors `.wg-tooltip { margin-top:36rem }`
// (the lane-0 anchor, clearing the track + lane-0 glyphs). clampTip adds lane*LANE_STEP_REM
// on top of this when hovering a dropped (lane >= 1) glyph so the tooltip clears it too.
const TOOLTIP_DROP_REM = 36;
// .wg-hot bottom (track-relative) once a row is dropped, so a lane-1 glyph hung
// ~37rem below the track + up to a 30rem-tall glyph still sits inside the hover
// overlay and can be hovered directly. Only applied when something actually stacks
// (CSS keeps the tighter default otherwise, so the drag dead-zone stays small).
const HOT_BOTTOM_STACKED_REM = -70;
// Visible glyph footprint (rem) hung below a tick, by mode/category. Half of it
// (+ a small gap) is the horizontal clearance each glyph needs to not overlap.
function glyphFootprintRem(t, mode) {
    if (mode === MODE.ELITE_REWARDS) return 30;                 // reward thumb
    if (mode === MODE.ELITE) return 36;                         // arrowhead tab badge (36rem wide)
    if (t.category === CAT.FIELDMOD) return 18;                 // hex badge
    if (t.category === CAT.VEHICLE) return 45;                  // framed tank contour
    return 24;                                                  // module glyph
}
function glyphHalfPct(t, mode) {
    return ((glyphFootprintRem(t, mode) / 2) + 3) / TICKS_WIDTH_REM * 100;
}
// Greedy interval colouring over glyph-bearing ticks (entries {left%, half},
// nulls for tickless gaps). Sorted by x, each glyph takes the lowest lane whose
// previous occupant's right edge clears this glyph's left edge, so overlapping
// neighbours land in different lanes and isolated glyphs stay in lane 0. The
// stagger is capped at MAX_LANES rows: when every lane is still occupied, the
// glyph reuses the lane that frees earliest (smallest right edge) to minimise the
// residual overlap. Sets .lane on each non-null entry; returns the max lane used.
function assignLanes(place) {
    const items = place.filter(Boolean).sort(function (a, b) { return a.left - b.left; });
    const laneRight = [];   // rightmost occupied %-edge, per lane
    let maxLane = 0;
    for (let i = 0; i < items.length; i++) {
        const it = items[i];
        const leftEdge = it.left - it.half;
        let lane = -1;
        for (let L = 0; L < laneRight.length; L++) {       // lowest free lane
            if (laneRight[L] <= leftEdge) { lane = L; break; }
        }
        if (lane === -1) {
            if (laneRight.length < MAX_LANES) {
                lane = laneRight.length;                   // open the next row
            } else {
                lane = 0;                                  // capped -> reuse earliest-freeing
                for (let L = 1; L < laneRight.length; L++) {
                    if (laneRight[L] < laneRight[lane]) lane = L;
                }
            }
        }
        it.lane = lane;
        laneRight[lane] = it.left + it.half;
        if (lane > maxLane) maxLane = lane;
    }
    return maxLane;
}
// Drop a glyph into its assigned lane: translate it down a row and draw a thin
// stem from the tick to it so the association reads clearly. No-op for lane 0.
function applyLane(mark, glyphEl, lane) {
    if (!lane || !glyphEl) return;
    glyphEl.style.transform = "translateX(-50%) translateY(" + (lane * LANE_STEP_REM) + "rem)";
    const stem = document.createElement("div");
    stem.className = "wg-tick-stem";
    stem.style.height = (lane * LANE_STEP_REM) + "rem";
    mark.appendChild(stem);
}

// Lane pre-pass shared by the linear and elite tick loops: reserve a footprint for each
// glyph-bearing tick so overlapping glyphs stagger into vertical lanes (de-crowding).
// `reserves(t)` picks which ticks carry a glyph -- omit it (elite: every tick has one)
// or pass a predicate (linear: only fieldmod / icon ticks). Grows the hover overlay
// down to cover any dropped row, then returns the per-tick placement array (null for
// gaps; assignLanes sets .lane on the rest, read via place[i].lane).
function computeLanes(ticks, n, pct, mode, hotEl, reserves) {
    const place = [];
    for (let i = 0; i < n; i++) {
        const t = arrGet(ticks, i);
        const on = t && (reserves ? reserves(t) : true);
        place.push(on ? { left: pct(t.position), half: glyphHalfPct(t, mode) } : null);
    }
    const maxLane = assignLanes(place);
    // Grow the hover overlay down to cover a dropped row's glyphs (only when something
    // stacked); CSS keeps the tighter default when nothing did.
    hotEl.style.bottom = maxLane > 0 ? HOT_BOTTOM_STACKED_REM + "rem" : "";
    return place;
}

// Root modifier class that mirrors WoT's color-blind mode. Appended to every root
// className assignment (all render branches) so the CSS .wg-colorblind overrides swap
// the meaning-carrying fills/pips to a color-blind-safe palette. Fail-open: absent flag
// (older Python build) -> standard palette.
function cbClass(data) {
    return data && data.colorBlind ? " wg-colorblind" : "";
}

// A signature of everything a rendered tick + its tooltip consume, so render() can tell a
// genuine data change (vehicle switch, XP/affordability move) from a spurious repeat push
// (onSyncCompleted coalesces, and render() runs on every one). Used ONLY to hide a
// now-stale tooltip on change: render() rebuilds the ticks but never re-runs the hover
// hit-test, so a still cursor would otherwise keep showing the PREVIOUS vehicle's tooltip
// until the pointer next moves. On an unchanged push the tooltip is left alone (which is
// why render() must not blanket-hide it -- that made it vanish whenever the cursor stopped).
function dataSig(data) {
    const ticks = data.ticks;
    const n = arrLen(ticks);
    let s = (data.mode || "") + "|" + (data.spendableXp | 0) + "|" + (data.combatXp | 0) +
        "|" + (data.fieldModsDone | 0) + "/" + (data.fieldModsTotal | 0) + "|" +
        (data.avgBattleXp | 0) + "," + (data.battleCount | 0) + "," +
        (data.accountAvgBattleXp | 0) + "," + (data.maxBattleXp | 0) + "," +
        (data.reserveMult | 0) + "," + (data.dailyDoubleFactor | 0) + "||";
    for (let i = 0; i < n; i++) {
        const t = arrGet(ticks, i);
        if (!t) continue;
        s += (t.position | 0) + "," + (t.category || "") + "," + (t.done ? 1 : 0) + "," +
            (t.locked ? 1 : 0) + "," + (t.affordable ? 1 : 0) + "," + (t.state || "") + "," +
            (t.name || "") + "," + (t.icon || "") + "," + (t.level | 0) + "," +
            (t.xpRequired | 0) + "," + (t.price | 0) + ";";
    }
    return s + "|chips:" + arrLen(data.availUpgrades);
}

// If the model's tick data changed since the last render, drop a tooltip that's still
// showing the previous data (see dataSig). Clears the show() cache so it re-shows fresh on
// the next mousemove. No-op when nothing changed -> a still cursor keeps its tooltip.
function hideStaleTooltip(hotEl, tipEl, data) {
    const sig = dataSig(data);
    if (hotEl._wgDataSig === sig) return;
    hotEl._wgDataSig = sig;
    tipEl.style.display = "none";
    tipEl._wgShownBody = null;
}

// The current Gameface viewport (CSS px). Both position paths key off this so a
// resolution / UI-scale change (which resizes the viewport) triggers a re-derive
// (auto) or a proportional rescale (pinned). 0 when unread -> callers no-op safely.
function currentVP() {
    return { w: window.innerWidth || 0, h: window.innerHeight || 0 };
}

// Apply the user's dragged bar position (px), or fall back to the CSS default. posX = bar
// CENTER-x, posY = bar TOP (px), both 0 == "auto". Both paths are VIEWPORT-AWARE so the bar
// tracks a resolution / UI-scale change instead of freezing at the resolution it was placed on:
//   - PINNED (posX/posY > 0): stored px were captured at data.posW x data.posH. If the
//     current viewport differs, rescale the px proportionally, apply, and echo the
//     rescaled px + new capture size back via setPosition so the settings steppers track
//     it (and the next push, now matching, won't re-rescale). A pre-fix pin with no
//     posW/posH just applies as-is and self-heals on the next drag.
//   - AUTO (0/0): clear inline left/top so the resolution-relative CSS default (centered,
//     17.6vh) re-derives. Nothing is measured or sent back -- the panel's position steppers
//     just show a plain 0 for "auto", so there's no default to feed.
// Fail-open: an older Python build without posX -> leave the CSS default untouched.
function applyPosition(root, data) {
    if (root._wgDragging) return;   // never fight an in-progress drag
    if (!data || data.posX === undefined) return;   // feature absent -> CSS default
    const vp = currentVP();
    const x = data.posX | 0;
    const y = data.posY | 0;
    if (x > 0 && y > 0) {
        let ax = x, ay = y;
        const rw = data.posW | 0, rh = data.posH | 0;
        if (rw && rh && vp.w && vp.h && (rw !== vp.w || rh !== vp.h)) {
            // resolution/scale changed since the pin was captured -> rescale proportionally
            ax = Math.round(x * vp.w / rw);
            ay = Math.round(y * vp.h / rh);
            // persist the rescaled px + the new capture size (steppers track it; converges
            // because the next push carries posW/posH == the current viewport).
            invokeCommand(CMD.SET_POSITION, { x: ax, y: ay, w: vp.w, h: vp.h });
        } else if ((!rw || !rh) && vp.w && vp.h) {
            // pinned px with NO recorded capture size -- a value typed into the panel
            // steppers, or a position saved by a pre-fix build. Adopt the current viewport
            // as the reference (apply the px unchanged now) so a LATER resolution / scale
            // change can rescale it. Echo converges: the next push carries posW/posH.
            invokeCommand(CMD.SET_POSITION, { x: x, y: y, w: vp.w, h: vp.h });
        }
        root.style.left = ax + "px";
        root.style.top = ay + "px";
        return;
    }
    // auto: keep the resolution-relative CSS default position (centered, 17.6vh) by clearing
    // any inline override. Nothing is measured or sent -- posX/posY stay 0 (auto) and the
    // panel's position steppers just show a plain 0.
    root.style.left = "";
    root.style.top = "";
}

// Keep a shown tooltip on-screen: clamp it horizontally within the BAR's own width
// (the track's left/right edges -- the tooltip's max-width is narrower than the bar, so
// it always fits, and since the drag keeps the bar on-screen this also prevents any
// screen-edge overflow), and flip it above the bar if it would spill past the viewport
// bottom. Overrides are set inline and reset each call so a tooltip that now fits
// returns to its centered, below-the-bar default. Reused for the tick + chip tooltips.
function clampTip(tipEl, lane) {
    // reset prior overrides -> transform reverts to the CSS translateX(-50%) centering
    tipEl.style.transform = "";
    tipEl.style.top = "";
    tipEl.style.bottom = "";
    tipEl.style.marginTop = "";
    tipEl.style.marginBottom = "";
    // Lane-aware below default: a de-crowded glyph is dropped lane*LANE_STEP_REM below the
    // track, so push the tooltip past it. Only when lane >= 1 -- otherwise leave marginTop
    // reset so each tip keeps its own CSS baseline (.wg-tooltip 36rem, .wg-chip-tip 6rem;
    // chips never lane-stack). Set BEFORE measuring so the overflow flip below sees the real
    // extent; the flip's marginTop:0 then cancels this (glyphs never stack upward).
    if (lane) tipEl.style.marginTop = (TOOLTIP_DROP_REM + lane * LANE_STEP_REM) + "rem";
    const track = document.querySelector("#wgmod-root .wg-track");
    if (!track) return;
    const bar = track.getBoundingClientRect();
    const tip = tipEl.getBoundingClientRect();
    if (!tip.width) return;
    let dx = 0;
    if (tip.left < bar.left) dx = bar.left - tip.left;
    else if (tip.right > bar.right) dx = bar.right - tip.right;
    if (dx) {
        // preserve the CSS centering (translateX(-50%)) and add the correction
        tipEl.style.transform = "translateX(-50%) translateX(" + Math.round(dx) + "px)";
    }
    const vh = window.innerHeight || 0;
    if (vh && tip.bottom > vh - 4) {
        // flip above the bar (default hangs below at top:100%)
        tipEl.style.top = "auto";
        tipEl.style.bottom = "100%";
        tipEl.style.marginTop = "0";
        tipEl.style.marginBottom = "8rem";
    }
}

// Shared tick builder for EVERY bar mode. For each data tick it creates a .wg-tick,
// positions it at spec.leftPct%, wires the nearest-by-x hover metadata (when spec.tip),
// registers a click command (when spec.cmd), hangs spec.glyph below it, and drops it into
// its pre-computed de-crowding lane. All the per-mode variation lives in spec(t, i), which
// returns { className, leftPct, tip, body, cmd, arg, glyph, lane }. The linear and elite
// paths used to carry near-identical copies of this skeleton; now only their spec differs.
// Returns { tickMeta, clickMeta } for the caller to stash on hotEl.
function renderTicks(ticksEl, ticks, n, spec) {
    ticksEl.innerHTML = "";
    const tickMeta = [];
    const clickMeta = [];
    for (let i = 0; i < n; i++) {
        const t = arrGet(ticks, i);
        if (!t) continue;
        const s = spec(t, i);
        const mark = document.createElement("div");
        mark.className = s.className;
        mark.style.left = s.leftPct + "%";
        if (s.tip) {
            // Tag the tick (read by the hover handler when Gameface deep-targets a glyph,
            // whose ancestor .wg-tick carries the body) AND keep a flat list for the
            // nearest-by-x fallback when it targets the bare layer.
            mark._wgBody = s.body;
            mark._wgLeft = s.leftPct;
            mark._wgLane = s.lane;   // de-crowding lane, so the tooltip can drop below a pushed-down glyph
            tickMeta.push({ left: s.leftPct, body: s.body, lane: s.lane });
        }
        if (s.cmd) {
            mark.classList.add("wg-clickable");
            clickMeta.push({ left: s.leftPct, cmd: s.cmd, arg: s.arg });
        }
        if (s.glyph) mark.appendChild(s.glyph);
        // De-crowd: drop the glyph into its assigned lane + draw a stem back to the tick
        // (no-op for lane 0). applyLane appends the stem to mark, so call it after the glyph.
        applyLane(mark, s.glyph, s.lane);
        ticksEl.appendChild(mark);
    }
    return { tickMeta: tickMeta, clickMeta: clickMeta };
}

// The below-bar glyph for a linear-mode (tech-tree / field-mods / skill-tree) tick, or
// null when it carries none. Done markers -> the compact green-check glyph; field mods ->
// the hexagon + roman numeral; the skill-tree final upgrade -> the framed perk chip;
// tech-tree ticks -> the real module/vehicle art (background-image; Gameface clips <img>).
function linearGlyph(t, mode) {
    if (t.done) return doneGlyph(t);
    if (t.category === CAT.FIELDMOD) {
        const hex = document.createElement("div");
        hex.className = "wg-tick-hex";
        const num = document.createElement("span");
        num.textContent = romanize(t.level);
        hex.appendChild(num);
        return hex;
    }
    if (t.icon && mode === MODE.SKILL_TREE) {
        // FINAL upgrade: a framed perk glyph (diamond -- a major 25k node), matching the
        // Next-available chips (reuses the chip frame/glyph classes).
        const fin = document.createElement("div");
        fin.className = "wg-final wg-chip-major";
        fillChipGlyph(fin, t.icon);
        return fin;
    }
    if (t.icon) {
        const img = document.createElement("div");
        img.className = "wg-tick-img";
        img.style.backgroundImage = "url('" + t.icon + "')";
        return img;
    }
    return null;
}

// The below-bar glyph for an elite-mode tick: a reward thumbnail (elite_rewards), the
// arrowhead "tab" grade badge (elite -- falling back to the hexagon emblem + emblemFont
// level number when a grade has no tab art), or a state-colored diamond pip when the icon
// URL is missing (the terminal MAX "prestige" tab has no grade family -> numberless hex).
function eliteGlyph(t, isRewards) {
    if (!t.icon) {
        const pip = document.createElement("div");
        pip.className = "wg-tick-pip";
        return pip;
    }
    if (isRewards) {
        const img = document.createElement("div");
        img.className = "wg-tick-reward";
        img.style.backgroundImage = "url('" + t.icon + "')";
        return img;
    }
    const gradeFam = gradeFamily(t.icon);
    const img = document.createElement("div");
    // Per-size class drives the centering nudge (the mirrored arrowhead arts are
    // right-anchored by different amounts, so each width sits centered under its tick).
    img.className = "wg-tick-tab wg-tab wg-tab-" + tabBadgeSize(t.icon, t.position | 0, false);
    if (!fillTabBadge(img, t.icon, t.position | 0, false)) {
        img.className = "wg-tick-emblem";
        img.style.backgroundImage = "url('" + t.icon + "')";
        if (gradeFam) img.appendChild(emblemNumber(t.position | 0, gradeFam));
    }
    return img;
}

// --- Header mode switch ------------------------------------------------------------
// A vehicle often qualifies for several bar modes at once (research/field-mods,
// elite-system/elite-rewards). Python pushes the ordered list of available modes as
// `availModes` (comma-joined); when there are >=2 we render the NEXT one's title dimmed
// beside the current one. Hover raises its opacity; a click fires selectMode, which
// stores the choice per-vehicle and re-pushes -- the bar then repaints in that mode and
// the previously-active title becomes the new switch (a clean A<->B swap with 2 modes; a
// forward cycle with 3+).

// The localized header title for a mode -- the SAME keys render() / renderElite() use for
// .wg-label (elite's grade-name suffix is intentionally omitted; the switch shows the base).
function modeTitle(mode) {
    switch (mode) {
        case MODE.SKILL_TREE: return L("headerSkillTree", "Upgrades");
        case MODE.POTENTIAL_TIER_XI: return L("capTierXI", "Tier XI");
        case MODE.FIELD_MODS: return L("headerFieldMods", "Field Modifications");
        case MODE.ELITE_REWARDS: return L("headerEliteRewards", "EXCLUSIVE REWARDS");
        case MODE.ELITE: return L("headerElite", "Elite System");
        default: return L("headerResearch", "Research");
    }
}

// Is (clientX, clientY) inside the switch title's CURRENT on-screen box? Measured fresh at
// event time (like chipAt) against the live layout, so a mode swap that re-texts/re-flows
// the title is always hit-tested correctly. The event coords and this rect are both in the
// same viewport space, so there's no positioning offset to get wrong.
function switchHit(switchEl, x, y) {
    if (!switchEl || switchEl.style.display === "none") return false;
    const r = switchEl.getBoundingClientRect();
    return !!r && x >= r.left && x <= r.right && y >= r.top && y <= r.bottom;
}

// Switch-title dim (inactive) vs bright (hovered) look, driven by an INLINE COLOR write.
// Measured live over two builds: motion events DO reach the header via .wg-hot and the
// hit-test passes, but neither a toggled `.wg-switch-hot` class NOR a dynamic inline
// OPACITY change ever brightened the title -- while a dynamic inline COLOR change repaints
// fine (the diagnostic's green text proved it). So dim/bright is a color swap, no opacity
// (dynamic opacity + `transition` is the combination that doesn't repaint in this Coherent
// build; cf. the :hover / :not() unreliability in gameface-css-gotchas). The fade comes from
// `transition: color` on .wg-switch -- color transitions DO animate here.
const SWITCH_COLOR = "#8e867d";       // dim / inactive (tertiary token)
// bright / hovered == the current heading's color EXACTLY (.wg-label #ede6d9), so a hovered
// switch title reads identically to the active title beside it -- keep these in lockstep.
const SWITCH_COLOR_HOT = "#ede6d9";
function setSwitchHot(switchEl, hot) {
    if (switchEl) switchEl.style.color = hot ? SWITCH_COLOR_HOT : SWITCH_COLOR;
}

// Hide the switch title. Called at the top of render() so any early return (no data,
// hidden bar, COMPLETE) leaves no stale switch title / hit-target. The switch's hover +
// click are hit-tested live off this element's rect by ensureHover (switchHit) via the
// .wg-hot layer, so hiding the element (display:none makes switchHit return false) is all
// that's needed -- there's no separate overlay to tear down.
function hideSwitch(root) {
    const r = root || getRoot();
    if (r && r.querySelector) {
        const sw = r.querySelector(".wg-switch");
        // Display:none only -- do NOT reset the hover color or _wgTarget here. hideSwitch
        // runs at the TOP of every render(), so clobbering the color would dim the title on
        // every push; a push while the cursor rests on it would leave it dim until the next
        // mousemove ("hover only works while moving"). While hidden, switchHit returns false
        // (display:none), so a stale _wgTarget can't be hovered or clicked anyway. The live
        // dim/bright color is owned by the mousemove handler; renderModeSwitch resets it only
        // on a genuine target change. (Same rule as the tooltip -- see gpb-widget skill.)
        if (sw) sw.style.display = "none";
    }
}

// Render (or hide) the dimmed switch title. Called at the end of BOTH render() and
// renderElite(). <2 available modes, or the current mode isn't in the list -> no switch.
// The title is VISUAL ONLY; ensureHover's .wg-hot handler hit-tests its rect for hover
// (brightening it via setSwitchHot) and click (firing selectMode with _wgTarget).
function renderModeSwitch(root, data) {
    const switchEl = root.querySelector(".wg-switch");
    if (!switchEl) return;
    const avail = ((data.availModes || "") + "").split(",").filter(Boolean);
    const idx = avail.indexOf(data.mode);
    if (avail.length < 2 || idx < 0) {
        switchEl.style.display = "none";
        switchEl._wgTarget = null;
        return;
    }
    const target = avail[(idx + 1) % avail.length];
    const prevTarget = switchEl._wgTarget;
    switchEl.textContent = modeTitle(target);
    switchEl._wgTarget = target;
    switchEl.style.display = "block";
    // Reset to the dim resting color ONLY when the switch first appears or its target
    // changes -- NOT on every push. A repeat push for the SAME target while the cursor rests
    // on the title must NOT clobber the hover color (no mousemove would fire to re-brighten,
    // so it would stay dim until the mouse moved). The mousemove handler owns the live
    // dim/bright color; render preserves it across repeat pushes. (Same rule as the tooltip
    // -- render never blanket-resets hover state; see gpb-widget skill.)
    if (prevTarget !== target) setSwitchHot(switchEl, false);
}

function render(model) {
    const root = ensureRoot();
    // Hide the switch title up front; renderModeSwitch re-shows it at the end of whichever
    // render path runs. Early returns below then leave the switch hidden.
    hideSwitch(root);
    const label = root.querySelector(".wg-label");
    const catIcon = root.querySelector(".wg-cat-icon");
    const upgradesEl = root.querySelector(".wg-upgrades");
    const data = unwrap(model && model.wgResearch);

    const xpEl = root.querySelector(".wg-xp");
    // Tier-XI "next upgrade available" CTA below the bar. Bound once; hidden by
    // default and only shown by the skill_tree branch below. Clicking it opens
    // WG's skill-tree screen (same command as the final tick).
    // Tier-XI "Next available:" row (caption + clickable upgrade chips) below the
    // bar. Hidden by default; the skill_tree branch shows it and (re)builds the chips
    // only when the upgrade set changes -- NOT every render -- so the hovered chip's
    // tooltip survives background pushes (rebuilding destroyed it, hence it only
    // appeared while the cursor was moving).
    const nextEl = root.querySelector(".wg-next");
    if (nextEl) nextEl.style.display = "none";

    if (!data) {
        const keys = model ? Object.keys(model).join(",") : "no-model";
        label.textContent = "WGMOD: waiting for data | keys=" + keys;
        setCatIcon(catIcon, "");
        setUpgrades(upgradesEl, 0, 0);
        xpEl.style.display = "none";
        return;
    }
    // Localized labels for this render (also read later by the hover tooltip builders).
    refreshLabels(data);
    // "Ignore Free XP": latch the flag for this render so the tooltip builders (which run
    // later, on hover) and the header readouts all pick the combat-XP glyph via
    // xpCurrencyIcon(). The root class drives the CSS glyph-size + shortfall-color tweaks.
    IGNORE_FREE_XP = !!data.ignoreFreeXp;

    // Show the bar ONLY in the plain garage. Python pushes visible=false while a
    // tank-setup / ammo loadout overlay is open (the params panel stays mounted to
    // show stat changes, so the bar would otherwise linger over it). An absent flag
    // (older Python build) is treated as visible -- fail open.
    if (data.visible === false) {
        root.style.display = "none";
        return;
    }
    root.style.display = "";

    // Apply the user's dragged/typed bar position (or the CSS default) before any
    // mode branch, so every mode -- including the elite early-return below -- honors it.
    // Stash the data so the window-resize handler can re-run applyPosition on a live
    // resolution / UI-scale change (which never re-pushes the model on its own).
    root._wgLastData = data;
    applyPosition(root, data);

    // Elite Levels (prestige) modes own the whole header + bar (grade/reward
    // readout, single-segment fill, combat-XP star), so they branch out early.
    if (data.mode === MODE.ELITE || data.mode === MODE.ELITE_REWARDS) {
        renderElite(root, data, data.mode === MODE.ELITE_REWARDS);
        return;
    }

    // The label-side counter is removed for the non-elite modes (tech-tree /
    // field-mods / skill-tree) -- hide it here. The elite branch (renderElite)
    // owns this slot for its own LVL n/m readout and isn't reached from here.
    setUpgrades(upgradesEl, 0, 0);
    // Right-side readout stays visible in every mode (set per-mode below).
    xpEl.style.display = "flex";

    const mode = data.mode;
    // Spendable XP (vehicle + free), the affordability yardstick for tooltips.
    const spendableXp = data.spendableXp | 0;
    // Inputs for the tooltip "≈ M-N battles" estimate (divisor selection + bonuses);
    // suppressed downstream when no divisor is available (no battles / unreadable).
    const battleEst = mkBattleEst(data);
    const sMin = data.scaleMin || 0;
    const sMax = data.scaleMax || 0;
    const fv = data.fillVehicle || 0;
    const ff = data.fillFree || 0;
    const span = Math.max(sMax - sMin, 1);
    const pct = (xp) => Math.max(0, Math.min(100, ((xp - sMin) / span) * 100));

    // Right-side readout: skill-tree shows the unlocked/total node COUNT fronted by
    // the Upgrades-screen counter glyph; every other mode (incl. COMPLETE below)
    // shows spendable Total XP.
    if (mode === MODE.SKILL_TREE) {
        root.querySelector(".wg-xp-ico").style.backgroundImage =
            "url('" + SKILL_COUNTER_ICON + "')";
        root.querySelector(".wg-xp-val").textContent =
            (data.fieldModsDone || 0) + "/" + (data.fieldModsTotal || 0);
        // ...and, beside the counter, the total spendable XP (vehicle + free) that
        // every other mode shows. NOT setXp(): its fillVehicle/fillFree args are a
        // node COUNT / 0 here, so use the already-plumbed spendableXp total instead.
        const xp2Val = root.querySelector(".wg-xp2-val");
        const xp2Ico = root.querySelector(".wg-xp2-ico");
        xp2Val.textContent = fmtXp(spendableXp, ",");
        xp2Ico.style.backgroundImage = "url('" + xpCurrencyIcon() + "')";
        // NB: Gameface rejects `display:inline-block` set imperatively (the stylesheet
        // value is fine, the CSSOM setter is not) -- use "block". As flex items they
        // stay in the header row regardless.
        xp2Val.style.display = "block";
        xp2Ico.style.display = "block";
    } else {
        setXp(root, data.fillVehicle, data.fillFree);
        hideXp2(root);
    }

    const vehEl = root.querySelector(".wg-fill-veh");
    const freeEl = root.querySelector(".wg-fill-free");
    // Clear any inline fill color set by a prior elite render (renderElite grade-colors
    // the fill inline). vehEl persists across renders/modes, so without this reset that
    // grade color leaks onto the tech-tree/field-mods/skill-tree fills, which want their
    // own CSS tone.
    vehEl.style.background = "";
    const ticksEl = root.querySelector(".wg-ticks");
    const tipEl = root.querySelector(".wg-tooltip");
    const hotEl = root.querySelector(".wg-hot");
    // Hover lives on a dedicated transparent overlay (.wg-hot), the only element
    // we re-enable pointer-events on (root stays pointer-events:none so it never
    // steals hangar drag-to-rotate). It's sized in CSS to span the bar AND the
    // glyphs below it, so hovering an icon registers too.
    ensureHover(hotEl, tipEl);
    hotEl._wgMode = mode;   // gates the tick-hover proximity (single-milestone modes)
    // Drop a tooltip left over from a previous vehicle/data on a genuine change (render()
    // rebuilds the ticks but doesn't re-run the hover hit-test); kept on a repeat push.
    hideStaleTooltip(hotEl, tipEl, data);
    // Default hover-overlay height (CSS); the tick loop below grows it only when a
    // glyph row is dropped. Reset here so a prior vehicle's stacked height doesn't
    // linger on this one (incl. the COMPLETE early-return just below).
    hotEl.style.bottom = "";
    // Tier-XI available-upgrade chips: render the visuals + register their hit-zones
    // on .wg-hot (which owns pointer events). Rebuild ONLY when the upgrade set
    // changes, so a hovered chip's tooltip isn't wiped by background pushes.
    // Capstone-only state: every node but the FINAL one is unlocked (done == total-1)
    // and the final is available. That lone available node is already the bar's
    // rightmost (final) tick, so the "Next available:" chip for it just duplicates
    // that glyph -- drop the chips row and instead point a "Final upgrade available"
    // caption at the right end (and brighten the final tick glyph in the loop below).
    const stDone = data.fieldModsDone || 0;
    const stTotal = data.fieldModsTotal || 0;
    const onlyFinal = mode === MODE.SKILL_TREE && stTotal > 0 &&
        stDone === stTotal - 1 && arrLen(data.availUpgrades) >= 1;
    if (mode === MODE.SKILL_TREE && nextEl && !onlyFinal) {
        const sig = upgradesSig(data.availUpgrades, spendableXp);
        if (nextEl._wgSig !== sig) {
            nextEl._wgSig = sig;
            setActiveChip(hotEl, null);
            renderNextAvailable(nextEl, data.availUpgrades, hotEl, spendableXp, battleEst);
        } else {
            nextEl.style.display = "flex";   // unchanged -> keep chips + tooltip, re-show
        }
    } else {
        // No chip row (non-skill-tree, or the capstone-only state where the lone
        // available node is already the bar's final tick -- brightened in the tick loop).
        nextEl._wgSig = null;
        hotEl._wgChips = [];
        setActiveChip(hotEl, null);
    }
    // NB: do NOT hide the tooltip here. render() runs on every model update
    // (which can fire while the cursor sits still over the bar); force-hiding it
    // each render made the tip vanish whenever the cursor stopped moving. The
    // hover handler owns visibility -- it re-reads the (rebuilt) tick metadata
    // below, so an in-place refresh just updates the data under the cursor.

    // COMPLETE (nothing left to research/upgrade/unlock) -> just hide the bar; there's
    // no localized "Fully researched" header we want to show, and an empty bar adds no
    // information. Same for a degenerate empty scale (sMax<=sMin).
    if (mode === MODE.COMPLETE || sMax <= sMin) {
        root.style.display = "none";
        return;
    }
    // Tier-XI skill-tree mode: a COUNT bar (axis = total upgrade nodes, fill =
    // nodes unlocked), with one evenly-spaced tick per node -- bright left of the
    // fill (unlocked), dim to the right (locked) -- and the signature 'final'
    // upgrade carrying its icon on the rightmost tick. No per-node tooltips (the
    // tick loop below skips hover wiring for this mode). wg-skill gives the fill its
    // own steel-blue tone (.wg-skill .wg-fill-veh in CSS), distinct from tech-tree.
    root.className = (mode === MODE.SKILL_TREE ? "wg-skill" : "") + cbClass(data) +
        (IGNORE_FREE_XP ? " wg-ignore-free" : "");

    label.textContent = mode === MODE.SKILL_TREE ? L("headerSkillTree", "Upgrades")
        : mode === MODE.POTENTIAL_TIER_XI ? L("capTierXI", "Tier XI")
        : mode === MODE.FIELD_MODS ? L("headerFieldMods", "Field Modifications")
        : L("headerResearch", "Research");
    setCatIcon(catIcon, CAT_ICON[mode] || "");

    const vehW = pct(sMin + fv);
    const freeW = Math.max(0, pct(sMin + fv + ff) - vehW);
    vehEl.style.left = "0%";
    vehEl.style.width = vehW + "%";
    freeEl.style.left = vehW + "%";
    freeEl.style.width = freeW + "%";

    // Glowing current-position marker riding the fill's leading edge (the player's
    // current level). Same combined edge as the fill end -- vehW + freeW == the
    // clamped pct(sMin + fv + ff); skill_tree has ff=0 so it lands on the fill front.
    const curEl = root.querySelector(".wg-cur");
    curEl.style.left = (vehW + freeW) + "%";
    curEl.style.display = "block";

    const ticks = data.ticks;
    const n = arrLen(ticks);
    // Skill-tree ticks carry no per-node metadata (non-linear tree) -> no hover tooltips
    // (only the named FINAL tick tips). Other modes wire every tick into the hover system.
    const noTips = mode === MODE.SKILL_TREE;
    // Field mods unlock linearly (one by one), so only the NEXT one -- the first remaining
    // tick -- is ever clickable. Consumed on the first fieldmod the spec sees.
    let nextFieldMod = true;
    // Pre-pass: only glyph-bearing ticks (field mods + any icon tick) reserve a lane.
    // Done markers are EXCLUDED: they're custom-positioned at the left edge in lane 0, so
    // reserving a footprint at pct(0)=0% for them would wrongly bump a real near-left tick
    // into lane 1 for no visual reason.
    const place = computeLanes(ticks, n, pct, mode, hotEl,
        function (t) { return !t.done && (t.category === CAT.FIELDMOD || !!t.icon); });
    const res = renderTicks(ticksEl, ticks, n, function (t, i) {
        // State class: locked -> dim, affordable -> bright. In the capstone-only state the
        // final (icon) skill_tree tick IS the available node, so force it bright (wg-aff)
        // instead of the count-axis "right of fill" wg-locked dim.
        let stateClass = t.locked ? " wg-locked" : t.affordable ? " wg-aff" : "";
        if (onlyFinal && mode === MODE.SKILL_TREE && t.icon) stateClass = " wg-aff";
        // wg-done = session marker (green check + open-screen click). Done markers ride the
        // bar's LEFT EDGE (0%); .wg-hot extends past it (CSS) so the overhang stays hoverable
        // (hit-tested against the track, so curPct goes slightly negative and still falls
        // within CLICK_HIT_PCT of 0%).
        const className = "wg-tick wg-cat-" + (t.category || "x") + stateClass +
            (t.done ? " wg-done" : "");
        const leftPct = t.done ? 0 : pct(t.position);
        // Clickability -> the reverse-channel command a click fires:
        //  - done marker: open the native screen (never re-research).
        //  - skill-tree: only the final (icon) tick opens WG's skill-tree screen.
        //  - field-mod: LINEAR -> only the next tick is a candidate; if affordable, unlock
        //    it (a choice-pair level opens the screen since a click can't pick a variant).
        //  - tech-tree (vehicle/module): affordable + prereqs met -> research it.
        let cmd = null, arg;
        if (t.done) {
            // Done markers complete their follow-up: a field-mod tick opens Field Mods,
            // a MODULE tick buys + mounts the module (self-clears once owned), a VEHICLE
            // tick (and any fallback) opens the Research screen -- you can't mount a tank.
            if (t.category === CAT.FIELDMOD) cmd = CMD.OPEN_FIELD_MODS;
            else if (t.category === CAT.MODULE && t.actionId) { cmd = CMD.BUY_MOUNT; arg = t.actionId; }
            else cmd = CMD.OPEN_RESEARCH;
        } else if (mode === MODE.SKILL_TREE) {
            if (t.icon) cmd = CMD.OPEN_SKILL_TREE;
        } else if (t.category === CAT.FIELDMOD) {
            if (nextFieldMod) {
                nextFieldMod = false;
                if (t.affordable && t.actionId) { cmd = CMD.UNLOCK_FIELD_MOD; arg = t.actionId; }
            }
        } else if ((t.category === CAT.VEHICLE || t.category === CAT.MODULE)
                   && t.affordable && !t.locked && t.actionId) {
            cmd = CMD.RESEARCH_UNLOCK; arg = t.actionId;
        }
        const tip = !noTips || !!t.name;
        return {
            className: className,
            leftPct: leftPct,
            tip: tip,
            body: tip ? tooltipHtml(t, spendableXp, fv, battleEst, onlyFinal) : "",
            cmd: cmd,
            arg: arg,
            glyph: linearGlyph(t, mode),
            // Done markers keep lane 0: they're custom-positioned (no translateX base) and
            // sit alone at the left, so applyLane's transform would displace them.
            lane: t.done ? 0 : (place[i] ? place[i].lane : 0),
        };
    });
    hotEl._wgTickMeta = res.tickMeta;
    hotEl._wgClickMeta = res.clickMeta;

    // Header mode switch (next available mode, dimmed, to the right of the title).
    renderModeSwitch(root, data);
}

// Tooltip body for an elite mark: the grade/reward name, (rewards) the reward
// type, and the elite level the mark sits at.
function eliteTooltipHtml(t, isRewards, combatXp, est) {
    const name = t.name || "";
    // Category caption at the TOP (like native tooltips put the kind line above the
    // title). Rewards: JUST the localized reward TYPE. Grade progression: the localized
    // "Elite Levels" label + the level this mark sits at.
    let caption;
    if (isRewards) {
        const opts = splitLines(t.options);
        caption = opts.length ? escapeHtml(opts[0]) : "";
    } else {
        // Just "Elite Levels" -- the specific level is painted over the emblem icon
        // (below), the way the carousel's prestige tooltip shows it.
        caption = escapeHtml(L("capEliteLevel", "Elite Levels"));
    }
    // Icon on the right: a reward thumbnail (rewards) or the grade emblem with the
    // elite level overlaid in the grade emblemFont (grade progression). Empty -> none.
    let iconHtml = "";
    if (t.icon && t.icon.indexOf("img://") === 0) {
        iconHtml = isRewards ? bgIconHtml(t.icon, "wg-tip-icon-reward")
            : eliteTipIconHtml(t.icon, t.position | 0);
    }
    let text = caption ? capHtml(caption) : "";
    if (name) text += '<div class="wg-tip-name">' + escapeHtml(name) + "</div>";
    // Footer: progress to this milestone as "<earned> / <needed> combat XP" (the
    // tick's xpRequired is the cumulative combat XP to reach the level).
    const foot = xpFracHtml(combatXp, t.xpRequired, COMBAT_XP_ICON, undefined, est);
    return joinSections([tipMain(iconHtml, text), foot]);
}

// Render the ELITE (grade band) / ELITE_REWARDS (reward roadmap) views. Reuses
// the bar's track + hover overlay but with a single fill segment, a combat-XP
// readout, an "Elite Lvl N/350" counter, and grade-pip / reward-thumbnail ticks.
function renderElite(root, data, isRewards) {
    root.className = "wg-elite" + (isRewards ? " wg-elite-rewards" : "") + cbClass(data) +
        (IGNORE_FREE_XP ? " wg-ignore-free" : "");
    const label = root.querySelector(".wg-label");
    const catIcon = root.querySelector(".wg-cat-icon");
    const upgradesEl = root.querySelector(".wg-upgrades");
    const xpEl = root.querySelector(".wg-xp");
    const vehEl = root.querySelector(".wg-fill-veh");
    const freeEl = root.querySelector(".wg-fill-free");
    const ticksEl = root.querySelector(".wg-ticks");
    const tipEl = root.querySelector(".wg-tooltip");
    const hotEl = root.querySelector(".wg-hot");
    ensureHover(hotEl, tipEl);
    hotEl._wgMode = data.mode;   // elite/elite_rewards -> nearest-anywhere tick hover
    hideStaleTooltip(hotEl, tipEl, data);   // drop a previous vehicle's tooltip on a data change
    hotEl._wgChips = [];         // no upgrade chips in elite modes
    setActiveChip(hotEl, null);  // clear any active chip ref from a prior skill_tree render
    // Null the chip signature too, else a skill_tree vehicle returned to after this
    // elite render keeps its stale _wgSig and render() takes the re-show-without-
    // rebuild branch -> chip DOM shows but _wgChips stays empty -> dead hover/click.
    const nextSig = root.querySelector(".wg-next");
    if (nextSig) nextSig._wgSig = null;

    // Header: title (grade family / "EXCLUSIVE REWARDS"), the Elite-level
    // counter, the class+elite badge, and the combat-XP readout.
    const grade = data.eliteGrade || "";
    const gradeName = grade ? grade.charAt(0).toUpperCase() + grade.slice(1) : "";
    label.textContent = isRewards
        ? L("headerEliteRewards", "EXCLUSIVE REWARDS")
        : (L("headerElite", "Elite System") + (gradeName ? " " + gradeName : ""));
    const lvl = data.eliteLevel | 0;
    // The current level now rides in the category-icon arrowhead badge, so the header
    // "LVL x/y" counter is redundant -- hide it in elite modes.
    upgradesEl.textContent = "";
    upgradesEl.style.display = "none";
    // Category icon: in BOTH elite modes show the CURRENT grade emblem -- the badge
    // of the highest grade reached, with the current elite level number over it,
    // exactly like the tick emblems -- instead of the generic class+elite badge. The
    // emblem URL comes from the model (domain), so it works even in ELITE_REWARDS
    // mode, whose ticks are reward art, not grade chevrons. Empty below the first
    // grade / no grades -> the class+elite badge fallback. The prestige/MAX badge
    // carries no emblemFont, so gradeFamily() returns "" and the number is skipped
    // (numberless badge), matching the in-game MAX emblem.
    const curEmblem = data.eliteCurrentIcon || "";
    const useTab = ELITE_CAT_ICON_STYLE === "tab" && !!gradeTabUrl(curEmblem, tabSizeFor(lvl));
    // .wg-cat-icon-tab gives the wider arrowhead its own layout; wg-tab carries the
    // art/num styling shared with the below-bar tick badges.
    catIcon.classList.toggle("wg-cat-icon-tab", useTab);
    catIcon.classList.toggle("wg-tab", useTab);
    // Per-size centering class (shared with the ticks) so the category-icon badge
    // content-centers on the bar's left edge and lines up with the first tick. The
    // cat-icon element persists across renders, so clear any stale size first.
    catIcon.classList.remove("wg-tab-short", "wg-tab-medium", "wg-tab-long");
    if (useTab) catIcon.classList.add("wg-tab-" + tabBadgeSize(curEmblem, lvl, ELITE_TAB_FORCE_MAX));
    if (useTab) {
        // Tab style: the cat-icon box stays anchored (centered) on the bar's LEFT edge
        // so the NUMBER centers there. fillTabBadge draws the arrowhead art + numeral
        // (ELITE_TAB_FORCE_MAX previews the numberless MAX hexagon on any vehicle).
        catIcon.style.backgroundImage = "";
        catIcon.style.display = "block";
        fillTabBadge(catIcon, curEmblem, lvl, ELITE_TAB_FORCE_MAX);
    } else if (curEmblem) {
        setCatIcon(catIcon, curEmblem);
        const curFam = gradeFamily(curEmblem);
        if (curFam) catIcon.appendChild(emblemNumber(lvl, curFam));
    } else {
        setCatIcon(catIcon, eliteIcon(data.vehicleClass));
    }
    xpEl.style.display = "flex";
    root.querySelector(".wg-xp-ico").style.backgroundImage = "url('" + COMBAT_XP_ICON + "')";
    root.querySelector(".wg-xp-val").textContent = fmtXp(data.combatXp || 0, ",");
    hideXp2(root);   // elite shows a single combat-XP figure -- no skill_tree XP pair

    // Single-segment fill across the band/roadmap axis.
    const sMin = data.scaleMin || 0;
    const sMax = data.scaleMax || 0;
    const span = Math.max(sMax - sMin, 1);
    const pct = (x) => Math.max(0, Math.min(100, ((x - sMin) / span) * 100));
    const fillPos = sMin + (data.fillVehicle || 0);
    vehEl.style.left = "0%";
    vehEl.style.width = pct(fillPos) + "%";
    // Glowing current-position marker at the single-segment fill edge (same white
    // "current" language as the tech-tree/skill-tree bars; the fill itself is
    // grade-colored, the marker stays white).
    const curEl = root.querySelector(".wg-cur");
    curEl.style.left = pct(fillPos) + "%";
    curEl.style.display = "block";
    // Grade-color the fill to the current grade family (iron/bronze/silver/gold),
    // matching the tab-badge number tint. Only in the grade-band mode -- ELITE_REWARDS
    // keeps its rarity purple (it's a reward roadmap, not a grade) -- and never in
    // color-blind mode, where an inline background would beat the .wg-colorblind CSS
    // override. Always reset first: vehEl persists across renders/modes, so a stale
    // inline color would leak. Empty family (MAX/prestige, below-first-grade) keeps
    // the CSS default gold.
    vehEl.style.background = "";
    if (!isRewards && !data.colorBlind) {
        const fillColor = GRADE_COLOR[gradeFamily(curEmblem)];
        if (fillColor) vehEl.style.background = fillColor;
    }
    freeEl.style.left = "0%";
    freeEl.style.width = "0%";

    // Milestone ticks: grade sub-pips, or reward thumbnails ringed by state.
    const ticks = data.ticks;
    const n = arrLen(ticks);
    // Pre-pass: every elite tick carries a glyph, so all reserve a lane (no predicate).
    const place = computeLanes(ticks, n, pct, data.mode, hotEl);
    const battleEst = mkBattleEst(data);
    const res = renderTicks(ticksEl, ticks, n, function (t, i) {
        return {
            className: "wg-tick wg-elite-tick wg-state-" + (t.state || "upcoming"),
            leftPct: pct(t.position),
            tip: true,
            body: eliteTooltipHtml(t, isRewards, data.combatXp | 0, battleEst),
            glyph: eliteGlyph(t, isRewards),
            lane: place[i] ? place[i].lane : 0,
        };
    });
    hotEl._wgTickMeta = res.tickMeta;
    hotEl._wgClickMeta = res.clickMeta;   // empty -- elite grade/reward marks aren't clickable
    // Don't force-hide the tooltip here (render() re-runs on model updates); the
    // hover handler owns visibility, same as the main bar.

    // Header mode switch (e.g. Elite System <-> Exclusive Rewards).
    renderModeSwitch(root, data);
}

// Attach the hover handler to the ticks layer exactly once. That layer is the
// only element we re-enable pointer-events on (the root stays
// pointer-events:none so it never steals hangar drag-to-rotate) and is extended
// in CSS to span the bar AND the glyphs below it. Resolve the hovered tick two
// ways: (1) the exact element under the cursor (works when hovering a glyph,
// whose ancestor .wg-tick carries the body); (2) otherwise the nearest tick by
// cursor x (when hovering bare bar, where e.target is the layer itself).
function ensureHover(hotEl, tipEl) {
    if (hotEl._wgHoverBound) return;
    hotEl._wgHoverBound = true;
    const show = (body, leftPct, lane) => {
        // Skip the work when the exact same tooltip is already shown at the same spot: the
        // mousemove fires this on EVERY pointer event over one tick, and rebuilding the
        // innerHTML + running clampTip (which resets inline styles, reads getBoundingClientRect
        // and may flip the tip) each time is pure churn. Re-show whenever it's hidden or the
        // content/position/lane changed (a data change clears the cache -- see render()).
        if (tipEl.style.display === "block" && tipEl._wgShownBody === body &&
            tipEl._wgShownLeft === leftPct && tipEl._wgShownLane === lane) return;
        tipEl._wgShownBody = body;
        tipEl._wgShownLeft = leftPct;
        tipEl._wgShownLane = lane;
        tipEl.innerHTML = body;
        tipEl.style.left = leftPct + "%";
        tipEl.style.display = "block";
        // lane = the hovered glyph's de-crowding row; clampTip drops the tooltip below it
        clampTip(tipEl, lane);   // keep it within the bar width / clear the glyph / flip above near the bottom
    };
    hotEl.addEventListener("mousemove", function (e) {
        // While Ctrl is held the bar is in reposition mode -> a move cursor, no matter
        // what's under the cursor (Ctrl+drag moves the bar; see the mousedown handler).
        const dragMode = e.ctrlKey;
        // Mode-switch title (in the header ABOVE the bar): .wg-hot is extended up over the
        // header, so it carries the switch's events (the title itself is pointer-events:none
        // under the root). Hit-test the title's live rect and, when the cursor is over it,
        // raise its opacity + show a pointer -- no bar tooltip. Skipped in drag mode.
        const root0 = getRoot();
        const switchEl = root0 && root0.querySelector && root0.querySelector(".wg-switch");
        if (switchEl && !dragMode && switchHit(switchEl, e.clientX, e.clientY)) {
            setSwitchHot(switchEl, true);
            setActiveChip(hotEl, null);
            tipEl.style.display = "none";
            hotEl.style.cursor = "pointer";
            return;
        }
        if (switchEl) setSwitchHot(switchEl, false);
        // Tier-XI "Next available:" chips first (they own a framed tooltip + click,
        // hit-tested here since they can't receive events themselves).
        const chip = chipAt(hotEl, e.clientX, e.clientY);
        if (chip) {
            setActiveChip(hotEl, chip);
            tipEl.style.display = "none";
            hotEl.style.cursor = dragMode ? "move" : "pointer";
            return;
        }
        setActiveChip(hotEl, null);
        // Read the bar TRACK rect ONCE for this event and share it across the affordance +
        // tooltip hit-tests (each did its own forced layout read before).
        const rect = barRect(hotEl);
        // Header band (above the ticks layer): .wg-hot now reaches up here for the switch,
        // but tick tooltips + the pointer affordance belong to the BAR only -- gate them out
        // when the cursor is above the ticks. (Ctrl+drag still works anywhere via mousedown.)
        if (rect && e.clientY < rect.top) {
            tipEl.style.display = "none";
            hotEl.style.cursor = dragMode ? "move" : "";
            return;
        }
        // Pointer affordance: a pointer cursor only while over a clickable tick.
        hotEl.style.cursor = dragMode ? "move"
            : (nearestClick(hotEl, e.clientX, rect) ? "pointer" : "");
        // (1) exact element under the cursor.
        let node = e.target;
        while (node && node !== hotEl) {
            if (node._wgBody !== undefined) { show(node._wgBody, node._wgLeft, node._wgLane); return; }
            node = node.parentElement;
        }
        // (2) nearest tick by cursor x.
        const near = nearestByX(hotEl._wgTickMeta, hotEl, e.clientX, rect);
        if (!near.best) { tipEl.style.display = "none"; return; }
        // Single-milestone bars (skill_tree final upgrade; the speculative potential-Tier-XI
        // tick, pinned at 100%) carry ONE tooltip-tick far from the bar's left, so gate it by
        // proximity -- else it would pop across the whole empty bar. Other modes keep
        // nearest-anywhere (dense ticks make that the right behavior).
        const single = hotEl._wgMode === MODE.SKILL_TREE ||
            hotEl._wgMode === MODE.POTENTIAL_TIER_XI;
        const ok = !single || near.dist <= 6;
        if (ok) show(near.best.body, near.best.left, near.best.lane); else tipEl.style.display = "none";
    });
    hotEl.addEventListener("mouseleave", function () {
        setActiveChip(hotEl, null);
        tipEl.style.display = "none";
        const root = getRoot();
        const sw = root && root.querySelector && root.querySelector(".wg-switch");
        if (sw) setSwitchHot(sw, false);
    });
    // Ctrl+drag to reposition the whole bar. Ctrl-gated so a normal click can't move it
    // by accident; a plain mousedown falls through to the click handler (research/unlock).
    // The bar is position:fixed with translateX(-50%), so we track the bar's CENTER-x /
    // TOP (the stored anchor). On release we report the final px to Python via
    // setPosition, which persists it (MSA) and re-pushes -- applyPosition then re-applies
    // the same coords (no jump). _wgDidDrag suppresses the click that follows the drag.
    hotEl.addEventListener("mousedown", function (e) {
        if (!e.ctrlKey) return;
        const root = getRoot();
        if (!root) return;
        e.preventDefault();
        e.stopPropagation();
        const r0 = root.getBoundingClientRect();
        const halfW = r0.width / 2;
        const offX = e.clientX - (r0.left + halfW);   // cursor -> bar center-x
        const offY = e.clientY - r0.top;              // cursor -> bar top
        root._wgDragging = true;
        root._wgDidDrag = true;
        hotEl.style.cursor = "move";
        const onMove = function (ev) {
            const w = window.innerWidth || 0;
            const h = window.innerHeight || 0;
            let cx = ev.clientX - offX;
            let cy = ev.clientY - offY;
            // clamp so the bar can't be dragged off-screen (whole width kept visible).
            // Floor y at 1, not 0: y=0 is the "auto" sentinel, so a flush-to-top drag stored
            // as 0 would be discarded (treated as auto) on the next push.
            if (w) cx = Math.max(halfW, Math.min(w - halfW, cx));
            if (h) cy = Math.max(1, Math.min(h - 20, cy));
            root.style.left = Math.round(cx) + "px";
            root.style.top = Math.round(cy) + "px";
        };
        const onUp = function () {
            document.removeEventListener("mousemove", onMove, true);
            document.removeEventListener("mouseup", onUp, true);
            root._wgDragging = false;
            const r = root.getBoundingClientRect();
            const vp = currentVP();
            invokeCommand(CMD.SET_POSITION, {
                x: Math.round(r.left + r.width / 2),
                y: Math.max(1, Math.round(r.top)),   // never 0 (the auto sentinel)
                // record the viewport this px was captured at, so a later resolution /
                // UI-scale change rescales it proportionally (see applyPosition).
                w: vp.w, h: vp.h,
            });
            // keep _wgDidDrag set through the click that fires right after this mouseup,
            // then clear it (the click handler reads it to suppress a research action).
            setTimeout(function () { root._wgDidDrag = false; }, 0);
        };
        document.addEventListener("mousemove", onMove, true);
        document.addEventListener("mouseup", onUp, true);
    });
    // Click -> a Tier-XI chip (exact box hit) first, else the nearest clickable tick
    // (proximity-gated, with WG's confirm dialog backstopping any imprecise hit). Bail on
    // a Ctrl-click or the tail of a drag so repositioning never triggers research/unlock.
    hotEl.addEventListener("click", function (e) {
        if (e.ctrlKey) return;
        const root = getRoot();
        if (root && root._wgDidDrag) return;
        // Mode-switch title click (header band): swap to the next mode, and DON'T fall
        // through to the bar-tick resolver (which is cursor-x only and would fire an
        // unlock for whatever tick sits at that x).
        const switchEl = root && root.querySelector && root.querySelector(".wg-switch");
        if (switchEl && switchHit(switchEl, e.clientX, e.clientY)) {
            if (switchEl._wgTarget) invokeCommand(CMD.SELECT_MODE, switchEl._wgTarget);
            return;
        }
        const chip = chipAt(hotEl, e.clientX, e.clientY);
        // chipAt returns any chip under the cursor regardless of clickability; an
        // unaffordable frontier chip carries a null cmd -> swallow the click here.
        if (chip) { if (chip.cmd) invokeCommand(chip.cmd, chip.arg); return; }
        // A click up in the header band (not on the switch) must not fire a tick action.
        const rect = barRect(hotEl);
        if (rect && e.clientY < rect.top) return;
        const hit = nearestClick(hotEl, e.clientX);
        if (hit) invokeCommand(hit.cmd, hit.arg);
    });
}

// A screen-resolution / UI-scale change resizes the Gameface viewport but does NOT
// re-push the model, so render()/applyPosition wouldn't otherwise re-run and the bar
// would keep its stale geometry. Re-run applyPosition on resize against the last-pushed
// data: auto re-derives the CSS default, a pinned position rescales proportionally.
// rAF-coalesced so a burst of resize events (e.g. dragging the scale slider) collapses to
// one recompute. (The Python g_guiResetters / settings listeners are a backstop for
// change types this event may not fire on.)
function onViewportResize() {
    if (onViewportResize._pending) return;
    onViewportResize._pending = true;
    const raf = window.requestAnimationFrame || function (f) { f(); };
    raf(function () {
        onViewportResize._pending = false;
        const root = getRoot();
        // The switch title flows inside the header, so it needs no re-measure on resize
        // (unlike the old body-level overlay).
        if (root && root._wgLastData) applyPosition(root, root._wgLastData);
    });
}

// Cold-mount self-heal. The widget repaints only when its ModelObserver's data-changed
// callback fires (observer.onUpdate -> render). But on a freshly mounted subview the engine
// does NOT deliver that callback until the view next composites -- which in the idle garage
// only happens when the camera moves. So after a mode/tank switch the bar looks frozen until
// the player nudges the camera (then every queued update lands at once). The first paint
// works only because it's a DIRECT render() call below, not observer-driven.
//
// Fix: poll a cheap monotonic counter (wgResearch.rev, bumped by Python on every push) and
// render when it changes. This runs even when the data-changed event is dormant, so the bar
// follows pushes within one poll interval. Idle cost is a shallow field read + compare; a
// real render happens only when rev actually moves, so no spurious tick rebuilds.
let _lastRev = null;

function revOf(model) {
    const data = unwrap(model && model.wgResearch);
    return data && data.rev !== undefined ? data.rev : null;
}

function renderAndTrack(model) {
    _lastRev = revOf(model);
    render(model);
}

function pollForChanges() {
    const rev = revOf(observer.model);
    if (rev !== null && rev !== _lastRev) renderAndTrack(observer.model);
}

engine.whenReady.then(() => {
    observer.onUpdate(renderAndTrack);   // warm path: instant repaint when the event fires
    observer.subscribe();
    renderAndTrack(observer.model);      // direct initial paint (observer event not needed)
    // Cold fallback: re-created per mount (cleared first) so intervals never stack and the
    // closure always targets the current observer.
    if (window.__wgPoll) clearInterval(window.__wgPoll);
    window.__wgPoll = setInterval(pollForChanges, 250);
    // Add the viewport listener once, even if this module is re-executed on a later
    // hangar mount (guarded so we don't stack duplicate handlers on the shared document).
    if (!window._wgResizeHooked) {
        window._wgResizeHooked = true;
        window.addEventListener("resize", onViewportResize);
    }
});

// WGMod research-progress widget. Injected into the hangar document by OpenWG.
// Reads our data model (exposed as `wgResearch` on the host sub-view's model)
// via ModelObserver, and renders a single-axis XP bar with stacked fill + ticks.
import { ModelObserver } from "../../libs/model.js";

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
    tech_tree: "img://gui/maps/icons/hangar/vehicleMenu/large/research.png",
    field_mods: "img://gui/maps/icons/hangar/vehicleMenu/large/fieldModification.png",
    // Tier-XI vehicle skill tree -> the dedicated "Upgrades" vehicle-management
    // section glyph (white tank + node network), matching research/fieldMod above.
    skill_tree: "img://gui/maps/icons/hangar/vehicleMenu/large/vehSkillTree.png",
};

// Skill-tree (Tier-XI upgrades) mode replaces the right-side Total-XP readout with
// an "unlocked / total nodes" counter, fronted by the in-game Upgrades-screen
// counter glyph (the small chevron shown beside its own node counter).
const SKILL_COUNTER_ICON = "img://gui/maps/icons/skillTree/tree/counter.png";

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

// EXPERIMENT (A-B): which art fills the elite category-icon slot.
//   "emblem" -> the hexagon grade emblem (current shipped default)
//   "tab"    -> the battle team-HP arrowhead/chevron grade badge ("tab" art)
// The tab set is .../prestige/tab/<family>/<size>/<grade>.png (size short|medium|
// long). NB the tab PNGs are OPAQUE in the game files -- their see-through look in
// battle is a game-applied style, not baked into the art. See IDEAS.md.
const ELITE_CAT_ICON_STYLE = "tab";     // "emblem" | "tab"
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

// The ELITE grade tick renders the in-game prestige HEXAGON EMBLEM -- the exact
// badge the hangar carousel vehicle tooltip shows (game component
// PrestigeProgressSymbol: a single emblem PNG drawn once, no backing/glow/blend).
// The 72x72 emblem art is solid (~245/255 alpha over the shape), so one draw reads
// opaque on the hangar -- no stacking trick needed (that was for the translucent
// chevron `tab` art, now retired). The emblem URL arrives on the tick as t.icon
// (.../prestige/emblem/<size>/<family>/<sub>.png, or .../prestige.png for MAX).
const GRADE_FAMILIES = { iron: 1, bronze: 1, silver: 1, gold: 1, enamel: 1 };
// Per-grade number tint -- the EXACT values from the game's own PrestigeProgressTab
// component CSS (.level color per grade). enamel reuses gold, as the game does.
const GRADE_COLOR = {
    iron: "#909ba1",
    bronze: "#f18140",
    silver: "#87b2ca",
    gold: "#ecbe6e",
    enamel: "#ecbe6e",
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
    return family === "enamel" ? "gold" : (family || "gold");
}
function emblemFontUrl(family, digit) {
    return "img://gui/maps/icons/prestige/emblemFont/16x33/" +
        emblemFontFamily(family) + "/" + digit + ".png";
}
// The level number centered over the hexagon emblem: a flex row of emblemFont digit
// glyph divs (Gameface clips an <img>, so each glyph is a background-image div). The
// "1" glyph is narrower in the game art, so flag it for a tighter width.
function emblemNumber(level, family) {
    const wrap = document.createElement("span");
    wrap.className = "wg-tick-emblem-num";
    const s = String(level);
    for (let i = 0; i < s.length; i++) {
        const d = document.createElement("span");
        d.className = "wg-emblem-digit" + (s[i] === "1" ? " wg-emblem-digit-one" : "");
        d.style.backgroundImage = "url('" + emblemFontUrl(family, s[i]) + "')";
        wrap.appendChild(d);
    }
    return wrap;
}

// HTML-string form of emblemNumber() (the tooltip is built as an innerHTML string,
// not DOM): the grade-colored emblemFont digit glyphs for `level`. Each glyph is a
// background-image span (Gameface clips <img>). "1" is flagged narrower.
function emblemNumberHtml(level, family) {
    const s = String(level | 0);
    let h = "";
    for (let i = 0; i < s.length; i++) {
        const cls = "wg-emblem-digit" + (s[i] === "1" ? " wg-emblem-digit-one" : "");
        h += '<span class="' + cls + '" style="background-image:url(\'' +
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
    if (t.category === "fieldmod") return L("capFieldMod", "Field Modification");
    return "";
}

// A faint horizontal rule between tooltip sections (mirrors WG's native tooltip
// divider). joinSections() drops it between any two empty sections, so a divider
// only ever appears where two real sections meet.
function joinSections(sections) {
    return sections.filter(function (s) { return s; })
        .join('<div class="wg-tip-div"></div>');
}

// A small inline XP-currency glyph (background-image span -- Gameface clips <img>,
// but honors background-size:contain on a box). `url` is XP_ICON (total XP) or
// COMBAT_XP_ICON (vehicle/combat XP). Sits right after the figure it annotates. The
// combat-XP art carries more transparent padding, so it gets a size-bump modifier to
// read at the same visual size as the total-XP glyph (mirrors the header's own
// .wg-elite .wg-xp-ico override).
function xpIco(url) {
    const cls = url === COMBAT_XP_ICON ? "wg-tip-xp-ico wg-tip-xp-ico-combat" : "wg-tip-xp-ico";
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
function xpFracHtml(have, need, iconUrl, vehHave) {
    need = need | 0;
    if (need <= 0) return "";
    have = have | 0;
    const ico = xpIco(iconUrl || XP_ICON);   // headline currency (reused by total remaining)
    // Unaffordable ("not yet reachable") -> the cost itself is tinted the shortfall red,
    // the same signal it carried before the cost-only headline change.
    const cls = have < need ? "wg-tip-xp wg-tip-short" : "wg-tip-xp";
    let h = '<div class="' + cls + '">' + fmtXp(need) + ico + "</div>";
    if (have < need) {
        const left = need - have;
        let sub = "";
        // Combat XP (the vehicle's own XP alone) FIRST -- shown only when free XP
        // actually moves the number (otherwise identical to the total remaining).
        if (vehHave !== undefined) {
            const vehLeft = need - (vehHave | 0);
            if (vehLeft > left) {
                sub += '<span class="wg-tip-rem-veh">-' + fmtXp(vehLeft) +
                    xpIco(COMBAT_XP_ICON) + "</span>";
            }
        }
        // Then the total remaining (free XP counts), in the headline's currency.
        sub += '<span class="wg-tip-rem-tot">-' + fmtXp(left) + ico + "</span>";
        h += '<div class="wg-tip-xp-rem">' + sub + "</div>";
    }
    return h;
}

// Effect/bonus lines (field-mod & skill-tree KPI text, e.g. "+1% to concealment"),
// one tertiary-body row per line. The Python side joins multiple KPIs with "\n".
// Empty string -> nothing rendered (features / mechanic perks carry no KPI text).
function effectHtml(effect) {
    const lines = (effect || "").split("\n").filter(function (s) { return s; });
    let h = "";
    for (let i = 0; i < lines.length; i++) {
        h += '<div class="wg-tip-effect">' + escapeHtml(lines[i]) + "</div>";
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
        // Each variant's buffs are TAB-separated (Python); render one row each.
        const buffs = (optEffects[i] || "").split("\t").filter(function (s) { return s; });
        for (let j = 0; j < buffs.length; j++) {
            h += '<div class="wg-tip-variant-eff">' + escapeHtml(buffs[j]) + "</div>";
        }
        h += "</div>";
    }
    return h + "</div>";
}

// A background-image icon box for the tooltip title block (module/vehicle art,
// grade emblem, or skill-tree perk glyph -- all full img:// URLs).
function bgIconHtml(url) {
    return '<div class="wg-tip-icon" style="background-image:url(\'' + url + '\')"></div>';
}

// Icon markup for a tick's tooltip title block. Field mods show their signature
// hexagon + roman numeral (matching the bar's own field-mod glyph), NOT a generic
// section icon. Everything else shows the item's img:// art (tech-tree module /
// vehicle glyph, grade emblem, skill-tree perk). A field-mod's t.icon is only a raw
// basename (not a URL), so it is never used as a background image. No usable art ->
// "" (text-only tooltip, header row omitted).
function tickIconHtml(t) {
    if (t.category === "fieldmod") {
        return '<div class="wg-tip-icon wg-tip-hex"><span>' +
            escapeHtml(romanize(t.level)) + "</span></div>";
    }
    if (t.icon && t.icon.indexOf("img://") === 0) return bgIconHtml(t.icon);
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
function tipMain(iconHtml, text) {
    if (!iconHtml) return text;
    // Tag the block with the icon it carries so the CSS can reserve a right-hand
    // column exactly as wide as that icon (see .wg-tip-main-* ). The icon is taken
    // out of flow (absolute, top-right) so .wg-tip-main is a plain BLOCK: Coherent
    // sized the former flex row from the text's FIRST line only, so any wrapped line
    // overflowed the row and spilled over the divider below -- a block always grows
    // to its full wrapped text. Order matters: the hex/elite icons also carry the
    // base "wg-tip-icon" class, so test the specific ones first.
    var mod = iconHtml.indexOf("wg-tip-hex") >= 0 ? " wg-tip-main-hex"
        : iconHtml.indexOf("wg-tip-icon-elite") >= 0 ? " wg-tip-main-elite"
        : " wg-tip-main-icon";
    return '<div class="wg-tip-main' + mod + '"><div class="wg-tip-text">' + text +
        "</div>" + iconHtml + "</div>";
}

// Tooltip body for a tick, built as ordered sections joined by dividers for clear
// hierarchy: MAIN (text block [type caption + title + effect / choice variants] +
// right-side icon) -> FOOTER ("have / need XP", or the prerequisite line when
// locked). A field-mod choice level puts its selectable variants (each with its
// buffs) in place of a single title.
function tooltipHtml(t, spendableXp, fillVehicle) {
    const opts = (t.options || "").split("\n").filter(function (s) { return s; });
    const optEffects = (t.optionEffects || "").split("\n");
    let text = "", foot = "";
    if (t.category === "fieldmod") {
        const cap = capHtml(escapeHtml(L("capFieldMod", "Field Modification")));
        if (opts.length) {
            // Choice level -> the selectable variants ARE the content (with buffs).
            text = cap + variantsHtml(opts, optEffects);
        } else {
            const name = tickName(t);
            const nm = name ? '<div class="wg-tip-name">' + escapeHtml(name) + "</div>" : "";
            text = cap + nm + effectHtml(t.effect);
        }
    } else {
        // Type caption: tech-tree kind ("Gun"/"Turret"/.../"Tier IX"), else "Upgrade"
        // for tier-XI skill-tree nodes (which carry no kindLabel).
        const cap = t.kindLabel ? capHtml(escapeHtml(t.kindLabel))
            : t.category === "upgrade" ? capHtml(escapeHtml(L("headerSkillTree", "Upgrades"))) : "";
        const name = tickName(t);
        const nm = name ? '<div class="wg-tip-name">' + escapeHtml(name) + "</div>" : "";
        text = cap + nm + effectHtml(t.effect);
    }
    if (t.locked) {
        // Name the blocking prerequisites when known, else the generic line.
        const reqs = (t.prereqNames || "").split("\n").filter(function (s) { return s; });
        foot = reqs.length
            ? '<div class="wg-tip-status">' + escapeHtml(L("requires", "Required:")) + " " +
                reqs.map(escapeHtml).join(", ") + "</div>"
            : '<div class="wg-tip-status">' +
                escapeHtml(L("prereqNotMet", "Prerequisites not met")) + "</div>";
    } else {
        foot = xpFracHtml(spendableXp, t.position, XP_ICON, fillVehicle);
    }
    // Text block + its icon are ONE unit (no divider between them); the divider only
    // separates that unit from the footer (cost / prerequisite).
    return joinSections([tipMain(tickIconHtml(t), text), foot]);
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
        "url('" + XP_ICON + "')";
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
        // that's already a map (e.g. setPosition's {x, y}) is passed through as-is.
        if (arg === undefined || arg === null) host[name]();
        else if (typeof arg === "object") host[name](arg);
        else host[name]({ value: arg });
    } catch (e) {
        console.error("[wgmod] invokeCommand failed: " + name, e);
    }
}

// Nearest CLICKABLE tick to a cursor x (from hotEl._wgClickMeta), gated by a small
// proximity window so a click on the bare bar between ticks doesn't fire an action.
// Imprecise hits are additionally backstopped by WG's confirm dialog (Python side).
const CLICK_HIT_PCT = 4;
function nearestClick(hotEl, clientX) {
    const meta = hotEl._wgClickMeta;
    if (!meta || !meta.length) return null;
    const rect = hotEl.getBoundingClientRect();
    const w = (rect && rect.width) || hotEl.clientWidth || 1;
    const left = rect ? rect.left : 0;
    const curPct = ((clientX - left) / w) * 100;
    let best = null, bestD = 1e9;
    for (let i = 0; i < meta.length; i++) {
        const d = Math.abs(meta[i].left - curPct);
        if (d < bestD) { bestD = d; best = meta[i]; }
    }
    return best && bestD <= CLICK_HIT_PCT ? best : null;
}

function ensureRoot() {
    let root = document.getElementById("wgmod-root");
    if (!root) {
        root = document.createElement("div");
        root.id = "wgmod-root";
        root.innerHTML =
            '<div class="wg-head">' +
            '<div class="wg-cat-icon"></div>' +
            '<div class="wg-head-left">' +
            '<div class="wg-label"></div>' +
            '<div class="wg-upgrades"></div>' +
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
function renderNextAvailable(nextEl, arr, hotEl, spendableXp, fillVehicle) {
    nextEl.innerHTML = "";
    const chips = [];
    const n = arrLen(arr);
    if (n) {
        // (No "Next available:" caption -- the chips speak for themselves and the label
        // had no localized game equivalent.)
        for (let i = 0; i < n; i++) {
            const u = unwrap(arr[i] !== undefined ? arr[i] : arr.get && arr.get(i));
            if (!u) continue;
            const xp = u.xpRequired | 0;
            // Match the Upgrades screen: minor (10k) -> square plate; major
            // (>=20k: 20k/25k) -> diamond. Frame + perk glyph layered.
            const chip = document.createElement("div");
            chip.className = "wg-chip " + (xp >= 20000 ? "wg-chip-major" : "wg-chip-minor");
            const frame = document.createElement("div");
            frame.className = "wg-chip-frame";
            const ico = document.createElement("div");
            ico.className = "wg-chip-ico";
            if (u.icon) ico.style.backgroundImage = "url('" + u.icon + "')";
            chip.appendChild(frame);
            chip.appendChild(ico);
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
            const cText = capHtml(escapeHtml(cCap)) + cName + effectHtml(u.effect);
            const cIcon = (u.icon && u.icon.indexOf("img://") === 0) ? bgIconHtml(u.icon) : "";
            const cFoot = xpFracHtml(spendableXp, xp, XP_ICON, fillVehicle);   // per-node cost (frontier nodes unlock independently)
            // Text block + icon as one unit (no divider between them); divider before cost.
            tip.innerHTML = joinSections([tipMain(cIcon, cText), cFoot]);
            chip.appendChild(tip);
            nextEl.appendChild(chip);
            chips.push({ el: chip, tip: tip, cmd: "unlockFieldMod", arg: u.actionId });
        }
        nextEl.style.display = "flex";
    } else {
        nextEl.style.display = "none";
    }
    if (hotEl) hotEl._wgChips = chips;
}

// Signature of the available-upgrade set, so render() can skip rebuilding identical
// chips (a rebuild destroys the hovered chip's tooltip element).
function upgradesSig(arr, spendableXp) {
    const n = arrLen(arr);
    // spendableXp is folded in so the chips rebuild when affordability flips; it's
    // stable between unlock actions, so this doesn't cause per-push rebuild flicker.
    let s = n + "@" + (spendableXp | 0) + ":";
    for (let i = 0; i < n; i++) {
        const u = unwrap(arr[i] !== undefined ? arr[i] : arr.get && arr.get(i));
        if (u) s += (u.actionId | 0) + "," + (u.xpRequired | 0) + ";";
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
// .wg-hot bottom (track-relative) once a row is dropped, so a lane-1 glyph hung
// ~37rem below the track + up to a 30rem-tall glyph still sits inside the hover
// overlay and can be hovered directly. Only applied when something actually stacks
// (CSS keeps the tighter default otherwise, so the drag dead-zone stays small).
const HOT_BOTTOM_STACKED_REM = -70;
// Visible glyph footprint (rem) hung below a tick, by mode/category. Half of it
// (+ a small gap) is the horizontal clearance each glyph needs to not overlap.
function glyphFootprintRem(t, mode) {
    if (mode === "elite_rewards") return 30;                       // reward thumb
    if (mode === "elite") return 36;                               // arrowhead tab badge (36rem wide)
    if (t.category === "fieldmod") return 18;                      // hex badge
    if (t.category === "vehicle") return 45;                       // framed tank contour
    return 24;                                                     // module glyph
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

// Root modifier class that mirrors WoT's color-blind mode. Appended to every root
// className assignment (all render branches) so the CSS .wg-colorblind overrides swap
// the meaning-carrying fills/pips to a color-blind-safe palette. Fail-open: absent flag
// (older Python build) -> standard palette.
function cbClass(data) {
    return data && data.colorBlind ? " wg-colorblind" : "";
}

// Apply the user's dragged bar position (px), or fall back to the CSS default and seed
// the settings fields from the live layout. posX = bar CENTER-x, posY = bar TOP (px),
// both 0 == "auto". When auto, we clear the inline left/top (so the CSS default --
// centered, 17.6vh -- applies) and, once, measure where the bar actually landed and
// report it back via setPosition, so the numeric settings fields show real coordinates
// with no visible jump. Fail-open: an older Python build without posX -> leave default.
function applyPosition(root, data) {
    if (root._wgDragging) return;   // never fight an in-progress drag
    if (!data || data.posX === undefined) return;   // feature absent -> CSS default
    const x = data.posX | 0;
    const y = data.posY | 0;
    if (x > 0 && y > 0) {
        root._wgSeedPending = false;
        root.style.left = x + "px";
        root.style.top = y + "px";
        return;
    }
    // auto / unseeded: keep the CSS default position...
    root.style.left = "";
    root.style.top = "";
    // ...and seed the settings fields once from the live layout (guarded so exactly one
    // seed is sent until Python echoes a concrete position back).
    if (root._wgSeedPending) return;
    root._wgSeedPending = true;
    const raf = window.requestAnimationFrame || function (f) { f(); };
    raf(function () {
        const r = root.getBoundingClientRect();
        if (!r || !r.width) { root._wgSeedPending = false; return; }
        const cx = Math.round(r.left + r.width / 2);
        const cy = Math.round(r.top);
        // seed:1 marks this as the DEFAULT position (measured at the CSS default spot), so
        // Python records it as the reset target -> the panel's reset repaints X/Y to the
        // real default coords, not 0/0.
        if (cx > 0 && cy > 0) invokeCommand("setPosition", { x: cx, y: cy, seed: 1 });
        else root._wgSeedPending = false;
    });
}

// Keep a shown tooltip on-screen: clamp it horizontally within the BAR's own width
// (the track's left/right edges -- the tooltip's max-width is narrower than the bar, so
// it always fits, and since the drag keeps the bar on-screen this also prevents any
// screen-edge overflow), and flip it above the bar if it would spill past the viewport
// bottom. Overrides are set inline and reset each call so a tooltip that now fits
// returns to its centered, below-the-bar default. Reused for the tick + chip tooltips.
function clampTip(tipEl) {
    // reset prior overrides -> transform reverts to the CSS translateX(-50%) centering
    tipEl.style.transform = "";
    tipEl.style.top = "";
    tipEl.style.bottom = "";
    tipEl.style.marginTop = "";
    tipEl.style.marginBottom = "";
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

function render(model) {
    const root = ensureRoot();
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

    // Show the bar ONLY in the plain garage. Python pushes visible=false while a
    // tank-setup / ammo loadout overlay is open (the params panel stays mounted to
    // show stat changes, so the bar would otherwise linger over it). An absent flag
    // (older Python build) is treated as visible -- fail open.
    if (data.visible === false) {
        root.style.display = "none";
        return;
    }
    root.style.display = "";

    // Apply the user's dragged/typed bar position (or the CSS default + seed) before any
    // mode branch, so every mode -- including the elite early-return below -- honors it.
    applyPosition(root, data);

    // Elite Levels (prestige) modes own the whole header + bar (grade/reward
    // readout, single-segment fill, combat-XP star), so they branch out early.
    if (data.mode === "elite" || data.mode === "elite_rewards") {
        renderElite(root, data, data.mode === "elite_rewards");
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
    const sMin = data.scaleMin || 0;
    const sMax = data.scaleMax || 0;
    const fv = data.fillVehicle || 0;
    const ff = data.fillFree || 0;
    const span = Math.max(sMax - sMin, 1);
    const pct = (xp) => Math.max(0, Math.min(100, ((xp - sMin) / span) * 100));

    // Right-side readout: skill-tree shows the unlocked/total node COUNT fronted by
    // the Upgrades-screen counter glyph; every other mode (incl. COMPLETE below)
    // shows spendable Total XP.
    if (mode === "skill_tree") {
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
        xp2Ico.style.backgroundImage = "url('" + XP_ICON + "')";
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
    hotEl._wgMode = mode;   // gates the tick-hover proximity (skill_tree only)
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
    const onlyFinal = mode === "skill_tree" && stTotal > 0 &&
        stDone === stTotal - 1 && arrLen(data.availUpgrades) >= 1;
    if (mode === "skill_tree" && nextEl && !onlyFinal) {
        const sig = upgradesSig(data.availUpgrades, spendableXp);
        if (nextEl._wgSig !== sig) {
            nextEl._wgSig = sig;
            setActiveChip(hotEl, null);
            renderNextAvailable(nextEl, data.availUpgrades, hotEl, spendableXp, fv);
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
    if (mode === "complete" || sMax <= sMin) {
        root.style.display = "none";
        return;
    }
    // Tier-XI skill-tree mode: a COUNT bar (axis = total upgrade nodes, fill =
    // nodes unlocked), with one evenly-spaced tick per node -- bright left of the
    // fill (unlocked), dim to the right (locked) -- and the signature 'final'
    // upgrade carrying its icon on the rightmost tick. No per-node tooltips (the
    // tick loop below skips hover wiring for this mode). wg-skill gives the fill its
    // own steel-blue tone (.wg-skill .wg-fill-veh in CSS), distinct from tech-tree.
    root.className = (mode === "skill_tree" ? "wg-skill" : "") + cbClass(data);

    label.textContent = mode === "skill_tree" ? L("headerSkillTree", "Upgrades")
        : mode === "field_mods" ? L("headerFieldMods", "Field Modifications")
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

    ticksEl.innerHTML = "";
    const ticks = data.ticks;
    const n = arrLen(ticks);
    // Skill-tree ticks carry no per-node metadata (non-linear tree) -> no hover
    // tooltips. Other modes wire each tick into the hover system.
    const noTips = mode === "skill_tree";
    // {left%, body} per tick, for the nearest-by-x hover fallback.
    const tickMeta = [];
    // {left%, cmd, arg} per CLICKABLE tick, for nearest-by-x click resolution.
    const clickMeta = [];
    // Field mods unlock linearly (one by one), so only the NEXT one -- the first
    // remaining tick -- is ever clickable. Consumed on the first fieldmod seen.
    let nextFieldMod = true;
    // Pre-pass: glyph positions + footprints, so overlapping glyphs can be
    // staggered into vertical lanes (de-crowding) before they're hung below the
    // bar. Only glyph-bearing ticks reserve space; tickless gaps are null.
    const place = [];
    for (let i = 0; i < n; i++) {
        const t = unwrap(ticks[i] !== undefined ? ticks[i] : ticks.get && ticks.get(i));
        const hasGlyph = t && (t.category === "fieldmod" || !!t.icon);
        place.push(hasGlyph ? { left: pct(t.position), half: glyphHalfPct(t, mode) } : null);
    }
    const maxLane = assignLanes(place);
    // Grow the hover overlay down to cover a dropped row's glyphs (only when something
    // stacked); CSS keeps the tighter default when nothing did.
    hotEl.style.bottom = maxLane > 0 ? HOT_BOTTOM_STACKED_REM + "rem" : "";
    for (let i = 0; i < n; i++) {
        const t = unwrap(ticks[i] !== undefined ? ticks[i] : ticks.get && ticks.get(i));
        if (!t) continue;
        const mark = document.createElement("div");
        // In the capstone-only state the final tick (the only skill_tree tick with an
        // icon) is the available node, so render it bright (wg-aff) instead of the
        // count-axis "right of fill" wg-locked dim -- matching the "Final upgrade
        // available" caption rather than reading as locked.
        let stateClass = t.locked ? " wg-locked" : t.affordable ? " wg-aff" : "";
        if (onlyFinal && mode === "skill_tree" && t.icon) stateClass = " wg-aff";
        mark.className = "wg-tick wg-cat-" + (t.category || "x") + stateClass;
        const leftPct = pct(t.position);
        mark.style.left = leftPct + "%";
        // Skill-tree count ticks carry no metadata, but the FINAL tick has a name
        // (+ cost) -> give it a hover tooltip too. Other modes: all ticks tip.
        if (!noTips || t.name) {
            const body = tooltipHtml(t, spendableXp, fv);
            // Tag the tick (and, via ancestry, its glyph) so the handler can read
            // the exact tick under the cursor when Gameface deep-targets; also keep
            // a flat list for the nearest-by-x fallback when it doesn't.
            mark._wgBody = body;
            mark._wgLeft = leftPct;
            tickMeta.push({ left: leftPct, body: body });
        }

        // Clickability -> the reverse-channel command a click fires:
        //  - skill-tree: only the final tick (the one carrying the icon) opens
        //    WG's skill-tree screen (nodes carry no per-node identity to unlock).
        //  - field-mod: LINEAR -> only the next (first remaining) tick is a
        //    candidate; if affordable, unlock it (a choice-pair level opens the
        //    screen since a click can't pick a variant).
        //  - tech-tree (vehicle/module): affordable + prereqs met -> research it.
        let cmd = null, arg;
        if (mode === "skill_tree") {
            if (t.icon) cmd = "openSkillTree";
        } else if (t.category === "fieldmod") {
            if (nextFieldMod) {
                nextFieldMod = false;   // only the next field mod is ever clickable
                // WG's research dialog handles the step (incl. choice-pair levels).
                if (t.affordable && t.actionId) { cmd = "unlockFieldMod"; arg = t.actionId; }
            }
        } else if ((t.category === "vehicle" || t.category === "module")
                   && t.affordable && !t.locked && t.actionId) {
            cmd = "researchUnlock"; arg = t.actionId;
        }
        if (cmd) {
            mark.classList.add("wg-clickable");
            clickMeta.push({ left: leftPct, cmd: cmd, arg: arg });
        }

        let glyphEl = null;
        if (t.category === "fieldmod") {
            // Field-mod ticks: a hexagon glyph with the level roman numeral
            // (mirrors the in-game field-modification level badges).
            const hex = document.createElement("div");
            hex.className = "wg-tick-hex";
            const num = document.createElement("span");
            num.textContent = romanize(t.level);
            hex.appendChild(num);
            mark.appendChild(hex);
            glyphEl = hex;
        } else if (t.icon && mode === "skill_tree") {
            // Skill-tree FINAL upgrade: a framed perk glyph (diamond -- it's a major
            // 25k node) hung below the rightmost tick, matching the Next-available
            // chips. Reuses the chip frame/glyph classes.
            const fin = document.createElement("div");
            fin.className = "wg-final wg-chip-major";
            const frame = document.createElement("div");
            frame.className = "wg-chip-frame";
            const ico = document.createElement("div");
            ico.className = "wg-chip-ico";
            ico.style.backgroundImage = "url('" + t.icon + "')";
            fin.appendChild(frame);
            fin.appendChild(ico);
            mark.appendChild(fin);
            glyphEl = fin;
        } else if (t.icon) {
            // Tech-tree ticks: the real in-game art (module-type glyph / framed
            // vehicle icon) as an img:// URL. Rendered as a background-image (not
            // <img>): Gameface honors background-size:contain for aspect-correct
            // scaling, whereas it clips an <img>. A URL that fails just renders
            // nothing (graceful).
            const img = document.createElement("div");
            img.className = "wg-tick-img";
            img.style.backgroundImage = "url('" + t.icon + "')";
            mark.appendChild(img);
            glyphEl = img;
        }
        // De-crowd: if this glyph would overlap a neighbour it was assigned a lower
        // lane in the pre-pass -- drop it a row + draw a stem back to the tick.
        applyLane(mark, glyphEl, place[i] ? place[i].lane : 0);
        ticksEl.appendChild(mark);
    }
    hotEl._wgTickMeta = tickMeta;
    hotEl._wgClickMeta = clickMeta;
}

// Tooltip body for an elite mark: the grade/reward name, (rewards) the reward
// type, and the elite level the mark sits at.
function eliteTooltipHtml(t, isRewards, combatXp) {
    const name = t.name || "";
    // Category caption at the TOP (like native tooltips put the kind line above the
    // title). Rewards: JUST the localized reward TYPE. Grade progression: the localized
    // "Elite Levels" label + the level this mark sits at.
    let caption;
    if (isRewards) {
        const opts = (t.options || "").split("\n").filter(function (s) { return s; });
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
        iconHtml = isRewards ? bgIconHtml(t.icon) : eliteTipIconHtml(t.icon, t.position | 0);
    }
    let text = caption ? capHtml(caption) : "";
    if (name) text += '<div class="wg-tip-name">' + escapeHtml(name) + "</div>";
    // Footer: progress to this milestone as "<earned> / <needed> combat XP" (the
    // tick's xpRequired is the cumulative combat XP to reach the level).
    const foot = xpFracHtml(combatXp, t.xpRequired, COMBAT_XP_ICON);
    return joinSections([tipMain(iconHtml, text), foot]);
}

// Render the ELITE (grade band) / ELITE_REWARDS (reward roadmap) views. Reuses
// the bar's track + hover overlay but with a single fill segment, a combat-XP
// readout, an "Elite Lvl N/350" counter, and grade-pip / reward-thumbnail ticks.
function renderElite(root, data, isRewards) {
    root.className = "wg-elite" + (isRewards ? " wg-elite-rewards" : "") + cbClass(data);
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
    hotEl._wgChips = [];         // no upgrade chips in elite modes
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
    ticksEl.innerHTML = "";
    const ticks = data.ticks;
    const n = arrLen(ticks);
    const tickMeta = [];
    // Pre-pass: stagger overlapping emblem/reward glyphs into vertical lanes (every
    // elite tick carries a glyph). Same de-crowding as the linear bar.
    const place = [];
    for (let i = 0; i < n; i++) {
        const t = unwrap(ticks[i] !== undefined ? ticks[i] : ticks.get && ticks.get(i));
        place.push(t ? { left: pct(t.position), half: glyphHalfPct(t, data.mode) } : null);
    }
    const maxLane = assignLanes(place);
    hotEl.style.bottom = maxLane > 0 ? HOT_BOTTOM_STACKED_REM + "rem" : "";
    for (let i = 0; i < n; i++) {
        const t = unwrap(ticks[i] !== undefined ? ticks[i] : ticks.get && ticks.get(i));
        if (!t) continue;
        const state = t.state || "upcoming";
        const mark = document.createElement("div");
        mark.className = "wg-tick wg-elite-tick wg-state-" + state;
        const leftPct = pct(t.position);
        mark.style.left = leftPct + "%";
        const body = eliteTooltipHtml(t, isRewards, data.combatXp | 0);
        mark._wgBody = body;
        mark._wgLeft = leftPct;
        tickMeta.push({ left: leftPct, body: body });

        const gradeFam = isRewards ? "" : gradeFamily(t.icon);
        if (t.icon) {
            // ELITE_REWARDS -> reward art thumbnail (a state-treated background-image
            // div; Gameface clips an <img>). ELITE -> the arrowhead "tab" grade badge,
            // the same one the category icon uses: fillTabBadge draws the mirrored
            // arrowhead + grade-tinted level numeral (the terminal MAX "prestige" tick
            // has no grade family, so it shows the numberless hexagon-arrowhead --
            // matching the in-game MAX badge). If a grade URL somehow has no tab art,
            // fall back to the hexagon emblem + emblemFont number.
            let img;
            if (isRewards) {
                img = document.createElement("div");
                img.className = "wg-tick-reward";
                img.style.backgroundImage = "url('" + t.icon + "')";
            } else {
                img = document.createElement("div");
                // Per-size class drives the centering nudge: the arrowhead arts are
                // right-anchored after the mirror by different amounts (short crammed
                // right, long ~centered), so each width needs its own margin-left to
                // sit centered under its tick.
                img.className = "wg-tick-tab wg-tab wg-tab-" + tabBadgeSize(t.icon, t.position | 0, false);
                if (!fillTabBadge(img, t.icon, t.position | 0, false)) {
                    img.className = "wg-tick-emblem" + (gradeFam ? " wg-grade-" + gradeFam : "");
                    img.style.backgroundImage = "url('" + t.icon + "')";
                    if (gradeFam) img.appendChild(emblemNumber(t.position | 0, gradeFam));
                }
            }
            mark.appendChild(img);
            applyLane(mark, img, place[i] ? place[i].lane : 0);
        } else {
            // fallback (icon URL missing): a state-colored diamond.
            const pip = document.createElement("div");
            pip.className = "wg-tick-pip";
            mark.appendChild(pip);
            applyLane(mark, pip, place[i] ? place[i].lane : 0);
        }
        ticksEl.appendChild(mark);
    }
    hotEl._wgTickMeta = tickMeta;
    hotEl._wgClickMeta = [];   // elite grade/reward marks aren't clickable
    // Don't force-hide the tooltip here (render() re-runs on model updates); the
    // hover handler owns visibility, same as the main bar.
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
    const show = (body, leftPct) => {
        tipEl.innerHTML = body;
        tipEl.style.left = leftPct + "%";
        tipEl.style.display = "block";
        clampTip(tipEl);   // keep it within the bar width / flip above near the bottom
    };
    hotEl.addEventListener("mousemove", function (e) {
        // While Ctrl is held the bar is in reposition mode -> a move cursor, no matter
        // what's under the cursor (Ctrl+drag moves the bar; see the mousedown handler).
        const dragMode = e.ctrlKey;
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
        // Pointer affordance: a pointer cursor only while over a clickable tick.
        hotEl.style.cursor = dragMode ? "move"
            : (nearestClick(hotEl, e.clientX) ? "pointer" : "");
        // (1) exact element under the cursor.
        let node = e.target;
        while (node && node !== hotEl) {
            if (node._wgBody !== undefined) { show(node._wgBody, node._wgLeft); return; }
            node = node.parentElement;
        }
        // (2) nearest tick by cursor x.
        const meta = hotEl._wgTickMeta;
        if (!meta || !meta.length) { tipEl.style.display = "none"; return; }
        const rect = hotEl.getBoundingClientRect();
        const w = (rect && rect.width) || hotEl.clientWidth || 1;
        const left = rect ? rect.left : 0;
        const curPct = ((e.clientX - left) / w) * 100;
        let best = null, bestD = 1e9;
        for (let i = 0; i < meta.length; i++) {
            const d = Math.abs(meta[i].left - curPct);
            if (d < bestD) { bestD = d; best = meta[i]; }
        }
        // In skill_tree mode the only tooltip-tick is the final upgrade (far right);
        // gate it by proximity so it doesn't show across the whole empty bar. Other
        // modes keep nearest-anywhere (dense ticks make that the right behavior).
        const ok = best && (hotEl._wgMode !== "skill_tree" || bestD <= 6);
        if (ok) show(best.body, best.left); else tipEl.style.display = "none";
    });
    hotEl.addEventListener("mouseleave", function () {
        setActiveChip(hotEl, null);
        tipEl.style.display = "none";
    });
    // Ctrl+drag to reposition the whole bar. Ctrl-gated so a normal click can't move it
    // by accident; a plain mousedown falls through to the click handler (research/unlock).
    // The bar is position:fixed with translateX(-50%), so we track the bar's CENTER-x /
    // TOP (the stored anchor). On release we report the final px to Python via
    // setPosition, which persists it (MSA) and re-pushes -- applyPosition then re-applies
    // the same coords (no jump). _wgDidDrag suppresses the click that follows the drag.
    hotEl.addEventListener("mousedown", function (e) {
        if (!e.ctrlKey) return;
        const root = document.getElementById("wgmod-root");
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
            // clamp so the bar can't be dragged off-screen (whole width kept visible)
            if (w) cx = Math.max(halfW, Math.min(w - halfW, cx));
            if (h) cy = Math.max(0, Math.min(h - 20, cy));
            root.style.left = Math.round(cx) + "px";
            root.style.top = Math.round(cy) + "px";
        };
        const onUp = function () {
            document.removeEventListener("mousemove", onMove, true);
            document.removeEventListener("mouseup", onUp, true);
            root._wgDragging = false;
            const r = root.getBoundingClientRect();
            invokeCommand("setPosition", {
                x: Math.round(r.left + r.width / 2),
                y: Math.round(r.top),
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
        const root = document.getElementById("wgmod-root");
        if (root && root._wgDidDrag) return;
        const chip = chipAt(hotEl, e.clientX, e.clientY);
        if (chip) { invokeCommand(chip.cmd, chip.arg); return; }
        const hit = nearestClick(hotEl, e.clientX);
        if (hit) invokeCommand(hit.cmd, hit.arg);
    });
}

engine.whenReady.then(() => {
    observer.onUpdate(render);
    observer.subscribe();
    render(observer.model);
});

// WGMod research-progress widget. Injected into the hangar document by OpenWG.
// Reads our data model (exposed as `wgResearch` on the host sub-view's model)
// via ModelObserver, and renders a single-axis XP bar with stacked fill + ticks.
import { ModelObserver } from "../../libs/model.js";

const observer = ModelObserver("WGModResearch");

// wulf exposes nested viewmodels / array elements wrapped as { value: ... }.
function unwrap(x) {
    return x && x.value !== undefined ? x.value : x;
}

function ensureRoot() {
    let root = document.getElementById("wgmod-root");
    if (!root) {
        root = document.createElement("div");
        root.id = "wgmod-root";
        root.innerHTML =
            '<div class="wg-label"></div>' +
            '<div class="wg-track">' +
            '<div class="wg-fill wg-fill-veh"></div>' +
            '<div class="wg-fill wg-fill-free"></div>' +
            '<div class="wg-ticks"></div>' +
            "</div>";
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

function render(model) {
    const root = ensureRoot();
    const label = root.querySelector(".wg-label");
    const data = unwrap(model && model.wgResearch);

    if (!data) {
        const keys = model ? Object.keys(model).join(",") : "no-model";
        label.textContent = "WGMOD: waiting for data | keys=" + keys;
        return;
    }

    const mode = data.mode;
    const sMin = data.scaleMin || 0;
    const sMax = data.scaleMax || 0;
    const fv = data.fillVehicle || 0;
    const ff = data.fillFree || 0;
    const span = Math.max(sMax - sMin, 1);
    const pct = (xp) => Math.max(0, Math.min(100, ((xp - sMin) / span) * 100));

    const vehEl = root.querySelector(".wg-fill-veh");
    const freeEl = root.querySelector(".wg-fill-free");
    const ticksEl = root.querySelector(".wg-ticks");

    if (mode === "complete" || sMax <= sMin) {
        label.textContent = "Fully researched";
        vehEl.style.width = "100%";
        freeEl.style.width = "0%";
        ticksEl.innerHTML = "";
        return;
    }

    label.textContent = mode === "field_mods" ? "Field Modifications" : "Research";

    const vehW = pct(sMin + fv);
    const freeW = Math.max(0, pct(sMin + fv + ff) - vehW);
    vehEl.style.left = "0%";
    vehEl.style.width = vehW + "%";
    freeEl.style.left = vehW + "%";
    freeEl.style.width = freeW + "%";

    ticksEl.innerHTML = "";
    const ticks = data.ticks;
    const n = arrLen(ticks);
    for (let i = 0; i < n; i++) {
        const t = unwrap(ticks[i] !== undefined ? ticks[i] : ticks.get && ticks.get(i));
        if (!t) continue;
        const mark = document.createElement("div");
        mark.className =
            "wg-tick wg-cat-" + (t.category || "x") +
            (t.locked ? " wg-locked" : t.affordable ? " wg-aff" : "");
        mark.style.left = pct(t.position) + "%";
        mark.title = (t.name || "") + " — " + (t.xpRequired || 0) + " XP";
        ticksEl.appendChild(mark);
    }
}

engine.whenReady.then(() => {
    observer.onUpdate(render);
    observer.subscribe();
    render(observer.model);
});

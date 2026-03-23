// Morning Briefing — Scriptable iOS Widget
// ─────────────────────────────────────────
// 1. Install Scriptable from the App Store
// 2. Copy this file to iCloud Drive/Scriptable/
// 3. Fill in API_URL and BEARER_TOKEN below
// 4. Add a Scriptable widget to your Home Screen (medium or large)

// ── Configuration ──────────────────────────────────────────────────
const API_URL = "https://morning.yourdomain.com"; // your briefing URL
const BEARER_TOKEN = "YOUR_BEARER_TOKEN_HERE";    // from install.sh output
const DASHBOARD_URL = `${API_URL}/dashboard/`;
// ───────────────────────────────────────────────────────────────────

const WIDGET_BG = new Color("#1a1a2e", 0.85);
const ACCENT     = new Color("#e94560");
const TEXT_PRIMARY   = Color.white();
const TEXT_SECONDARY = new Color("#a0a0b0");

async function fetchBriefing() {
    let loc;
    try {
        Location.setAccuracyToThreeKilometers();
        loc = await Location.current();
    } catch {
        loc = { latitude: 0, longitude: 0 };
    }

    const url = `${API_URL}/summary?lat=${loc.latitude}&lon=${loc.longitude}`;
    const req = new Request(url);
    req.headers = { Authorization: `Bearer ${BEARER_TOKEN}` };
    req.timeoutInterval = 15;

    try {
        const data = await req.loadJSON();
        data._location = loc;
        return data;
    } catch (e) {
        return null;
    }
}

function formatTime(isoString) {
    if (!isoString) return "";
    const d = new Date(isoString);
    return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function weatherSymbol(condition) {
    const map = {
        Clear: "sun.max.fill",
        Clouds: "cloud.fill",
        Rain: "cloud.rain.fill",
        Drizzle: "cloud.drizzle.fill",
        Thunderstorm: "cloud.bolt.rain.fill",
        Snow: "cloud.snow.fill",
        Mist: "cloud.fog.fill",
        Fog: "cloud.fog.fill",
        Haze: "sun.haze.fill",
    };
    return map[condition] || "cloud.fill";
}

// ── Medium Widget ──────────────────────────────────────────────────
function buildMediumWidget(data) {
    const w = new ListWidget();
    w.backgroundColor = WIDGET_BG;
    w.setPadding(8, 8, 8, 8);
    w.url = DASHBOARD_URL;

    // Date & location
    const now = new Date();
    const dateStr = now.toLocaleDateString([], {
        weekday: "long", month: "short", day: "numeric",
    });

    const header = w.addStack();
    const dateText = header.addText(dateStr);
    dateText.font = Font.semiboldSystemFont(13);
    dateText.textColor = TEXT_SECONDARY;

    if (data.weather && data.weather.location) {
        header.addSpacer();
        const locText = header.addText(data.weather.location);
        locText.font = Font.regularSystemFont(12);
        locText.textColor = TEXT_SECONDARY;
    }

    w.addSpacer(6);

    // Weather row
    const wc = data.weather ? data.weather.current : null;
    if (wc && !data.weather.error) {
        const weatherRow = w.addStack();
        weatherRow.centerAlignContent();

        const sfName = weatherSymbol(wc.condition);
        const sym = SFSymbol.named(sfName);
        if (sym) {
            const img = weatherRow.addImage(sym.image);
            img.imageSize = new Size(22, 22);
            img.tintColor = ACCENT;
            weatherRow.addSpacer(6);
        }

        const tempText = weatherRow.addText(
            `${Math.round(wc.temp || 0)}°`
        );
        tempText.font = Font.boldSystemFont(24);
        tempText.textColor = TEXT_PRIMARY;

        weatherRow.addSpacer(8);

        const condText = weatherRow.addText(
            wc.description || wc.condition || ""
        );
        condText.font = Font.regularSystemFont(14);
        condText.textColor = TEXT_SECONDARY;

        if (wc.humidity != null) {
            weatherRow.addSpacer(8);
            const precip = weatherRow.addText(
                `${wc.humidity}%`
            );
            precip.font = Font.regularSystemFont(12);
            precip.textColor = TEXT_SECONDARY;
        }
    }

    w.addSpacer(6);

    // Hourly forecast row
    if (data.weather && data.weather.hourly && data.weather.hourly.length > 0) {
        const hourlyRow = w.addStack();
        hourlyRow.spacing = 10;
        const hours = data.weather.hourly.slice(0, 6);
        for (const h of hours) {
            const col = hourlyRow.addStack();
            col.layoutVertically();
            col.centerAlignContent();

            const dt = h.dt ? new Date(h.dt * 1000) : null;
            const timeStr = dt ? dt.toLocaleTimeString([], { hour: "numeric", hour12: true }).replace(" ", "") : "";
            const tLabel = col.addText(timeStr);
            tLabel.font = Font.regularSystemFont(9);
            tLabel.textColor = TEXT_SECONDARY;

            const sfName = weatherSymbol(h.condition);
            const sym = SFSymbol.named(sfName);
            if (sym) {
                const img = col.addImage(sym.image);
                img.imageSize = new Size(14, 14);
                img.tintColor = TEXT_SECONDARY;
            }

            const tTemp = col.addText(`${Math.round(h.temp || 0)}°`);
            tTemp.font = Font.mediumSystemFont(11);
            tTemp.textColor = TEXT_PRIMARY;
        }
    }

    w.addSpacer(6);

    // Commute
    if (data.commute && data.commute.duration_text) {
        const commuteRow = w.addStack();
        commuteRow.centerAlignContent();

        const carSym = SFSymbol.named("car.fill");
        if (carSym) {
            const carImg = commuteRow.addImage(carSym.image);
            carImg.imageSize = new Size(14, 14);
            carImg.tintColor = TEXT_SECONDARY;
            commuteRow.addSpacer(4);
        }

        const commuteText = commuteRow.addText(
            `${data.commute.duration_text} — ${data.commute.distance_text || ''}`
        );
        commuteText.font = Font.regularSystemFont(12);
        commuteText.textColor = TEXT_SECONDARY;

        if (data.commute.leave_by) {
            commuteRow.addSpacer(6);
            const leaveText = commuteRow.addText(`Leave by ${data.commute.leave_by}`);
            leaveText.font = Font.mediumSystemFont(12);
            leaveText.textColor = ACCENT;
        }
    }

    w.addSpacer(4);

    // Next event
    if (data.calendar && data.calendar.length > 0) {
        const ev = data.calendar[0];
        const evRow = w.addStack();
        evRow.centerAlignContent();

        const calSym = SFSymbol.named("calendar");
        if (calSym) {
            const calImg = evRow.addImage(calSym.image);
            calImg.imageSize = new Size(14, 14);
            calImg.tintColor = ACCENT;
            evRow.addSpacer(4);
        }

        const evTime = evRow.addText(formatTime(ev.start));
        evTime.font = Font.monospacedDigitSystemFont(12, 0.3);
        evTime.textColor = ACCENT;
        evRow.addSpacer(6);
        const evName = evRow.addText(ev.subject || ev.title || "Event");
        evName.font = Font.mediumSystemFont(12);
        evName.textColor = TEXT_PRIMARY;
        evName.lineLimit = 1;
    } else {
        const noEvRow = w.addStack();
        noEvRow.centerAlignContent();
        const calSym = SFSymbol.named("calendar");
        if (calSym) {
            const calImg = noEvRow.addImage(calSym.image);
            calImg.imageSize = new Size(14, 14);
            calImg.tintColor = TEXT_SECONDARY;
            noEvRow.addSpacer(4);
        }
        const noEvText = noEvRow.addText("No events today");
        noEvText.font = Font.regularSystemFont(12);
        noEvText.textColor = TEXT_SECONDARY;
    }

    // Birthdays
    if (data.birthdays && data.birthdays.length > 0) {
        w.addSpacer(4);
        const bdayRow = w.addStack();
        bdayRow.centerAlignContent();
        const giftSym = SFSymbol.named("gift.fill");
        if (giftSym) {
            const giftImg = bdayRow.addImage(giftSym.image);
            giftImg.imageSize = new Size(14, 14);
            giftImg.tintColor = ACCENT;
            bdayRow.addSpacer(4);
        }
        const names = data.birthdays.map(b => b.name).join(", ");
        const bdayText = bdayRow.addText(names);
        bdayText.font = Font.mediumSystemFont(12);
        bdayText.textColor = TEXT_PRIMARY;
        bdayText.lineLimit = 1;
    }

    w.addSpacer();
    return w;
}

// ── Large Widget ───────────────────────────────────────────────────
function buildLargeWidget(data) {
    const w = buildMediumWidget(data);
    w.addSpacer(8);

    // Additional calendar events
    if (data.calendar && data.calendar.length > 1) {
        const divider = w.addText("─ Upcoming ─");
        divider.font = Font.regularSystemFont(11);
        divider.textColor = TEXT_SECONDARY;
        w.addSpacer(4);

        const maxEvents = Math.min(data.calendar.length, 5);
        for (let i = 1; i < maxEvents; i++) {
            const ev = data.calendar[i];
            const row = w.addStack();
            row.centerAlignContent();
            const t = row.addText(formatTime(ev.start));
            t.font = Font.monospacedDigitSystemFont(12, 0.3);
            t.textColor = ACCENT;
            row.addSpacer(6);
            const n = row.addText(ev.subject || ev.title || "Event");
            n.font = Font.regularSystemFont(12);
            n.textColor = TEXT_PRIMARY;
            n.lineLimit = 1;
            w.addSpacer(2);
        }
    }

    // Birthdays
    if (data.birthdays && data.birthdays.length > 0) {
        w.addSpacer(6);
        const bdayHeader = w.addText("🎂 Birthdays");
        bdayHeader.font = Font.mediumSystemFont(12);
        bdayHeader.textColor = TEXT_SECONDARY;
        w.addSpacer(2);

        for (const b of data.birthdays.slice(0, 3)) {
            const row = w.addStack();
            const name = row.addText(b.name || "Birthday");
            name.font = Font.regularSystemFont(12);
            name.textColor = TEXT_PRIMARY;
            w.addSpacer(2);
        }
    }

    w.addSpacer();
    return w;
}

// ── Error Widget ───────────────────────────────────────────────────
function buildErrorWidget() {
    const w = new ListWidget();
    w.backgroundColor = WIDGET_BG;
    w.setPadding(16, 16, 16, 16);
    w.url = DASHBOARD_URL;

    const title = w.addText("Morning Briefing");
    title.font = Font.boldSystemFont(16);
    title.textColor = TEXT_PRIMARY;
    w.addSpacer(8);

    const err = w.addText("Could not connect");
    err.font = Font.regularSystemFont(14);
    err.textColor = ACCENT;
    w.addSpacer(4);

    const hint = w.addText("Check API_URL and network");
    hint.font = Font.regularSystemFont(12);
    hint.textColor = TEXT_SECONDARY;

    w.addSpacer();
    return w;
}

// ── Notification ───────────────────────────────────────────────────
async function sendNotification(data) {
    const n = new Notification();
    n.title = "Morning Briefing";
    n.subtitle = "Your morning briefing is ready";

    const nc = data && data.weather ? data.weather.current : null;
    if (nc && !data.weather.error) {
        const temp = Math.round(nc.temp || 0);
        const desc = nc.description || nc.condition || "";
        n.body = `${temp}° ${desc}`;
        if (data.calendar && data.calendar.length > 0) {
            const ev = data.calendar[0];
            n.body += ` | Next: ${ev.subject || ev.title || "Event"} at ${formatTime(ev.start)}`;
        }
    } else {
        n.body = "Tap to view your dashboard";
    }

    n.openURL = DASHBOARD_URL;
    await n.schedule();
}

// ── Main ───────────────────────────────────────────────────────────
async function main() {
    const data = await fetchBriefing();

    let widget;
    if (!data) {
        widget = buildErrorWidget();
    } else if (config.widgetFamily === "large") {
        widget = buildLargeWidget(data);
    } else {
        widget = buildMediumWidget(data);
    }

    if (data) {
        await sendNotification(data);
    }

    if (config.runsInWidget) {
        Script.setWidget(widget);
    } else {
        // Preview as medium when run from app
        widget.presentMedium();
    }

    Script.complete();
}

await main();

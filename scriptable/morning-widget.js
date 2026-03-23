// Morning Briefing — Scriptable iOS Widget v2
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

// ── Theme ──────────────────────────────────────────────────────────
const BG_TOP       = new Color("#0d0d1a");
const BG_BOTTOM    = new Color("#1a1a2e");
const ACCENT       = new Color("#e94560");
const ACCENT_DIM   = new Color("#e94560", 0.6);
const TEXT_PRIMARY  = Color.white();
const TEXT_SECONDARY = new Color("#8b8ba0");
const TEXT_MUTED    = new Color("#555568");
const DIVIDER_CLR   = new Color("#ffffff", 0.06);

// ── Helpers ────────────────────────────────────────────────────────
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

function weatherSF(condition) {
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

function createWidget() {
    const w = new ListWidget();
    const gradient = new LinearGradient();
    gradient.locations = [0, 1];
    gradient.colors = [BG_TOP, BG_BOTTOM];
    w.backgroundGradient = gradient;
    w.url = DASHBOARD_URL;
    return w;
}

function addIcon(stack, name, size, color) {
    const sym = SFSymbol.named(name);
    if (sym) {
        const img = stack.addImage(sym.image);
        img.imageSize = new Size(size, size);
        img.tintColor = color;
    }
}

function addDivider(w) {
    w.addSpacer(5);
    const ctx = new DrawContext();
    ctx.size = new Size(400, 1);
    ctx.opaque = false;
    ctx.setFillColor(DIVIDER_CLR);
    ctx.fillRect(new Rect(0, 0, 400, 1));
    const divStack = w.addStack();
    const img = divStack.addImage(ctx.getImage());
    img.imageSize = new Size(400, 1);
    w.addSpacer(5);
}

// ── Section Builders ───────────────────────────────────────────────

function addHeader(w, data) {
    const now = new Date();
    const dateStr = now.toLocaleDateString([], {
        weekday: "long", month: "short", day: "numeric",
    });

    const header = w.addStack();
    header.centerAlignContent();
    const dateText = header.addText(dateStr);
    dateText.font = Font.boldSystemFont(14);
    dateText.textColor = TEXT_PRIMARY;

    if (data.weather && data.weather.location) {
        header.addSpacer();
        const locText = header.addText(data.weather.location);
        locText.font = Font.regularSystemFont(11);
        locText.textColor = TEXT_MUTED;
    }
}

function addWeather(w, data) {
    const wc = data.weather ? data.weather.current : null;
    if (!wc || data.weather.error) return;

    const row = w.addStack();
    row.centerAlignContent();

    addIcon(row, weatherSF(wc.condition), 26, ACCENT);
    row.addSpacer(8);

    const tempText = row.addText(`${Math.round(wc.temp || 0)}°`);
    tempText.font = Font.boldSystemFont(30);
    tempText.textColor = TEXT_PRIMARY;

    row.addSpacer(10);

    const detailCol = row.addStack();
    detailCol.layoutVertically();

    const condText = detailCol.addText(wc.description || wc.condition || "");
    condText.font = Font.mediumSystemFont(14);
    condText.textColor = TEXT_SECONDARY;

    const statsRow = detailCol.addStack();
    statsRow.spacing = 8;
    if (wc.humidity != null) {
        const hum = statsRow.addText(`${wc.humidity}%`);
        hum.font = Font.regularSystemFont(11);
        hum.textColor = TEXT_MUTED;
    }
    if (wc.feels_like != null) {
        const fl = statsRow.addText(`Feels ${Math.round(wc.feels_like)}°`);
        fl.font = Font.regularSystemFont(11);
        fl.textColor = TEXT_MUTED;
    }
}

function addHourly(w, data) {
    if (!data.weather || !data.weather.hourly || data.weather.hourly.length === 0) return;

    const hourlyRow = w.addStack();
    hourlyRow.spacing = 0;
    const hours = data.weather.hourly.slice(0, 6);

    for (const h of hours) {
        const col = hourlyRow.addStack();
        col.layoutVertically();
        col.centerAlignContent();
        col.size = new Size(0, 0);

        if (hours.indexOf(h) > 0) hourlyRow.addSpacer();

        const dt = h.dt ? new Date(h.dt * 1000) : null;
        const timeStr = dt
            ? dt.toLocaleTimeString([], { hour: "numeric", hour12: true }).replace(" ", "").toLowerCase()
            : "";
        const tLabel = col.addText(timeStr);
        tLabel.font = Font.regularSystemFont(9);
        tLabel.textColor = TEXT_MUTED;
        col.addSpacer(2);

        addIcon(col, weatherSF(h.condition), 13, TEXT_SECONDARY);
        col.addSpacer(2);

        const tTemp = col.addText(`${Math.round(h.temp || 0)}°`);
        tTemp.font = Font.mediumSystemFont(11);
        tTemp.textColor = TEXT_PRIMARY;
    }
}

function addCommuteRow(w, data) {
    if (!data.commute || !data.commute.duration_text) return;

    const row = w.addStack();
    row.centerAlignContent();

    addIcon(row, "car.fill", 12, TEXT_SECONDARY);
    row.addSpacer(5);

    const dur = row.addText(data.commute.duration_text);
    dur.font = Font.mediumSystemFont(12);
    dur.textColor = TEXT_PRIMARY;

    if (data.commute.distance_text) {
        row.addSpacer(6);
        const dist = row.addText(data.commute.distance_text);
        dist.font = Font.regularSystemFont(11);
        dist.textColor = TEXT_MUTED;
    }

    if (data.commute.leave_by) {
        row.addSpacer();
        const leave = row.addText(`Leave ${data.commute.leave_by}`);
        leave.font = Font.mediumSystemFont(11);
        leave.textColor = ACCENT;
    }
}

function addCalendarEvents(w, data, startIdx, maxCount) {
    if (!data.calendar || data.calendar.length <= startIdx) {
        if (startIdx === 0) {
            const row = w.addStack();
            row.centerAlignContent();
            addIcon(row, "calendar", 12, TEXT_MUTED);
            row.addSpacer(5);
            const t = row.addText("No events today");
            t.font = Font.regularSystemFont(12);
            t.textColor = TEXT_MUTED;
        }
        return;
    }

    const end = Math.min(data.calendar.length, startIdx + maxCount);
    for (let i = startIdx; i < end; i++) {
        const ev = data.calendar[i];
        const row = w.addStack();
        row.centerAlignContent();

        addIcon(row, "calendar", 12, i === 0 ? ACCENT : ACCENT_DIM);
        row.addSpacer(5);

        const evTime = row.addText(formatTime(ev.start));
        evTime.font = Font.mediumMonospacedSystemFont(12);
        evTime.textColor = ACCENT;
        row.addSpacer(6);

        const evName = row.addText(ev.subject || ev.title || "Event");
        evName.font = Font.mediumSystemFont(12);
        evName.textColor = TEXT_PRIMARY;
        evName.lineLimit = 1;

        if (i < end - 1) w.addSpacer(2);
    }
}

function addBirthdays(w, data) {
    if (!data.birthdays || data.birthdays.length === 0) return;

    const row = w.addStack();
    row.centerAlignContent();
    addIcon(row, "gift.fill", 12, ACCENT);
    row.addSpacer(5);
    const names = data.birthdays.map(b => b.name).join(", ");
    const t = row.addText(names);
    t.font = Font.mediumSystemFont(12);
    t.textColor = TEXT_PRIMARY;
    t.lineLimit = 1;
}

function addNewsHeadlines(w, data, max) {
    if (!data.news) return;
    const headlines = data.news.headlines || data.news.Headlines || [];
    if (headlines.length === 0) return;

    const hdr = w.addStack();
    hdr.centerAlignContent();
    addIcon(hdr, "newspaper.fill", 11, TEXT_SECONDARY);
    hdr.addSpacer(5);
    const label = hdr.addText("Headlines");
    label.font = Font.semiboldSystemFont(11);
    label.textColor = TEXT_SECONDARY;
    w.addSpacer(3);

    const count = Math.min(headlines.length, max);
    for (let i = 0; i < count; i++) {
        const article = headlines[i];
        const row = w.addStack();
        row.centerAlignContent();
        row.addSpacer(17);
        const title = row.addText(article.title || "");
        title.font = Font.regularSystemFont(11);
        title.textColor = TEXT_PRIMARY;
        title.lineLimit = 1;
        if (i < count - 1) w.addSpacer(2);
    }
}

function addReminders(w, data, max) {
    if (!data.reminders || data.reminders.length === 0) return;

    const hdr = w.addStack();
    hdr.centerAlignContent();
    addIcon(hdr, "checklist", 11, TEXT_SECONDARY);
    hdr.addSpacer(5);
    const label = hdr.addText("Reminders");
    label.font = Font.semiboldSystemFont(11);
    label.textColor = TEXT_SECONDARY;
    w.addSpacer(3);

    const count = Math.min(data.reminders.length, max);
    for (let i = 0; i < count; i++) {
        const r = data.reminders[i];
        const row = w.addStack();
        row.centerAlignContent();
        row.addSpacer(17);
        const t = row.addText(r.title || "Reminder");
        t.font = Font.regularSystemFont(11);
        t.textColor = TEXT_PRIMARY;
        t.lineLimit = 1;
        if (i < count - 1) w.addSpacer(2);
    }
}

function addFlaggedEmails(w, data, max) {
    if (!data.flagged_emails || data.flagged_emails.length === 0) return;

    const hdr = w.addStack();
    hdr.centerAlignContent();
    addIcon(hdr, "flag.fill", 11, ACCENT);
    hdr.addSpacer(5);
    const label = hdr.addText("Flagged Emails");
    label.font = Font.semiboldSystemFont(11);
    label.textColor = TEXT_SECONDARY;
    w.addSpacer(3);

    const count = Math.min(data.flagged_emails.length, max);
    for (let i = 0; i < count; i++) {
        const e = data.flagged_emails[i];
        const row = w.addStack();
        row.centerAlignContent();
        row.addSpacer(17);
        const subj = row.addText(e.subject || "Email");
        subj.font = Font.regularSystemFont(11);
        subj.textColor = TEXT_PRIMARY;
        subj.lineLimit = 1;
        if (i < count - 1) w.addSpacer(2);
    }
}

// ── Medium Widget ──────────────────────────────────────────────────
function buildMediumWidget(data) {
    const w = createWidget();
    w.setPadding(10, 12, 10, 12);

    addHeader(w, data);
    w.addSpacer(6);
    addWeather(w, data);
    w.addSpacer(5);
    addHourly(w, data);
    w.addSpacer(5);
    addCommuteRow(w, data);
    w.addSpacer(3);
    addCalendarEvents(w, data, 0, 1);

    if (data.birthdays && data.birthdays.length > 0) {
        w.addSpacer(3);
        addBirthdays(w, data);
    }

    w.addSpacer();
    return w;
}

// ── Large Widget ───────────────────────────────────────────────────
function buildLargeWidget(data) {
    const w = createWidget();
    w.setPadding(12, 14, 12, 14);

    // ─ Top: Header + Weather ─
    addHeader(w, data);
    w.addSpacer(6);
    addWeather(w, data);
    w.addSpacer(5);
    addHourly(w, data);

    addDivider(w);

    // ─ Middle: Commute + Schedule ─
    addCommuteRow(w, data);
    w.addSpacer(4);
    addCalendarEvents(w, data, 0, 4);

    if (data.birthdays && data.birthdays.length > 0) {
        w.addSpacer(4);
        addBirthdays(w, data);
    }

    addDivider(w);

    // ─ Bottom: News + Reminders + Flagged ─
    // Show whichever sections have data, fill the remaining space
    const hasNews = data.news && ((data.news.headlines || []).length > 0 || (data.news.Headlines || []).length > 0);
    const hasReminders = data.reminders && data.reminders.length > 0;
    const hasFlagged = data.flagged_emails && data.flagged_emails.length > 0;

    if (hasNews) {
        addNewsHeadlines(w, data, 3);
    }

    if (hasReminders) {
        if (hasNews) w.addSpacer(5);
        addReminders(w, data, 3);
    }

    if (hasFlagged) {
        if (hasNews || hasReminders) w.addSpacer(5);
        addFlaggedEmails(w, data, 2);
    }

    if (!hasNews && !hasReminders && !hasFlagged) {
        const row = w.addStack();
        row.centerAlignContent();
        addIcon(row, "checkmark.circle", 12, TEXT_MUTED);
        row.addSpacer(5);
        const t = row.addText("All clear");
        t.font = Font.regularSystemFont(12);
        t.textColor = TEXT_MUTED;
    }

    w.addSpacer();
    return w;
}

// ── Error Widget ───────────────────────────────────────────────────
function buildErrorWidget() {
    const w = createWidget();
    w.setPadding(16, 16, 16, 16);

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
        widget.presentLarge();
    }

    Script.complete();
}

await main();

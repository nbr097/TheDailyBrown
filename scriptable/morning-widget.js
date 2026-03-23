// Morning Briefing — Scriptable iOS Widget v3
// Inspired by Weather-Cal & Marco79 card-based layouts
// ─────────────────────────────────────────
// 1. Install Scriptable from the App Store
// 2. Copy this file to iCloud Drive/Scriptable/
// 3. Fill in API_URL and BEARER_TOKEN below
// 4. Add a Scriptable widget to your Home Screen (medium or large)

// ── Configuration ──────────────────────────────────────────────────
const API_URL = "https://morning.yourdomain.com";
const BEARER_TOKEN = "YOUR_BEARER_TOKEN_HERE";
const DASHBOARD_URL = `${API_URL}/dashboard/`;
// ───────────────────────────────────────────────────────────────────

// ── Theme ──────────────────────────────────────────────────────────
const CARD_BG     = new Color("#ffffff", 0.07);
const CARD_BG_ALT = new Color("#ffffff", 0.04);
const ACCENT       = new Color("#e94560");
const ACCENT_SOFT  = new Color("#e94560", 0.7);
const TEAL         = new Color("#4ecdc4");
const WHITE        = Color.white();
const TEXT_DIM     = new Color("#9999ad");
const TEXT_MUTED   = new Color("#666680");
const CARD_RADIUS  = 14;

// ── Data Fetching ──────────────────────────────────────────────────
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
    } catch { return null; }
}

// ── Utilities ──────────────────────────────────────────────────────
function fmtTime(iso) {
    if (!iso) return "";
    return new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function sfImg(name, size, color, stack) {
    const sym = SFSymbol.named(name);
    if (!sym) return;
    const img = stack.addImage(sym.image);
    img.imageSize = new Size(size, size);
    img.tintColor = color;
}

function weatherSF(cond) {
    return {
        Clear: "sun.max.fill", Clouds: "cloud.fill", Rain: "cloud.rain.fill",
        Drizzle: "cloud.drizzle.fill", Thunderstorm: "cloud.bolt.rain.fill",
        Snow: "cloud.snow.fill", Mist: "cloud.fog.fill", Fog: "cloud.fog.fill",
        Haze: "sun.haze.fill",
    }[cond] || "cloud.fill";
}

// ── Card Factory ───────────────────────────────────────────────────
function makeCard(parent, opts = {}) {
    const card = parent.addStack();
    card.layoutVertically();
    card.backgroundColor = opts.bg || CARD_BG;
    card.cornerRadius = opts.radius || CARD_RADIUS;
    card.setPadding(
        opts.pt || 10, opts.pl || 12,
        opts.pb || 10, opts.pr || 12
    );
    if (opts.url) card.url = opts.url;
    return card;
}

// ── Section: Date Card (left side of top row) ──────────────────────
function buildDateCard(parent) {
    const card = makeCard(parent, { pt: 10, pb: 10, pl: 14, pr: 14 });

    const now = new Date();
    const dayNum = now.getDate().toString();
    const dayName = now.toLocaleDateString([], { weekday: "short" }).toUpperCase();
    const monthName = now.toLocaleDateString([], { month: "short" }).toUpperCase();

    const dayLabel = card.addText(dayName);
    dayLabel.font = Font.boldSystemFont(11);
    dayLabel.textColor = ACCENT;

    card.addSpacer(2);

    const numLabel = card.addText(dayNum);
    numLabel.font = Font.boldSystemFont(32);
    numLabel.textColor = WHITE;
    numLabel.minimumScaleFactor = 0.8;

    card.addSpacer(1);

    const monthLabel = card.addText(monthName);
    monthLabel.font = Font.semiboldSystemFont(11);
    monthLabel.textColor = TEXT_DIM;

    return card;
}

// ── Section: Weather Card (right side of top row) ──────────────────
function buildWeatherCard(parent, data) {
    const card = makeCard(parent, { pt: 10, pb: 10 });
    const wc = data.weather ? data.weather.current : null;

    if (!wc || data.weather.error) {
        const t = card.addText("No weather data");
        t.font = Font.regularSystemFont(12);
        t.textColor = TEXT_MUTED;
        return card;
    }

    // Top: icon + temp + description + spacer to stretch
    const topRow = card.addStack();
    topRow.centerAlignContent();

    sfImg(weatherSF(wc.condition), 22, ACCENT, topRow);
    topRow.addSpacer(8);

    const temp = topRow.addText(`${Math.round(wc.temp || 0)}°`);
    temp.font = Font.boldSystemFont(26);
    temp.textColor = WHITE;

    topRow.addSpacer(8);

    const descCol = topRow.addStack();
    descCol.layoutVertically();
    const desc = descCol.addText(wc.description || wc.condition || "");
    desc.font = Font.mediumSystemFont(12);
    desc.textColor = TEXT_DIM;
    desc.lineLimit = 1;

    if (wc.feels_like != null) {
        const fl = descCol.addText(`Feels ${Math.round(wc.feels_like)}°`);
        fl.font = Font.regularSystemFont(10);
        fl.textColor = TEXT_MUTED;
    }

    topRow.addSpacer(); // stretch to fill width

    card.addSpacer(4);

    // Bottom: stats row
    const statsRow = card.addStack();
    statsRow.centerAlignContent();
    statsRow.spacing = 12;

    if (wc.humidity != null) {
        const humStack = statsRow.addStack();
        humStack.centerAlignContent();
        sfImg("drop.fill", 10, TEAL, humStack);
        humStack.addSpacer(3);
        const h = humStack.addText(`${wc.humidity}%`);
        h.font = Font.regularSystemFont(10);
        h.textColor = TEXT_DIM;
    }

    if (wc.wind_speed != null) {
        const windStack = statsRow.addStack();
        windStack.centerAlignContent();
        sfImg("wind", 10, TEXT_DIM, windStack);
        windStack.addSpacer(3);
        const w = windStack.addText(`${Math.round((wc.wind_speed || 0) * 3.6)} km/h`);
        w.font = Font.regularSystemFont(10);
        w.textColor = TEXT_DIM;
    }

    statsRow.addSpacer(); // stretch to fill width

    if (data.weather.location) {
        const loc = statsRow.addText(data.weather.location);
        loc.font = Font.regularSystemFont(10);
        loc.textColor = TEXT_MUTED;
        loc.lineLimit = 1;
    }

    return card;
}

// ── Section: Hourly Forecast Card ──────────────────────────────────
function buildHourlyCard(parent, data) {
    if (!data.weather || !data.weather.hourly || data.weather.hourly.length === 0) return null;

    const card = makeCard(parent, { pt: 8, pb: 8, pl: 10, pr: 10, bg: CARD_BG_ALT });
    const row = card.addStack();
    row.centerAlignContent();

    const hours = data.weather.hourly.slice(0, 6);
    for (let i = 0; i < hours.length; i++) {
        const h = hours[i];
        if (i > 0) row.addSpacer();

        const col = row.addStack();
        col.layoutVertically();
        col.centerAlignContent();

        const dt = h.dt ? new Date(h.dt * 1000) : null;
        const timeStr = dt
            ? dt.toLocaleTimeString([], { hour: "numeric", hour12: true }).replace(" ", "").toLowerCase()
            : "";
        const tLabel = col.addText(timeStr);
        tLabel.font = Font.regularSystemFont(9);
        tLabel.textColor = TEXT_MUTED;
        tLabel.centerAlignText();

        col.addSpacer(3);
        sfImg(weatherSF(h.condition), 14, TEXT_DIM, col);
        col.addSpacer(3);

        const tTemp = col.addText(`${Math.round(h.temp || 0)}°`);
        tTemp.font = Font.semiboldSystemFont(12);
        tTemp.textColor = WHITE;
        tTemp.centerAlignText();
    }

    return card;
}

// ── Section: Commute Card ──────────────────────────────────────────
function buildCommuteCard(parent, data) {
    if (!data.commute || !data.commute.duration_text) return null;

    const card = makeCard(parent, { pt: 8, pb: 8, bg: CARD_BG_ALT });
    const row = card.addStack();
    row.centerAlignContent();

    sfImg("car.fill", 13, TEAL, row);
    row.addSpacer(6);

    const dur = row.addText(data.commute.duration_text);
    dur.font = Font.semiboldSystemFont(13);
    dur.textColor = WHITE;

    if (data.commute.distance_text) {
        row.addSpacer(6);
        const dist = row.addText(data.commute.distance_text);
        dist.font = Font.regularSystemFont(11);
        dist.textColor = TEXT_MUTED;
    }

    row.addSpacer(); // always stretch to full width

    if (data.commute.leave_by) {
        const leave = row.addText(`Leave ${data.commute.leave_by}`);
        leave.font = Font.semiboldSystemFont(11);
        leave.textColor = ACCENT;
    }

    return card;
}

// ── Section: Calendar Card ─────────────────────────────────────────
function buildCalendarCard(parent, data, maxEvents) {
    const card = makeCard(parent, { pt: 8, pb: 8 });

    // Header — trailing spacer stretches card to full width
    const hdr = card.addStack();
    hdr.centerAlignContent();
    sfImg("calendar", 11, ACCENT, hdr);
    hdr.addSpacer(5);
    const label = hdr.addText("Schedule");
    label.font = Font.semiboldSystemFont(11);
    label.textColor = TEXT_DIM;
    hdr.addSpacer();
    card.addSpacer(5);

    if (!data.calendar || data.calendar.length === 0) {
        const t = card.addText("No events today");
        t.font = Font.regularSystemFont(12);
        t.textColor = TEXT_MUTED;
        return card;
    }

    const count = Math.min(data.calendar.length, maxEvents);
    for (let i = 0; i < count; i++) {
        const ev = data.calendar[i];
        const evRow = card.addStack();
        evRow.centerAlignContent();

        const time = evRow.addText(fmtTime(ev.start));
        time.font = Font.mediumMonospacedSystemFont(11);
        time.textColor = ACCENT_SOFT;
        time.minimumScaleFactor = 0.8;

        evRow.addSpacer(8);

        const name = evRow.addText(ev.subject || ev.title || "Event");
        name.font = Font.mediumSystemFont(12);
        name.textColor = WHITE;
        name.lineLimit = 1;

        evRow.addSpacer(); // stretch row

        if (ev.location) {
            const loc = evRow.addText(ev.location.split(",")[0]);
            loc.font = Font.regularSystemFont(9);
            loc.textColor = TEXT_MUTED;
            loc.lineLimit = 1;
        }

        if (i < count - 1) card.addSpacer(3);
    }

    // Birthdays inline
    if (data.birthdays && data.birthdays.length > 0) {
        card.addSpacer(5);
        const bdayRow = card.addStack();
        bdayRow.centerAlignContent();
        sfImg("gift.fill", 11, ACCENT, bdayRow);
        bdayRow.addSpacer(5);
        const names = data.birthdays.map(b => b.name).join(", ");
        const t = bdayRow.addText(names);
        t.font = Font.mediumSystemFont(11);
        t.textColor = WHITE;
        t.lineLimit = 1;
    }

    return card;
}

// ── Section: News Card ─────────────────────────────────────────────
function buildNewsCard(parent, data, maxItems) {
    if (!data.news) return null;
    const headlines = data.news.headlines || data.news.Headlines || [];
    if (headlines.length === 0) return null;

    const card = makeCard(parent, { pt: 8, pb: 8 });

    const hdr = card.addStack();
    hdr.centerAlignContent();
    sfImg("newspaper.fill", 11, TEXT_DIM, hdr);
    hdr.addSpacer(5);
    const label = hdr.addText("Headlines");
    label.font = Font.semiboldSystemFont(11);
    label.textColor = TEXT_DIM;
    hdr.addSpacer(); // stretch card to full width
    card.addSpacer(4);

    const count = Math.min(headlines.length, maxItems);
    for (let i = 0; i < count; i++) {
        const row = card.addStack();
        row.topAlignContent();
        sfImg("circle.fill", 5, ACCENT_SOFT, row);
        row.addSpacer(6);
        const t = row.addText(headlines[i].title || "");
        t.font = Font.regularSystemFont(11);
        t.textColor = new Color("#ccccdd");
        t.lineLimit = 2;
        if (i < count - 1) card.addSpacer(3);
    }

    return card;
}

// ── Section: Reminders Card ────────────────────────────────────────
function buildRemindersCard(parent, data, maxItems) {
    if (!data.reminders || data.reminders.length === 0) return null;

    const card = makeCard(parent, { pt: 8, pb: 8 });

    const hdr = card.addStack();
    hdr.centerAlignContent();
    sfImg("checklist", 11, TEAL, hdr);
    hdr.addSpacer(5);
    const label = hdr.addText("Reminders");
    label.font = Font.semiboldSystemFont(11);
    label.textColor = TEXT_DIM;
    hdr.addSpacer();
    card.addSpacer(4);

    const count = Math.min(data.reminders.length, maxItems);
    for (let i = 0; i < count; i++) {
        const r = data.reminders[i];
        const row = card.addStack();
        row.centerAlignContent();
        sfImg("circle", 8, TEXT_MUTED, row);
        row.addSpacer(5);
        const t = row.addText(r.title || "Reminder");
        t.font = Font.regularSystemFont(11);
        t.textColor = new Color("#ccccdd");
        t.lineLimit = 1;
        if (i < count - 1) card.addSpacer(2);
    }

    return card;
}

// ── Section: Flagged Emails Card ───────────────────────────────────
function buildFlaggedCard(parent, data, maxItems) {
    if (!data.flagged_emails || data.flagged_emails.length === 0) return null;

    const card = makeCard(parent, { pt: 8, pb: 8 });

    const hdr = card.addStack();
    hdr.centerAlignContent();
    sfImg("flag.fill", 11, ACCENT, hdr);
    hdr.addSpacer(5);
    const label = hdr.addText("Flagged");
    label.font = Font.semiboldSystemFont(11);
    label.textColor = TEXT_DIM;
    hdr.addSpacer();
    card.addSpacer(4);

    const count = Math.min(data.flagged_emails.length, maxItems);
    for (let i = 0; i < count; i++) {
        const e = data.flagged_emails[i];
        const t = card.addText(e.subject || "Email");
        t.font = Font.regularSystemFont(11);
        t.textColor = new Color("#ccccdd");
        t.lineLimit = 1;
        if (i < count - 1) card.addSpacer(2);
    }

    return card;
}

// ── Medium Widget ──────────────────────────────────────────────────
function buildMediumWidget(data) {
    const w = new ListWidget();
    const grad = new LinearGradient();
    grad.locations = [0, 1];
    grad.colors = [new Color("#0d0d1a"), new Color("#171728")];
    w.backgroundGradient = grad;
    w.setPadding(10, 10, 10, 10);
    w.url = DASHBOARD_URL;
    w.spacing = 6;

    // Row 1: Date card + Weather card
    const topRow = w.addStack();
    topRow.spacing = 6;

    const dateCard = buildDateCard(topRow);
    dateCard.size = new Size(70, 0);

    buildWeatherCard(topRow, data);

    // Row 2: Hourly
    buildHourlyCard(w, data);

    // Row 3: Commute or Event (pick most useful)
    if (data.commute && data.commute.duration_text) {
        buildCommuteCard(w, data);
    }

    // Event inline
    if (data.calendar && data.calendar.length > 0) {
        const evCard = makeCard(w, { pt: 6, pb: 6, bg: CARD_BG_ALT });
        const ev = data.calendar[0];
        const evRow = evCard.addStack();
        evRow.centerAlignContent();
        sfImg("calendar", 11, ACCENT, evRow);
        evRow.addSpacer(5);
        const time = evRow.addText(fmtTime(ev.start));
        time.font = Font.mediumMonospacedSystemFont(11);
        time.textColor = ACCENT_SOFT;
        evRow.addSpacer(6);
        const name = evRow.addText(ev.subject || ev.title || "Event");
        name.font = Font.mediumSystemFont(12);
        name.textColor = WHITE;
        name.lineLimit = 1;
    }

    return w;
}

// ── Large Widget ───────────────────────────────────────────────────
function buildLargeWidget(data) {
    const w = new ListWidget();
    const grad = new LinearGradient();
    grad.locations = [0, 1];
    grad.colors = [new Color("#0d0d1a"), new Color("#171728")];
    w.backgroundGradient = grad;
    w.setPadding(12, 12, 12, 12);
    w.url = DASHBOARD_URL;
    w.spacing = 6;

    // ── Row 1: Date + Weather ──
    const topRow = w.addStack();
    topRow.spacing = 6;

    const dateCard = buildDateCard(topRow);
    dateCard.size = new Size(74, 0);

    buildWeatherCard(topRow, data);

    // ── Row 2: Hourly Forecast ──
    buildHourlyCard(w, data);

    // ── Row 3: Commute ──
    buildCommuteCard(w, data);

    // ── Row 4: Calendar ──
    buildCalendarCard(w, data, 4);

    // ── Row 5: News (full width, more items) ──
    const hasNews = data.news && ((data.news.headlines || data.news.Headlines || []).length > 0);
    const hasReminders = data.reminders && data.reminders.length > 0;
    const hasFlagged = data.flagged_emails && data.flagged_emails.length > 0;

    if (hasNews) {
        buildNewsCard(w, data, 5);
    }

    // ── Row 6: Reminders + Flagged side by side ──
    if (hasReminders || hasFlagged) {
        const bottomRow = w.addStack();
        bottomRow.spacing = 6;

        if (hasReminders) {
            buildRemindersCard(bottomRow, data, 3);
        }
        if (hasFlagged) {
            buildFlaggedCard(bottomRow, data, 3);
        }
    }

    w.addSpacer();
    return w;
}

// ── Error Widget ───────────────────────────────────────────────────
function buildErrorWidget() {
    const w = new ListWidget();
    const grad = new LinearGradient();
    grad.locations = [0, 1];
    grad.colors = [new Color("#0d0d1a"), new Color("#171728")];
    w.backgroundGradient = grad;
    w.setPadding(16, 16, 16, 16);
    w.url = DASHBOARD_URL;

    const card = makeCard(w, { pt: 20, pb: 20 });

    const title = card.addText("Morning Briefing");
    title.font = Font.boldSystemFont(16);
    title.textColor = WHITE;
    card.addSpacer(8);
    const err = card.addText("Could not connect");
    err.font = Font.regularSystemFont(14);
    err.textColor = ACCENT;
    card.addSpacer(4);
    const hint = card.addText("Check API_URL and network");
    hint.font = Font.regularSystemFont(12);
    hint.textColor = TEXT_DIM;

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
            n.body += ` | Next: ${ev.subject || ev.title || "Event"} at ${fmtTime(ev.start)}`;
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

    if (data) await sendNotification(data);

    if (config.runsInWidget) {
        Script.setWidget(widget);
    } else {
        widget.presentLarge();
    }
    Script.complete();
}

await main();

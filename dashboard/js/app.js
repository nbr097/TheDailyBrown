/* ============================================================
   app.js — Dashboard data loading & rendering
   ============================================================ */

const CONFIG = {
    API_URL: '',           // Leave empty for same-origin
    BEARER_TOKEN: '',      // Fill in your bearer token
};

// ---------- Weather icon mapping ----------

const WEATHER_ICONS = {
    Clear:        'ph-sun',
    Sunny:        'ph-sun',
    Clouds:       'ph-cloud',
    Cloudy:       'ph-cloud',
    Overcast:     'ph-cloud',
    Rain:         'ph-cloud-rain',
    Drizzle:      'ph-cloud-rain',
    Thunderstorm: 'ph-lightning',
    Snow:         'ph-snowflake',
    Mist:         'ph-cloud-fog',
    Fog:          'ph-cloud-fog',
    Haze:         'ph-cloud-fog',
    Wind:         'ph-wind',
};

function weatherIcon(condition) {
    if (!condition) return 'ph-cloud';
    for (const [key, icon] of Object.entries(WEATHER_ICONS)) {
        if (condition.toLowerCase().includes(key.toLowerCase())) return icon;
    }
    return 'ph-cloud';
}

// ---------- Greeting ----------

function setGreeting() {
    const hour = new Date().getHours();
    const el = document.getElementById('greeting-text');
    const icon = document.getElementById('greeting-icon');

    if (hour < 12) {
        el.textContent = 'Good Morning, Nic';
        icon.className = 'ph ph-sun-horizon text-3xl text-amber-400';
    } else if (hour < 17) {
        el.textContent = 'Good Afternoon, Nic';
        icon.className = 'ph ph-sun text-3xl text-yellow-400';
    } else {
        el.textContent = 'Good Evening, Nic';
        icon.className = 'ph ph-moon-stars text-3xl text-indigo-300';
    }

    const now = new Date();
    document.getElementById('header-date').textContent = now.toLocaleDateString('en-US', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
    });
}

// ---------- Location ----------

async function reverseGeocode(lat, lon) {
    try {
        const res = await fetch(
            `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json&zoom=10`,
            { headers: { 'Accept-Language': 'en' } }
        );
        const data = await res.json();
        const addr = data.address || {};
        const city = addr.city || addr.town || addr.village || addr.county || '';
        const state = addr.state || '';
        return [city, state].filter(Boolean).join(', ');
    } catch {
        return `${lat.toFixed(2)}, ${lon.toFixed(2)}`;
    }
}

// ---------- Main loader ----------

async function loadDashboard() {
    setGreeting();
    hideError();

    try {
        const { lat, lon } = await getPosition();
        const locationName = await reverseGeocode(lat, lon);
        document.getElementById('header-location').textContent = locationName;

        const headers = {};
        if (CONFIG.BEARER_TOKEN) {
            headers['Authorization'] = `Bearer ${CONFIG.BEARER_TOKEN}`;
        } else if (authToken) {
            headers['Authorization'] = `Bearer ${authToken}`;
        }

        const res = await fetch(`${CONFIG.API_URL}/summary?lat=${lat}&lon=${lon}`, { headers });
        if (!res.ok) throw new Error(`API returned ${res.status}`);
        const data = await res.json();

        renderWeather(data.weather);
        renderCommute(data.commute);
        renderCalendar(data.calendar);
        renderBirthdays(data.birthdays);
        renderNews(data.news);
        renderReminders(data.reminders);
        renderFlaggedEmails(data.flagged_emails);

        // Also load admin health
        loadHealth();
    } catch (err) {
        console.error('Dashboard load error:', err);
        showError();
    }
}

function getPosition() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error('Geolocation not supported'));
            return;
        }
        navigator.geolocation.getCurrentPosition(
            pos => resolve({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
            err => reject(err),
            { enableHighAccuracy: true, timeout: 10000 }
        );
    });
}

// ---------- Error state ----------

function showError() {
    document.getElementById('error-state').classList.remove('hidden');
    // Hide data cards
    ['weather-card', 'commute-card', 'calendar-card', 'birthdays-card',
     'news-section', 'reminders-emails-card', 'admin-section'].forEach(id => {
        document.getElementById(id).classList.add('hidden');
    });
}

function hideError() {
    document.getElementById('error-state').classList.add('hidden');
    ['weather-card', 'commute-card', 'calendar-card',
     'news-section', 'reminders-emails-card', 'admin-section'].forEach(id => {
        document.getElementById(id).classList.remove('hidden');
    });
}

// ---------- Render: Weather ----------

function renderWeather(w) {
    if (!w) return;
    const cur = document.getElementById('weather-current');
    // API returns { current: { temp, feels_like, condition, ... }, hourly: [...] }
    const current = w.current || {};
    const iconClass = weatherIcon(current.condition);

    cur.innerHTML = `
        <div class="flex items-center gap-3">
            <i class="ph ${iconClass} text-4xl text-amber-300"></i>
            <div>
                <span class="text-3xl font-bold">${Math.round(current.temp || 0)}&deg;</span>
                <p class="text-xs text-slate-400">${current.description || current.condition || ''}</p>
            </div>
        </div>
        <div class="text-right text-sm text-slate-400">
            <p>Feels ${Math.round(current.feels_like || 0)}&deg;</p>
        </div>
    `;

    const details = document.getElementById('weather-details');
    const windKmh = Math.round((current.wind_speed || 0) * 3.6);
    details.innerHTML = `
        <span class="flex items-center gap-1"><i class="ph ph-drop"></i> ${current.humidity || 0}%</span>
        <span class="flex items-center gap-1"><i class="ph ph-wind"></i> ${windKmh} km/h</span>
    `;

    const hourly = document.getElementById('weather-hourly');
    if (w.hourly && w.hourly.length) {
        hourly.innerHTML = w.hourly.slice(0, 8).map(h => {
            const hIcon = weatherIcon(h.condition);
            const precipClass = (h.precipitation_chance || 0) > 0.3 ? 'precip-high' : 'text-slate-500';
            const precipPct = Math.round((h.precipitation_chance || 0) * 100);
            const dt = h.dt ? new Date(h.dt * 1000) : null;
            const timeStr = dt ? dt.toLocaleTimeString('en-AU', { hour: 'numeric', hour12: true }) : '';
            return `
                <div class="flex-shrink-0 text-center space-y-1 w-14">
                    <p class="text-xs text-slate-400">${timeStr}</p>
                    <i class="ph ${hIcon} text-lg"></i>
                    <p class="text-sm font-medium">${Math.round(h.temp || 0)}&deg;</p>
                    <p class="text-xs ${precipClass}">
                        <i class="ph ph-drop text-[10px]"></i> ${precipPct}%
                    </p>
                </div>
            `;
        }).join('');
    } else {
        hourly.innerHTML = '<p class="text-xs text-slate-500">No hourly data</p>';
    }
}

// ---------- Render: Commute ----------

function renderCommute(c) {
    if (!c || c.error) return;
    const el = document.getElementById('commute-content');
    el.innerHTML = `
        <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
                <i class="ph ph-clock text-indigo-400"></i>
                <span class="text-lg font-semibold">${c.duration_text || '--'}</span>
            </div>
            <span class="text-sm text-slate-400">Leave by ${c.leave_by || '--'}</span>
        </div>
        <p class="text-xs text-slate-500 mt-1">
            <i class="ph ph-map-pin"></i> ${c.distance_text || ''} to Office
        </p>
    `;
}

// ---------- Render: Calendar ----------

function renderCalendar(events) {
    const el = document.getElementById('calendar-events');
    if (!events || !events.length) {
        el.innerHTML = '<p class="text-sm text-slate-500">No events today</p>';
        return;
    }

    const sorted = [...events].sort((a, b) => (a.time || '').localeCompare(b.time || ''));
    el.innerHTML = sorted.map(ev => {
        const borderClass = (ev.source || '').toLowerCase() === 'work' ? 'source-work' : 'source-personal';
        const teamsLink = ev.teams_link
            ? `<a href="${ev.teams_link}" target="_blank" class="text-indigo-400 hover:text-indigo-300 flex items-center gap-1 text-xs"><i class="ph ph-video-camera"></i>Join</a>`
            : '';
        const location = ev.location
            ? `<span class="flex items-center gap-1 text-xs text-slate-500"><i class="ph ph-map-pin"></i>${ev.location}</span>`
            : '';
        return `
            <div class="pl-3 py-2 ${borderClass} space-y-0.5">
                <div class="flex items-center justify-between">
                    <span class="text-sm font-medium">${ev.title || 'Untitled'}</span>
                    ${teamsLink}
                </div>
                <div class="flex items-center gap-3">
                    <span class="text-xs text-slate-400">${ev.time || ''}</span>
                    ${location}
                </div>
            </div>
        `;
    }).join('');
}

// ---------- Render: Birthdays ----------

function renderBirthdays(birthdays) {
    const card = document.getElementById('birthdays-card');
    const el = document.getElementById('birthdays-content');

    if (!birthdays || !birthdays.length) {
        card.classList.add('hidden');
        return;
    }

    card.classList.remove('hidden');
    el.innerHTML = birthdays.map(b => `
        <div class="flex items-center gap-2 text-sm">
            <i class="ph ph-gift text-pink-400"></i>
            <span>${typeof b === 'string' ? b : b.name || ''}</span>
        </div>
    `).join('');
}

// ---------- Render: News ----------

const NEWS_TABS = [
    { key: 'headlines', label: 'Headlines', icon: 'ph-newspaper' },
    { key: 'ai',        label: 'AI',        icon: 'ph-robot' },
    { key: 'movies',    label: 'Movies',    icon: 'ph-film-slate' },
    { key: 'tesla',     label: 'Tesla',     icon: 'ph-lightning' },
    { key: 'stremio',   label: 'Stremio',   icon: 'ph-play' },
];

let currentNewsData = {};

function renderNews(news) {
    if (!news) return;
    currentNewsData = news;

    const tabsEl = document.getElementById('news-tabs');
    tabsEl.innerHTML = NEWS_TABS.map((tab, i) => `
        <button class="glass-tab px-3 py-1.5 text-xs flex items-center gap-1 whitespace-nowrap ${i === 0 ? 'active' : ''}"
                onclick="switchNewsTab('${tab.key}', this)">
            <i class="ph ${tab.icon}"></i>
            ${tab.label}
        </button>
    `).join('');

    // Show first tab
    renderNewsArticles(NEWS_TABS[0].key);
}

function switchNewsTab(key, btn) {
    // Update active state
    document.querySelectorAll('#news-tabs .glass-tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    renderNewsArticles(key);
}

function renderNewsArticles(key) {
    const el = document.getElementById('news-content');
    const articles = currentNewsData[key] || [];

    if (!articles.length) {
        el.innerHTML = '<p class="text-sm text-slate-500">No articles available</p>';
        return;
    }

    el.innerHTML = articles.map(a => `
        <a href="${a.url || '#'}" target="_blank" rel="noopener"
           class="block glass-card-hover rounded-lg p-3 space-y-1 transition cursor-pointer">
            <p class="text-sm font-medium leading-snug">${a.title || ''}</p>
            <p class="text-xs text-slate-400 line-clamp-2">${a.excerpt || a.description || ''}</p>
            <span class="text-[10px] text-slate-500">${a.source || ''}</span>
        </a>
    `).join('');
}

// ---------- Render: Reminders ----------

function renderReminders(reminders) {
    const el = document.getElementById('reminders-content');
    if (!reminders || !reminders.length) {
        el.innerHTML = '<p class="text-xs text-slate-500">No reminders</p>';
        return;
    }
    el.innerHTML = reminders.map(r => `
        <div class="flex items-start gap-2 text-sm">
            <i class="ph ph-check-square text-indigo-400 mt-0.5"></i>
            <span class="text-slate-300">${typeof r === 'string' ? r : r.title || r.text || ''}</span>
        </div>
    `).join('');
}

// ---------- Render: Flagged Emails ----------

function renderFlaggedEmails(emails) {
    const el = document.getElementById('flagged-emails-content');
    if (!emails || !emails.length) {
        el.innerHTML = '<p class="text-xs text-slate-500">No flagged emails</p>';
        return;
    }
    el.innerHTML = emails.map(e => `
        <div class="flex items-start gap-2 text-sm">
            <i class="ph ph-flag text-red-400 mt-0.5"></i>
            <div>
                <p class="text-slate-300">${e.subject || e.title || ''}</p>
                <p class="text-xs text-slate-500">${e.from || e.sender || ''}</p>
            </div>
        </div>
    `).join('');
}

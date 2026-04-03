/* ============================================================
   admin.js — System health panel & update trigger
   ============================================================ */

// ---------- Health ----------

async function loadHealth() {
    try {
        const res = await fetch(`${CONFIG.API_URL}/health`);
        if (!res.ok) throw new Error(`Health returned ${res.status}`);
        const data = await res.json();
        renderHealth(data);
    } catch (err) {
        console.error('Health load error:', err);
        document.getElementById('health-banner').innerHTML =
            '<span class="text-red-400 flex items-center gap-1"><i class="ph ph-x-circle"></i> Could not load health</span>';
    }
}

async function refreshHealth() {
    const btn = document.querySelector('#admin-section button');
    if (btn) btn.classList.add('animate-spin');
    await loadHealth();
    if (btn) btn.classList.remove('animate-spin');
}

function renderHealth(data) {
    const banner = document.getElementById('health-banner');
    const grid = document.getElementById('health-grid');
    const lastUpdated = document.getElementById('last-updated');

    const overallHealthy = data.status === 'healthy';
    const systems = data.systems || {};
    const systemEntries = Object.entries(systems);

    // Count degraded
    const degradedCount = systemEntries.filter(([, s]) => s.status !== 'ok' && s.status !== 'healthy').length;

    if (overallHealthy) {
        banner.innerHTML = '<span class="text-emerald-400 flex items-center gap-1"><i class="ph ph-heartbeat"></i> All Systems Healthy</span>';
    } else {
        banner.innerHTML = `<span class="text-amber-400 flex items-center gap-1"><i class="ph ph-warning"></i> ${degradedCount} System${degradedCount !== 1 ? 's' : ''} Degraded</span>`;
    }

    grid.innerHTML = systemEntries.map(([name, info]) => {
        const status = info.status || 'unknown';
        let badgeClass, iconClass;

        if (status === 'ok' || status === 'healthy') {
            badgeClass = 'badge-healthy';
            iconClass = 'ph ph-heartbeat';
        } else if (status === 'warning' || status === 'degraded') {
            badgeClass = 'badge-warning';
            iconClass = 'ph ph-warning';
        } else {
            badgeClass = 'badge-error';
            iconClass = 'ph ph-x-circle';
        }

        const lastCheck = info.last_check
            ? new Date(info.last_check).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            : '';

        return `
            <div class="text-center space-y-1 p-2 rounded-lg bg-white/[0.02]">
                <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] ${badgeClass}">
                    <i class="${iconClass} text-xs"></i>
                </span>
                <p class="text-xs font-medium capitalize">${formatSystemName(name)}</p>
                <p class="text-[10px] text-slate-500">${lastCheck}</p>
            </div>
        `;
    }).join('');

    lastUpdated.textContent = `Updated ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
}

function formatSystemName(name) {
    return name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

// ---------- Update ----------

async function triggerUpdate() {
    const btn = document.getElementById('update-btn');
    const statusEl = document.getElementById('update-status');

    statusEl.classList.remove('hidden');
    statusEl.innerHTML = '<span class="text-slate-400 flex items-center gap-2"><div class="spinner"></div> Updating system...</span>';
    btn.disabled = true;

    try {
        const res = await fetch(`${CONFIG.API_URL}/admin/update`, {
            method: 'POST',
        });

        if (!res.ok) throw new Error(`Update returned ${res.status}`);
        const result = await res.json();

        statusEl.innerHTML = '<span class="text-emerald-400 flex items-center gap-1"><i class="ph ph-check-circle"></i> Update successful</span>';

        // Refresh health after update
        setTimeout(() => {
            loadHealth();
            statusEl.classList.add('hidden');
        }, 3000);
    } catch (err) {
        statusEl.innerHTML = `<span class="text-red-400 flex items-center gap-1"><i class="ph ph-x-circle"></i> Update failed: ${err.message}</span>`;
    } finally {
        btn.disabled = false;
    }
}

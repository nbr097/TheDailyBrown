/* ============================================================
   devices.js — Credential management for admin page
   ============================================================ */

// ---------- helpers: base64url <-> ArrayBuffer ----------

function base64urlToBuffer(base64url) {
    const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/');
    const pad = base64.length % 4 === 0 ? '' : '='.repeat(4 - (base64.length % 4));
    const binary = atob(base64 + pad);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return bytes.buffer;
}

function bufferToBase64url(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (const b of bytes) binary += String.fromCharCode(b);
    return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

// ---------- Load devices ----------

async function loadDevices() {
    const el = document.getElementById('devices-list');
    try {
        const res = await fetch(`${CONFIG.API_URL}/auth/webauthn/credentials`);
        if (!res.ok) throw new Error(`Failed: ${res.status}`);
        const devices = await res.json();

        if (!devices.length) {
            el.innerHTML = '<p class="text-sm text-slate-500">No devices registered</p>';
            return;
        }

        el.innerHTML = devices.map(d => {
            const date = new Date(d.created_at * 1000).toLocaleDateString('en-AU', {
                day: 'numeric', month: 'short', year: 'numeric',
            });
            return `
                <div class="flex items-center justify-between py-2 px-1">
                    <div class="flex items-center gap-2">
                        <i class="ph ph-device-mobile text-indigo-400"></i>
                        <div>
                            <p class="text-sm font-medium">${d.device_name || 'Unknown'}</p>
                            <p class="text-xs text-slate-500">Registered ${date}</p>
                        </div>
                    </div>
                    <button onclick="deleteDevice('${d.id}')" class="text-xs text-red-400 hover:text-red-300 transition flex items-center gap-1">
                        <i class="ph ph-trash"></i>
                        Remove
                    </button>
                </div>
            `;
        }).join('');
    } catch (err) {
        el.innerHTML = `<p class="text-sm text-red-400">Could not load devices: ${err.message}</p>`;
    }
}

// ---------- Delete device ----------

async function deleteDevice(id) {
    try {
        const res = await fetch(`${CONFIG.API_URL}/auth/webauthn/credentials/${encodeURIComponent(id)}`, {
            method: 'DELETE',
        });
        if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
        loadDevices();
    } catch (err) {
        alert('Failed to remove device: ' + err.message);
    }
}

// ---------- Register this device ----------

async function registerDevice() {
    const btn = document.getElementById('register-device-btn');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner"></div><span>Registering...</span>';

    try {
        const optRes = await fetch(`${CONFIG.API_URL}/auth/webauthn/register-options`);
        if (!optRes.ok) throw new Error('Could not get registration options');
        const options = await optRes.json();

        options.challenge = base64urlToBuffer(options.challenge);
        options.user.id = base64urlToBuffer(options.user.id);
        if (options.excludeCredentials) {
            options.excludeCredentials = options.excludeCredentials.map(cred => ({
                ...cred,
                id: base64urlToBuffer(cred.id),
            }));
        }

        const credential = await navigator.credentials.create({ publicKey: options });

        const body = {
            id: credential.id,
            rawId: bufferToBase64url(credential.rawId),
            response: {
                attestationObject: bufferToBase64url(credential.response.attestationObject),
                clientDataJSON: bufferToBase64url(credential.response.clientDataJSON),
            },
            type: credential.type,
        };

        const regRes = await fetch(`${CONFIG.API_URL}/auth/webauthn/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        if (!regRes.ok) throw new Error('Registration failed');

        loadDevices();
    } catch (err) {
        alert('Registration failed: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="ph ph-plus"></i><span>Register This Device</span>';
    }
}

// ---------- Auto-load ----------

window.addEventListener('DOMContentLoaded', () => {
    loadDevices();
    loadHealth();

    // Scroll to health section if URL has #health
    if (window.location.hash === '#health') {
        setTimeout(() => {
            document.getElementById('health-section')?.scrollIntoView({ behavior: 'smooth' });
        }, 300);
    }
});

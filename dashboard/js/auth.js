/* ============================================================
   auth.js — WebAuthn authentication / registration client
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

// ---------- DOM refs ----------

const authScreen    = document.getElementById('auth-screen');
const dashboard     = document.getElementById('dashboard-screen');
const authStatus    = document.getElementById('auth-status');
const authError     = document.getElementById('auth-error');
const registerSec   = document.getElementById('register-section');
const authBtn       = document.getElementById('auth-btn');

// ---------- state ----------

let authToken = null;

// ---------- page load: attempt auth ----------

window.addEventListener('DOMContentLoaded', async () => {
    authStatus.textContent = 'Checking credentials...';
    try {
        await authenticate();
    } catch (err) {
        // If authenticate fails, maybe no credential — show register
        console.log('Auto-auth failed, showing options:', err.message);
        authStatus.textContent = '';
        registerSec.classList.remove('hidden');
    }
});

// ---------- public entry points (called from HTML buttons) ----------

async function startAuth() {
    authError.classList.add('hidden');
    authBtn.disabled = true;
    authBtn.innerHTML = '<div class="spinner"></div><span>Authenticating...</span>';
    try {
        await authenticate();
    } catch (err) {
        showAuthError(err.message || 'Authentication failed');
    } finally {
        authBtn.disabled = false;
        authBtn.innerHTML = '<i class="ph ph-fingerprint text-xl"></i><span>Authenticate with Face ID</span>';
    }
}

async function startRegister() {
    const btn = document.getElementById('register-btn');
    authError.classList.add('hidden');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner"></div><span>Registering...</span>';
    try {
        await register();
        // Registration proves identity — go straight to dashboard
        onAuthSuccess();
        return;
    } catch (err) {
        showAuthError(err.message || 'Registration failed');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="ph ph-user-plus text-xl"></i><span>Register Device</span>';
    }
}

// ---------- WebAuthn authenticate ----------

async function authenticate() {
    // 1. Get options from server
    const optRes = await fetch('/auth/webauthn/authenticate-options');
    if (!optRes.ok) throw new Error('Could not get authentication options');
    const options = await optRes.json();

    // Convert challenge
    options.challenge = base64urlToBuffer(options.challenge);

    // Convert allowCredentials ids
    if (options.allowCredentials) {
        options.allowCredentials = options.allowCredentials.map(cred => ({
            ...cred,
            id: base64urlToBuffer(cred.id),
        }));
    }

    // 2. Prompt biometric / security key
    const credential = await navigator.credentials.get({ publicKey: options });

    // 3. Send assertion to server
    const body = {
        id: credential.id,
        rawId: bufferToBase64url(credential.rawId),
        response: {
            authenticatorData: bufferToBase64url(credential.response.authenticatorData),
            clientDataJSON: bufferToBase64url(credential.response.clientDataJSON),
            signature: bufferToBase64url(credential.response.signature),
            userHandle: credential.response.userHandle
                ? bufferToBase64url(credential.response.userHandle)
                : null,
        },
        type: credential.type,
    };

    const verifyRes = await fetch('/auth/webauthn/authenticate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });

    if (!verifyRes.ok) throw new Error('Authentication verification failed');

    const result = await verifyRes.json();
    authToken = result.token || null;

    // Success — switch to dashboard
    onAuthSuccess();
}

// ---------- WebAuthn register ----------

async function register() {
    // 1. Get registration options
    const optRes = await fetch('/auth/webauthn/register-options');
    if (!optRes.ok) throw new Error('Could not get registration options');
    const options = await optRes.json();

    // Convert challenge and user.id
    options.challenge = base64urlToBuffer(options.challenge);
    options.user.id = base64urlToBuffer(options.user.id);

    // Convert excludeCredentials ids if present
    if (options.excludeCredentials) {
        options.excludeCredentials = options.excludeCredentials.map(cred => ({
            ...cred,
            id: base64urlToBuffer(cred.id),
        }));
    }

    // 2. Create credential
    const credential = await navigator.credentials.create({ publicKey: options });

    // 3. Send attestation to server
    const body = {
        id: credential.id,
        rawId: bufferToBase64url(credential.rawId),
        response: {
            attestationObject: bufferToBase64url(credential.response.attestationObject),
            clientDataJSON: bufferToBase64url(credential.response.clientDataJSON),
        },
        type: credential.type,
    };

    const regRes = await fetch('/auth/webauthn/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });

    if (!regRes.ok) throw new Error('Registration verification failed');
    return regRes.json();
}

// ---------- post-auth transition ----------

function onAuthSuccess() {
    authScreen.classList.add('hidden');
    dashboard.classList.remove('hidden');
    loadDashboard();
}

// ---------- helpers ----------

function showAuthError(msg) {
    authError.textContent = msg;
    authError.classList.remove('hidden');
}

// Re-authenticate for admin actions (returns true/false)
async function reauthenticate() {
    try {
        await authenticate();
        return true;
    } catch {
        return false;
    }
}

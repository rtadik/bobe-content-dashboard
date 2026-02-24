/**
 * intake.js — Client Intake Form Logic
 *
 * Responsibilities:
 *  1. Tip system — contextual tooltips on field focus
 *  2. Progress bar — updates as user scrolls through sections
 *  3. Form validation
 *  4. Password derivation ({client_id}123)
 *  5. EmailJS credential email send
 *  6. JSON assembly and download
 *  7. Success panel + fallback on email failure
 */

'use strict';

// ── State ──────────────────────────────────────────────────────
let intakeData = null;

// ── Helpers ────────────────────────────────────────────────────
function getValue(id) {
  const el = document.getElementById(id);
  return el ? el.value.trim() : '';
}

function getLines(id) {
  return getValue(id).split('\n').map(l => l.trim()).filter(Boolean);
}

function getChecked(name) {
  return Array.from(document.querySelectorAll(`input[name="${name}"]:checked`))
    .map(el => el.value);
}

function getRadio(name) {
  const el = document.querySelector(`input[name="${name}"]:checked`);
  return el ? el.value : '';
}

// ── Tip System ─────────────────────────────────────────────────
function initTips() {
  document.querySelectorAll('[data-tip]').forEach(field => {
    const wrapper = field.closest('.field-wrapper');
    if (!wrapper) return;
    const tipBox = wrapper.querySelector('.tip-box');
    if (!tipBox) return;

    field.addEventListener('focus', () => tipBox.classList.add('visible'));
    field.addEventListener('blur',  () => tipBox.classList.remove('visible'));
  });
}

// ── Progress Bar ───────────────────────────────────────────────
function updateProgress() {
  const sections = document.querySelectorAll('.section-card');
  const steps = document.querySelectorAll('.progress-step');
  const scrollY = window.scrollY + window.innerHeight * 0.4;

  let lastVisible = 0;
  sections.forEach((sec, i) => {
    if (sec.getBoundingClientRect().top + window.scrollY <= scrollY) {
      lastVisible = i;
    }
  });

  steps.forEach((step, i) => {
    step.classList.remove('active', 'done');
    if (i < lastVisible) step.classList.add('done');
    else if (i === lastVisible) step.classList.add('active');
  });
}

// ── Airtable toggle ────────────────────────────────────────────
function initAirtableToggle() {
  document.querySelectorAll('input[name="airtable_enabled"]').forEach(radio => {
    radio.addEventListener('change', () => {
      const row = document.getElementById('airtable-base-row');
      if (getRadio('airtable_enabled') === 'yes') {
        row.classList.add('show');
      } else {
        row.classList.remove('show');
      }
    });
  });
}

// ── Color pickers ──────────────────────────────────────────────
function initColorPickers() {
  const pairs = [
    ['primary_color', 'primary_color_text'],
    ['accent_color',  'accent_color_text'],
    ['text_color',    'text_color_text'],
  ];

  pairs.forEach(([pickerId, textId]) => {
    const picker = document.getElementById(pickerId);
    const text   = document.getElementById(textId);
    if (!picker || !text) return;

    // Sync text from picker initial value
    text.value = picker.value;

    picker.addEventListener('input', () => { text.value = picker.value; });
    text.addEventListener('input', () => {
      const val = text.value.trim();
      if (/^#[0-9a-fA-F]{6}$/.test(val)) picker.value = val;
    });
  });
}

// ── Validation ─────────────────────────────────────────────────
function showError(id, show) {
  const el = document.getElementById('error-' + id);
  if (el) el.classList.toggle('show', show);

  const input = document.getElementById(id);
  if (input) input.classList.toggle('error', show);
}

function validateForm() {
  let valid = true;

  // Email
  const email = getValue('email');
  const emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  showError('email', !emailOk);
  if (!emailOk) valid = false;

  // client_id
  const clientId = getValue('client_id');
  const clientIdOk = /^[a-z0-9_-]+$/.test(clientId) && clientId.length > 0;
  showError('client_id', !clientIdOk);
  if (!clientIdOk) valid = false;

  // display_name
  const displayNameOk = getValue('display_name').length > 0;
  showError('display_name', !displayNameOk);
  if (!displayNameOk) valid = false;

  // description
  const descOk = getValue('description').length > 10;
  showError('description', !descOk);
  if (!descOk) valid = false;

  // audience_situation
  const situationOk = getValue('audience_situation').length > 10;
  showError('audience_situation', !situationOk);
  if (!situationOk) valid = false;

  // pain_points
  const painOk = getLines('pain_points').length > 0;
  showError('pain_points', !painOk);
  if (!painOk) valid = false;

  // differentiators
  const diffOk = getLines('differentiators').length > 0;
  showError('differentiators', !diffOk);
  if (!diffOk) valid = false;

  // tone_adjectives
  const toneOk = getValue('tone_adjectives').length > 0;
  showError('tone_adjectives', !toneOk);
  if (!toneOk) valid = false;

  // content_avoid
  const avoidOk = getLines('content_avoid').length > 0;
  showError('content_avoid', !avoidOk);
  if (!avoidOk) valid = false;

  // messaging_pillars
  const pillarsOk = getLines('messaging_pillars').length > 0;
  showError('messaging_pillars', !pillarsOk);
  if (!pillarsOk) valid = false;

  // platforms (at least one)
  const platformsOk = getChecked('platforms').length > 0;
  showError('platforms', !platformsOk);
  if (!platformsOk) valid = false;

  // keywords
  const keywordsOk = getLines('keywords').length >= 3;
  showError('keywords', !keywordsOk);
  if (!keywordsOk) valid = false;

  // cta_examples
  const ctaOk = getLines('cta_examples').length > 0;
  showError('cta_examples', !ctaOk);
  if (!ctaOk) valid = false;

  // hashtags
  const hashtagsOk = getLines('hashtags').length > 0;
  showError('hashtags', !hashtagsOk);
  if (!hashtagsOk) valid = false;

  if (!valid) {
    // Scroll to first error
    const firstError = document.querySelector('.field-error.show');
    if (firstError) {
      firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }

  return valid;
}

// ── Password derivation ────────────────────────────────────────
function derivePassword(clientId) {
  return clientId + '123';
}

// ── JSON assembly ──────────────────────────────────────────────
function buildIntakeJSON() {
  const clientId = getValue('client_id');
  const platforms = getChecked('platforms');
  const languages = ['english'];
  if (document.querySelector('input[name="languages"][value="russian"]')?.checked) {
    languages.push('russian');
  }
  const airtableEnabled = getRadio('airtable_enabled') === 'yes';

  return {
    intake_version: '1.0',
    submitted_at: new Date().toISOString(),
    contact: {
      email: getValue('email')
    },
    client_id: clientId,
    display_name: getValue('display_name'),
    website: getValue('website'),
    tagline: getValue('tagline'),
    description: getValue('description'),
    audience: {
      age_range: getValue('audience_age'),
      situation: getValue('audience_situation'),
      pain_points: getLines('pain_points'),
      desired_outcome: getValue('desired_outcome')
    },
    differentiators: getLines('differentiators'),
    voice: {
      tone_adjectives: getValue('tone_adjectives').split(',').map(s => s.trim()).filter(Boolean),
      tone_description: getValue('tone_description'),
      content_avoid: getLines('content_avoid'),
      messaging_pillars: getLines('messaging_pillars')
    },
    platforms: platforms,
    languages: languages,
    scraping: {
      keywords: getLines('keywords'),
      negative_keywords: getLines('negative_keywords'),
      subreddits: getLines('subreddits')
    },
    content: {
      cta_examples: getLines('cta_examples'),
      hashtags: getLines('hashtags')
    },
    brand: {
      primary_color: document.getElementById('primary_color')?.value || '#1a1a2e',
      accent_color:  document.getElementById('accent_color')?.value  || '#1589DC',
      text_color:    document.getElementById('text_color')?.value    || '#ffffff',
      mascot: getValue('mascot')
    },
    airtable: {
      enabled: airtableEnabled,
      base_id: airtableEnabled ? getValue('airtable_base_id') : ''
    }
  };
}

// ── EmailJS send ───────────────────────────────────────────────
async function sendCredentialEmail({ email, displayName, clientId, password, loginUrl, dashboardUrl }) {
  if (!window.INTAKE_CONFIG || !window.INTAKE_CONFIG.emailjs) {
    throw new Error('INTAKE_CONFIG not loaded. Create intake-config.js from the example template.');
  }
  const { publicKey, serviceId, templateId } = window.INTAKE_CONFIG.emailjs;

  emailjs.init(publicKey);
  return emailjs.send(serviceId, templateId, {
    to_email:      email,
    to_name:       displayName,
    client_id:     clientId,
    username:      'admin',
    password:      password,
    login_url:     loginUrl,
    dashboard_url: dashboardUrl
  });
}

// ── Success panel ──────────────────────────────────────────────
function showSuccessPanel({ emailFailed = false, clientId = '', password = '', workerStatus = 'pending' } = {}) {
  document.getElementById('intakeForm').style.display = 'none';
  const panel = document.getElementById('successPanel');
  panel.classList.add('show');

  const email = getValue('email');
  document.getElementById('clientEmail').textContent = email;

  // Credentials display
  const creds = document.getElementById('successCredentials');
  creds.innerHTML =
    '<strong>Your credentials:</strong><br>' +
    'Username: <strong>admin</strong><br>' +
    'Password: <strong>' + (password || derivePassword(getValue('client_id'))) + '</strong>';

  // Worker / onboarding status message
  const statusEl = document.getElementById('onboardStatus');
  if (statusEl) {
    if (workerStatus === 'ok') {
      statusEl.style.display = 'block';
      statusEl.className = 'onboard-status onboard-ok';
      statusEl.textContent =
        'Your dashboard is being set up automatically. It will be live at content.rejiglabs.com/dashboard/' +
        (clientId || getValue('client_id')) + '/ within 3-5 minutes.';
    } else if (workerStatus === 'error') {
      statusEl.style.display = 'block';
      statusEl.className = 'onboard-status onboard-warn';
      statusEl.textContent =
        'Automatic setup encountered an issue. Your intake file has been downloaded. ' +
        'Forward it to your partner to complete setup manually.';
    }
    // If 'pending' (workerUrl not configured), show nothing extra
  }

  if (emailFailed) {
    const warn = document.getElementById('emailWarning');
    warn.style.display = 'block';
    warn.textContent =
      'Email delivery failed. Your credentials are shown above — save them now. ' +
      'Download your intake file and send it to your partner to complete setup.';
    document.getElementById('successMsg').innerHTML =
      'There was a problem sending the credential email to <strong>' + email + '</strong>.';
  }

  panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ── Download / Copy ────────────────────────────────────────────
function downloadJSON() {
  if (!intakeData) return;
  const clientId = intakeData.client_id || 'intake';
  const blob = new Blob([JSON.stringify(intakeData, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = clientId + '-intake.json';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function copyJSON() {
  if (!intakeData) return;
  const text = JSON.stringify(intakeData, null, 2);
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(() => {
      const btn = document.querySelector('.btn-copy');
      if (btn) {
        const orig = btn.textContent;
        btn.textContent = 'Copied!';
        setTimeout(() => { btn.textContent = orig; }, 2000);
      }
    });
  }
}

// ── Form submit ────────────────────────────────────────────────
async function handleSubmit(e) {
  e.preventDefault();
  if (!validateForm()) return;

  const submitBtn = document.getElementById('submitBtn');
  submitBtn.textContent = 'Sending credentials...';
  submitBtn.disabled = true;

  const clientId    = getValue('client_id');
  const password    = derivePassword(clientId);
  const email       = getValue('email');
  const displayName = getValue('display_name');

  const baseUrl      = window.INTAKE_CONFIG ? window.INTAKE_CONFIG.dashboardBaseUrl : '';
  const loginUrl     = baseUrl ? baseUrl + '/login.html' : '';
  const dashboardUrl = baseUrl ? baseUrl + '/dashboard/' + clientId + '/' : '';

  // Build JSON first (needed for fallback download even if email fails)
  intakeData = buildIntakeJSON();

  // ── Step 1: EmailJS credential email ──────────────────────────────────────
  let emailFailed = false;
  try {
    await sendCredentialEmail({ email, displayName, clientId, password, loginUrl, dashboardUrl });
  } catch (err) {
    console.warn('EmailJS error:', err);
    emailFailed = true;
  }

  // ── Step 2: Cloudflare Worker — trigger auto-onboard (non-blocking) ───────
  let workerStatus = 'pending'; // 'ok' | 'error' | 'pending'
  const workerUrl = window.INTAKE_CONFIG ? window.INTAKE_CONFIG.workerUrl : null;

  if (workerUrl) {
    try {
      submitBtn.textContent = 'Setting up your dashboard...';
      const resp = await fetch(workerUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(intakeData),
      });
      if (resp.ok) {
        workerStatus = 'ok';
      } else {
        const errBody = await resp.json().catch(() => ({}));
        console.warn('Worker error response:', resp.status, errBody);
        workerStatus = 'error';
      }
    } catch (err) {
      console.warn('Worker fetch error:', err);
      workerStatus = 'error';
    }
  } else {
    console.warn('INTAKE_CONFIG.workerUrl not set — skipping auto-onboard trigger');
  }

  // ── Step 3: Show success panel ────────────────────────────────────────────
  showSuccessPanel({ emailFailed, clientId, password, workerStatus });
}

// ── Init ───────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initTips();
  initAirtableToggle();
  initColorPickers();
  updateProgress();

  window.addEventListener('scroll', updateProgress, { passive: true });

  const form = document.getElementById('intakeForm');
  if (form) form.addEventListener('submit', handleSubmit);
});

// Expose for inline onclick handlers
window.downloadJSON = downloadJSON;
window.copyJSON = copyJSON;

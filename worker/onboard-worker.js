/**
 * onboard-worker.js — Cloudflare Worker
 *
 * Secure proxy between the intake form (public browser JS) and GitHub Actions.
 * Holds the GitHub PAT in Cloudflare env vars. Never exposed to the browser.
 *
 * Environment variables required (set via wrangler secret / Cloudflare dashboard):
 *   GITHUB_PAT      — Fine-grained PAT with Actions: write on the repo
 *   GITHUB_REPO     — e.g. "rtadik/bobe-content-dashboard"
 *   ALLOWED_ORIGIN  — e.g. "https://content.rejiglabs.com"
 */

const WORKFLOW_FILE = 'auto-onboard.yml';
const GITHUB_API    = 'https://api.github.com';

export default {
  async fetch(request, env) {
    const allowedOrigin = env.ALLOWED_ORIGIN || 'https://content.rejiglabs.com';

    // ── CORS preflight ────────────────────────────────────────────────────────
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: corsHeaders(allowedOrigin),
      });
    }

    // ── Only accept POST ──────────────────────────────────────────────────────
    if (request.method !== 'POST') {
      return jsonResponse({ error: 'Method not allowed' }, 405, allowedOrigin);
    }

    // ── Parse body ────────────────────────────────────────────────────────────
    let intake;
    try {
      intake = await request.json();
    } catch {
      return jsonResponse({ error: 'Invalid JSON body' }, 400, allowedOrigin);
    }

    // ── Validate required fields ──────────────────────────────────────────────
    const validationError = validateIntake(intake);
    if (validationError) {
      return jsonResponse({ error: validationError }, 400, allowedOrigin);
    }

    // ── Trigger GitHub Actions workflow_dispatch ───────────────────────────────
    const intakeJson = JSON.stringify(intake);
    const ghResponse = await fetch(
      `${GITHUB_API}/repos/${env.GITHUB_REPO}/actions/workflows/${WORKFLOW_FILE}/dispatches`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${env.GITHUB_PAT}`,
          Accept: 'application/vnd.github+json',
          'X-GitHub-Api-Version': '2022-11-28',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ref: 'main',
          inputs: {
            intake_json: intakeJson,
          },
        }),
      }
    );

    if (!ghResponse.ok) {
      let ghError = 'GitHub API error';
      try {
        const body = await ghResponse.json();
        ghError = body.message || ghError;
      } catch {}
      console.error(`GitHub API returned ${ghResponse.status}: ${ghError}`);
      return jsonResponse(
        { error: 'Failed to trigger onboarding workflow', detail: ghError },
        502,
        allowedOrigin
      );
    }

    // GitHub returns 204 No Content on success
    return jsonResponse(
      {
        ok: true,
        message: `Onboarding workflow triggered for client "${intake.client_id}". Your dashboard will be live in 3-5 minutes.`,
        client_id: intake.client_id,
      },
      200,
      allowedOrigin
    );
  },
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function validateIntake(intake) {
  if (!intake || typeof intake !== 'object') {
    return 'Intake must be a JSON object';
  }
  if (!intake.client_id || typeof intake.client_id !== 'string') {
    return 'Missing required field: client_id';
  }
  if (!/^[a-z0-9_-]+$/.test(intake.client_id)) {
    return 'client_id must be lowercase letters, numbers, hyphens, or underscores only';
  }
  if (!intake.display_name || typeof intake.display_name !== 'string') {
    return 'Missing required field: display_name';
  }
  if (!intake.contact || !intake.contact.email) {
    return 'Missing required field: contact.email';
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(intake.contact.email)) {
    return 'contact.email is not a valid email address';
  }
  return null; // valid
}

function corsHeaders(origin) {
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400',
  };
}

function jsonResponse(body, status, origin) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...corsHeaders(origin),
    },
  });
}

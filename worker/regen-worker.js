/**
 * regen-worker.js — Cloudflare Worker
 *
 * Secure proxy between the live dashboard (public browser JS) and GitHub Actions.
 * Holds the GitHub PAT as a Cloudflare secret. Never exposed to the browser.
 *
 * Handles three workflows:
 *   - regenerate-item      (regen image/content for a topic)
 *   - publish-to-x         (publish Twitter thread)
 *   - generate-announcement (generate 7 announcement angles)
 *
 * Environment variables required (set via wrangler secret / Cloudflare dashboard):
 *   GITHUB_PAT      — Fine-grained PAT with Actions: write on the repo
 *   GITHUB_REPO     — e.g. "rtadik/bobe-content-dashboard"
 *   ALLOWED_ORIGIN  — e.g. "https://content.rejiglabs.com"
 *
 * Routes:
 *   POST /          — dispatch a workflow
 *   GET  /status    — poll latest run status for a workflow file
 */

const GITHUB_API = 'https://api.github.com';

const ALLOWED_WORKFLOWS = new Set([
  'regenerate-item',
  'publish-to-x',
  'generate-announcement',
]);

// Required inputs per workflow (beyond client_id and week_of)
const REQUIRED_INPUTS = {
  'regenerate-item':      ['topic_index', 'regen_type'],
  'publish-to-x':         ['topic_index'],
  'generate-announcement': ['bucket', 'announcement_text'],
};

export default {
  async fetch(request, env) {
    const allowedOrigin = env.ALLOWED_ORIGIN || 'https://content.rejiglabs.com';
    const url = new URL(request.url);

    // ── CORS preflight ────────────────────────────────────────────────────────
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: corsHeaders(allowedOrigin),
      });
    }

    // ── Route: GET /status — poll latest run for a workflow ───────────────────
    if (request.method === 'GET' && url.pathname === '/status') {
      const workflowFile = url.searchParams.get('workflow');
      if (!workflowFile) {
        return jsonResponse({ error: 'Missing ?workflow= parameter' }, 400, allowedOrigin);
      }

      const ghResp = await fetch(
        `${GITHUB_API}/repos/${env.GITHUB_REPO}/actions/workflows/${workflowFile}/runs?per_page=3`,
        {
          headers: {
            Authorization: `Bearer ${env.GITHUB_PAT}`,
            Accept: 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
            'User-Agent': 'regen-worker/1.0',
          },
        }
      );

      if (!ghResp.ok) {
        return jsonResponse({ error: `GitHub API returned ${ghResp.status}` }, 502, allowedOrigin);
      }

      const data = await ghResp.json();
      const run = data.workflow_runs && data.workflow_runs[0];
      if (!run) {
        return jsonResponse({ status: 'not_found', conclusion: null }, 200, allowedOrigin);
      }
      return jsonResponse({ status: run.status, conclusion: run.conclusion }, 200, allowedOrigin);
    }

    // ── Route: POST / — dispatch a workflow ───────────────────────────────────
    if (request.method === 'POST' && url.pathname === '/') {
      let body;
      try {
        body = await request.json();
      } catch {
        return jsonResponse({ error: 'Invalid JSON body' }, 400, allowedOrigin);
      }

      const validationError = validateBody(body);
      if (validationError) {
        return jsonResponse({ error: validationError }, 400, allowedOrigin);
      }

      const { workflow, client_id, week_of, ...extraInputs } = body;
      const workflowFile = `${workflow}.yml`;

      const ghResp = await fetch(
        `${GITHUB_API}/repos/${env.GITHUB_REPO}/actions/workflows/${workflowFile}/dispatches`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${env.GITHUB_PAT}`,
            Accept: 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
            'Content-Type': 'application/json',
            'User-Agent': 'regen-worker/1.0',
          },
          body: JSON.stringify({
            ref: 'main',
            inputs: {
              client_id,
              week_of,
              ...extraInputs,
            },
          }),
        }
      );

      if (!ghResp.ok) {
        let detail = `HTTP ${ghResp.status}`;
        try {
          const ghBody = await ghResp.text();
          const parsed = JSON.parse(ghBody);
          detail = `HTTP ${ghResp.status}: ${parsed.message || ghBody}`;
        } catch {}
        console.error(`GitHub API error: ${detail}`);
        return jsonResponse(
          { error: 'Failed to trigger workflow', detail },
          502,
          allowedOrigin
        );
      }

      // GitHub returns 204 No Content on success
      return jsonResponse(
        { ok: true, message: `Workflow "${workflow}" triggered for client "${client_id}".` },
        200,
        allowedOrigin
      );
    }

    return jsonResponse({ error: 'Not found' }, 404, allowedOrigin);
  },
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function validateBody(body) {
  if (!body || typeof body !== 'object') return 'Body must be a JSON object';

  if (!body.client_id || typeof body.client_id !== 'string') {
    return 'Missing required field: client_id';
  }
  if (!/^[a-z0-9_-]+$/.test(body.client_id)) {
    return 'client_id must be lowercase letters, numbers, hyphens, or underscores only';
  }

  if (!body.week_of || typeof body.week_of !== 'string') {
    return 'Missing required field: week_of';
  }

  if (!body.workflow || !ALLOWED_WORKFLOWS.has(body.workflow)) {
    return `workflow must be one of: ${[...ALLOWED_WORKFLOWS].join(', ')}`;
  }

  for (const field of REQUIRED_INPUTS[body.workflow] || []) {
    if (!body[field] || String(body[field]).trim() === '') {
      return `Missing required field for workflow "${body.workflow}": ${field}`;
    }
  }

  return null; // valid
}

function corsHeaders(origin) {
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
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

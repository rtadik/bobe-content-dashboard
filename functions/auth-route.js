// functions/auth-route.js
// Cloudflare Pages Function: reads CF Access JWT, maps email → client_id, redirects.
// Intercepts GET /login and /login.html only. Falls through on all other paths.
// EMAIL_MAP env var: JSON string mapping email → client_id, e.g. {"user@example.com": "bobe"}
// ADMIN_EMAIL env var: comma-separated admin emails, e.g. "admin@example.com"
export async function onRequest(context) {
  const { request, env } = context;

  // Only intercept GET /login or /login.html
  const url = new URL(request.url);
  if (url.pathname !== '/login' && url.pathname !== '/login.html') {
    return context.next();
  }

  // Read CF Access JWT from cookie
  const cookieHeader = request.headers.get('Cookie') || '';
  const cfJwt = cookieHeader
    .split(';')
    .map(c => c.trim())
    .find(c => c.startsWith('CF_Authorization='))
    ?.split('=')[1];

  if (!cfJwt) {
    // No CF Access token — serve static login.html (local dev or Access not configured)
    return context.next();
  }

  // Decode JWT payload (segment 1, base64url).
  // CF Access already validated the JWT at the network layer — no signature check needed here.
  let email;
  try {
    const payload = cfJwt.split('.')[1];
    const decoded = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
    email = decoded.email;
  } catch (e) {
    return new Response('Invalid session. Please try again.', { status: 400 });
  }

  if (!email) {
    return new Response('No email in session. Contact support.', { status: 403 });
  }

  // Look up email in EMAIL_MAP env var
  let emailMap = {};
  try {
    emailMap = JSON.parse(env.EMAIL_MAP || '{}');
  } catch (e) {
    return new Response('Server configuration error.', { status: 500 });
  }

  const adminEmail = env.ADMIN_EMAIL || '';
  const adminEmails = adminEmail.split(',').map(e => e.trim()).filter(Boolean);

  // Admin routing
  if (adminEmails.includes(email)) {
    return redirectWithCookie('/admin/', email);
  }

  // Client routing
  const clientId = emailMap[email];
  if (clientId) {
    return redirectWithCookie(`/dashboard/${clientId}/`, email);
  }

  return new Response(
    `Your email (${email}) is not authorized. Contact your account manager.`,
    { status: 403, headers: { 'Content-Type': 'text/plain' } }
  );
}

function redirectWithCookie(location, email) {
  // Set a lightweight session indicator cookie.
  // dash_routed signals to dashboard JS that the user came through CF Access routing.
  // CF Access JWT is the real security gate — this cookie is just a UX signal.
  const headers = new Headers({
    Location: location,
    'Set-Cookie': `dash_routed=1; Path=/; Max-Age=28800; SameSite=Lax`,
  });
  return new Response(null, { status: 302, headers });
}

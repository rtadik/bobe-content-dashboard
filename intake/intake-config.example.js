// intake-config.js — EmailJS credentials, dashboard URL, and Cloudflare Worker URL
// Copy this file to intake-config.js and fill in your values.
// intake-config.js is gitignored and must never be committed.

window.INTAKE_CONFIG = {
  emailjs: {
    publicKey:  "YOUR_EMAILJS_PUBLIC_KEY",   // emailjs.com → Account → API Keys
    serviceId:  "YOUR_EMAILJS_SERVICE_ID",   // emailjs.com → Email Services
    templateId: "YOUR_EMAILJS_TEMPLATE_ID"   // emailjs.com → Email Templates
  },
  dashboardBaseUrl: "https://content.rejiglabs.com",
  // Login URL sent to client: {dashboardBaseUrl}/login.html
  // Dashboard URL: {dashboardBaseUrl}/dashboard/{client_id}/

  workerUrl: "https://intake-onboard-worker.YOUR_SUBDOMAIN.workers.dev"
  // Cloudflare Worker URL. After deploying with wrangler, replace with your actual URL.
  // If you set a custom domain: "https://onboard.rejiglabs.com"
  // Leave as empty string "" to disable auto-onboarding (manual /onboard-from-intake only).
};

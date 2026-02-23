// intake-config.js — EmailJS credentials and dashboard URL
// Copy this file to intake-config.js and fill in your values.
// intake-config.js is gitignored and must never be committed.

window.INTAKE_CONFIG = {
  emailjs: {
    publicKey:  "YOUR_EMAILJS_PUBLIC_KEY",   // emailjs.com → Account → API Keys
    serviceId:  "YOUR_EMAILJS_SERVICE_ID",   // emailjs.com → Email Services
    templateId: "YOUR_EMAILJS_TEMPLATE_ID"   // emailjs.com → Email Templates
  },
  dashboardBaseUrl: "https://rtadik.github.io/bobe-content-dashboard"
  // Login URL sent to client: {dashboardBaseUrl}/login.html
  // Dashboard URL: {dashboardBaseUrl}/dashboard/{client_id}/
};

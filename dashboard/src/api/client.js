/**
 * AdaptiFocus Dashboard — API Client
 */

const API_BASE = "https://adaptifocus.onrender.com";

async function fetchJSON(path) {
  const token = localStorage.getItem('adaptifocus_token');
  const headers = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const res = await fetch(`${API_BASE}${path}`, { headers });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function getFocusSummary(days = 1) {
  return fetchJSON(`/analytics/focus-summary?days=${days}`);
}

export async function getHourlyBreakdown(days = 7) {
  const tzOffset = new Date().getTimezoneOffset();
  return fetchJSON(`/analytics/hourly-breakdown?days=${days}&tz_offset=${tzOffset}`);
}

export async function getPatterns() {
  return fetchJSON("/analytics/patterns");
}

export async function getInterventionHistory(days = 7) {
  return fetchJSON(`/analytics/intervention-history?days=${days}`);
}

export async function getStreak() {
  return fetchJSON("/streaks/current");
}

export async function getDailyReport() {
  return fetchJSON("/reports/daily");
}

export async function getWeeklyReport() {
  return fetchJSON("/reports/weekly");
}

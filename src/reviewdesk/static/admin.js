const appState = {
  token: sessionStorage.getItem("reviewdesk-token") || "",
  overview: null,
  contacts: [],
  feedback: [],
  sequence: [],
  settings: null,
  activeSection: "overview",
};

const byId = (id) => document.getElementById(id);

function escapeHtml(value) {
  const node = document.createElement("div");
  node.textContent = value == null ? "" : String(value);
  return node.innerHTML;
}

function initials(name) {
  return String(name || "?").split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
}

function shortDate(value) {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric" }).format(date);
}

function timeAgo(value) {
  if (!value) return "";
  const seconds = Math.max(0, (Date.now() - new Date(value).getTime()) / 1000);
  if (seconds < 60) return "now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
  return `${Math.floor(seconds / 86400)}d`;
}

function toast(message) {
  const node = byId("toast");
  node.textContent = message;
  node.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => node.classList.remove("show"), 2600);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Token": appState.token,
      ...(options.headers || {}),
    },
  });
  if (response.status === 401) {
    if (appState.token !== "reviewdesk-demo-view") {
      sessionStorage.removeItem("reviewdesk-token");
      byId("auth-screen").hidden = false;
      byId("dashboard").hidden = true;
    }
    throw new Error(appState.token === "reviewdesk-demo-view" ? "The public demo is read-only." : "The dashboard token is incorrect.");
  }
  const data = await response.json();
  if (!response.ok) {
    const detail = Array.isArray(data.detail) ? data.detail.map((item) => item.msg).join(" ") : data.detail;
    throw new Error(detail || "The request could not be completed.");
  }
  return data;
}

async function authenticate(token) {
  appState.token = token;
  const overview = await api("/api/admin/overview");
  sessionStorage.setItem("reviewdesk-token", token);
  byId("auth-screen").hidden = true;
  byId("dashboard").hidden = false;
  appState.overview = overview;
  renderOverview(overview);
  await Promise.all([loadContacts(), loadFeedback(), loadSequence(), loadSettings()]);
}

byId("auth-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  byId("auth-error").textContent = "";
  try {
    await authenticate(byId("admin-token").value);
  } catch (error) {
    byId("auth-error").textContent = error.message;
  }
});

byId("demo-token-button").addEventListener("click", async () => {
  byId("auth-error").textContent = "";
  try {
    await authenticate("reviewdesk-demo-view");
    toast("Public demo opened in read-only mode");
  } catch (error) {
    byId("auth-error").textContent = error.message;
  }
});

const sectionCopy = {
  overview: ["COMMAND CENTER", "Reputation overview"],
  customers: ["REQUEST AUDIENCE", "Customers"],
  feedback: ["CUSTOMER VOICE", "Feedback library"],
  automation: ["REQUEST ENGINE", "Automation"],
  brand: ["WHITE-LABEL SYSTEM", "Brand and widget"],
};

function openSection(section) {
  appState.activeSection = section;
  document.querySelectorAll(".side-nav button").forEach((button) => button.classList.toggle("active", button.dataset.section === section));
  document.querySelectorAll(".admin-section").forEach((node) => node.classList.toggle("active", node.id === `section-${section}`));
  byId("section-kicker").textContent = sectionCopy[section][0];
  byId("section-title").textContent = sectionCopy[section][1];
}

document.querySelectorAll(".side-nav button").forEach((button) => button.addEventListener("click", () => openSection(button.dataset.section)));
document.querySelectorAll("[data-go]").forEach((button) => button.addEventListener("click", () => openSection(button.dataset.go)));

function renderOverview(data) {
  const m = data.metrics;
  const metrics = [
    ["REQUESTS SENT", m.requested, `${m.messages_sent} email events recorded`],
    ["OPENED", m.opened, "Customers who opened the request"],
    ["RESPONSES", m.responded, `${m.response_rate}% response rate`],
    ["PUBLIC CLICKS", m.public_clicks, "Honest-review handoffs"],
  ];
  byId("metrics-grid").innerHTML = metrics.map(([label, value, note]) => `
    <article class="metric-card"><span>${label}</span><strong>${value}</strong><small>${note}</small></article>
  `).join("");
  byId("response-rate").textContent = `${m.response_rate}% response`;
  byId("average-rating").textContent = Number(m.average_rating || 0).toFixed(1);
  const max = Math.max(1, m.contacts);
  const stages = [
    ["Added", m.contacts], ["Requested", m.requested], ["Opened", m.opened], ["Responded", m.responded],
  ];
  byId("funnel").innerHTML = stages.map(([label, value]) => `
    <div class="funnel-stage" style="--fill:${Math.round(value / max * 100)}%"><strong>${value}</strong><span>${label}</span></div>
  `).join("");
  renderRecentFeedback(data.feedback);
  byId("activity-list").innerHTML = data.events.length ? data.events.map((event) => `
    <div class="activity-row">
      <span class="activity-dot"></span>
      <div><strong>${escapeHtml(event.contact_name || "System")} · ${escapeHtml(event.event_type.replaceAll(".", " "))}</strong><small>Workflow activity recorded</small></div>
      <time>${timeAgo(event.created_at)}</time>
    </div>
  `).join("") : '<div class="empty-state">Activity will appear here.</div>';
  byId("provider-name").textContent = data.email_provider === "demo" ? "Demo provider" : "SMTP connected";
}

function renderRecentFeedback(items) {
  byId("recent-feedback").innerHTML = items.length ? items.slice(0, 5).map((item) => `
    <div class="feedback-row">
      <span class="avatar">${escapeHtml(initials(item.display_name))}</span>
      <div><strong>${escapeHtml(item.display_name)}</strong><p>${escapeHtml(item.comment)}</p></div>
      <span class="stars" aria-label="${item.rating} out of 5">${"★".repeat(item.rating)}${"☆".repeat(5 - item.rating)}</span>
    </div>
  `).join("") : '<div class="empty-state">Feedback will appear here.</div>';
}

async function refreshOverview() {
  const data = await api("/api/admin/overview");
  appState.overview = data;
  renderOverview(data);
}

byId("refresh-button").addEventListener("click", async () => {
  try { await refreshOverview(); toast("Dashboard refreshed"); } catch (error) { toast(error.message); }
});

async function loadContacts() {
  const data = await api("/api/admin/contacts");
  appState.contacts = data.items;
  renderContacts();
  byId("export-link").href = `/api/admin/export.csv`;
  byId("export-link").addEventListener("click", async (event) => {
    event.preventDefault();
    try {
      const response = await fetch("/api/admin/export.csv", { headers: { "X-Admin-Token": appState.token } });
      if (!response.ok) throw new Error("Export is unavailable in read-only demo mode.");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "reviewdesk-export.csv";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error) { toast(error.message); }
  }, { once: true });
}

function renderContacts(filter = "") {
  const value = filter.trim().toLowerCase();
  const items = appState.contacts.filter((item) => [item.name, item.email, item.service].join(" ").toLowerCase().includes(value));
  byId("customers-table").innerHTML = items.length ? items.map((item) => `
    <tr>
      <td><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.email)}</small></td>
      <td><strong>${escapeHtml(item.service || "Recent service")}</strong><small>${escapeHtml(item.service_date || "Date not supplied")}</small></td>
      <td><span class="status-badge ${escapeHtml(item.status)}">${escapeHtml(item.status)}</span></td>
      <td>${item.messages_sent}</td>
      <td>${item.rating ? `<span class="stars">${"★".repeat(item.rating)}</span>` : "Not yet"}</td>
      <td>${shortDate(item.created_at)}</td>
    </tr>
  `).join("") : '<tr><td colspan="6"><div class="empty-state">No matching customers.</div></td></tr>';
}

byId("customer-search").addEventListener("input", (event) => renderContacts(event.target.value));

async function loadFeedback() {
  const data = await api("/api/admin/feedback");
  appState.feedback = data.items;
  renderFeedback();
}

function renderFeedback() {
  byId("feedback-cards").innerHTML = appState.feedback.length ? appState.feedback.map((item) => `
    <article class="feedback-detail">
      <div class="feedback-detail-head">
        <div><span class="stars">${"★".repeat(item.rating)}${"☆".repeat(5 - item.rating)}</span><small>${shortDate(item.created_at)}</small></div>
        <button class="feature-toggle ${item.featured ? "active" : ""}" data-feature="${item.id}" data-value="${!item.featured}" ${item.testimonial_consent ? "" : "disabled"}>
          ${item.featured ? "Featured" : item.testimonial_consent ? "Feature story" : "No consent"}
        </button>
      </div>
      <blockquote>“${escapeHtml(item.comment)}”</blockquote>
      <footer><span><strong>${escapeHtml(item.display_name)}</strong> · ${escapeHtml(item.service || "Customer")}</span><span>${item.testimonial_consent ? "Permission granted" : "Private only"}</span></footer>
    </article>
  `).join("") : '<div class="empty-state">No feedback yet.</div>';
  document.querySelectorAll("[data-feature]").forEach((button) => button.addEventListener("click", async () => {
    try {
      await api(`/api/admin/feedback/${button.dataset.feature}`, { method: "PUT", body: JSON.stringify({ featured: button.dataset.value === "true" }) });
      await loadFeedback();
      toast("Testimonial wall updated");
    } catch (error) { toast(error.message); }
  }));
}

async function loadSequence() {
  const data = await api("/api/admin/sequence");
  appState.sequence = data.items;
  renderSequence();
}

function renderSequence() {
  byId("sequence-list").innerHTML = appState.sequence.map((item) => `
    <article class="sequence-card" data-sequence="${item.step}">
      <div class="sequence-number">0${item.step}</div>
      <div>
        <h3>${escapeHtml(item.name)}</h3>
        <p><strong>${escapeHtml(item.subject)}</strong><br>${escapeHtml(item.body.split("\n")[0])}</p>
        <div class="sequence-editor" hidden>
          <label><span class="field-label">Name</span><input data-field="name" value="${escapeHtml(item.name)}"></label>
          <label><span class="field-label">Subject</span><input data-field="subject" value="${escapeHtml(item.subject)}"></label>
          <label><span class="field-label">Delay in hours</span><input data-field="delay_hours" type="number" min="0" value="${item.delay_hours}"></label>
          <label><span class="field-label">Message</span><textarea data-field="body" rows="6">${escapeHtml(item.body)}</textarea></label>
          <label class="consent-row"><input data-field="enabled" type="checkbox" ${item.enabled ? "checked" : ""}><span><strong>Step enabled</strong></span></label>
        </div>
      </div>
      <div class="sequence-delay">${item.delay_hours ? `+${item.delay_hours}h` : "Immediate"}<small>${item.enabled ? "Active" : "Paused"}</small><button class="text-button edit-sequence" type="button">Edit</button></div>
    </article>
  `).join("") + '<button class="primary-button save-sequence" id="save-sequence" type="button" hidden>Save automation sequence <span>↗</span></button>';
  document.querySelectorAll(".edit-sequence").forEach((button) => button.addEventListener("click", () => {
    const editor = button.closest(".sequence-card").querySelector(".sequence-editor");
    editor.hidden = !editor.hidden;
    button.textContent = editor.hidden ? "Edit" : "Close";
    byId("save-sequence").hidden = false;
  }));
  byId("save-sequence").addEventListener("click", saveSequence);
}

async function saveSequence() {
  const items = [...document.querySelectorAll("[data-sequence]")].map((card) => ({
    step: Number(card.dataset.sequence),
    delay_hours: Number(card.querySelector('[data-field="delay_hours"]').value),
    name: card.querySelector('[data-field="name"]').value,
    subject: card.querySelector('[data-field="subject"]').value,
    body: card.querySelector('[data-field="body"]').value,
    enabled: card.querySelector('[data-field="enabled"]').checked,
  }));
  try {
    await api("/api/admin/sequence", { method: "PUT", body: JSON.stringify({ items }) });
    await loadSequence();
    toast("Automation sequence saved");
  } catch (error) { toast(error.message); }
}

byId("process-button").addEventListener("click", async () => {
  try {
    const result = await api("/api/admin/process", { method: "POST" });
    toast(`${result.processed} due requests processed`);
    await refreshOverview();
  } catch (error) { toast(error.message); }
});

const settingFields = [
  ["name", "Business name"], ["short_name", "Short name"], ["logo_text", "Logo letters"], ["tagline", "Tagline"],
  ["primary_color", "Primary color", "color"], ["accent_color", "Accent color", "color"],
  ["contact_email", "Contact email", "email"], ["sender_name", "Sender name"], ["reply_to", "Reply-to email", "email"],
  ["public_review_label", "Public review button"], ["public_review_url", "Public review URL", "url"], ["privacy_url", "Privacy URL", "url"],
  ["review_prompt", "Feedback question", "text", "full"], ["thank_you_message", "Thank-you message", "textarea", "full"],
  ["testimonial_heading", "Testimonial wall heading", "text", "full"],
];

async function loadSettings() {
  appState.settings = await api("/api/admin/settings");
  renderSettings();
}

function renderSettings() {
  byId("settings-fields").innerHTML = settingFields.map(([name, label, type = "text", className = ""]) => {
    const value = appState.settings[name] || "";
    if (type === "textarea") return `<label class="${className}"><span class="field-label">${label}</span><textarea name="${name}" rows="3">${escapeHtml(value)}</textarea></label>`;
    if (type === "color") return `<label><span class="field-label">${label}</span><div class="color-input"><input name="${name}_picker" type="color" value="${escapeHtml(value)}"><input name="${name}" value="${escapeHtml(value)}" required></div></label>`;
    return `<label class="${className}"><span class="field-label">${label}</span><input name="${name}" type="${type}" value="${escapeHtml(value)}"></label>`;
  }).join("");
  document.querySelectorAll('input[type="color"]').forEach((picker) => picker.addEventListener("input", () => {
    const target = byId("settings-form").elements[picker.name.replace("_picker", "")];
    target.value = picker.value;
  }));
  const origin = location.origin;
  byId("embed-code").value = `<script async src="${origin}/widget.js" data-height="250px"><\/script>`;
  const example = appState.feedback.find((item) => item.featured) || appState.feedback[0];
  byId("mini-widget").innerHTML = example ? `<span class="stars">${"★".repeat(example.rating)}</span><blockquote>“${escapeHtml(example.comment)}”</blockquote><small>${escapeHtml(example.display_name)}</small>` : "Approved stories will appear here.";
}

byId("settings-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const payload = {};
  settingFields.forEach(([name]) => { payload[name] = form.get(name) || ""; });
  try {
    appState.settings = await api("/api/admin/settings", { method: "PUT", body: JSON.stringify(payload) });
    byId("settings-status").textContent = "Brand settings saved.";
    toast("White-label settings saved");
  } catch (error) { byId("settings-status").textContent = error.message; }
});

byId("copy-embed").addEventListener("click", async () => {
  await navigator.clipboard.writeText(byId("embed-code").value);
  toast("Embed code copied");
});

const dialog = byId("customer-dialog");
byId("add-customer-button").addEventListener("click", () => dialog.showModal());
byId("close-dialog").addEventListener("click", () => dialog.close());
byId("cancel-dialog").addEventListener("click", () => dialog.close());

byId("customer-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const payload = {
    name: form.get("name"), email: form.get("email"), phone: "", service: form.get("service"),
    service_date: form.get("service_date"), source: "dashboard", reminders_enabled: form.get("reminders_enabled") === "on", website: "",
  };
  try {
    const result = await api("/api/admin/contacts", { method: "POST", body: JSON.stringify(payload) });
    event.target.reset();
    dialog.close();
    await Promise.all([loadContacts(), refreshOverview()]);
    toast(`Request created for ${result.contact.name}`);
  } catch (error) { byId("customer-error").textContent = error.message; }
});

function parseCsv(text) {
  const rows = [];
  let row = [], field = "", quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (char === '"' && quoted && text[index + 1] === '"') { field += '"'; index += 1; }
    else if (char === '"') quoted = !quoted;
    else if (char === "," && !quoted) { row.push(field.trim()); field = ""; }
    else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && text[index + 1] === "\n") index += 1;
      row.push(field.trim()); field = "";
      if (row.some(Boolean)) rows.push(row);
      row = [];
    } else field += char;
  }
  row.push(field.trim());
  if (row.some(Boolean)) rows.push(row);
  return rows;
}

byId("csv-file").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  try {
    const rows = parseCsv(await file.text());
    const headers = rows.shift().map((item) => item.toLowerCase().replaceAll(" ", "_"));
    const contacts = rows.map((row) => Object.fromEntries(headers.map((header, index) => [header, row[index] || ""]))).map((item) => ({
      name: item.name || item.customer_name, email: item.email, phone: item.phone || "", service: item.service || "",
      service_date: item.service_date || "", source: "csv", reminders_enabled: true, website: "",
    }));
    const result = await api("/api/admin/contacts/import", { method: "POST", body: JSON.stringify({ contacts }) });
    await Promise.all([loadContacts(), refreshOverview()]);
    toast(`${result.created} customers imported`);
  } catch (error) { toast(error.message); }
  event.target.value = "";
});

if (appState.token) {
  authenticate(appState.token).catch(() => {
    byId("auth-screen").hidden = false;
    byId("dashboard").hidden = true;
  });
}

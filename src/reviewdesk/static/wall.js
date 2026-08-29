const grid = document.getElementById("wall-grid");
const heading = document.getElementById("wall-heading");
const query = new URLSearchParams(location.search);

if (location.pathname === "/widget" || query.get("embed") === "1") {
  document.body.classList.add("embed");
}

function initials(name) {
  return name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
}

function escapeHtml(value) {
  const node = document.createElement("div");
  node.textContent = value || "";
  return node.innerHTML;
}

async function loadTestimonials() {
  try {
    const response = await fetch("/api/testimonials");
    const data = await response.json();
    document.documentElement.style.setProperty("--ink", data.primary_color);
    document.documentElement.style.setProperty("--accent", data.accent_color);
    heading.textContent = data.heading;
    document.title = `${data.heading} | ${data.business}`;
    if (!data.items.length) {
      grid.innerHTML = '<div class="empty-state">Approved customer stories will appear here.</div>';
      return;
    }
    grid.innerHTML = data.items.map((item) => `
      <article class="story-card">
        <div class="stars" aria-label="${item.rating} out of 5">${"★".repeat(item.rating)}${"☆".repeat(5 - item.rating)}</div>
        <blockquote>“${escapeHtml(item.comment)}”</blockquote>
        <footer>
          <span class="avatar">${escapeHtml(initials(item.display_name))}</span>
          <span><strong>${escapeHtml(item.display_name)}</strong><br>${escapeHtml(item.service || "Verified customer")}</span>
        </footer>
      </article>
    `).join("");
  } catch {
    grid.innerHTML = '<div class="empty-state">Customer stories are temporarily unavailable.</div>';
  }
}

loadTestimonials();


const state = {
  rating: 0,
  token: location.pathname.startsWith("/r/") ? location.pathname.split("/")[2] : "",
  demo: !location.pathname.startsWith("/r/"),
};

const el = (id) => document.getElementById(id);

function applyBrand(brand) {
  document.documentElement.style.setProperty("--ink", brand.primary_color);
  document.documentElement.style.setProperty("--accent", brand.accent_color);
  el("brand-mark").textContent = brand.logo_text;
  el("brand-name").textContent = brand.name;
  el("brand-tagline").textContent = brand.tagline;
  el("review-heading").textContent = brand.review_prompt;
  document.title = `Share your experience | ${brand.name}`;
  if (brand.privacy_url) {
    el("privacy-wrap").hidden = false;
    el("privacy-link").href = brand.privacy_url;
  }
}

function humanDate(value) {
  if (!value) return "Recently completed";
  const date = new Date(`${value}T12:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en", { month: "long", day: "numeric", year: "numeric" }).format(date);
}

async function loadContext() {
  try {
    if (state.demo) {
      const response = await fetch("/api/public/config");
      const brand = await response.json();
      applyBrand(brand);
      return;
    }
    const response = await fetch(`/api/review/${encodeURIComponent(state.token)}`);
    if (!response.ok) throw new Error("This feedback request is no longer available.");
    const data = await response.json();
    applyBrand(data.business);
    el("customer-name").textContent = data.name.split(" ")[0];
    el("display-name").value = data.name;
    el("service-name").textContent = data.service || "Recent service";
    el("service-date").textContent = humanDate(data.service_date);
    el("demo-ribbon").hidden = true;
    el("reset-demo").hidden = true;
    if (data.responded) {
      showAlreadyReceived(data.business);
    }
  } catch (error) {
    el("form-error").textContent = error.message;
    el("submit-button").disabled = true;
  }
}

function showAlreadyReceived(brand) {
  el("feedback-form-view").hidden = true;
  el("success-view").hidden = false;
  el("thank-you-message").textContent = brand.thank_you_message;
  el("public-review-button").textContent = brand.public_review_label;
  el("public-review-button").href = `/r/${encodeURIComponent(state.token)}/public`;
}

document.querySelectorAll("[data-rating]").forEach((button) => {
  button.addEventListener("click", () => {
    state.rating = Number(button.dataset.rating);
    document.querySelectorAll("[data-rating]").forEach((item) => {
      item.classList.toggle("selected", Number(item.dataset.rating) <= state.rating);
      item.setAttribute("aria-pressed", Number(item.dataset.rating) === state.rating ? "true" : "false");
    });
    el("form-error").textContent = "";
  });
});

el("comment").addEventListener("input", (event) => {
  el("char-count").textContent = `${event.target.value.length} / 2000`;
});

el("feedback-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const error = el("form-error");
  if (!state.rating) {
    error.textContent = "Please choose a rating from 1 to 5.";
    return;
  }
  const button = el("submit-button");
  button.disabled = true;
  button.firstChild.textContent = "Sending feedback ";
  error.textContent = "";
  const endpoint = state.demo
    ? "/api/demo-feedback"
    : `/api/review/${encodeURIComponent(state.token)}/feedback`;
  const payload = {
    rating: state.rating,
    comment: el("comment").value,
    display_name: el("display-name").value,
    testimonial_consent: el("testimonial-consent").checked,
    website: document.querySelector('[name="website"]').value,
  };
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Feedback could not be submitted.");
    el("feedback-form-view").hidden = true;
    el("success-view").hidden = false;
    el("thank-you-message").textContent = data.message;
    el("public-review-button").href = data.public_review_url;
    el("public-review-button").firstChild.textContent = `${data.public_review_label} `;
    el("success-view").focus();
  } catch (submitError) {
    error.textContent = submitError.message;
    button.disabled = false;
    button.firstChild.textContent = "Send private feedback ";
  }
});

el("reset-demo").addEventListener("click", () => {
  state.rating = 0;
  el("feedback-form").reset();
  el("display-name").value = "Jordan Blake";
  el("char-count").textContent = "0 / 2000";
  document.querySelectorAll("[data-rating]").forEach((item) => item.classList.remove("selected"));
  el("success-view").hidden = true;
  el("feedback-form-view").hidden = false;
  const button = el("submit-button");
  button.disabled = false;
  button.firstChild.textContent = "Send private feedback ";
});

loadContext();


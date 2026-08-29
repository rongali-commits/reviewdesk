(() => {
  const script = document.currentScript;
  if (!script || script.dataset.reviewdeskLoaded) return;
  script.dataset.reviewdeskLoaded = "true";
  const base = new URL(script.src).origin;
  const frame = document.createElement("iframe");
  frame.src = `${base}/widget?embed=1`;
  frame.title = "Customer testimonials";
  frame.loading = "lazy";
  frame.style.width = "100%";
  frame.style.height = script.dataset.height || "250px";
  frame.style.border = "0";
  frame.style.display = "block";
  frame.style.background = "transparent";
  frame.setAttribute("referrerpolicy", "strict-origin-when-cross-origin");
  script.insertAdjacentElement("afterend", frame);
})();

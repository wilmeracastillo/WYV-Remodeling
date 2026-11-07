const menuToggle = document.querySelector(".menu-toggle");
const navigation = document.querySelector("#primary-navigation");
const navigationLinks = navigation.querySelectorAll("a");
const requestDialog = document.querySelector("#request-dialog");
const requestForm = document.querySelector("#request-form");
const requestStatus = document.querySelector("#request-status");
let requestTrigger;

function setMenuOpen(isOpen) {
  menuToggle.setAttribute("aria-expanded", String(isOpen));
  menuToggle.querySelector(".visually-hidden").textContent = isOpen
    ? "Close navigation"
    : "Open navigation";
  navigation.classList.toggle("is-open", isOpen);
}

menuToggle.addEventListener("click", () => {
  setMenuOpen(menuToggle.getAttribute("aria-expanded") !== "true");
});

navigationLinks.forEach((link) => {
  link.addEventListener("click", () => setMenuOpen(false));
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && menuToggle.getAttribute("aria-expanded") === "true") {
    setMenuOpen(false);
    menuToggle.focus();
  }
});

document.querySelectorAll(".filter-button").forEach((button) => {
  button.addEventListener("click", () => {
    const filter = button.dataset.filter;

    document.querySelectorAll(".filter-button").forEach((filterButton) => {
      const isActive = filterButton === button;
      filterButton.classList.toggle("is-active", isActive);
      filterButton.setAttribute("aria-pressed", String(isActive));
    });

    document.querySelectorAll(".project-card").forEach((card) => {
      card.hidden = filter !== "all" && card.dataset.category !== filter;
    });
  });
});

document.querySelectorAll("[data-open-request]").forEach((link) => {
  link.addEventListener("click", (event) => {
    event.preventDefault();
    requestTrigger = link;
    requestStatus.textContent = "";
    requestDialog.showModal();
    requestDialog.querySelector("#request-name").focus();
  });
});

requestDialog.querySelector(".dialog-close").addEventListener("click", () => {
  requestDialog.close();
});

requestDialog.addEventListener("click", (event) => {
  if (event.target === requestDialog) {
    requestDialog.close();
  }
});

requestDialog.addEventListener("close", () => {
  requestTrigger?.focus();
});

requestForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!requestForm.reportValidity()) {
    return;
  }

  const submitButton = requestForm.querySelector('button[type="submit"]');
  submitButton.disabled = true;
  requestStatus.textContent = "Sending your request…";

  try {
    const response = await fetch("/api/lead", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Object.fromEntries(new FormData(requestForm))),
    });

    if (!response.ok) {
      const result = await response.json().catch(() => ({}));
      throw new Error(result.error || "We couldn't send your request. Please try again or call us.");
    }

    requestForm.reset();
    requestStatus.textContent = "Thanks! Your request has been sent to W.Y.V. We'll be in touch soon.";
  } catch (error) {
    requestStatus.textContent = error.message || "We couldn't send your request. Please try again or call us.";
  } finally {
    submitButton.disabled = false;
  }
});

document.querySelector("#current-year").textContent = String(new Date().getFullYear());

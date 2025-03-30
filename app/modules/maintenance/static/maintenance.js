document.addEventListener("DOMContentLoaded", function () {
  const overlay = document.getElementById("goodbye-overlay");
  const content = document.getElementById("goodbye-content");

  // Show overlay immediately
  overlay.style.display = "flex";

  // Close when clicking on overlay background
  overlay.addEventListener("click", function (e) {
    if (e.target === overlay) {
      overlay.style.display = "none";
    }
  });

  // Also close on Escape key
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      overlay.style.display = "none";
    }
  });
});

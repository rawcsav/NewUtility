function getCsrfToken() {
  return document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute("content");
}

document
  .getElementById("signup-form")
  .addEventListener("submit", function (event) {
    event.preventDefault();

    if (document.getElementById("middle-name").value) {
      console.error("Bot submission detected.");
      return;
    }

    var formData = new FormData(this);

    fetch("/auth/signup", {
      method: "POST",
      headers: {
        "X-CSRFToken": getCsrfToken(),
      },
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.status === "success") {
          window.location.href = data.redirect;
        } else if (data.status === "error") {
          var messageContainer = document.getElementById("message-container");
          messageContainer.innerHTML = data.message;
        } else {
          document.getElementById("message-container").innerText = data.message;
        }
      })
      .catch((error) => {
        console.error("Error:", error);
        document.getElementById("message-container").innerText =
          "An error occurred while trying to log in.";
      });
  });

// This code would go in the global scope so that it runs on every page load
window.addEventListener("load", () => {
  const elementsToAnimateIn = document.querySelectorAll(".animatable");
  elementsToAnimateIn.forEach((el) => {
    el.classList.add("slide-in");
  });
});

// Add event listeners to links for the "slide out" animations
document.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", (e) => {
    e.preventDefault();
    const href = link.href;
    const elementsToAnimateOut = document.querySelectorAll(".animatable");
    elementsToAnimateOut.forEach((el) => {
      el.classList.add("slide-out");
    });

    // Delay the navigation until after the animations have time to play
    setTimeout(() => {
      window.location.href = href;
    }, 500); // 500ms for the animation to complete
  });
});

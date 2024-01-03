function getCsrfToken() {
  return document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute("content");
}

document
  .getElementById("confirm-email-form")
  .addEventListener("submit", function (event) {
    event.preventDefault();

    if (document.getElementById("middle-name").value) {
      console.error("Bot submission detected.");
      return;
    }

    var formData = new FormData(this);

    fetch("/auth/confirm_email", {
      method: "POST",
      headers: {
        "X-CSRFToken": getCsrfToken(),
      },
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        var messageContainer = document.getElementById("message-container");
        if (data.status === "success") {
          messageContainer.innerText = data.message;
          messageContainer.classList.add("success");

          setTimeout(function () {
            window.location.href = data.redirect;
          }, 5000);
        } else {
          messageContainer.innerText = data.message;
          messageContainer.classList.add("error");
        }
      })
      .catch((error) => {
        console.error("Error:", error);
        document.getElementById("message-container").innerText =
          "An error occurred while trying to confirm your email.";
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

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

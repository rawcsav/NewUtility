function getCsrfToken() {
  return document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute("content");
}

document
  .getElementById("login-form")
  .addEventListener("submit", function (event) {
    event.preventDefault();
    if (document.getElementById("middle-name").value) {
      console.error("Bot submission detected.");
      return;
    }

    var formData = new FormData(this);
    var remember = document.getElementById("remember").checked;
    formData.set("remember", remember ? "true" : "false");

    fetch("/auth/login", {
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
        } else if (data.status === "unconfirmed") {
          document.getElementById("message-container").innerHTML =
            `<p>Please confirm your email. <a href="${data.redirect}">Click here to confirm</a></p>`;
        } else if (data.status === "error") {
          var messageContainer = document.getElementById("message-container");
          if (data.errors) {
            var errorMessages = Object.values(data.errors).flat().join("<br>");
            messageContainer.innerHTML = errorMessages;
          } else {
            messageContainer.textContent = data.message;
          }
        } else {
          document.getElementById("message-container").textContent =
            data.message;
        }
      })
      .catch((error) => {
        console.error("Error:", error);
        document.getElementById("message-container").innerText =
          "An error occurred while trying to log in.";
      });
  });

function getCsrfToken() {
  return document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute("content");
}

document.addEventListener("DOMContentLoaded", function () {
  var passwordResetRequestForm = document.getElementById(
    "password-reset-request-form",
  );
  var passwordResetForm = document.getElementById("password-reset-form");

  if (passwordResetRequestForm) {
    passwordResetRequestForm.addEventListener("submit", function (event) {
      event.preventDefault();
      submitFormWithRecaptcha(
        passwordResetRequestForm,
        "password-reset-request-message",
      );
    });
  }

  if (passwordResetForm) {
    passwordResetForm.addEventListener("submit", function (event) {
      event.preventDefault();
      submitFormWithRecaptcha(
        passwordResetForm,
        "password-reset-message",
        true,
      );
    });
  }

  function submitFormWithRecaptcha(form, messageContainerId, shouldRedirect) {
    if (document.getElementById("middle-name").value) {
      console.error("Bot submission detected.");
      return;
    }

    var formData = new FormData(this);

    fetch(form.action, {
      method: form.method,
      headers: {
        "X-CSRFToken": getCsrfToken(),
      },
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => handleResponse(data, messageContainerId, shouldRedirect))
      .catch((error) => handleError(error, messageContainerId));
  }

  function handleResponse(data, messageContainerId, shouldRedirect) {
    var messageContainer = document.getElementById(messageContainerId);
    messageContainer.textContent = data.message;
    messageContainer.classList.remove("success", "error");
    messageContainer.classList.add(
      data.status === "success" ? "success" : "error",
    );

    if (data.status === "success" && shouldRedirect) {
      setTimeout(function () {
        window.location.href = data.redirect;
      }, 3000);
    }
  }
  function handleError(error, messageContainerId) {
    var messageContainer = document.getElementById(messageContainerId);
    messageContainer.textContent = "An error occurred: " + error;
    messageContainer.classList.remove("success");
    messageContainer.classList.add("error");
  }
});

document.addEventListener("DOMContentLoaded", function () {
  var passwordResetRequestForm = document.getElementById(
    "password-reset-request-form"
  );
  var passwordResetForm = document.getElementById("password-reset-form");

  if (passwordResetRequestForm) {
    passwordResetRequestForm.addEventListener("submit", function (event) {
      event.preventDefault();
      submitFormWithRecaptcha(
        passwordResetRequestForm,
        "password-reset-request-message"
      );
    });
  }

  if (passwordResetForm) {
    passwordResetForm.addEventListener("submit", function (event) {
      event.preventDefault();
      submitFormWithRecaptcha(
        passwordResetForm,
        "password-reset-message",
        true
      );
    });
  }

  function submitFormWithRecaptcha(form, messageContainerId, shouldRedirect) {
    grecaptcha.ready(function () {
      grecaptcha
        .execute("6LfilA0pAAAAAGjtNjRkGcgJqCNKTjs9xoPRNTme", {
          action: "submit"
        })
        .then(function (captcha_token) {
          var formData = new FormData(form);
          formData.append("g-recaptcha-response", captcha_token);

          fetch(form.action, {
            method: form.method,
            body: formData
          })
            .then((response) => response.json())
            .then((data) =>
              handleResponse(data, messageContainerId, shouldRedirect)
            )
            .catch((error) => handleError(error, messageContainerId));
        });
    });
  }

  function handleResponse(data, messageContainerId, shouldRedirect) {
    var messageContainer = document.getElementById(messageContainerId);
    messageContainer.textContent = data.message;
    messageContainer.classList.remove("success", "error");
    messageContainer.classList.add(
      data.status === "success" ? "success" : "error"
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

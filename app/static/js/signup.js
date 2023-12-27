function getCsrfToken() {
  return document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute("content");
}

document
  .getElementById("signup-form")
  .addEventListener("submit", function (event) {
    event.preventDefault();

    var formData = new FormData(this);
    grecaptcha.ready(function () {
      grecaptcha
        .execute("6LfilA0pAAAAAGjtNjRkGcgJqCNKTjs9xoPRNTme", {
          action: "signup",
        })
        .then(function (token) {
          formData.append("g-recaptcha-response", token);

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
                var messageContainer =
                  document.getElementById("message-container");
                messageContainer.innerHTML = data.message;
              } else {
                document.getElementById("message-container").innerText =
                  data.message;
              }
            })
            .catch((error) => {
              console.error("Error:", error);
              document.getElementById("message-container").innerText =
                "An error occurred while trying to log in.";
            });
        });
    });
  });

var googleLoginButton = document.querySelector("#google-login-button");
if (googleLoginButton) {
  googleLoginButton.addEventListener("click", function () {
    window.location.href = "{{ url_for('auth.google_login') }}";
  });
}

var githubLoginButton = document.querySelector("#github-login-button");
if (githubLoginButton) {
  githubLoginButton.addEventListener("click", function () {
    window.location.href = "{{ url_for('auth.github_login') }}";
  });
}

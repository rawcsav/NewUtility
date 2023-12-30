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
    console.log("Remember Me value:", remember.toString());

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
            `Please confirm your email. <a href="${data.redirect}">Click here to confirm</a>`;
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

var googleLoginButton = document.getElementById("google-login-button");
var githubLoginButton = document.getElementById("github-login-button");

if (googleLoginButton) {
  googleLoginButton.addEventListener("click", function () {
    window.location.href = "{{ url_for('auth.google_login') }}";
  });
}

if (githubLoginButton) {
  githubLoginButton.addEventListener("click", function () {
    window.location.href = "{{ url_for('auth.github_login') }}";
  });
}

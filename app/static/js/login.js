document
  .getElementById("login-form")
  .addEventListener("submit", function (event) {
    event.preventDefault(); // Prevent the default form submission

    // Create FormData object from the form
    var formData = new FormData(this);
    var remember = document.getElementById("remember").checked;
    formData.set("remember", remember ? "true" : "false");
    console.log("Remember Me value:", remember.toString()); // Should log "true" or "false"

    grecaptcha.ready(function () {
      grecaptcha
        .execute("6LfilA0pAAAAAGjtNjRkGcgJqCNKTjs9xoPRNTme", {
          action: "login"
        })
        .then(function (token) {
          // Add the reCAPTCHA token to the form data
          formData.append("g-recaptcha-response", token);

          // Perform the login request using Fetch API
          fetch("/auth/login", {
            method: "POST",
            body: formData // Send the FormData object
          })
            .then((response) => response.json())
            .then((data) => {
              if (data.status === "success") {
                // Redirect to the user's dashboard on success
                window.location.href = data.redirect;
              } else if (data.status === "unconfirmed") {
                // Update the message container with the confirmation prompt
                document.getElementById(
                  "message-container"
                ).innerHTML = `Please confirm your email. <a href="${data.redirect}">Click here to confirm</a>`;
              } else {
                // Show error message for any other status
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

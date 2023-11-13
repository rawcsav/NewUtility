document.getElementById("login-form").onsubmit = function (event) {
  event.preventDefault();
  var login_credential = document.getElementById("login_credential").value;
  var password = document.getElementById("password").value;

  // Perform the login request using Fetch API
  fetch("/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      login_credential: login_credential,
      password: password
    })
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
        document.getElementById("message-container").innerText = data.message;
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      document.getElementById("message-container").innerText =
        "An error occurred while trying to log in.";
    });
};

document
  .getElementById("signup-form")
  .addEventListener("submit", function (event) {
    event.preventDefault(); // Prevent the default form submission

    var formData = new FormData(this);
    grecaptcha.ready(function () {
      grecaptcha
        .execute("6LfilA0pAAAAAGjtNjRkGcgJqCNKTjs9xoPRNTme", {
          action: "signup"
        })
        .then(function (token) {
          // Add the reCAPTCHA token to the form data
          formData.append("g-recaptcha-response", token);

          // Perform an AJAX request to the server
          fetch("/auth/signup", {
            method: "POST",
            body: formData
          })
            .then((response) => response.json())
            .then((data) => {
              if (data.status === "success") {
                // Redirect to the user's dashboard on success
                window.location.href = data.redirect;
              } else if (data.status === "error") {
                // Handle the response data
                var messageContainer =
                  document.getElementById("message-container");
                messageContainer.innerHTML = data.message;
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

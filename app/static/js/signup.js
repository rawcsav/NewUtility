document
  .getElementById("signup-form")
  .addEventListener("submit", function (event) {
    event.preventDefault();

    var formData = new FormData(this);
    grecaptcha.ready(function () {
      grecaptcha
        .execute("6LfilA0pAAAAAGjtNjRkGcgJqCNKTjs9xoPRNTme", {
          action: "signup"
        })
        .then(function (token) {
          formData.append("g-recaptcha-response", token);

          fetch("/auth/signup", {
            method: "POST",
            body: formData
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

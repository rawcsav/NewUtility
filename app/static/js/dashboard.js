function updateApiKeyMessages(message, status) {
  var messageDiv = document.getElementById("api-key-messages");
  messageDiv.textContent = message;
  messageDiv.className = status;
}

document
  .getElementById("username-change-form")
  .addEventListener("submit", function (event) {
    event.preventDefault();
    var formData = new FormData(this);

    fetch("/user/change_username", {
      method: "POST",
      headers: {
        "X-CSRFToken": formData.get("csrf_token")
      },
      body: formData
    })
      .then((response) => response.json())
      .then((data) => {
        document.getElementById("username-change-message").textContent =
          data.message;
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  });

document
  .getElementById("api-key-form")
  .addEventListener("submit", function (e) {
    e.preventDefault();
    var formData = new FormData(this);
    var form = this;

    fetch("/user/upload_api_key", {
      method: "POST",
      headers: {
        "X-CSRFToken": formData.get("csrf_token")
      },
      body: formData
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.status === "success") {
          updateApiKeyMessages(data.message, "success");
          form.reset();
        } else {
          updateApiKeyMessages(data.message, "error");
        }
      })
      .catch((error) => {
        updateApiKeyMessages("Error: " + error, "error");
      });
  });

$("#toggleFormButton").on("click", function () {
  $("#api-key-form").slideToggle();
  $(this).toggleClass("active");
});

$("#toggleUserButton").on("click", function () {
  $("#username-change-form").slideToggle();
  $(this).toggleClass("active");
});
document
  .querySelectorAll(
    ".retest-api-key-form, .delete-api-key-form, .select-api-key-form"
  )
  .forEach((form) => {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var formData = new FormData(this);
      var actionUrl = form.action;

      fetch(actionUrl, {
        method: "POST",
        body: formData
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.status === "success") {
            updateApiKeyMessages(data.message, "success");
          } else {
            updateApiKeyMessages(data.message, "error");
          }
        })
        .catch((error) => {
          console.error("Error:", error);
          alert("Error processing the request.");
        });
    });
  });

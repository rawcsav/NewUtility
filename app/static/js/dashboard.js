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

// Define a function to start spinning the refresh icon
function startSpinningIcon(form) {
  const submitButton = form.querySelector(".retest-key-button i");
  if (submitButton) {
    submitButton.classList.add("spinning");
  }
}

// Define a function to stop spinning the refresh icon
function stopSpinningIcon(form) {
  const submitButton = form.querySelector(".retest-key-button i");
  if (submitButton) {
    submitButton.classList.remove("spinning");
  }
}

document.querySelectorAll(".retest-api-key-form").forEach((form) => {
  form.addEventListener("submit", function (event) {
    event.preventDefault();

    // Start the spinning effect on the refresh button
    var refreshButton = form.querySelector(".retest-key-button i.fa-sync-alt");
    if (refreshButton) {
      refreshButton.classList.add("spinning");
    }

    var formData = new FormData(form);
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
        updateApiKeyMessages(
          "An error occurred while processing your request.",
          "error"
        );
      })
      .finally(() => {
        // Stop the spinning effect on the refresh button
        if (refreshButton) {
          refreshButton.classList.remove("spinning");
        }
      });
  });
});

document
  .querySelectorAll(".delete-api-key-form, .select-api-key-form")
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

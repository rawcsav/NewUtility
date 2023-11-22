// Function to handle the display of API key related messages
function updateApiKeyMessages(message, status) {
  var messageDiv = document.getElementById("api-key-messages");
  messageDiv.textContent = message; // Set the message text
  messageDiv.className = status; // Set the class for styling based on status
}

document
  .getElementById("username-change-form")
  .addEventListener("submit", function (event) {
    event.preventDefault();
    var formData = new FormData(this);

    // Add the CSRF token to your request headers
    fetch("/user/change_username", {
      method: "POST",
      headers: {
        "X-CSRFToken": formData.get("csrf_token") // Assuming you're using the default header name for CSRF
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
    var form = this; // Save reference to the form

    fetch("/user/upload_api_key", {
      method: "POST",
      headers: {
        "X-CSRFToken": formData.get("csrf_token") // Include the CSRF token in the request headers
        // If you're sending JSON instead, you'll need to set 'Content-Type': 'application/json'
        // and convert formData to JSON.
      },
      body: formData
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.status === "success") {
          // Display success message and clear the form
          updateApiKeyMessages(data.message, "success");
          form.reset();
        } else {
          // Display error message
          updateApiKeyMessages(data.message, "error");
        }
      })
      .catch((error) => {
        updateApiKeyMessages("Error: " + error, "error");
      });
  });

$("#toggleFormButton").on("click", function () {
  $("#api-key-form").slideToggle(); // Toggle the visibility of the form
  $(this).toggleClass("active"); // Toggle the active class on the button
});

$("#toggleUserButton").on("click", function () {
  $("#username-change-form").slideToggle(); // Toggle the visibility of the form
  $(this).toggleClass("active"); // Toggle the active class on the button
});
document
  .querySelectorAll(
    ".retest-api-key-form, .delete-api-key-form, .select-api-key-form"
  )
  .forEach((form) => {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var formData = new FormData(this);
      var actionUrl = form.action; // URL from the form's action attribute

      fetch(actionUrl, {
        method: "POST",
        body: formData // CSRF token and key_id are included automatically
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.status === "success") {
            // Display success message
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

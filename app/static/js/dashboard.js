document
  .getElementById("username-change-form")
  .addEventListener("submit", function (event) {
    event.preventDefault();
    var formData = new FormData(this);
    fetch("/user/change_username", {
      method: "POST",
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

$(document).ready(function () {
  // Form submission handler
  $("#api-keys-form").on("submit", function (e) {
    e.preventDefault(); // Prevent default form submission
    var formData = new FormData(this);

    $.ajax({
      url: "/user/upload_api_keys",
      type: "POST",
      data: formData,
      contentType: false,
      processData: false,
      success: function (response) {
        // Update the page with the response
        $("#upload-status").text(response.message);
        // Clear the form if needed
      },
      error: function (xhr, status, error) {
        // Handle errors
        $("#upload-status").text("Error: " + xhr.responseJSON.message);
      }
    });
  });
});

function checkProgress() {
  $.ajax({
    url: "/user/progress",
    type: "GET",
    success: function (response) {
      $("#progress-bar").width(response.progress + "%");
      $("#progress-text").text(response.progress + "% completed");

      if (parseFloat(response.progress) < 100) {
        setTimeout(checkProgress, 1000); // Poll every second
      } else {
        $("#progress-text").text("Update complete!");
      }
    },
    error: function (xhr, status, error) {
      $("#progress-text").text("Error checking progress.");
    }
  });
}

$("#start-update-button").on("click", function () {
  // Start the update process
  $.ajax({
    url: "/user/update_models",
    type: "GET",
    success: function (response) {
      $("#progress-text").text("Update started...");
      // Start checking for progress
      checkProgress();
    },
    error: function (xhr, status, error) {
      $("#progress-text").text("Error starting update: " + error);
    }
  });
});

document
  .getElementById("test-api-keys-button")
  .addEventListener("click", function () {
    // Start the test process
    fetch("/user/test_api_keys", {
      method: "GET"
    })
      .then((response) => response.json())
      .then((data) => {
        // Update the page with the response
        document.getElementById("test-api-keys-result").textContent =
          data.message;
      })
      .catch((error) => {
        // Handle errors
        document.getElementById("test-api-keys-result").textContent =
          "Error: " + error;
      });
  });
s;

function updateUploadMessages(message, status) {
  var messageDiv = document.getElementById("uploadStatus");
  messageDiv.textContent = message;
  messageDiv.className = status;
}

document.addEventListener("DOMContentLoaded", function () {
  var form = document.getElementById("uploadForm");
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var formData = new FormData(form);

    // Show an in-progress message
    updateUploadMessages("Uploading and processing...", "info");

    fetch(form.action, {
      method: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": formData.get("csrf_token")
      },
      body: formData
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error("Server returned an error response");
        }
        return response.json();
      })
      .then((data) => {
        if (data.error) {
          console.error("Server error:", data.error);
          updateUploadMessages(data.error, "error");
        } else {
          form.reset(); // Reset the form after successful upload
          updateUploadMessages(
            "File uploaded and processed successfully!",
            "success"
          );
        }
      })
      .catch((error) => {
        console.error("Error:", error);
        updateUploadMessages("Error: " + error.message, "error");
      });
  });
});

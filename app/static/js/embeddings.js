function updateUploadMessages(message, status) {
  var messageDiv = document.getElementById("uploadStatus");
  // Replace newline characters with <br> tags for HTML
  var formattedMessage = message.replace(/\n/g, "<br>");
  messageDiv.innerHTML = formattedMessage; // Use innerHTML to render <br> tags
  messageDiv.className = status;
}

function enableEditing(editButton) {
  // Find the closest parent list item and then the form within it
  var listItem = editButton.closest("li");
  var form = listItem.querySelector("form.edit-document-form");
  var inputs = form.querySelectorAll(".editable");

  inputs.forEach(function (input) {
    input.removeAttribute("readonly");
  });
  inputs[0].focus();

  // Update button display properties
  editButton.style.display = "none";
  var saveButton = listItem.querySelector(".save-btn");
  saveButton.style.display = "inline-block";

  inputs.forEach(function (input) {
    input.addEventListener("keypress", function (event) {
      if (event.key === "Enter") {
        event.preventDefault();
        saveButton.click();
      }
    });
  });
}

document.addEventListener("DOMContentLoaded", function () {
  var uploadForm = document.getElementById("uploadForm");

  if (uploadForm) {
    uploadForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var formData = new FormData(uploadForm);

      // Show an in-progress message
      updateUploadMessages("Uploading and processing...", "info");

      fetch(uploadForm.action, {
        method: "POST",
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
            uploadForm.reset(); // Reset the form after successful upload
            updateUploadMessages(
              "File uploaded and processed successfully!\nPlease refresh to see changes",
              "success"
            );
          }
        })
        .catch((error) => {
          console.error("Error:", error);
          updateUploadMessages("Error: " + error.message, "error");
        });
    });
  }
  var saveButtons = document.querySelectorAll(".save-btn");

  saveButtons.forEach(function (saveButton) {
    document.addEventListener("click", function (event) {
      if (
        event.target.matches(".save-btn") ||
        event.target.closest(".save-btn")
      ) {
        var saveButton = event.target;
        var listItem = saveButton.closest("li");
        var form = listItem.querySelector("form.edit-document-form");

        if (form) {
          event.preventDefault(); // Prevent default form submission
          var formData = new FormData(form);

          fetch(form.action, {
            method: "POST",
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
                alert("Error updating document: " + data.error);
              } else {
                updateUploadMessages(
                  "Document details updated successfully!",
                  "success"
                );
                // Hide the save button and set inputs back to read-only
                saveButton.style.display = "none";
                listItem.querySelector(".edit-btn").style.display =
                  "inline-block"; // Re-show the edit button

                Array.from(listItem.querySelectorAll(".editable")).forEach(
                  (input) => {
                    input.setAttribute("readonly", "readonly");
                  }
                );
              }
            })
            .catch((error) => {
              alert("An error occurred: " + error);
              updateUploadMessages(
                "Error updating document: " + error.message,
                "error"
              );
            });
        }
      }
    });
  });
  document.addEventListener("click", function (event) {
    if (
      event.target.classList.contains("delete-btn") ||
      event.target.closest(".delete-btn")
    ) {
      // If the clicked element is not the button itself but an icon inside it, find the button
      var deleteButton = event.target.classList.contains("delete-btn")
        ? event.target
        : event.target.closest(".delete-btn");
      var documentId = deleteButton.dataset.docId;
      var csrfToken = deleteButton.dataset.csrfToken;

      if (confirm("Are you sure you want to delete this document?")) {
        fetch(`/embeddings/delete/${documentId}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json", // Assuming the server expects JSON
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRF-Token": csrfToken
          },
          body: JSON.stringify({ document_id: documentId }) // Send the document ID in the request body if needed
        })
          .then((response) => {
            if (!response.ok) {
              throw new Error("Server returned an error response");
            }
            return response.json();
          })
          .then((data) => {
            if (data.error) {
              alert("Error deleting document: " + data.error);
            } else {
              updateUploadMessages("Document deleted successfully!", "success");
              // Remove the document from the DOM
              var listItem = deleteButton.closest("li");
              if (listItem) {
                listItem.remove();
              }
            }
          })
          .catch((error) => {
            alert("An error occurred: " + error);
            updateUploadMessages(
              "Error deleting document: " + error.message,
              "error"
            );
          });
      }
    }
  });
});

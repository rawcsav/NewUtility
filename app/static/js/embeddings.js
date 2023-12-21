function updateUploadMessages(message, status) {
  var messageDiv = document.getElementById("uploadStatus");
  var formattedMessage = message.replace(/\n/g, "<br>");
  messageDiv.innerHTML = formattedMessage;
  messageDiv.className = status;
}

function getCsrfToken() {
  return document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute("content");
}

function enableEditing(editButton) {
  var listItem = editButton.closest("li");
  var form = listItem.querySelector("form.edit-document-form");
  var inputs = form.querySelectorAll(".editable");

  inputs.forEach(function (input) {
    input.removeAttribute("readonly");
    if (input.name === "author" && input.value.startsWith("Author: ")) {
      input.value = input.value.substring("Author: ".length);
    }
  });

  inputs[0].focus();
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
  var fileInput = document.getElementById("file");
  var fileNameDisplay = document.getElementById("file-name-display");
  var filesToUpload = [];
  var currentFileIndex = 0;

  fileInput.addEventListener("change", function () {
    filesToUpload = Array.from(fileInput.files);
    if (filesToUpload.length > 0) {
      fileNameDisplay.textContent =
        "Selected document: " + filesToUpload[0].name;
      // Display first file information and wait for user action
      currentFileIndex = 0; // Start with the first file
    }
  });

  if (uploadForm) {
    uploadForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var file = filesToUpload[currentFileIndex];

      var formData = new FormData(uploadForm);
      formData.set("file", file); // Set the current file in the FormData
      fetch(uploadForm.action, {
        method: "POST",
        headers: {
          "X-CSRF-Token": getCsrfToken()
        },
        body: formData
      })
        .then(function (response) {
          if (!response.ok) {
            throw new Error(
              "Server returned an error response for " + file.name
            );
          }
          return response.json();
        })
        .then(function (data) {
          if (data.error) {
            updateUploadMessages(data.error, "error");
          } else {
            updateUploadMessages(
              file.name + " uploaded successfully!",
              "success"
            );
            if (currentFileIndex < filesToUpload.length) {
              // Update display with the next file name
              fileNameDisplay.textContent =
                "Selected document: " + filesToUpload[currentFileIndex].name;
            } else {
              fileNameDisplay.textContent = "All files have been uploaded.";
              fileInput.value = ""; // Optionally clear the file input
            }
          }
        })
        .catch(function (error) {
          updateUploadMessages("Error: " + error.message, "error");
        });
      currentFileIndex++;
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
          event.preventDefault();
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
                saveButton.style.display = "none";
                listItem.querySelector(".edit-btn").style.display =
                  "inline-block";
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
      var deleteButton = event.target.classList.contains("delete-btn")
        ? event.target
        : event.target.closest(".delete-btn");
      var documentId = deleteButton.dataset.docId;
      var csrfToken = deleteButton.dataset.csrfToken;

      if (confirm("Are you sure you want to delete this document?")) {
        fetch(`/embeddings/delete/${documentId}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRF-Token": csrfToken
          },
          body: JSON.stringify({ document_id: documentId })
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

var fileInput = document.getElementById("file");
var fileNameDisplay = document.getElementById("file-name-display");

fileInput.addEventListener("change", function () {
  if (fileInput.files.length > 0) {
    fileNameDisplay.textContent =
      "Selected document: " + fileInput.files[0].name;
  } else {
    fileNameDisplay.textContent = "";
  }
});

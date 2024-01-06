function updateUploadMessages(message, status) {
  var messageDiv = document.getElementById("uploadStatus");
  messageDiv.innerHTML = message.replace(/\n/g, "<br>");
  messageDiv.className = status;
}

function showToast(message, type) {
  let toast = document.getElementById("toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "toast";
    document.body.appendChild(toast);
  }

  toast.textContent = message;
  toast.className = type;

  toast.style.display = "block";
  toast.style.opacity = "1";

  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => {
      toast.style.display = "none";
    }, 600);
  }, 3000);
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

function pollDocumentStatus() {
  fetch("/status", {
    method: "GET",
    headers: {
      "X-CSRFToken": getCsrfToken(),
    },
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.error) {
        updateUploadMessages("Error: " + data.error, "error");
      } else if (data.length === 0) {
        // Stop polling if there are no documents
        updateUploadMessages("No documents to process.", "success");
      } else {
        // Update status and continue polling
        let statusMessage = data
          .map((doc) => `${doc.title}: ${doc.status}`)
          .join("<br>");
        updateUploadMessages(statusMessage, "success");
        setTimeout(pollDocumentStatus, 5000); // Continue polling every 5 seconds
      }
    })
    .catch((error) => {
      console.error("Error during status update:", error);
      updateUploadMessages(
        "Error during status update: " + error.message,
        "error",
      );
    });
}
function updateFileList() {
  const fileList = fileInput.files;
  totalPages = fileList.length;
  document.getElementById("total-pages").textContent = totalPages;
  createDocumentForms(fileList);
  displayCurrentForm();
}

function createDocumentForms(fileList) {
  documentForms = [];
  for (let i = 0; i < fileList.length; i++) {
    const formHtml = `
        <div class="form-group">
          <label>Document Title (optional):</label>
          <input type="text" name="title" placeholder="Enter document title" />
        </div>
        <div class="form-group">
          <label>Author Name (optional):</label>
          <input type="text" name="author" placeholder="Enter author's name" />
        </div>
        <div class="form-group">
          <label>Max Tokens per Chunk (default is 512):</label>
          <input type="number" name="chunk_size" min="1" value="512" />
        </div>
      `;
    documentForms.push(formHtml);
  }
}

function onSubmit(event) {
  event.preventDefault();
  updateUploadMessages("Uploading...", "success");

  documentForms.forEach((formHtml, index) => {
    if (index !== currentPage - 1) {
      const div = document.createElement("div");
      div.innerHTML = formHtml;
      div.style.display = "none";
      uploadForm.appendChild(div);
    }
  });

  // Use FormData to capture all form inputs for the AJAX request
  const formData = new FormData(uploadForm);

  // Send the AJAX request to the upload endpoint
  fetch(uploadForm.action, {
    method: "POST",
    headers: {
      "X-CSRFToken": getCsrfToken(),
    },
    body: formData,
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.status === "success") {
        startProcessing();
      } else {
        updateUploadMessages("Upload Failed.", "error");
        console.error("Upload failed:", data.message);
      }
    })
    .catch((error) => {
      console.error("Error during upload:", error);
    });
}

function startProcessing() {
  updateUploadMessages("Processing & Embedding...", "success");
  fetch("/embeddings/process", {
    method: "POST",
    headers: {
      "X-CSRFToken": getCsrfToken(),
    },
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.status === "success") {
        // Start polling for status updates when processing starts
        pollDocumentStatus();
      } else {
        updateUploadMessages("Processing Failed.", "error");
        console.error("Processing failed:", data.message);
      }
    })
    .catch((error) => {
      console.error("Error during processing:", error);
    });
}

function displayCurrentForm() {
  // Update the inner HTML of the documentFormsContainer with the current form
  documentFormsContainer.innerHTML = documentForms[currentPage - 1];
  document.getElementById("current-page").textContent = currentPage;

  // Display the filename for the current document
  const currentFilenameDisplay = document.getElementById("file-name-display");
  if (fileInput.files[currentPage - 1]) {
    currentFilenameDisplay.textContent = `Current Document: ${
      fileInput.files[currentPage - 1].name
    }`;
  } else {
    currentFilenameDisplay.textContent = "No document selected";
  }
}

function navigate(step) {
  currentPage += step;
  if (currentPage < 1) {
    currentPage = 1;
  } else if (currentPage > totalPages) {
    currentPage = totalPages;
  }
  displayCurrentForm();
}

let currentPage = 1;
let totalPages = 1;
let documentForms = [];
const uploadForm = document.getElementById("uploadForm");
const fileInput = document.getElementById("file");
const prevButton = document.getElementById("prev-button");
const nextButton = document.getElementById("next-button");
const documentFormsContainer = document.getElementById(
  "document-forms-container",
);

fileInput.addEventListener("change", updateFileList);
prevButton.addEventListener("click", () => navigate(-1));
nextButton.addEventListener("click", () => navigate(1));
uploadForm.addEventListener("submit", onSubmit);

const saveButtons = document.querySelectorAll(".save-btn");

saveButtons.forEach(function (saveButton) {
  saveButton.addEventListener("click", function (event) {
    var listItem = saveButton.closest("li");
    var form = listItem.querySelector("form.edit-document-form");

    if (form) {
      event.preventDefault();
      var formData = new FormData(form);

      fetch(form.action, {
        method: "POST",
        headers: {
          "X-CSRFToken": getCsrfToken(),
        },
        body: formData,
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
            showToast("Updated successfully!", "success");
            saveButton.style.display = "none";
            listItem.querySelector(".edit-btn").style.display = "inline-block";
            Array.from(listItem.querySelectorAll(".editable")).forEach(
              (input) => {
                input.setAttribute("readonly", "readonly");
              },
            );
          }
        })
        .catch((error) => {
          alert("An error occurred: " + error);
          showToast("Error updating document: " + error.message, "error");
        });
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

    if (confirm("Are you sure you want to delete this document?")) {
      fetch(`/embeddings/delete/${documentId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRF-Token": getCsrfToken(),
        },
        body: JSON.stringify({ document_id: documentId }),
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
            "error",
          );
        });
    }
  }
});

var editButtons = document.querySelectorAll(".btn-icon.edit-btn");
editButtons.forEach(function (button) {
  button.addEventListener("click", function () {
    enableEditing(this);
  });
});

const submitButton = document.querySelector(".doc-submit-btn");
const paginationControls = document.getElementById("pagination-controls");

submitButton.disabled = true;
paginationControls.style.display = "none"; // Hide pagination controls

// Event listener to enable submit button and show pagination controls when files are selected
fileInput.addEventListener("change", function () {
  if (fileInput.files.length > 0) {
    submitButton.disabled = false; // Enable submit button
    // Show pagination controls only if more than one file is uploaded
    paginationControls.style.display =
      fileInput.files.length > 1 ? "block" : "none";
  } else {
    submitButton.disabled = true; // Keep submit button disabled
    paginationControls.style.display = "none"; // Hide pagination controls
  }
});

let documentData = {}; // Object to store form data for each document

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

function updateFileList() {
  const fileList = fileInput.files;
  totalPages = fileList.length;
  document.getElementById("total-pages").textContent = totalPages;
  createDocumentForms(fileList);
  displayCurrentForm();
  updatePaginationControls();
}

function createDocumentForms(fileList) {
  documentForms = [];
  for (let i = 0; i < fileList.length; i++) {
    const file = fileList[i];
    const formHtml = `
  <div class="form-group">
    <label>Title&nbsp;(optional):</label>
    <input type="text" name="title" placeholder="Enter document title" value="${
      documentData[i]?.title || ""
    }" />
  </div>
  <div class="form-group">
    <label>Author&nbsp;(optional):</label>
    <input type="text" name="author" placeholder="Enter author's name" value="${
      documentData[i]?.author || ""
    }" />
  </div>
  <div class="form-group">
    <label>Tokens per Chunk&nbsp;(default is 1024):</label>
    <input type="number" name="chunk_size" min="1" value="${
      documentData[i]?.chunk_size || "1024"
    }" />
  </div>
  <div class="form-group">
    <label>
      <input type="checkbox" name="advanced_preprocessing" ${
        documentData[i]?.advanced_preprocessing ? "checked" : ""
      } />&nbsp;Advanced PDF Preprocessing?
    </label>
  </div>
`;
    documentForms.push(formHtml);
  }
}

function updatePaginationControls() {
  if (totalPages > 1) {
    paginationControls.style.display = "flex";
    submitButton.disabled = false;
  } else {
    paginationControls.style.display = "none";
    submitButton.disabled = totalPages === 0;
  }
}

function onSubmit(event) {
  event.preventDefault();
  const formData = new FormData();
  const fileList = fileInput.files;

  for (let i = 0; i < fileList.length; i++) {
    const file = fileList[i];
    const fileType = file.type;
    const fileExtension = file.name.split(".").pop().toLowerCase();

    if (
      fileType !== "text/plain" &&
      fileType !== "application/pdf" &&
      !["py", "html", "css", "js", "md", "yml", "json"].includes(fileExtension)
    ) {
      updateUploadMessages(
        "Only .txt, .pdf, .py, .html, .css, .js, .md, .yml, and .json files are allowed.",
        "error",
      );
      return;
    }

    let title = document.querySelector('input[name="title"]').value;
    if (
      ["py", "html", "css", "js", "md", "yml", "json"].includes(fileExtension)
    ) {
      if (title) {
        title = `${title} (${file.name})`;
      } else {
        title = file.name;
      }
    } else {
      title = title || file.name;
    }

    const author = document.querySelector('input[name="author"]').value || "";
    const chunkSize =
      document.querySelector('input[name="chunk_size"]').value || "512";
    const advancedPreprocessing = document.querySelector(
      'input[name="advanced_preprocessing"]',
    ).checked;

    formData.append("file", file);
    formData.append("title", title);
    formData.append("author", author);
    formData.append("chunk_size", chunkSize);
    formData.append("advanced_preprocessing", advancedPreprocessing);
  }

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
        updateUploadMessages("Processing...", "success");
      } else {
        updateUploadMessages("Upload Failed.", "error");
        console.error("Upload failed:", data.message);
      }
    })
    .catch((error) => {
      console.error("Error during upload:", error);
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

function saveFormData(index) {
  const formData = new FormData(document.querySelector("form"));
  const file = fileInput.files[index];
  let title = formData.get("title");
  title = title || file.name; // Use file name if title is not provided
  let advanced_preprocessing = formData.get("advanced_preprocessing") === "on"; // Check if advanced preprocessing is enabled
  documentData[index] = {
    file: file,
    title: title,
    author: formData.get("author"),
    chunk_size: formData.get("chunk_size"),
    advanced_preprocessing: advanced_preprocessing, // Store advanced preprocessing setting
  };
}

function restoreFormData(index) {
  // Restore form data for the given document
  const data = documentData[index];
  if (data) {
    const form = document.querySelector("form");
    form.querySelector('input[name="title"]').value = data.title || "";
    form.querySelector('input[name="author"]').value = data.author || ""; // Use empty string if author is not provided
    form.querySelector('input[name="chunk_size"]').value = data.chunk_size;
    form.querySelector('input[name="advanced_preprocessing"]').checked =
      data.advanced_preprocessing;
  }
}

function navigate(step) {
  const newIndex = currentPage + step;
  if (newIndex >= 1 && newIndex <= totalPages) {
    saveFormData(currentPage - 1); // Save data for the current document
    currentPage = newIndex;
    displayCurrentForm(); // Display the new current form
    restoreFormData(currentPage - 1); // Restore data for the new current document
  }
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
            showToast("Error updating document: " + data.error, "error");
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
      fetch(`/embedding/delete/${documentId}`, {
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
            showToast("Error deleting document: " + data.error, "error");
          } else {
            showToast("Document deleted successfully!", "success");
            var listItem = deleteButton.closest("li");
            if (listItem) {
              listItem.remove();
            }
          }
        })
        .catch((error) => {
          showToast("An error occurred: " + error, "error");
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

fileInput.addEventListener("change", function () {
  if (fileInput.files.length > 0) {
    submitButton.disabled = false; // Enable submit button
    // Show pagination controls only if more than one file is uploaded
    paginationControls.style.display =
      fileInput.files.length > 1 ? "flex" : "none";
  } else {
    submitButton.disabled = true; // Keep submit button disabled
    paginationControls.style.display = "none"; // Hide pagination controls
  }
});

// Function to hide the upload prompt

document.getElementById("file").addEventListener("change", function () {
  var fileInput = this;
  var fileNameDisplay = document.getElementById("file-name-display");
  var submitButton = document.querySelector(".doc-submit-btn");
  const uploadPrompt = document.getElementById("upload-prompt");
  const typesList = document.getElementById("file-types-list");

  if (fileInput.files.length > 0) {
    fileNameDisplay.textContent = "Selected file: " + fileInput.files[0].name;
    submitButton.style.display = "flex";
    uploadPrompt.style.display = "none";
    typesList.style.display = "none";
  } else {
    uploadPrompt.style.display = "flex";
    typesList.style.display = "flex";
    fileNameDisplay.textContent = "";
    submitButton.style.display = "none";
  }
});

// Assuming you have already established a connection to the '/embeddings' namespace
// eslint-disable-next-line no-undef
var socket = io("/embedding");

// Listen for task progress updates
socket.on("task_progress", function (data) {
  updateUploadMessages(data.message, "information");
});

// Listen for task completion
socket.on("task_complete", function (data) {
  updateUploadMessages(data.message, "success");
  appendDocumentToList(data.document);
});

// Listen for task errors
socket.on("task_update", function (data) {
  if (data.status === "error") {
    updateUploadMessages("Error: " + data.error, "error");
  }
});

function appendDocumentToList(documentObj) {
  // Assuming 'documentObj' has id, title, author, total_tokens, chunk_count, page_amount

  var docsList = document.querySelector(".docs_list");
  var listItem = document.createElement("li");
  listItem.id = `document-${documentObj.document_id}`;

  // Form for editing document details
  var editForm = document.createElement("form");
  editForm.className = "edit-document-form";
  editForm.action = `/embedding/update_document/${documentObj.document_id}`; // Assuming a URL pattern
  editForm.method = "post";

  var hiddenInput = document.createElement("input");
  hiddenInput.type = "hidden";
  hiddenInput.name = "document_id";
  hiddenInput.value = documentObj.document_id;

  var titleInput = document.createElement("input");
  titleInput.className = "editable";
  titleInput.id = "title-edit";
  titleInput.type = "text";
  titleInput.name = "title";
  titleInput.value = documentObj.title;
  titleInput.readOnly = true;

  var authorInput = document.createElement("input");
  authorInput.className = "editable";
  authorInput.id = "author-edit";
  authorInput.type = "text";
  authorInput.name = "author";
  authorInput.value = documentObj.author;
  authorInput.readOnly = true;

  var totalTokensP = document.createElement("p");
  totalTokensP.textContent = `Total Tokens:  ${documentObj.total_tokens}`;

  var chunkCountP = document.createElement("p");
  chunkCountP.textContent = `Chunk Count:  ${documentObj.chunk_count}`;

  editForm.appendChild(hiddenInput);
  editForm.appendChild(titleInput);
  editForm.appendChild(authorInput);
  editForm.appendChild(totalTokensP);
  editForm.appendChild(chunkCountP);

  // Button container
  var buttonContainer = document.createElement("div");
  buttonContainer.className = "button-container";

  var editButton = document.createElement("button");
  editButton.type = "button";
  editButton.className = "btn-icon edit-btn";
  editButton.setAttribute("onclick", "enableEditing(this)");
  editButton.title = "Edit Document";
  editButton.innerHTML = `<i class="nuicon-file-pen"></i>`;

  var saveButton = document.createElement("button");
  saveButton.type = "button";
  saveButton.className = "btn-icon save-btn";
  saveButton.title = "Save Changes";
  saveButton.style.display = "none";
  saveButton.innerHTML = `<i class="nuicon-check"></i>`;

  var deleteButton = document.createElement("button");
  deleteButton.type = "button";
  deleteButton.className = "btn-icon delete-btn";
  deleteButton.setAttribute("data-doc-id", documentObj.document_id);
  deleteButton.title = "Delete Document";
  deleteButton.innerHTML = `<i class="nuicon-trash-can"></i>`;

  buttonContainer.appendChild(editButton);
  buttonContainer.appendChild(saveButton);
  buttonContainer.appendChild(deleteButton);

  // Append form and button container to the list item
  listItem.appendChild(editForm);
  listItem.appendChild(buttonContainer);

  // Append the list item to the documents list
  docsList.appendChild(listItem);
}

const dropzone = document.querySelector(".doc-upload");

dropzone.addEventListener("dragover", function (e) {
  e.preventDefault();
  dropzone.classList.add("dragover");
});

dropzone.addEventListener("dragleave", function (e) {
  e.preventDefault();
  dropzone.classList.remove("dragover");
});

dropzone.addEventListener("drop", function (e) {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  fileInput.files = e.dataTransfer.files;
  updateFileList();

  // Update the upload menu elements when files are dropped
  var fileNameDisplay = document.getElementById("file-name-display");
  var submitButton = document.querySelector(".doc-submit-btn");
  const uploadPrompt = document.getElementById("upload-prompt");
  const typesList = document.getElementById("file-types-list");

  if (fileInput.files.length > 0) {
    fileNameDisplay.textContent = "Selected file: " + fileInput.files[0].name;
    submitButton.style.display = "flex";
    uploadPrompt.style.display = "none";
    typesList.style.display = "none";
  }
});

document
  .querySelector(".delete-all-btn")
  .addEventListener("click", function () {
    if (
      confirm(
        "Are you sure you want to delete all documents? This action cannot be undone.",
      )
    ) {
      fetch(`/embedding/delete_all`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({}),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.status === "success") {
            showToast(data.message, "success");
            // Find and remove all document list items
            const documentListItems =
              document.querySelectorAll(".docs_list li");
            documentListItems.forEach((item) => item.remove());
          } else {
            showToast("Error: " + data.message, "error");
          }
        })
        .catch((error) => {
          console.error("Error:", error);
          showToast("An error occurred while deleting documents.", "error");
        });
    }
  });

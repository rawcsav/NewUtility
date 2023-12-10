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

// Function to update the selected key visual indication
function updateSelectedKeyVisual(selectedForm) {
  // Remove the 'selected-key' class from all key list elements
  document.querySelectorAll(".key-list").forEach((keyItem) => {
    keyItem.classList.remove("selected-key");
  });

  // Add the 'selected-key' class to the key list element of the selected form
  const keyListItem = selectedForm.closest(".key-list");
  if (keyListItem) {
    keyListItem.classList.add("selected-key");
  }
}

// Function to remove a key from the UI
function removeKeyFromUI(form) {
  const keyListItem = form.closest(".key-list");
  if (keyListItem) {
    keyListItem.remove(); // Removes the key item from the list
  }
}

// Event listeners for the select and delete key forms
document
  .querySelectorAll(".delete-api-key-form, .select-api-key-form")
  .forEach((form) => {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      const formData = new FormData(this);
      const actionUrl = form.action;
      const isSelectForm = form.classList.contains("select-api-key-form");

      fetch(actionUrl, {
        method: "POST",
        body: formData
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.status === "success") {
            updateApiKeyMessages(data.message, "success");

            if (isSelectForm) {
              // If this is a select API key form, update the UI to show the selected key
              updateSelectedKeyVisual(form);
            } else {
              // If this is a delete API key form, remove the key from the UI
              removeKeyFromUI(form);
            }
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
        });
    });
  });

function updateUploadMessages(message, status) {
  var messageDiv = document.getElementById("docsStatus");
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
              updateUploadMessages("Updated successfully!", "success");
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

document.addEventListener("DOMContentLoaded", function () {
  // Add click event listeners to all thumbnails in the image history carousel
  const thumbnails = document.querySelectorAll(".image-history-item img");
  thumbnails.forEach((thumbnail) => {
    thumbnail.addEventListener("click", function () {
      // Extract the UUID from the image src attribute
      const uuid = this.getAttribute("src").split("/").pop().split(".")[0];
      // Toggle the icons for the clicked image
      toggleIcons(uuid, this);
    });
  });
});

function toggleIcons(uuid, imageElement) {
  // Find the image history item container for the clicked thumbnail
  const imageItem = imageElement.closest(".image-history-item");
  // Check if the .icons-container exists
  const iconsContainer = imageItem.querySelector(".icons-container");

  // If icons already exist, toggle visibility
  if (iconsContainer && iconsContainer.hasChildNodes()) {
    // Icons are already present, so toggle visibility
    iconsContainer.style.display =
      iconsContainer.style.display === "none" ? "block" : "none";
  } else {
    // No icons present, add them
    addIconsToImage(uuid, iconsContainer);
  }
}

function addIconsToImage(uuid, iconsContainer) {
  if (iconsContainer) {
    // Clear any previously added icons
    iconsContainer.innerHTML = "";

    // Append new icons
    iconsContainer.appendChild(
      createIconLink(`/image/download_image/${uuid}`, "fa-download")
    );
    iconsContainer.appendChild(
      createIconLink(
        `/static/temp_img/${uuid}.webp`,
        "fa-external-link-alt",
        true
      )
    );

    // Set display to block to ensure icons are visible
    iconsContainer.style.display = "block";
  } else {
    console.error("Icons container not found for image UUID:", uuid);
  }
}

function createIconLink(href, iconClass, isNewWindow) {
  const icon = document.createElement("i");
  icon.className = `fas ${iconClass}`;
  const link = document.createElement("a");
  link.href = href;
  link.className = "image-icon";
  if (isNewWindow) {
    link.target = "_blank";
  }
  link.appendChild(icon);
  return link;
}

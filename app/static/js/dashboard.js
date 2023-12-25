function getCsrfToken() {
  return document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute("content");
}

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
        "X-CSRFToken": getCsrfToken()
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
        "X-CSRFToken": getCsrfToken()
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

function startSpinningIcon(form) {
  const submitButton = form.querySelector(".retest-key-button i");
  if (submitButton) {
    submitButton.classList.add("spinning");
  }
}

function stopSpinningIcon(form) {
  const submitButton = form.querySelector(".retest-key-button i");
  if (submitButton) {
    submitButton.classList.remove("spinning");
  }
}

document.querySelectorAll(".retest-api-key-form").forEach((form) => {
  form.addEventListener("submit", function (event) {
    event.preventDefault();

    var refreshButton = form.querySelector(".retest-key-button i.fa-sync-alt");
    if (refreshButton) {
      refreshButton.classList.add("spinning");
    }

    var formData = new FormData(form);
    var actionUrl = form.action;

    fetch(actionUrl, {
      method: "POST",
      headers: {
        "X-CSRFToken": getCsrfToken()
      },
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
        if (refreshButton) {
          refreshButton.classList.remove("spinning");
        }
      });
  });
});

function updateSelectedKeyVisual(selectedForm) {
  document.querySelectorAll(".key-list").forEach((keyItem) => {
    keyItem.classList.remove("selected-key");
  });

  const keyListItem = selectedForm.closest(".key-list");
  if (keyListItem) {
    keyListItem.classList.add("selected-key");
  }
}

function removeKeyFromUI(form) {
  const keyListItem = form.closest(".key-list");
  if (keyListItem) {
    keyListItem.remove();
  }
}

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
        headers: {
          "X-CSRFToken": getCsrfToken()
        },
        body: formData
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.status === "success") {
            updateApiKeyMessages(data.message, "success");

            if (isSelectForm) {
              updateSelectedKeyVisual(form);
            } else {
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
  var formattedMessage = message.replace(/\n/g, "<br>");
  messageDiv.innerHTML = formattedMessage;
  messageDiv.className = status;
}

function enableEditing(editButton) {
  var listItem = editButton.closest("li");
  var form = listItem.querySelector("form.edit-document-form");
  var inputs = form.querySelectorAll(".editable");

  inputs.forEach(function (input) {
    input.removeAttribute("readonly");
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
          headers: {
            "X-CSRFToken": getCsrfToken()
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
              alert("Error updating document: " + data.error);
            } else {
              updateUploadMessages("Updated successfully!", "success");
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
          "X-CSRF-Token": getCsrfToken()
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

document.addEventListener("DOMContentLoaded", function () {
  const thumbnails = document.querySelectorAll(".image-history-item img");
  thumbnails.forEach((thumbnail) => {
    thumbnail.addEventListener("click", function () {
      const uuid = this.getAttribute("src").split("/").pop().split(".")[0];
      toggleIcons(uuid, this);
    });
  });
});

function toggleIcons(uuid, imageElement) {
  const imageItem = imageElement.closest(".image-history-item");
  const iconsContainer = imageItem.querySelector(".icons-container");

  if (iconsContainer && iconsContainer.hasChildNodes()) {
    iconsContainer.style.display =
      iconsContainer.style.display === "none" ? "block" : "none";
  } else {
    addIconsToImage(uuid, iconsContainer);
  }
}

function addIconsToImage(uuid, iconsContainer) {
  if (iconsContainer) {
    iconsContainer.innerHTML = "";

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

function toggleUsageInfo(usageInfoId) {
  var usageInfoDiv = document.getElementById(usageInfoId);
  if (usageInfoDiv.style.display === "none") {
    usageInfoDiv.style.display = "block";
  } else {
    usageInfoDiv.style.display = "none";
  }
}

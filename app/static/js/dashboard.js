function getCsrfToken() {
  return document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute("content");
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

document
  .getElementById("username-change-form")
  .addEventListener("submit", function (event) {
    event.preventDefault();
    var formData = new FormData(this);

    fetch("/user/change_username", {
      method: "POST",
      headers: {
        "X-CSRFToken": getCsrfToken(),
      },
      body: formData,
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

    // Retrieve the input values containing the API key string and nickname
    var apiKeyInput = document.getElementById("api_key"); // ID for the API key input field
    var nicknameInput = document.getElementById("nickname"); // ID for the nickname input field
    var apiKeysString = apiKeyInput.value;
    var nickname = nicknameInput.value;

    // Find unique API keys within the input string
    var apiKeys = findOpenAIKeys(apiKeysString);

    // Handle each API key
    apiKeys.forEach((apiKey, index) => {
      var formData = new FormData();
      formData.append("api_key", apiKey); // 'api_key' is the name expected by the server
      formData.append("nickname", nickname + " " + (index + 1)); // Append index to nickname to make it unique

      // Fetch request to submit each API key
      fetch("/user/upload_api_key", {
        method: "POST",
        headers: {
          "X-CSRFToken": getCsrfToken(),
          "Content-Type": "application/json", // Assuming your server expects JSON
        },
        body: JSON.stringify({
          api_key: apiKey,
          nickname: nickname + " " + (index + 1), // Send as JSON
        }),
      })
        .then((response) => response.json())
        .then((data) => {
          // Show a toast message for each API key processed
          showToast(
            data.message,
            data.status === "success" ? "success" : "error",
          );
        })
        .catch((error) => {
          showToast("Error: " + error, "error");
        });
    });

    // Clear the form fields after submission
    apiKeyInput.value = "";
    nicknameInput.value = "";
  });

document
  .querySelector("#toggleFormButton")
  .addEventListener("click", function () {
    let apiKeyForm = document.querySelector("#api-key-form");
    apiKeyForm.style.display =
      apiKeyForm.style.display === "none" ? "block" : "none";
    this.classList.toggle("active");
  });

// Replace $("#toggleUserButton").on("click", function () {...});
document
  .querySelector("#toggleUserButton")
  .addEventListener("click", function () {
    let usernameChangeForm = document.querySelector("#username-change-form");
    usernameChangeForm.style.display =
      usernameChangeForm.style.display === "none" ? "block" : "none";
    this.classList.toggle("active");
  });

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
        "X-CSRFToken": getCsrfToken(),
      },
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.status === "success") {
          showToast(data.message, "success");
        } else {
          showToast(data.message, "error");
        }
      })
      .catch((error) => {
        console.error("Error:", error);
        showToast("An error occurred while processing your request.", "error");
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
          "X-CSRFToken": getCsrfToken(),
        },
        body: formData,
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.status === "success") {
            showToast(data.message, "success");

            if (isSelectForm) {
              updateSelectedKeyVisual(form);
            } else {
              removeKeyFromUI(form);
            }
          } else {
            showToast(data.message, "error");
          }
        })
        .catch((error) => {
          console.error("Error:", error);
          showToast(
            "An error occurred while processing your request.",
            "error",
          );
        });
    });
  });

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
            showToast("Document deleted successfully!", "success");
            var listItem = deleteButton.closest("li");
            if (listItem) {
              listItem.remove();
            }
          }
        })
        .catch((error) => {
          alert("An error occurred: " + error);
          showToast("Error deleting document: " + error.message, "error");
        });
    }
  }
});

const thumbnails = document.querySelectorAll(".image-history-item img");
thumbnails.forEach((thumbnail) => {
  thumbnail.addEventListener("click", function () {
    const uuid = this.getAttribute("src").split("/").pop().split(".")[0];
    toggleIcons(uuid, this);
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

function setActiveButton(activeButtonId) {
  document.querySelectorAll(".options-button").forEach(function (button) {
    button.classList.remove("active");
  });

  if (activeButtonId) {
    var activeButton = document.getElementById(activeButtonId);
    if (activeButton) {
      activeButton.classList.add("active");
    }
  }
}
function findOpenAIKeys(inputString) {
  const apiKeyPattern = /sk-[A-Za-z0-9]{48}/g;
  const apiKeys = inputString.match(apiKeyPattern) || [];
  return [...new Set(apiKeys)];
}

function setupFormSubmission(
  formId,
  submitUrl,
  successCallback,
  errorCallback,
) {
  const form = document.getElementById(formId);
  if (!form) return;

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    const formData = new FormData(event.target);

    submitForm(formData, submitUrl).then(successCallback).catch(errorCallback);
  });
}

function submitForm(formData, submitUrl) {
  return fetch(submitUrl, {
    method: "POST",
    headers: {
      "X-CSRFToken": getCsrfToken(),
    },
    body: formData,
  }).then((response) => {
    if (!response.ok) {
      throw new Error("Failed to update preferences.");
    }
    return response.json();
  });
}

function handleResponse(data) {
  if (data.status === "success") {
    showToast(data.message, "success");
  } else {
    showToast(data.message, "error");
    console.error(data.errors);
  }
}

setupFormSubmission(
  "update-preferences-form",
  "/chat/update-preferences",
  handleResponse,
  (error) => showToast("Error: " + error.message, "error"),
);

setupFormSubmission(
  "docs-preferences-form",
  "/embeddings/update-doc-preferences",
  handleResponse,
  (error) => showToast("Error: " + error.message, "error"),
);

function togglePopup(activePopupId, activeButtonId) {
  requestAnimationFrame(() => {
    // Define all popup elements and their corresponding buttons
    const popups = {
      "preference-popup": "show-preferences-btn",
      "docs-settings-popup": "docs-preferences-btn",
      "docs-edit-popup": "docs-edit-btn",
    };

    // Iterate through the popups to show/hide them as necessary
    Object.keys(popups).forEach((popupId) => {
      document.getElementById(popupId).style.display =
        popupId === activePopupId ? "block" : "none";
    });

    // Set the active button
    setActiveButton(activeButtonId);
  });
}

var showPreferencesBtn = document.getElementById("show-preferences-btn");
if (showPreferencesBtn) {
  showPreferencesBtn.addEventListener("click", function () {
    togglePopup("preference-popup", "show-preferences-btn");
  });
}

var docsPreferencesBtn = document.getElementById("docs-preferences-btn");
if (docsPreferencesBtn) {
  docsPreferencesBtn.addEventListener("click", function () {
    togglePopup("docs-settings-popup", "docs-preferences-btn");
  });
}

function addIconsToImage(uuid, iconsContainer) {
  if (iconsContainer) {
    iconsContainer.innerHTML = "";

    iconsContainer.appendChild(
      createIconLink(`/image/download_image/${uuid}`, "fa-download"),
    );
    iconsContainer.appendChild(
      createIconLink(
        `/static/temp_img/${uuid}.webp`,
        "fa-external-link-alt",
        true,
      ),
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
  console.log(usageInfoId);
  if (usageInfoDiv.style.display === "none") {
    usageInfoDiv.style.display = "block";
  } else {
    usageInfoDiv.style.display = "none";
  }
}

var docsEditBtn = document.getElementById("docs-edit-btn");
if (docsEditBtn) {
  docsEditBtn.addEventListener("click", function () {
    togglePopup("docs-edit-popup", "docs-edit-btn");
  });
}

document.querySelectorAll(".edit-btn").forEach(function (editBtn) {
  editBtn.addEventListener("click", function () {
    enableEditing(editBtn);
  });
});

document
  .querySelectorAll(".view-usage-button")
  .forEach(function (viewUsageBtn) {
    viewUsageBtn.addEventListener("click", function () {
      var usageInfoId = viewUsageBtn.getAttribute("usage-div-id");
      toggleUsageInfo(usageInfoId);
    });
  });

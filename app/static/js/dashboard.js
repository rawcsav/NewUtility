function getCsrfToken() {
  return document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute("content");
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
  const uniqueApiKeys = [...new Set(apiKeys)]; // Remove duplicates
  return uniqueApiKeys;
}
function setupUpdatePreferencesForm() {
  const updatePreferencesForm = document.getElementById(
    "update-preferences-form",
  );
  if (!updatePreferencesForm) return;

  updatePreferencesForm.addEventListener("submit", function (event) {
    handleUpdatePreferencesFormSubmission(event);
  });
}

function handleUpdatePreferencesFormSubmission(event) {
  event.preventDefault();
  const formData = new FormData(event.target);

  submitUpdatePreferences(formData)
    .then((data) => {
      processUpdatePreferencesResponse(data);
    })
    .catch((error) => showToast("Error: " + error.message, "error"));
}

function submitUpdatePreferences(formData) {
  return fetch("/chat/update-preferences", {
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

function processUpdatePreferencesResponse(data) {
  if (data.status === "success") {
    showToast(data.message, "success");
  } else {
    showToast(data.message, "error");
    console.error(data.errors);
  }
}

function debounce(func, delay) {
  let debounceTimer;
  return function () {
    const context = this;
    const args = arguments;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => func.apply(context, args), delay);
  };
}

function updateKnowledgeContextTokens() {
  var value = document.getElementById("max-context-tokens").value;
  fetch("/embeddings/update-knowledge-context-tokens", {
    method: "POST",
    headers: {
      "X-CSRFToken": getCsrfToken(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      knowledge_context_tokens: value,
    }),
  })
    .then((response) => response.json())
    .then((data) => console.log(data));
}

// Here we pass the reference to the function without invoking it
let debounceKnowledgeContextTokens = debounce(
  updateKnowledgeContextTokens,
  250,
);

function updateKnowledgeQueryMode() {
  var isChecked = document.getElementById("use-docs").checked;
  fetch("/embeddings/update-knowledge-query-mode", {
    method: "POST",
    headers: {
      "X-CSRFToken": getCsrfToken(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      knowledge_query_mode: isChecked,
    }),
  })
    .then((response) => response.json())
    .then((data) => console.log(data));
}

function updateDocumentSelection(documentId) {
  var isChecked = document.getElementById("checkbox-" + documentId).checked;
  fetch("/embeddings/update-document-selection", {
    method: "POST",
    headers: {
      "X-CSRFToken": getCsrfToken(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      document_id: documentId,
      selected: isChecked,
    }),
  })
    .then((response) => response.json())
    .then((data) => console.log(data));
}

// Get the slider and the display elements
let slider = document.getElementById("max-context-tokens");
let sliderValueDisplay = document.getElementById("max-context-tokens-value");

// Function to update the display value with a percentage sign
function updateDisplayValue(value) {
  sliderValueDisplay.value = value + "%";
}

// Set the initial value of the display to match the slider with a percentage sign
updateDisplayValue(slider.value);

// Update the display value when the slider is moved
slider.addEventListener("input", function () {
  updateDisplayValue(this.value);
});

// Update the slider value when the display value is changed
sliderValueDisplay.addEventListener("input", function () {
  let value = parseInt(this.value.replace("%", ""), 10);
  if (!isNaN(value) && value >= 0 && value <= 80) {
    // Assuming 0 to 80 is the slider's range
    slider.value = value;
  }
});

slider.addEventListener("change", debounceKnowledgeContextTokens);
sliderValueDisplay.addEventListener("change", debounceKnowledgeContextTokens);
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

setupUpdatePreferencesForm();

function toggleDocPreferences() {
  requestAnimationFrame(() => {
    document.getElementById("preference-popup").style.display = "none";
    document.getElementById("docs-settings-popup").style.display = "block";
    setActiveButton("docs-preferences-btn");

    // Get the form element
    var form = document.getElementById("docs-settings-form");

    // Add a submit event listener to the form
    form.addEventListener("submit", function (event) {
      // Prevent the form from submitting normally
      event.preventDefault();

      // Call the function to update the preferences
      updateDocumentSelection();

      // You could also add any other functions you need to run on form submission here
    });
  });
}

function togglePreferences() {
  requestAnimationFrame(() => {
    document.getElementById("preference-popup").style.display = "block";
    document.getElementById("docs-settings-popup").style.display = "none";
    setActiveButton("show-preferences-btn");
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

// Event listener for 'Show Preferences' button
var showPreferencesBtn = document.getElementById("show-preferences-btn");
if (showPreferencesBtn) {
  showPreferencesBtn.addEventListener("click", togglePreferences);
}

// Event listener for 'Documents Preferences' button
var docsPreferencesBtn = document.getElementById("docs-preferences-btn");
if (docsPreferencesBtn) {
  docsPreferencesBtn.addEventListener("click", toggleDocPreferences);
}

// Event listener for 'Use Documents' checkbox
var useDocsCheckbox = document.getElementById("use-docs");
if (useDocsCheckbox) {
  useDocsCheckbox.addEventListener("click", updateKnowledgeQueryMode);
}

// Event listeners for document selection checkboxes
document
  .querySelectorAll('input[type="checkbox"][id^="checkbox-"]')
  .forEach(function (checkbox) {
    var documentId = checkbox.id.split("-")[1];
    checkbox.addEventListener("click", function () {
      updateDocumentSelection(documentId);
    });
  });

// Event listener for 'Edit Document' buttons
document.querySelectorAll(".edit-btn").forEach(function (editBtn) {
  editBtn.addEventListener("click", function () {
    enableEditing(this.closest("li"));
  });
});

// Event listener for 'View Usage Info' buttons
document
  .querySelectorAll(".view-usage-button")
  .forEach(function (viewUsageBtn) {
    viewUsageBtn.addEventListener("click", function () {
      var usageInfoId = viewUsageBtn.getAttribute("usage-div-id");
      toggleUsageInfo(usageInfoId);
    });
  });

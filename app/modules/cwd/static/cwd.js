let controller = new AbortController();
let signal = controller.signal;

function getCsrfToken() {
  return document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute("content");
}

function showToast(message, type) {
  let toast = document.getElementById("toast") || createToastElement();
  toast.textContent = message;
  toast.className = type;
  showAndHideToast(toast);
}

function createToastElement() {
  const toast = document.createElement("div");
  toast.id = "toast";
  document.body.appendChild(toast);
  return toast;
}

function showAndHideToast(toast) {
  Object.assign(toast.style, {
    display: "block",
    opacity: "1",
  });

  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => {
      toast.style.display = "none";
    }, 600);
  }, 3000);
}

document.addEventListener("DOMContentLoaded", function () {
  const queryInput = document.getElementById("query");
  queryInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
      event.preventDefault();
      queryDocument();
    }
  });
  const systemPromptTextarea = document.getElementById("system_prompt");
  if (systemPromptTextarea) {
    systemPromptTextarea.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        triggerFormSubmission("docs-preferences-form");
      }
    });
  }
});

function triggerFormSubmission(formId) {
  const form = document.getElementById(formId);
  if (form) {
    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) {
      submitButton.click();
    }
  }
}
function debounce(func, wait, immediate) {
  let timeout;
  return function () {
    const context = this,
      args = arguments;
    const later = function () {
      timeout = null;
      if (!immediate) func.apply(context, args);
    };
    const callNow = immediate && !timeout;
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
    if (callNow) func.apply(context, args);
  };
}

// Modify setupFormSubmission to support debounced submission
function setupFormSubmission(
  formId,
  submitUrl,
  successCallback,
  errorCallback,
) {
  const form = document.getElementById(formId);
  if (!form) return;

  const debouncedSubmit = debounce(function () {
    const formData = new FormData(form);
    submitForm(formData, submitUrl).then(successCallback).catch(errorCallback);
  }, 1000); // Debounce time of 1000 milliseconds

  form.addEventListener("input", function (event) {
    event.preventDefault();
    debouncedSubmit();
  });
}

async function submitForm(formData, submitUrl) {
  const response = await fetch(submitUrl, {
    method: "POST",
    headers: {
      "X-CSRFToken": getCsrfToken(),
    },
    body: formData,
  });

  if (!response.ok) {
    throw new Error("Failed to update preferences.");
  }

  return response.json();
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
  "docs-preferences-form",
  "/embedding/update-doc-preferences",
  handleResponse,
  (error) => showToast("Error: " + error.message, "error"),
);

let previousQuery = null;
let previousResponse = null;

function addToQueryHistory(query, response) {
  const queryResultsSection = document.getElementById("query-results-section");
  const currentQueryResponse = document.getElementById("current-query");

  // Create a new history entry
  const historyEntry = document.createElement("div");
  historyEntry.className = "history-entry";
  historyEntry.innerHTML = `
    <strong>Query:</strong> <pre>${query}</pre><br><br>
    <strong>Response:</strong> <pre>${response}</pre>
    <hr class="history-delimiter">  <!-- This is the delimiter -->
  `;

  // Insert the history entry before the current query-response
  queryResultsSection.insertBefore(historyEntry, currentQueryResponse);

  // Update the current query-response
  document.getElementById("user_query").textContent = "";
  document.getElementById("results").textContent = "";

  // Set the display of the query and response elements to none
  document.getElementById("user_query").parentNode.style.display = "none";
  document.getElementById("response_container").style.display = "none";
}

let isQueryRunning = false;

function toggleQuery() {
  if (!isQueryRunning) {
    queryDocument();
  } else {
    interruptQuery();
  }
}

async function queryDocument() {
  isQueryRunning = true;
  document.getElementById("queryIcon").classList.remove("nuicon-paper-plane");
  document.getElementById("queryIcon").classList.add("nuicon-pause");

  const query = document.getElementById("query").value.trim();
  if (query === "") {
    showToast("Query cannot be empty.", "warning");
    return;
  }

  const userQueryElement = document.getElementById("user_query");
  userQueryElement.parentNode.style.display = "block";
  userQueryElement.textContent = query;
  document.getElementById("query").value = "";

  const resultsDiv = document.getElementById("results");
  resultsDiv.innerHTML = "<pre></pre>";

  // Update previousQuery for the next iteration
  previousQuery = query;
  previousResponse = "";

  const imageUploadElement = document.getElementById("image-upload");
  const uploadedImages = imageUploadElement.files;

  const base64Images = await Promise.all(
    Array.from(uploadedImages).map(encodeImageAsBase64),
  );

  const requestBody = {
    query: query,
    images: base64Images,
  };

  try {
    const response = await fetch("/cwd/query", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify(requestBody),
      signal: signal,
    });

    if (response.ok) {
      const reader = response.body.getReader();
      let decoder = new TextDecoder();
      const responseLabelContainer =
        document.getElementById("response_container");
      const resultsSpan = document.getElementById("results");
      responseLabelContainer.style.display = "block";
      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          break;
        }
        resultsSpan.textContent += decoder.decode(value);
        previousResponse += decoder.decode(value);
      }

      // At this point, the whole response has been read
      document.getElementById("results").textContent = previousResponse;

      // Add the query and response to the history as soon as they are completed
      addToQueryHistory(previousQuery, previousResponse);

      // Reset previousResponse for the next request
      previousResponse = "";
    } else {
      showToast("Error occurred while querying.", "error");
    }
  } catch (error) {
    if (error.name === "AbortError") {
      showToast("Interrupted!", "warning");
    } else {
      showToast("Error occurred while querying.", "error");
    }
  }
}

document.addEventListener("DOMContentLoaded", function () {
  const selectAllCheckbox = document.getElementById("select-all");
  if (selectAllCheckbox) {
    selectAllCheckbox.addEventListener("change", function () {
      const checkboxes = document.querySelectorAll('input[type="checkbox"]');
      checkboxes.forEach((checkbox) => {
        if (checkbox !== selectAllCheckbox) {
          checkbox.checked = selectAllCheckbox.checked;
        }
      });
    });
  }
  const resetPreferencesButton = document.getElementById("resetPreferences");
  if (resetPreferencesButton) {
    resetPreferencesButton.addEventListener("click", async () => {
      const form = document.getElementById("docs-preferences-form");
      const formData = new FormData(form);
      formData.append("reset", true);
      try {
        const response = await submitForm(
          formData,
          "/embedding/update-doc-preferences",
        );
        handleResponse(response);
        if (response.status === "success") {
          // Load default values
          loadDefaultValues();
        }
      } catch (error) {
        showToast("Error: " + error.message, "error");
      }
    });
  }
});

function loadDefaultValues() {
  // Set default values for form fields
  document.getElementById("top_k").value = 10;
  document.getElementById("top_k_value").value = 10;
  document.getElementById("threshold").value = 0.5;
  document.getElementById("threshold_value").value = 0.5;
  document.getElementById("temperature").value = 1.0;
  document.getElementById("temperature-value").value = 1.0;
  document.getElementById("top_p").value = 1.0;
  document.getElementById("top-p-value").value = 1.0;
  document.getElementById("system_prompt").value =
    "You are a helpful academic literary assistant. Provide in -depth guidance, suggestions, code snippets, and explanations as needed to help the user. Leverage your expertise and intuition to offer innovative and effective solutions.Be informative, clear, and concise in your responses, and focus on providing accurate and reliable information. Use the provided text excerpts directly to aid in your responses.";
}

function selectAll() {
  let selectAllCheckbox = document.getElementById("select-all");
  let checkboxes = document.querySelectorAll('input[type="checkbox"]');

  // Iterate over all checkboxes and set their checked state to match the "select all" checkbox
  checkboxes.forEach((checkbox) => {
    if (checkbox !== selectAllCheckbox) {
      // Ensure we're not toggling the "select all" checkbox itself
      checkbox.checked = selectAllCheckbox.checked;
    }
  });
}

function interruptQuery() {
  controller.abort();
  controller = new AbortController();
  signal = controller.signal;

  const resultsSpan = document.getElementById("results");
  if (resultsSpan.lastChild) {
    resultsSpan.removeChild(resultsSpan.lastChild);
  }

  isQueryRunning = false;
  document.getElementById("queryIcon").classList.remove("nuicon-pause");
  document.getElementById("queryIcon").classList.add("nuicon-paper-plane");
}

document;
const advancedSettingsToggle = document.getElementById("showAdvancedSettings");
const advancedSettings = document.getElementById("advancedSettings");

advancedSettingsToggle.addEventListener("click", function (event) {
  event.preventDefault(); // Prevent default behavior

  if (advancedSettings.style.display === "none") {
    advancedSettings.style.display = "block";
    advancedSettingsToggle.innerHTML = "Hide Advanced Settings";
  } else {
    advancedSettings.style.display = "none";
    advancedSettingsToggle.innerHTML = "Show Advanced Settings";
  }
});

function encodeImageAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result.split(",")[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function generateImagePreviews(files) {
  const imagePreviewsContainer = document.getElementById("image-previews");
  imagePreviewsContainer.innerHTML = "";

  Array.from(files).forEach((file) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = document.createElement("img");
      img.src = e.target.result;
      img.classList.add("image-preview");
      imagePreviewsContainer.appendChild(img);
    };
    reader.readAsDataURL(file);
  });
}

document
  .getElementById("image-upload")
  .addEventListener("change", function (e) {
    generateImagePreviews(e.target.files);
  });

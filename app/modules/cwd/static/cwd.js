let controller = new AbortController();
let signal = controller.signal;
let isQueryRunning = false;
let previousQuery = null;
let previousResponse = null;
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

let isSubmitting = false;
function handleSubmitOnEnter(event, textarea) {
  if (event.key === "Enter" && !event.shiftKey) {
    if (textarea.value.trim() === "") {
      event.preventDefault();
      console.error("Cannot submit an empty message.");
    } else if (isSubmitting) {
      event.preventDefault();
      console.error("Submission in progress.");
    } else {
      event.preventDefault();
      isSubmitting = true;
      queryDocument();
      setTimeout(() => (isSubmitting = false), 2000);
    }
  }
}

document.addEventListener("DOMContentLoaded", function () {
  const systemPromptTextarea = document.getElementById("system_prompt");
  if (systemPromptTextarea) {
    systemPromptTextarea.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        triggerFormSubmission("docs-preferences-form");
      }
    });
  }
  const docsToggle = document.getElementById("docsToggle");
  const settingsToggle = document.getElementById("settingsToggle");
  const imageUploadToggle = document.getElementById("imageUploadToggle");
  const systemPromptToggle = document.getElementById("systemPromptToggle");
  const docsPanel = document.getElementById("docsPanel");
  const settingsPanel = document.getElementById("settingsPanel");
  const imageUploadPanel = document.getElementById("imageUploadPanel");
  const systemPromptPanel = document.getElementById("systemPromptPanel");

  function togglePanel(panel) {
    const panels = [
      docsPanel,
      settingsPanel,
      imageUploadPanel,
      systemPromptPanel,
    ];

    // Check if panel is currently visible and if it's the image panel
    if (
      panel.style.display === "block" ||
      (panel === imageUploadPanel && panel.style.display === "flex")
    ) {
      panel.style.display = "none";
    } else {
      panels.forEach((p) => {
        p.style.display = "none";
      });

      // Check if it's the image panel to set as flex
      if (panel === imageUploadPanel) {
        panel.style.display = "flex";
      } else {
        panel.style.display = "block";
      }
    }
  }

  docsToggle.addEventListener("click", (event) => {
    event.preventDefault();
    togglePanel(docsPanel);
  });

  settingsToggle.addEventListener("click", (event) => {
    event.preventDefault();
    togglePanel(settingsPanel);
  });

  imageUploadToggle.addEventListener("click", (event) => {
    event.preventDefault();
    togglePanel(imageUploadPanel);
  });

  systemPromptToggle.addEventListener("click", (event) => {
    event.preventDefault();
    togglePanel(systemPromptPanel);
  });

  document.addEventListener("click", (event) => {
    const panels = [
      docsPanel,
      settingsPanel,
      imageUploadPanel,
      systemPromptPanel,
    ];
    const toggles = [
      docsToggle,
      settingsToggle,
      imageUploadToggle,
      systemPromptToggle,
    ];
    const outsidePanel = !panels.some((panel) => panel.contains(event.target));
    const outsideToggle = !toggles.some((toggle) =>
      toggle.contains(event.target),
    );

    if (outsidePanel && outsideToggle) {
      const clickedElement = event.target;
      const isFormElement =
        clickedElement.tagName === "INPUT" ||
        clickedElement.tagName === "TEXTAREA" ||
        clickedElement.tagName === "SELECT" ||
        clickedElement.tagName === "BUTTON";

      if (!isFormElement) {
        panels.forEach((panel) => (panel.style.display = "none"));
      }
    }
  });
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

    // Remove the image-upload input from the form data
    formData.delete("image-upload");

    submitForm(formData, submitUrl).then(successCallback).catch(errorCallback);
  }, 1000);

  form.addEventListener("input", function (event) {
    if (event.target.id !== "image-upload") {
      event.preventDefault();
      debouncedSubmit();
    }
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

function addToQueryHistory(query, response, base64Images, documentsUsed) {
  const queryResultsSection = document.getElementById("query-results-section");
  const currentQueryResponse = document.getElementById("current-query");

  // Create a new history entry
  const historyEntry = document.createElement("div");
  historyEntry.className = "history-entry";

  // Create the query and response elements
  const queryElement = document.createElement("div");
  queryElement.innerHTML = `<i class="nuicon-user-tie"></i><pre>${escapeHTML(
    query,
  )}</pre>`;

  const responseElement = document.createElement("div");
  responseElement.innerHTML = `<i class="nuicon-user-robot"></i><pre>${escapeHTML(
    response,
  )}</pre>`;

  // Add clipboard icon to the response element
  const clipboardIcon = createClipboardIcon("message");
  responseElement.appendChild(clipboardIcon);

  historyEntry.appendChild(queryElement);
  historyEntry.appendChild(responseElement);

  // Add the used images to the history entry
  if (base64Images && base64Images.length > 0) {
    const imagesContainer = document.createElement("div");
    imagesContainer.className = "history-images";
    base64Images.forEach((base64Image) => {
      const img = document.createElement("img");
      img.src = `data:image/png;base64,${base64Image}`;
      img.classList.add("history-image");
      imagesContainer.appendChild(img);
    });
    historyEntry.appendChild(imagesContainer);
  }

  if (documentsUsed) {
    const documentsUsedContainer = document.createElement("div");
    documentsUsedContainer.innerHTML = `<strong>Documents Used:</strong> ${escapeHTML(
      documentsUsed,
    )}`;
    historyEntry.appendChild(documentsUsedContainer);
  }

  // Add the delimiter after everything else
  const delimiter = document.createElement("hr");
  delimiter.className = "history-delimiter";
  historyEntry.appendChild(delimiter);

  // Insert the history entry before the current query-response
  queryResultsSection.insertBefore(historyEntry, currentQueryResponse);

  // Update the current query-response
  document.getElementById("user_query").textContent = "";
  document.getElementById("results").textContent = "";

  // Set the display of the query and response elements to none
  document.getElementById("user_query").parentNode.style.display = "none";
  document.getElementById("response_container").style.display = "none";
}
function createClipboardIcon(copyTarget) {
  let clipboardIcon = document.createElement("i");
  clipboardIcon.classList.add("nuicon-clipboard", "clipboard-icon");
  clipboardIcon.addEventListener("click", function (event) {
    event.stopPropagation();

    let textToCopy;
    if (copyTarget === "code") {
      textToCopy = this.parentNode.textContent;
    } else if (copyTarget === "message") {
      textToCopy = this.parentNode.querySelector("pre").textContent;
    }
    navigator.clipboard
      .writeText(textToCopy)
      .then(() => {
        showToast("Copied to clipboard!", "success");
      })
      .catch((err) => {
        showToast("Failed to copy!", "error");
        console.error("Failed to copy text:", err);
      });
  });

  return clipboardIcon;
}

function escapeHTML(str) {
  return str.replace(/[&<>'"]/g, (tag) => {
    const charsToReplace = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "'": "&#39;",
      '"': "&quot;",
    };
    return charsToReplace[tag] || tag;
  });
}

function toggleQuery() {
  if (!isQueryRunning) {
    queryDocument();
  } else {
    interruptQuery();
  }
}

const queryButton = document.getElementById("queryButton");
if (queryButton) {
  queryButton.addEventListener("click", toggleQuery);
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
  const uploadedImages = Array.from(imageUploadElement.files);

  const base64Images = await Promise.all(
    uploadedImages.map(encodeImageAsBase64),
  );

  const requestBody = {
    query: query,
    images: base64Images,
  };

  imageUploadElement.value = "";
  const imagePreviewsContainer = document.getElementById("image-previews");
  imagePreviewsContainer.innerHTML = "";

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
      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          break;
        }
        resultsSpan.textContent += decoder.decode(value);
        previousResponse += decoder.decode(value);
      }

      document.getElementById("results").textContent = previousResponse;

      addToQueryHistory(
        previousQuery,
        previousResponse,
        base64Images,
        documentsUsedSummary,
      );

      // Clear the image upload input and previews

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

  // Revert the pause button to a paper plane icon
  isQueryRunning = false;
  document.getElementById("queryIcon").classList.remove("nuicon-pause");
  document.getElementById("queryIcon").classList.add("nuicon-paper-plane");
}

document.addEventListener("DOMContentLoaded", function () {
  function syncValues(source, target) {
    target.value = source.value;
  }

  const topKRange = document.getElementById("top_k");
  const topKValue = document.getElementById("top_k_value");
  if (topKRange && topKValue) {
    topKRange.addEventListener("input", function () {
      syncValues(topKRange, topKValue);
    });
    topKValue.addEventListener("input", function () {
      syncValues(topKValue, topKRange);
    });
  }

  const thresholdRange = document.getElementById("threshold");
  const thresholdValue = document.getElementById("threshold_value");
  if (thresholdRange && thresholdValue) {
    thresholdRange.addEventListener("input", function () {
      syncValues(thresholdRange, thresholdValue);
    });
    thresholdValue.addEventListener("input", function () {
      syncValues(thresholdValue, thresholdRange);
    });
  }

  const temperatureRange = document.getElementById("temperature");
  const temperatureValue = document.getElementById("temperature-value");
  if (temperatureRange && temperatureValue) {
    temperatureRange.addEventListener("input", function () {
      syncValues(temperatureRange, temperatureValue);
    });
    temperatureValue.addEventListener("input", function () {
      syncValues(temperatureValue, temperatureRange);
    });
  }

  const topPRange = document.getElementById("top_p");
  const topPValue = document.getElementById("top-p-value");
  if (topPRange && topPValue) {
    topPRange.addEventListener("input", function () {
      syncValues(topPRange, topPValue);
    });
    topPValue.addEventListener("input", function () {
      syncValues(topPValue, topPRange);
    });
  }

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

function encodeImageAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result.split(",")[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

document
  .getElementById("image-upload")
  .addEventListener("change", function (e) {
    e.preventDefault();
    const files = Array.from(e.target.files);
    generateImagePreviews(files);
  });

function generateImagePreviews(files) {
  const imagePreviewContainer = document.getElementById("image-previews");
  imagePreviewContainer.innerHTML = ""; // Clear previous previews

  // Limit the number of previews to 5
  const limitedFiles = Array.from(files).slice(0, 5);

  limitedFiles.forEach((file) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const imgContainer = document.createElement("div");
      imgContainer.classList.add("image-preview");

      const img = document.createElement("img");
      img.src = e.target.result;
      img.dataset.file = escapeHTML(file.name); // Store the file name as a data attribute
      imgContainer.appendChild(img);

      const removeBtn = document.createElement("button");
      removeBtn.classList.add("remove-image");
      removeBtn.innerHTML = "&times;";
      removeBtn.addEventListener("click", () => {
        imgContainer.remove();
        removeImageFromFileList(file);
      });
      imgContainer.appendChild(removeBtn);

      imagePreviewContainer.appendChild(imgContainer);
    };
    reader.readAsDataURL(file);
  });
}

function removeImageFromFileList(fileToRemove) {
  const imageUploadElement = document.getElementById("image-upload");
  const fileList = Array.from(imageUploadElement.files);
  const updatedFileList = fileList.filter((file) => file !== fileToRemove);
  const dataTransfer = new DataTransfer();
  updatedFileList.forEach((file) => dataTransfer.items.add(file));
  imageUploadElement.files = dataTransfer.files;
}

function setupMessageInput() {
  let messageInput = document.getElementById("query");
  if (!messageInput) return;

  messageInput.addEventListener("input", function () {
    adjustTextareaHeight(this);
  });

  messageInput.addEventListener("keydown", function (e) {
    handleSubmitOnEnter(e, this);
  });
}

function adjustTextareaHeight(textarea) {
  requestAnimationFrame(() => {
    textarea.style.height = "auto";
    textarea.style.height = textarea.scrollHeight + "px";
  });
}

setupMessageInput();
let documentsUsedSummary = "";
document.addEventListener("DOMContentLoaded", (event) => {
  // eslint-disable-next-line no-unused-vars,no-undef
  var socket = io("/cwd");

  function appendDocumentsUsed(data) {
    const resultsSpan = document.getElementById("documents-used");
    resultsSpan.innerHTML = `<strong>Documents Used:</strong> ${escapeHTML(
      data.message,
    )}`;
  }

  socket.on("documents_used", function (documentsUsedSummary) {
    appendDocumentsUsed(documentsUsedSummary);
  });

  socket.on("documents_used", function (data) {
    documentsUsedSummary = data.message;
  });
});

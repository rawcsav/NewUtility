let isUploading = false;
let controller = new AbortController();
let signal = controller.signal;

function getCsrfToken() {
  return document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute("content");
}

document.addEventListener("DOMContentLoaded", function () {
  const fileInput = document.getElementById("fileInput");

  fileInput.addEventListener("change", function () {
    uploadDocuments();
  });

  const queryInput = document.getElementById("query");
  queryInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
      event.preventDefault();
      queryDocument();
    }
  });
});

async function uploadDocuments() {
  showAlert("Uploading...", "info", "upload");
  updateQueryButtonStatus(true);

  isUploading = true;

  const formData = new FormData(document.querySelector("#uploadForm"));
  const allowedFileTypes = ["docx", "pdf", "txt"];
  const existingFiles = [
    ...document.querySelectorAll("#uploaded_docs_list li"),
  ].map((li) => li.textContent.trim());

  // Create a new FormData instance to hold valid files
  const filteredFormData = new FormData();

  for (let [key, value] of formData.entries()) {
    if (key === "file") {
      const file = value;
      const fileExtension = file.name.split(".").pop().toLowerCase();

      if (!allowedFileTypes.includes(fileExtension)) {
        showAlert(
          `The file "${file.name}" is not an allowed type. Only 'docx', 'pdf', or 'txt' files are allowed.`,
          "warning",
          "upload",
        );
        continue;
      }

      if (existingFiles.includes(file.name)) {
        showAlert(
          `The file "${file.name}" is already uploaded. Skipping duplicate.`,
          "warning",
          "upload",
        );
        continue;
      }

      // If the file passes all checks, add it to the filtered FormData
      filteredFormData.append(key, file);
    } else {
      // For other form fields, directly append to filteredFormData
      filteredFormData.append(key, value);
    }
  }

  if (filteredFormData.getAll("file").length === 0) {
    showAlert("No valid files to upload.", "danger", "upload");
    return;
  }

  try {
    const response = await fetch("/cwd/upload", {
      method: "POST",
      headers: {
        "X-CSRFToken": getCsrfToken(),
      },
      body: filteredFormData,
    });

    const data = await response.json();

    if (data.status === "success") {
      let uploadedCount = 0;
      const docList = document.getElementById("uploaded_docs_list");

      for (let msg of data.messages) {
        if (msg.includes("processed successfully")) {
          uploadedCount += 1;
          const docNameWithExtension = msg.split(" ")[1];
          const docName = docNameWithExtension.split(".")[0]; // Remove the extension

          const listItem = document.createElement("li");

          // Create and configure the delete button
          const deleteButton = document.createElement("button");
          deleteButton.className = "delete-btn";
          deleteButton.textContent = "X";
          deleteButton.onclick = function () {
            removeFile(docNameWithExtension);
          }; // Attach the removeFile function

          // Add the checkbox and the document name (without extension)
          listItem.innerHTML = `<input type="checkbox" name="selected_docs" value="${docNameWithExtension}" checked> ${docName}`;

          // Append the delete button to the list item
          listItem.appendChild(deleteButton);

          // Finally, append the list item to the document list
          docList.appendChild(listItem);
        }
      }

      if (uploadedCount > 0) {
        showAlert(
          `${uploadedCount} files uploaded successfully.`,
          "success",
          "upload",
        );
      } else {
        showAlert("No files uploaded successfully.", "danger", "upload");
      }
    } else {
      for (let msg of data.messages) {
        showAlert(msg, "danger", "upload");
      }
    }
  } catch (error) {
    showAlert(
      "There was an error processing your request.",
      "danger",
      "upload",
    );
  }

  // Reset the isUploading flag and update the query button's status
  isUploading = false;
}

function updateQueryButtonStatus(isUploadingStatus = false) {
  const queryInput = document.getElementById("query");
  const queryButton = document.getElementById("queryButton");

  if (isUploadingStatus || isUploading) {
    queryInput.disabled = true;
    queryButton.disabled = true;
    queryInput.placeholder = "Uploading...";
  } else {
    queryInput.disabled = false;
    queryButton.disabled = false;
    queryInput.placeholder = "Enter your query here...";
  }
}

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

async function queryDocument() {
  document.getElementById("interruptButton").disabled = false;
  const checkboxes = document.querySelectorAll(
    'input[name="selected_docs"]:checked',
  );

  if (checkboxes.length === 0) {
    return;
  }

  const query = document.getElementById("query").value.trim();

  if (query === "") {
    showAlertInChatbox("Query cannot be empty.", "warning");
    return;
  }

  const userQueryElement = document.getElementById("user_query");
  userQueryElement.parentNode.style.display = "block";
  userQueryElement.textContent = query;
  document.getElementById("query").value = "";

  const resultsDiv = document.getElementById("results");
  resultsDiv.innerHTML = "<pre></pre>";
  // eslint-disable-next-line no-unused-vars
  const preElement = resultsDiv.querySelector("pre");
  const selectedDocs = [];
  checkboxes.forEach((checkbox) => {
    selectedDocs.push(checkbox.value);
  });

  // Update previousQuery for the next iteration
  previousQuery = query;
  previousResponse = "";

  try {
    const response = await fetch("/cwd/query", {
      method: "POST",

      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-CSRFToken": getCsrfToken(),
      },
      body: `query=${encodeURIComponent(
        query,
      )}&selected_docs=${encodeURIComponent(selectedDocs.join(","))}`,
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

      // At this point, the whole response has been read
      document.getElementById("results").textContent = previousResponse;

      // Add the query and response to the history as soon as they are completed
      addToQueryHistory(previousQuery, previousResponse);

      // Reset previousResponse for the next request
      previousResponse = "";
    } else {
      showAlertInChatbox("Error occurred while querying.", "danger");
    }
  } catch (error) {
    if (error.name === "AbortError") {
      showAlertInChatbox("Interrupted!", "warning");
    } else {
      showAlertInChatbox("Error occurred while querying.", "danger");
    }
  }
}

function interruptQuery() {
  controller.abort();
  controller = new AbortController();
  signal = controller.signal;

  const resultsSpan = document.getElementById("results");
  if (resultsSpan.lastChild) {
    resultsSpan.removeChild(resultsSpan.lastChild);
  }

  document.getElementById("interruptButton").disabled = true;
  document.getElementById("queryButton").disabled = false;
}

async function removeFile(fileName) {
  try {
    const response = await fetch(
      `/cwd/remove_file?fileName=${encodeURIComponent(fileName)}`,
      {
        method: "DELETE",
      },
    );

    if (response.ok) {
      // Log the fileName for debugging
      console.log("Attempting to remove file with name:", fileName);

      // Remove the list item from the DOM
      const listItem = document.querySelector(`[data-file-name='${fileName}']`);

      // Check if listItem exists before trying to remove it
      if (listItem) {
        listItem.remove();
      } else {
        console.warn("No listItem found with the given fileName.");
        showAlert("Failed to locate the file in the UI.", "warning", "upload");
      }
    } else {
      showAlert(
        "Failed to delete the file. Please try again.",
        "danger",
        "upload",
      );
    }
  } catch (err) {
    console.error("Failed to delete the file", err);
    showAlert(
      "An error occurred while trying to delete the file.",
      "danger",
      "upload",
    );
  }
}

function showAlert(message, type, context = "apiKey") {
  let alertsDiv;
  switch (context) {
    case "upload":
      alertsDiv = document.querySelector(".uploadAlerts");
      break;
    case "query":
      alertsDiv = document.getElementById("queryAlertInsideInput");
      break;
    default:
      alertsDiv = document.querySelector(".apiKeyAlerts");
  }

  // For the alert inside the input box, we directly set the text content
  if (context === "query") {
    alertsDiv.textContent = message;
  } else {
    // For the other alerts, we append a new div with the message
    alertsDiv.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
  }
}

function showAlertInChatbox(message, type) {
  const resultsSpan = document.getElementById("results");
  const responseLabel = document.getElementById("responseLabel"); // Fetching the element by ID

  // Clear existing content
  resultsSpan.textContent = "";

  // Insert the alert message
  resultsSpan.innerHTML = `<div class='alert alert-${type}'>${message}</div>`;

  // Hide the 'Response:' label
}

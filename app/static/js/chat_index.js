let isUploading = false;

// Initially hide the Submit button

async function uploadDocuments() {
  showAlert("Uploading...", "info", "upload");
  updateQueryButtonStatus(true);

  // Check if the API key is set
  if (document.getElementById("uploadButton").disabled) {
    showAlert("Please set your OpenAI API Key first.", "danger", "upload");
    return;
  }

  isUploading = true;

  const formData = new FormData(document.querySelector("#uploadForm"));

  // Check for duplicates before uploading
  const existingFiles = [
    ...document.querySelectorAll("#uploaded_docs_list li"),
  ].map((li) => li.textContent.trim());
  for (let file of formData.getAll("file")) {
    if (existingFiles.includes(file.name)) {
      showAlert(
        `The file "${file.name}" is already uploaded. Skipping duplicate.`,
        "warning",
        "upload",
      );
      formData.delete("file"); // Remove the file from formData to prevent upload
    }
  }

  try {
    const response = await fetch("/upload", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (data.status === "success") {
      let uploadedCount = 0;
      const docList = document.getElementById("uploaded_docs_list");

      for (let msg of data.messages) {
        if (msg.includes("processed successfully")) {
          uploadedCount += 1;
          const docNameWithExtension = msg.split(" ")[1];
          const docName = docNameWithExtension.split(".")[0];
          const listItem = document.createElement("li");
          listItem.innerHTML = `<input type="checkbox" name="selected_docs" value="${docName}" checked> ${docName}`;
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
  showQueryButtonIfNeeded();
}

function updateQueryButtonStatus(isUploadingStatus = false) {
  const queryButton = document.getElementById("queryButton");
  const queryStatus = document.getElementById("queryStatus"); // Get the new status message element

  if (isUploadingStatus || isUploading) {
    queryButton.disabled = true;
    queryStatus.textContent = "Uploading..."; // Update the status message
  } else {
    queryButton.disabled = false;
    queryStatus.textContent = ""; // Clear the status message
  }
}

function showQueryButtonIfNeeded() {
  const queryButton = document.getElementById("queryButton");
  const queryStatus = document.getElementById("queryStatus"); // Get the new status message element
  const hasAPIKey = !document.getElementById("uploadButton").disabled;
  const hasUploadedFiles =
    document.querySelectorAll("#uploaded_docs_list li").length > 0;
  const shouldEnable = hasAPIKey && hasUploadedFiles && !isUploading;

  queryButton.disabled = !shouldEnable;
  queryStatus.textContent = shouldEnable ? "" : "Waiting for docs..."; // Update the status message
}

async function queryDocument() {
  const checkboxes = document.querySelectorAll(
    'input[name="selected_docs"]:checked',
  );

  if (checkboxes.length === 0) {
    showAlert(
      "Please upload at least one document before querying.",
      "danger",
      "query",
    );
    return;
  }

  const query = document.getElementById("query").value;

  // Show the 'Query:' text and set its value
  const userQueryElement = document.getElementById("user_query");
  userQueryElement.parentNode.style.display = "block";
  userQueryElement.textContent = query;
  const resultsDiv = document.getElementById("results");
  resultsDiv.innerHTML = "<pre></pre>";
  const preElement = resultsDiv.querySelector("pre");
  const selectedDocs = [];
  checkboxes.forEach((checkbox) => {
    selectedDocs.push(checkbox.value);
  });

  try {
    const response = await fetch("/query", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: `query=${encodeURIComponent(
        query,
      )}&selected_docs=${encodeURIComponent(selectedDocs.join(","))}`,
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
      }
    } else {
      showAlert("Error querying the document", "danger", "query");
    }
  } catch (error) {
    showAlert("There was an error processing your request.", "danger", "query");
  }
}

function setAPIKey() {
  const formData = new FormData(document.querySelector("#apiKeyForm"));

  fetch("/set_api_key", {
    method: "POST",
    body: formData,
  })
    .then((response) => {
      console.log("Response received:", response);
      if (response.ok) {
        console.log("Response is OK.");
        document.getElementById("uploadButton").disabled = false;

        // Clear any previous alerts in .apiKeyAlerts
        document.querySelector(".apiKeyAlerts").innerHTML = "";

        // Show the API Key set successfully message
        document.getElementById("apiKeyStatus").style.display = "block";

        // Determine if the "Submit" button should be shown
        showQueryButtonIfNeeded();
      } else {
        console.log("Response is not OK.");
        document.getElementById("apiKeyStatus").style.display = "none"; // Hide the success message
        showAlert("Error. Please check the key and try again.", "danger");
      }
    })
    .catch((error) => {
      console.log("Error occurred:", error);
      document.getElementById("apiKeyStatus").style.display = "none"; // Hide the success message
      showAlert("Error setting the API Key.", "danger");
    });
}

function showAlert(message, type, context = "apiKey") {
  let alertsDiv;
  switch (context) {
    case "upload":
      alertsDiv = document.querySelector(".uploadAlerts");
      break;
    case "query":
      alertsDiv = document.querySelector(".queryAlerts");
      break;
    default:
      alertsDiv = document.querySelector(".apiKeyAlerts");
  }

  // This line sets the alertsDiv's innerHTML to the new message instead of appending
  alertsDiv.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
}

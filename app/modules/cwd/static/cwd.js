let controller = new AbortController();
let signal = controller.signal;

function getCsrfToken() {
  return document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute("content");
}

document.addEventListener("DOMContentLoaded", function () {
  const queryInput = document.getElementById("query");
  queryInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
      event.preventDefault();
      queryDocument();
    }
  });
});

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

document.addEventListener("DOMContentLoaded", function () {
  // Find all delete buttons
  const deleteButtons = document.querySelectorAll(".delete-btn");

  // Attach click event listeners to each delete button
  deleteButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const documentId = this.getAttribute("data-doc-id");
      console.log(`Attempting to delete document with ID: ${documentId}`); // For debugging

      // Attempt to delete the document from the server
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
            throw new Error("Server failed to delete the document.");
          }
          // If the server responds OK, remove the document's UI element
          console.log("Document deleted successfully from the server."); // For debugging
          const listItem = this.closest("li");
          if (listItem) {
            listItem.remove(); // Immediately remove the element from the UI
            console.log("Document removed from UI."); // For debugging
          }
        })
        .catch((error) => {
          console.error("Deletion error:", error);
        });
    });
  });
});

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

async function uploadDocuments() {
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
        showAlert(`${uploadedCount} files uploaded successfully.`, "success");
      } else {
        showAlert("No files uploaded successfully.", "danger");
      }
    } else {
      for (let msg of data.messages) {
        showAlert(msg, "danger");
      }
    }
  } catch (error) {
    showAlert("There was an error processing your request.", "danger");
  }
}

function showAlert(message, type) {
  const alertsDiv = document.querySelector(".alerts");
  alertsDiv.innerHTML += `<div class="alert alert-${type}">${message}</div>`;
}

async function queryDocument() {
  const checkboxes = document.querySelectorAll(
    'input[name="selected_docs"]:checked',
  );

  if (checkboxes.length === 0) {
    showAlert("Please upload at least one document before querying.", "danger");
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
      resultsSpan.innerHTML =
        '<span style="color:red;">Error querying the document.</span>';
    }
  } catch (error) {
    resultsSpan.innerHTML =
      '<span style="color:red;">There was an error processing your request.</span>';
  }
}

function setAPIKey() {
  const formData = new FormData(document.querySelector("#apiKeyForm"));

  fetch("/set_api_key", {
    method: "POST",
    body: formData,
  })
    .then((response) => response.text())
    .then((data) => {
      if (data.includes("successfully")) {
        document.getElementById("docs-query-section").style.display = "block";
      }
    })
    .catch((error) => {
      showAlert("Error setting the API Key.", "danger");
    });
}

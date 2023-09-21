let isAPIKeySet = false;

document.addEventListener('DOMContentLoaded', async function () {
  isAPIKeySet = await checkAPIKeyStatus();
});

let eventSource = new EventSource('/status');

// Find the 'status' element in the DOM
let statusElement = document.getElementById('status');

// Listen for new messages and update the DOM
eventSource.onmessage = function (event) {
  let newElement = document.createElement('div');
  newElement.textContent = event.data;
  statusElement.appendChild(newElement);
};

async function setAPIKey() {
  const apiKey = $("input[name='api_key']").val();
  const formData = new FormData();
  formData.append('api_key', apiKey);

  try {
    const response = await fetch('/set_api_key', {
      method: 'POST',
      body: formData,
    });

    if (response.ok) {
      document.getElementById('fileInput').disabled = false;
      document.querySelector('.apiKeyAlerts').innerHTML = '';
      document.getElementById('apiKeyStatus').style.display = 'block';

      isAPIKeySet = await checkAPIKeyStatus();
      showQueryButtonIfNeeded(isAPIKeySet);
    } else {
      showAlert('Error. Please check the key and try again.', 'danger');
    }
  } catch (error) {
    showAlert('Error setting the API Key.', 'danger');
  }
}

async function checkAPIKeyStatus() {
  const response = await fetch('/check_api_key');
  const data = await response.json();
  const isSet = data.status === 'set';

  if (data.status === 'set') {
    isAPIKeySet = true;
    document.getElementById('fileInput').disabled = false;
    document.getElementById('apiKeyStatus').style.display = 'block';
    showQueryButtonIfNeeded(true); // Pass a parameter to indicate API key is set
  } else {
    document.getElementById('fileInput').disabled = true;
    document.getElementById('apiKeyStatus').style.display = 'none';
  }
  return isSet;
}
// eslint-disable-next-line no-unused-vars
function toggleLanguageDiv() {
  var transcribeSelected = document.getElementById('transcribe').checked;
  document.getElementById('language').disabled = !transcribeSelected;
}

// eslint-disable-next-line no-unused-vars
async function processForm() {
  var files = document.getElementById('audio-files').files;
  var totalSize = 0;
  var alertContainer = document.getElementById('alert-container');
  var supportedFormats = [
    'audio/mp3',
    'audio/mp4',
    'audio/mpeg',
    'audio/mpga',
    'audio/x-m4a',
    'audio/wav',
    'audio/webm',
    'video/mp4',
    'video/webm',
    'video/mpeg',
  ]; // Add or remove formats as needed

  if (typeof isAPIKeySet === 'undefined') {
    isAPIKeySet = await checkAPIKeyStatus(); // Set it here for the first time
  }

  alertContainer.innerHTML = '';

  function setAlert(message, type) {
    var className =
      type === 'success'
        ? 'custom-alert custom-success'
        : 'custom-alert custom-danger';
    alertContainer.innerHTML = `<div class='${className}'>${message}</div>`;
  }

  if (!isAPIKeySet) {
    setAlert(
      'API key is not set. Please provide your OpenAI API key before uploading.',
      'danger',
    );
    return; // Stop the function if the API key is not set
  }

  if (files.length > 1) {
    setAlert('You can only select one file at a time.', 'danger');
    return;
  }

  if (files.length === 1 && !supportedFormats.includes(files[0].type)) {
    setAlert(
      'Unsupported file format. Please select a supported format.',
      'danger',
    );
    return;
  }

  for (var i = 0; i < files.length; i++) {
    totalSize += files[i].size;
  }
  if (totalSize > 52428800) {
    setAlert(
      'Total file size exceeds 50MB. Please select a smaller file.',
      'danger',
    );
    return;
  }

  setAlert('File uploaded successfully!', 'success');
}

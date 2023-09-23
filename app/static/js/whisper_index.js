let isAPIKeySet = false;

function showAlert(message, type, context = 'apiKey') {
  let alertsDiv;
  switch (context) {
    case 'upload':
      alertsDiv = document.querySelector('.uploadAlerts');
      break;
    case 'transcribe':
      alertsDiv = document.querySelector('.transcribeAlerts');
      break;
    default:
      alertsDiv = document.querySelector('.apiKeyAlerts');
  }
  {
    // For the other alerts, we append a new div with the message
    alertsDiv.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
  }
}

document.addEventListener('DOMContentLoaded', async function () {
  isAPIKeySet = await checkAPIKeyStatus();
});

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
  const isSet = data.status === 'success';

  if (data.status === 'success') {
    isAPIKeySet = true;
    document.getElementById('fileInput').disabled = false;
    document.getElementById('apiKeyStatus').style.display = 'block';
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

async function uploadFile() {
  const file = document.getElementById('fileInput').files[0];
  const totalSize = file.size;

  if (!isAPIKeySet) {
    showAlert('Please set your OpenAI API Key first.', 'danger', 'upload');
    return;
  }
  if (totalSize > 52428800) {
    showAlert(
      'Total file size exceeds 50MB. Please select a smaller file.',
      'danger',
      'upload',
    );
    return;
  }

  if (!supportedFormats.includes(file.type)) {
    showAlert(
      'Unsupported file format. Please select a supported format.',
      'danger',
      'upload',
    );
    return;
  }

  const formData = new FormData();
  formData.append('audio_file', file); // Change 'file' to 'audio_file'

  const response = await fetch('/upload_audio', {
    method: 'POST',
    body: formData,
  });

  if (response.ok) {
    const data = await response.json();
    showAlert('File uploaded successfully.', 'success', 'upload');
  } else {
    showAlert('File uploaded failed.', 'danger', 'upload');
  }
}
// eslint-disable-next-line no-unused-vars
async function processForm() {
  if (!isAPIKeySet) {
    showAlert('Please set the API Key first', 'danger');
    return;
  }

  showAlert('Transcription in progress...', 'info', 'transcribe');

  const translate =
    document.querySelector('input[name="translate"]:checked').value === 'yes'; // Make sure the value is a boolean or string that the backend expects
  const use_timestamps = document.querySelector(
    'input[name="use_timestamps"]',
  ).checked;

  const language = document.getElementById('language').value;

  const formData = new FormData();
  formData.append('translate', translate);
  formData.append('use_timestamps', use_timestamps); // Changed to "use_timestamps"
  formData.append('language', language);

  try {
    const response = await fetch('/transcribe', {
      method: 'POST',
      body: formData,
    });

    if (response.ok) {
      const data = await response.json();
      const downloadLink = data.download_url; // Assume download link is returned in the JSON response
      showAlert('Transcription successful.', 'success', 'transcribe');
      document.querySelector(
        '.transcribeAlerts',
      ).innerHTML += `<a href="${downloadLink}" class="btn btn-primary">Download Transcript</a>`;
    } else {
      showAlert(
        'Transcription failed. Please try again.',
        'danger',
        'transcribe',
      );
    }
  } catch (error) {
    showAlert('Network error occurred.', 'danger', 'transcribe');
  }
}

function toggleLanguageDiv() {
  var transcribeSelected = document.getElementById("transcribe").checked;
  document.getElementById("language").disabled = !transcribeSelected;
}

function processForm() {
  var files = document.getElementById("audio-files").files;
  var totalSize = 0;
  for (var i = 0; i < files.length; i++) {
    totalSize += files[i].size;
  }
  if (totalSize > 52428800) {
    alert("Total file size exceeds 50MB. Please select smaller files.");
  }
}

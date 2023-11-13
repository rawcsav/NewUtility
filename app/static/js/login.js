document.getElementById('login-form').onsubmit = function(event) {
       event.preventDefault();

       var username = document.getElementById('username').value;
       var password = document.getElementById('password').value;

       // Perform the login request using Fetch API or XMLHttpRequest
       // Here's an example using Fetch API
       fetch('/auth/login', {
           method: 'POST',
           headers: {
               'Content-Type': 'application/json'
           },
           body: JSON.stringify({ username: username, password: password })
       })
       .then(response => response.json())
       .then(data => {
           if (data.status === 'success') {
               window.location.href = data.redirect; // Redirect on success
           } else {
               // Show error message
               document.getElementById('message-container').innerText = data.message;
           }
       })
       .catch(error => {
           console.error('Error:', error);
       });
   };

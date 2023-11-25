document.getElementById('upload-form').addEventListener('submit', async (e) => { // Corrected the ID reference
    e.preventDefault();
    let fileInput = document.getElementById('file-upload'); // Using consistent method for element selection
    let file = fileInput.files[0];

    // This function will handle the upload
    if (file) { // Only proceed if a file is selected
        let videoFormat = file.type;
        await uploadFile(file);
        alert('File uploading!');
    } else {
        alert('Please select a file to upload.');
    }
});

async function uploadFile(file) {
    // Get the pre-signed URL from your API
    const response = await fetch('__API_ENDPOINT__', {
        method: 'GET',
        headers: {
            'filename': file.name, // You can pass the filename as a header to your Lambda
            'video-format': file.type // Sending the detected video format
        }
    });

    if (response.ok) {
        let result = await response.json();

        if (result) {
            const presignedUrl = result.upload_url;
            const xhr = new XMLHttpRequest();
            xhr.open('PUT', presignedUrl, true);

            // Event listener to update the progress bar
            xhr.upload.onprogress = function (event) {
                if (event.lengthComputable) {
                    var percentComplete = Math.round((event.loaded / event.total) * 100);
                    var progressBar = document.getElementById('progress-bar');
                    progressBar.style.width = percentComplete + '%';
                    progressBar.textContent = percentComplete + '%'; // Add text inside the progress bar
                }
            };

            xhr.withCredentials = false;
            xhr.setRequestHeader('Content-Type', file.type);
            xhr.onload = function () {
                if (xhr.status === 200) {
                    alert('File uploaded.');
                }
            };
            xhr.onerror = function () {
                alert('Error uploading file.');
            };
            xhr.send(file);
        } else {
            alert('Unexpected API response format');
        }
    } else {
        alert('API request failed with status: ' + response.status);
    }
}

document.getElementById('query-button').addEventListener('click', function() {
    const videoId = document.getElementById('video-id-input').value;
    if (videoId) {
        queryVideoDescription(videoId);
    } else {
        alert('Please enter a video ID.');
    }
});

function queryVideoDescription(videoId) {
    // Construct the API URL with the video ID
    const apiUrl = `__API_ENDPOINT__video/${videoId}`;
    
    // Make the API call using fetch or XMLHttpRequest
    fetch(apiUrl)
        .then(response => {
            if (response.ok) {
                return response.json(); // assuming the response is JSON
            }
            throw new Error('Network response was not ok.');
        })
        // .then(data => {
        //     // Display the video description in your HTML page
        //     document.getElementById('video-description').textContent = data.description;
        // })
        // .catch(error => {
        //     console.error('There has been a problem with your fetch operation:', error);
        // });

        .then(data => {
            // Display the video description
            document.getElementById('video-description').textContent = data.description;
    
            // Additionally, display the full response in the new element
            document.getElementById('video-response').textContent = JSON.stringify(data, null, 2);
        })
        .catch(error => {
            console.error('There has been a problem with your fetch operation:', error);
            document.getElementById('video-response').textContent = 'Error: ' + error.message;
        });
}

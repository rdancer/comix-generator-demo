function resetErrors() {
    document.getElementById('console').textContent = '';
}

document.getElementById('generate-button').addEventListener('click', function() {
    resetErrors();
    let button = document.getElementById('generate-button');
    let title = document.getElementById('comix-title').value;
    let captions = [
        document.getElementById('caption1').value,
        document.getElementById('caption2').value,
        document.getElementById('caption3').value
    ];

    // strip leading and trailing whitespace from title and captions
    title = title.trim();
    captions = captions.map(caption => caption.trim());

    // Check that the captions are all there, and not empty, and if not, complain loudly
    // if (title === '') {
    //     alert('Please enter a title');
    //     return;
    // }
    if (captions.some(caption => caption === '')) {
        alert('Please enter all three captions');
        return;
    }

    // Disable the button and show spinner
    button.disabled = true;
    let originalButtonText = button.textContent;
    button.innerHTML = 'generating, please wait <span style="font-family: monospace; display: inline-block; width: 1ch;">|</span>'; // Initial state of spinner with monospaced font
    let spinnerStates = ['|', '/', '-', '\\'];
    let currentSpinnerIndex = 0;
    let spinnerInterval = setInterval(() => {
        currentSpinnerIndex = (currentSpinnerIndex + 1) % spinnerStates.length;
        button.querySelector('span').textContent = spinnerStates[currentSpinnerIndex];
    }, 250);
    
    // Function to stop spinner, clear timeout, and re-enable button
    function resetButtonState() {
        clearInterval(spinnerInterval);
        clearTimeout(timeoutId); // Safe to call even if timeout hasn't triggered
        button.textContent = originalButtonText;
        button.disabled = false;
    }

    // Set up a 2-minute timeout
    let timeoutId = setTimeout(() => {
        resetButtonState();
        alert('This is taking too long. Please try again.');
    }, 120_000); // 2 minutes

    fetch('https://api.comix-generator.rdancer.org/generate-images', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ title: title, captions: captions })
    })
    .then(response => {
        if (!response.ok) {
            // If the response is not ok, throw an error with the status text
            return response.json().then(err => {
                throw new Error(err.error || 'Unknown error');
            });
        }
        return response.json();
    })
        .then(data => {
        // Handle the images data from the response
        data.images.forEach((imageData, index) => {
            let imgElement = document.getElementById('image' + (index + 1));
            imgElement.src = `data:${imageData.content_type};base64,${imageData.base64}`;
            imgElement.classList.add('generated');
            console.log('Prompt for image ' + (index + 1) + ': ' + imageData.prompt); // For debugging
        });
        
        // Handle the final composite image data
        let finalImageElement = document.getElementById('final-image');
        finalImageElement.src = `data:${data.finalImage.content_type};base64,${data.finalImage.base64}`;
        console.log('Prompt for final image: ' + data.finalImage.prompt); // For debugging
    })
    .catch(error => {
        console.error('Error:', error);
        resetButtonState(); // Reset button state in case of error
        document.getElementById('console').textContent = error;
    })
    .finally(() => {
        resetButtonState(); // Reset button state after handling data
    })
});

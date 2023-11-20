document.getElementById('generate-button').addEventListener('click', function() {
    let title = document.getElementById('comix-title').value;
    let captions = [
        document.getElementById('caption1').value,
        document.getElementById('caption2').value,
        document.getElementById('caption3').value
    ];

    fetch('https://api.comix-generator.rdancer.org/generate-images', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ title: title, captions: captions })
    })
    .then(response => response.json())
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
    });
});

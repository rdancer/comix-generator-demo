# app.py (Flask Backend)

from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont
import io
import base64

app = Flask(__name__)
CORS(app)

@app.route('/generate-images', methods=['POST'])
def generate_images():
    data = request.json
    captions = data['captions']
    
    # Placeholder for DALL-E image generation based on captions
    images = [generate_placeholder_image(caption) for caption in captions]
    
    # Placeholder for creating a composite image from generated images
    final_image = create_composite_image(images, captions)
    
    images_data = [{
        'content_type': 'image/jpeg',
        'base64': image_to_base64(image, 'JPEG'),
        'prompt': caption
    } for caption, image in zip(captions, images)]
    
    final_image_data = {
        'content_type': 'image/png',
        'base64': image_to_base64(final_image, 'PNG'),
        'prompt': 'Composite image'
    }
    
    return jsonify({
        'images': images_data,
        'finalImage': final_image_data
    })

def generate_placeholder_image(caption):
    # This function would interface with DALL-E to generate an image
    # For now, it returns a placeholder image with the caption
    image = Image.new('RGB', (400, 400), color='white')
    draw = ImageDraw.Draw(image)
    draw.text((10, 10), caption, fill='black')
    return image

def create_composite_image(images, captions):
    image_width, image_height = images[0].size
    gap = 10  # White gap between images
    border = 3  # Border width around each image
    caption_height = 40  # Space for the caption text

    # Total dimensions including borders and gaps
    total_width = (image_width * 3) + (gap * 2) + (border * 6)
    total_height = image_height + caption_height + (border * 2)

    final_image = Image.new('RGB', (total_width, total_height), 'white')
    draw = ImageDraw.Draw(final_image)

    # Draw images with borders and captions
    for i, (image, caption) in enumerate(zip(images, captions)):
        # Calculate x offset for each image considering previous images, gaps, and borders
        x_offset = (image_width + gap + border * 2) * i
        # Paste image onto the final image with an offset for borders
        final_image.paste(image, (x_offset + border, border))
        # Draw border around the image
        draw.rectangle([x_offset, 0, x_offset + image_width + (border * 2), image_height + (border * 2)], outline='black', width=border)
        # Draw caption below the image
        draw.text((x_offset + border, image_height + (border * 2)), caption, fill='black', font=ImageFont.load_default())

    return final_image

def image_to_base64(image, format):
    buffered = io.BytesIO()
    image.save(buffered, format=format)
    image_bytes = buffered.getvalue()
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    return image_base64

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

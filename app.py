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
    title = data['title']
    
    # Placeholder for DALL-E image generation based on captions
    images = [generate_placeholder_image(caption) for caption in captions]
    
    # Placeholder for creating a composite image from generated images
    final_image = create_composite_image(images, captions, title)
    
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

def create_composite_image(images, captions, title):
    image_width, image_height = images[0].size
    gap = 10  # White gap between images
    border = 3  # Border width around each image
    title_height = 24  # Space for the title text
    caption_height = 24  # Space for the caption text
    title_space = 30  # Additional space reserved for the title at the top

    # Total dimensions including borders, gaps, and title space
    total_width = (image_width * 3) + (gap * 2) + (border * 6)
    total_height = image_height + caption_height + title_space + (border * 4)

    # Create the final composite image with additional space for title
    final_image = Image.new('RGB', (total_width, total_height), 'white')
    draw = ImageDraw.Draw(final_image)

    # Define the fonts for title and captions
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)  # Bold font for title
        caption_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)  # Regular font for captions
    except IOError:
        title_font = ImageFont.load_default()
        caption_font = ImageFont.load_default()

    # Draw the title at the top left
    draw.text((border, border), title, fill='black', font=title_font)

    # Draw images with borders and captions
    for i, (image, caption) in enumerate(zip(images, captions)):
        # Calculate x offset for each image considering previous images, gaps, and borders
        x_offset = (image_width + gap + border * 2) * i
        # Paste image onto the final image with an offset for borders and title space
        final_image.paste(image, (x_offset + border, border + title_space))
        # Draw border around the image
        draw.rectangle(
            [x_offset, title_space, x_offset + image_width + (border * 2), title_space + image_height + (border * 2)],
            outline='black', width=border)
        # Draw caption below the image
        draw.text(
            (x_offset + border, title_space + image_height + (border * 2)),
            caption, fill='black', font=caption_font)

    return final_image
def image_to_base64(image, format):
    buffered = io.BytesIO()
    image.save(buffered, format=format)
    image_bytes = buffered.getvalue()
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    return image_base64

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

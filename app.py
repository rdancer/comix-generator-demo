# app.py (Flask Backend)

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont
import io

app = Flask(__name__)
CORS(app)  # Enable CORS for all domains on all routes

@app.route('/generate_images', methods=['POST'])
def generate_images():
    captions = request.json['captions']
    images = [generate_placeholder_image() for _ in captions]
    final_image = create_composite_image(images, captions)
    img_byte_arr = io.BytesIO()
    final_image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return send_file(img_byte_arr, mimetype='image/png', as_attachment=True, download_name="composite.png")

def generate_placeholder_image():
    # This function would interface with DALL-E to generate an image
    # For now, it returns a placeholder image
    return Image.new('RGB', (400, 400), color='white')

def create_composite_image(images, captions):
    image_height = max(image.size[1] for image in images)
    caption_height = 40  # Allocate space for caption text
    total_height_per_segment = image_height + caption_height
    total_width = max(image.size[0] for image in images)
    final_image = Image.new('RGB', (total_width, total_height_per_segment * len(images)), 'white')
    
    # Use a truetype font if available
    # font = ImageFont.truetype("arial.ttf", 32)
    font = ImageFont.load_default()
    
    y_offset = 0
    for i, image in enumerate(images):
        final_image.paste(image, (0, y_offset))
        y_offset += image_height
        draw = ImageDraw.Draw(final_image)
        draw.text((10, y_offset), captions[i], fill="black", font=font)
        y_offset += caption_height  # Move to the next image segment position
    
    return final_image

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

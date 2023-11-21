# app.py (Flask Backend)

import openai
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import textwrap
import os

app = Flask(__name__)
CORS(app)

# openai.api_key = os.getenv('OPENAI_API_KEY') # This is the default

@app.route('/generate-images', methods=['POST'])
def generate_images():
    data = request.json
    captions = [caption.strip() for caption in data['captions']]
    title = data['title']

    # Generate individual panels using DALL-E image generation based on captions
    images = []
    revised_prompts = []
    for caption in captions:
        image, revised_prompt = generate_image(caption)
        images.append(image)
        revised_prompts.append(revised_prompt)

    # Compose the full strip from generated images
    final_image = create_composite_image(images, captions, title)

    images_data = [{
        'content_type': 'image/jpeg',
        'base64': image_to_base64(image, 'JPEG'),
        'original_prompt': caption,
        'revised_prompt': revised_prompt
    } for caption, revised_prompt, image in zip(captions, revised_prompts, images)]
    
    final_image_data = {
        'content_type': 'image/png',
        'base64': image_to_base64(final_image, 'PNG'),
    }
    
    return jsonify({
        'images': images_data,
        'finalImage': final_image_data
    })

def generate_image(caption: str) -> (Image, str):
    """
    Use the OpenAI client to generate an image
    """
    response = openai.images.generate(
        model="dall-e-3", # Defaults to v2 as of November 2023
        prompt=caption,
        n=1,
        size="1024x1024",  # Setting the desired image size
        response_format="b64_json"  # Requesting base64-encoded image
    )

    # Extract and decode the base64-encoded image
    first_image = response.data[0]
    b64_data = first_image.b64_json
    decoded_image = base64.b64decode(b64_data)

    # Load the image into PIL and return it
    image = Image.open(io.BytesIO(decoded_image))
    resized_image = image.resize((400, 400), Image.Resampling.LANCZOS)

    try:
        revised_prompt = response[0].revised_prompt
        if revised_prompt is None:
            revised_prompt = caption
    except:
        revised_prompt = caption

    return resized_image, revised_prompt

def draw_text(draw, text, position, font, container_width):
    """
    Draw the text within a fixed width and return the height of the drawn text.
    """
    wrapped_lines = textwrap.wrap(text, width=40)  # Initial guess for wrapping
    y_offset = position[1]
    for line in wrapped_lines:
        # Check if the line fits within the specified width, break it if it doesn't
        while font.getbbox(line)[2] > container_width:
            # Remove the last word until the line fits the container
            line = line.rsplit(' ', 1)[0]
        
        # Draw the line on the image
        draw.text((position[0], y_offset), line, font=font, fill='black')
        
        # Update the y_offset to move to the next line
        y_offset += font.getbbox(line)[3] + 5  # Add space between lines

    return y_offset - position[1]  # Return the height of the drawn text

def create_composite_image(images, captions, title):
    panel_width = 400
    panel_height = 400
    gap = 10  # Gap between panels and above caption
    border = 3  # Border around each panel
    title_height = 24
    title_space = 10  # Reduced gap below the title

    # Load fonts
    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 24)  # Bold font for title
        caption_font = ImageFont.truetype("DejaVuSans.ttf", 16)  # Increased size for captions
    except IOError:
        title_font = ImageFont.load_default()
        caption_font = ImageFont.load_default()

    # Calculate height needed for captions dynamically
    caption_draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    caption_heights = [draw_text(caption_draw, caption, (0, 0), caption_font, panel_width) for caption in captions]
    max_caption_height = max(caption_heights)

    # Total dimensions of the final image
    total_width = (panel_width * len(images)) + (gap * (len(images) - 1)) + (border * 2)
    total_height = panel_height + title_height + title_space + max_caption_height + gap + (border * 2)

    final_image = Image.new('RGB', (total_width, total_height), 'white')
    draw = ImageDraw.Draw(final_image)

    # Draw title
    draw.text((border, border), title, font=title_font, fill='black')

    # Draw images, borders, and captions
    for i, (image, caption) in enumerate(zip(images, captions)):
        x_offset = border + (panel_width + gap) * i
        y_offset = border + title_height + title_space
        final_image.paste(image, (x_offset, y_offset))
        draw.rectangle([x_offset - border, y_offset - border, x_offset + panel_width + border, y_offset + panel_height + border], outline='black', width=border)
        
        caption_position = (x_offset, y_offset + panel_height + gap)
        draw_text(draw, caption, caption_position, caption_font, panel_width)

    return final_image

def image_to_base64(image, format):
    buffered = io.BytesIO()
    image.save(buffered, format=format)
    image_bytes = buffered.getvalue()
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    return image_base64

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

# app.py (FastAPI Backend)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import textwrap
import os
import openai
from pydantic import BaseModel
from typing import List
import logging
from logger_config import get_logger
from token_verifier import TokenVerifier

# Hardcoded config vars are in config.py
from config import *


logger = get_logger(logging.DEBUG)
logger.info(f"Starting up rdancer's {__name__}")

app = FastAPI()

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://comix-generator.rdancer.org"],
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],  # Allows all headers
)

# openai.api_key = os.getenv('OPENAI_API_KEY') # This is the default

# Define Pydantic models for request and response
class ImageRequest(BaseModel):
    captions: List[str]
    title: str

    token: str
class ImageData(BaseModel):
    content_type: str
    base64: str
    original_prompt: str

class CompositeImage(BaseModel):
    content_type: str
    base64: str

class ImageResponse(BaseModel):
    images: List[ImageData]
    finalImage: CompositeImage

@app.get("/test")
async def test_cors():
    from fastapi.responses import JSONResponse

    content = {"message": "Test CORS"}
    headers = {"Access-Control-Allow-Origin": "*"}
    return JSONResponse(content=content, headers=headers)

@app.post('/generate-images', response_model=ImageResponse)
async def generate_images(request: ImageRequest):
    token = request.token.strip()
    print(f"DEBUG: token: {token}, request: {request}")
    try:
        verifier = TokenVerifier(token)
    except Exception as e:
        logger.error("Error processing token", exc_info=True)
        raise HTTPException(status_code=401, detail="Invalid token")
    if not verifier.update_quota(1_000):
        raise HTTPException(status_code=429, detail="Quota exceeded")
    try:
        captions = [caption.strip() for caption in request.captions]
        title = request.title.strip()

        # Generate individual panels using DALL-E image generation based on captions
        images, captions = _generate_images(captions, title)  # This should be an async function

        # Sometimes the images and captions are mismatched
        images = _rearrange_images(images, captions, title)

        # Throw away the autogenerated panel
        images = images[:-1]

        # Compose the full strip
        final_image = create_composite_image(images, captions, title)  # This should be an async function

        images_data = [ImageData(
            content_type='image/jpeg',
            base64=image_to_base64(image, 'JPEG'),
            original_prompt=caption,
        ) for caption, image in zip(captions, images)]

        final_image_data = CompositeImage(
            content_type='image/png',
            base64=image_to_base64(final_image, 'PNG'),
        )

        return ImageResponse(
            images=images_data,
            finalImage=final_image_data
        )
    except Exception as e:
        logger.error("An error occured", exc_info=True)
        raise e

# Additional utility functions would need to be defined or imported
# e.g., _generate_images, create_composite_image, image_to_base64

def create_fourth_panel_prompt(captions: list[str]) -> str:
    """
    Create a prompt for the fourth panel based on the captions and title.
    """

    global client
    try:
        client
    except NameError:
        client = openai.OpenAI()

    completion = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[
            {"role": "system", "content": "here are three picture descriptions. write a fourth description that is similar"},
            {"role": "user", "content": captions[0]},
            {"role": "user", "content": captions[1]},
            {"role": "user", "content": captions[2]},
        ],
    )

    logger.debug(f"auto-generated fourth panel caption: {completion.choices[0].message.content.strip()}")
    return completion.choices[0].message.content.strip()

def _generate_images(captions: list[str], title: str) -> tuple[list[Image], list[str]]:
    """
    @param list[str] captions: the captions for the first three panels
    @param str title: the title of the whole comic strip
    @return tuple[list[Image], list[str]]: images, captions (including the autogenerated fourth panel caption)

    Generate individual images that hopefully have something to do with one anoher.
    """
    assert len(captions) == 3
    amended_captions = captions + [create_fourth_panel_prompt(captions)]
    image_grid = generate_2x2_image_grid(amended_captions, title)
    images = chop_up_2x2_image_grid(image_grid)
    resized_images = [image.resize((400, 400), Image.Resampling.LANCZOS) for image in images]
    assert len(amended_captions) == 4
    return resized_images, amended_captions

def chop_up_2x2_image_grid(image):
    """
    Given an image that is a 2x2 grid of panels, retun a list of the four indivial images.
    """ 
    width, height = image.size
    panel_width = width // 2
    panel_height = height // 2

    # Crop the image into four panels
    panels = []
    for i in range(2):
        for j in range(2):
            left = j * panel_width
            upper = i * panel_height
            right = left + panel_width
            lower = upper + panel_height
            panel = image.crop((left, upper, right, lower))
            panels.append(panel)
    return panels

def generate_2x2_image_grid(captions: list[str], title: str) -> list[Image]:
    """
    Use the OpenAI client to generate a composite 2x2 grid of images.
    """
    MAX_NUM_TRIES = 3
    prompt = "Draw a 2x2 grid of pictures:\n\n"
    prompt += f"{title}\n" if title else ""
    for caption in [caption.replace('\n', ' ') for caption in captions]:
        prompt += f"* {caption}\n"
    logger.debug(f"prompt: {prompt}")
    for retry in range(1, MAX_NUM_TRIES+1):
        response = openai.images.generate(
            model="dall-e-3", # Defaults to v2 as of November 2023
            prompt=prompt,
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
        if is_proper_grid(image, tolerance=10):
            logger.info(f"successfully generated image after {retry} {'try' if retry == 1 else 'tries'}")
            break
        else:
            logger.warn("generated image is not a proper 2x2 grid" + (", retrying" if retry < MAX_NUM_TRIES else ""))
    else:
        s = f"failed to generate image after trying {MAX_NUM_TRIES} times"
        logger.error(s)
        # raise(s)

    try:
        revised_prompt = response[0].revised_prompt
        if revised_prompt is not None and revised_prompt != prompt:
            logger.debug(f"revised_prompt: {revised_prompt}")
    except:
        pass

    return image

def is_proper_grid(image: Image, tolerance: int) -> bool:
    """
    Check if the image is a proper 2x2 grid.
    
    Use edge detection.
    """
    import cv2
    import numpy as np

    # Convert PIL Image to grayscale if not already
    if image.mode != 'L':
        image = image.convert('L')

    # Convert PIL Image to NumPy array
    image_np = np.array(image)

    # Apply Canny edge detection
    edges = cv2.Canny(image_np, 100, 200)

    # Define divider line positions (for a 1024x1024 image)
    vertical_line = edges[:, 512]
    horizontal_line = edges[512, :]

    # Count edges in the divider lines
    vertical_edges = np.sum(vertical_line > 0)
    horizontal_edges = np.sum(horizontal_line > 0)

    # Check if the number of edges is within the tolerance
    return vertical_edges <= tolerance and horizontal_edges <= tolerance

def _analyze_images_with_vision_model(images: list[Image]) -> list[str]:
    """
    Create a short description of each of the images individually.

    There is no knowledge shared amongst the runs: each panel is freshly examined and described.

    XXX We should run the four requests in parallel, but not sure if we'd not get rate limited by OpenAI
    """

    observations = []

    for i in range(len(images)):
        # Convert image
        image = images[i]
        try:
            response = client.chat.completions.create(
                model=VISION_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "What's in this image, in 10-15 words?"},
                            {
                                # Note that the type is always URL, so we send it as data URL
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_to_base64(image, 'PNG')}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=300,
            )
            observation = response.choices[0].message.content.strip()
        except Exception as e:
            logger.warn(f"GPT Vision failed for image #{i}: {e}")
            observation = ""
        observations.append(observation)
    logger.debug("Observations:\n" + "\n".join([f"{i+1}. {obs}" for i, obs in enumerate(observations)]))
    assert len(observations) == len(images)
    return observations

from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def _calculate_cosine_similarities(caption_embeddings: list, observation_embeddings: list) -> list[list[float]]:
    # Convert lists to numpy arrays for compatibility with sklearn
    caption_embeddings = np.array(caption_embeddings)
    observation_embeddings = np.array(observation_embeddings)

    # Calculate cosine similarity
    # The result is a matrix of shape (len(caption_embeddings), len(observation_embeddings))
    similarities = cosine_similarity(caption_embeddings, observation_embeddings)

    return similarities.tolist()

from scipy.optimize import linear_sum_assignment

def _reorder_images_based_on_similarity(images: list, similarity_matrix: list[list[float]]) -> list:
    # Convert the similarity matrix to a numpy array
    similarity_matrix = np.array(similarity_matrix)

    logger.debug(f"Similarity matrix shape: {similarity_matrix.shape}")
    logger.debug(f"Similarity matrix: {similarity_matrix}")

    # The Hungarian algorithm works by finding the minimum cost in a cost matrix, so we
    # convert our similarity matrix to a cost matrix by subtracting from a large number
    cost_matrix = 1 - similarity_matrix

    # Apply the Hungarian algorithm
    # row_indices will be indices of captions, col_indices will be indices of images
    row_indices, col_indices = linear_sum_assignment(cost_matrix)

    log_reorder(col_indices)

    # Reorder images based on the optimal assignment
    reordered_images = [images[i] for i in col_indices]

    return reordered_images

def log_reorder(col_indices: list[int]) -> None:
    reorder_info = []
    for index, col_index in enumerate(col_indices):
        # Check if the order has changed (col_index does not match its position)
        if index != col_index:
            reorder_info.append(str(col_index + 1))  # Add 1 to make it 1-indexed
        else:
            reorder_info.append("_")  # Placeholder for unchanged order

    # Create a string for logging
    reorder_str = ", ".join(reorder_info)

    # Log the information
    if reorder_str != "_, _, _, _":  # This means some order has changed
        logger.info("Reorder: " + reorder_str)
    else:
        logger.debug("Order not changed")

def _rearrange_images(images: list[Image], captions: list[str], title: str) -> list[Image]:
    """
    Rearrange the images and captions so that they are in the correct order.

    Sometimes (often) the images and captions are shuffled.

    Use OpenAI GPT-4 Vision
    """
    global client

    # Step 1: Analyze images using the vision model
    observations = _analyze_images_with_vision_model(images)
    if observations.count("") > 1:
        logger.warn("More than one image failed to be analyzed, giving up on reordering")
        return images

    # Step 2: Generate embeddings for captions and observations
    try:
        caption_embeddings = [embed_string(s) for s in captions]
        observation_embeddings = [embed_string(s) for s in observations]
    except Exception as e:
        logger.warn(f"Embedding failed, giving up on reordering: {e}")
        return images

    # Step 3: Calculate cosine similarities
    similarity_matrix = _calculate_cosine_similarities(caption_embeddings, observation_embeddings)

    # Step 4: Reorder images based on similarities
    reordered_images = _reorder_images_based_on_similarity(images, similarity_matrix)

    # Step 5: Return reordered data
    return reordered_images

def embed_string(s: str) -> list[float]:
    """
    Simply generate the embedding vector
    """
    global client

    s = s.replace("\n", " ").strip()
    response = client.embeddings.create(
        input=s,
        model=EMBEDDING_MODEL
    )

    return response.data[0].embedding


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
        logo_font = ImageFont.truetype("DejaVuSansMono.ttf", 12)  # Smaller font for logo
    except IOError:
        title_font = ImageFont.load_default()
        caption_font = ImageFont.load_default()
        logo_font = ImageFont.load_default()

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

    # Draw logo
    logo_width = logo_font.getbbox(LOGO_TEXT)[2]
    logo_height = logo_font.getbbox(LOGO_TEXT)[3]
    title_bottom = border + title_font.getbbox(title)[3]
    # The logo needs optically adjusted to look aligned
    x_adjustment = 1
    y_adjustment = 3
    logo_position = (total_width - logo_width - border - x_adjustment, title_bottom - logo_height + y_adjustment)
    draw.text(logo_position, LOGO_TEXT, font=logo_font, fill='darkgray')

    return final_image

def image_to_base64(image, format):
    buffered = io.BytesIO()
    image.save(buffered, format=format)
    image_bytes = buffered.getvalue()
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    return image_base64

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=True)

import openai

generate_image_json = {
    "name": "generate_image",
    "description": "Generate an image based on a prompt.",
    "parameters": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "The prompt to generate the image from.",
            }
        },
        "required": ["prompt"]
    }
}

def generate_image(prompt):
    client = openai.OpenAI()
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    return response.data[0].url
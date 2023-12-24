import os
from flask import Flask, request, jsonify, render_template
import openai
from openai import OpenAI


app = Flask(__name__, static_folder='static')

# Load the OpenAI API key from the OPENAI_API_KEY environment variable
openai_api_key = os.getenv('OPENAI_API_KEY')


if openai_api_key is None:
    raise ValueError("No OPENAI_API_KEY found in environment variables")


# Use the API key with the OpenAI library

client = OpenAI(api_key=openai_api_key)


@app.route('/')
def index():
    # Serve your HTML page
    return render_template('index.html')


@app.route('/analyze_genes', methods=['POST'])
def analyze_genes():
    # Retrieve genes from the request
    data = request.json
    gene_set = data['gene_set']

    # Prepend your predefined prompt to the gene set
    prompt = f"Predefined prompt: {gene_set}"

    try:
        # Send the prompt to OpenAI's API


        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="gpt-3.5-turbo",
        )


        #print(chat_completion)
        print(chat_completion.choices[0].message.content)


        # Return the response to the frontend
        response = jsonify({"text":chat_completion.choices[0].message.content})
        print(response)
        return response

    except openai.OpenAIError as e:
        # Handle exceptions and errors
        return jsonify({'error': str(e)}), 500


print("starting Flask")
if __name__ == '__main__':
    app.run(debug=True, port=8000)

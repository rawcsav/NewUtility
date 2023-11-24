from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy.sql import func
from app import db
from app.database import DocumentEmbedding
import openai
import os

# Initialize the blueprint
bp = Blueprint('embeddings', __name__, url_prefix='/embeddings')


@bp.route('/embed', methods=['POST'])
@login_required
def get_embeddings():
    # Get the document text from the request
    data = request.json
    text = data.get('document')
    model_name = data.get('model',
                          'text-similarity-babbage-001')  # Default to a specific model

    # Check if the text is provided
    if not text:
        return jsonify({'error': 'No document text provided for embedding.'}), 400

    try:
        # Call the OpenAI API to get the embeddings
        response = openai.Embedding.create(
            model=model_name,
            input=text
        )
        embeddings = response['data'][0]['embedding']

        # Save embeddings to the database
        new_embedding = DocumentEmbedding(
            user_id=current_user.id,
            document=text,
            embedding=str(embeddings),  # Store the list as a string
            model=model_name
        )
        db.session.add(new_embedding)
        db.session.commit()

        return jsonify({'message': 'Embedding saved successfully.'}), 200
    except openai.OpenAIError as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

import tempfile
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app, render_template
from flask_login import login_required, current_user
from sqlalchemy.sql import func
from tenacity import RetryError
from werkzeug.utils import secure_filename
from openai import OpenAI
from app import db
from app.database import DocumentEmbedding, Document, DocumentChunk, UserAPIKey
import openai
import os

from app.util.embeddings_util import split_text, extract_text_from_file, \
    remove_temp_file, get_embedding_batch, store_embeddings, save_temp_file
from app.util.forms_util import DocumentUploadForm
from app.util.session_util import decrypt_api_key

# Initialize the blueprint
bp = Blueprint('embeddings', __name__, url_prefix='/embeddings')


@bp.route('/embeddings', methods=['GET'])
@login_required
def embeddings_center():
    # Query the database for the current user's documents
    user_documents = Document.query.filter_by(user_id=current_user.id).all()

    # Prepare document data for the template
    documents_data = [
        {
            'id': doc.id,
            'title': doc.title,
            'author': doc.author,
            'total_tokens': doc.total_tokens,
            'chunk_count': len(doc.chunks),
        }
        for doc in user_documents
    ]

    return render_template('embeddings.html', documents=documents_data)


@bp.route('/upload', methods=['POST'])
@login_required
def upload_document():
    form = DocumentUploadForm()
    if not form.validate_on_submit():
        return jsonify({'error': 'Invalid form submission'}), 400

    file = form.file.data
    title = form.title.data or secure_filename(file.filename)
    author = form.author.data
    chunk_size = form.chunk_size.data or 512
    key_id = current_user.selected_api_key_id
    user_api_key = UserAPIKey.query.filter_by(user_id=current_user.id,
                                              id=key_id).first()
    api_key = decrypt_api_key(user_api_key.encrypted_api_key)
    client = OpenAI(api_key=api_key)
    if not file:
        return jsonify({'error': 'No file provided'}), 400

    temp_path = save_temp_file(file)

    try:
        content = extract_text_from_file(temp_path)
        chunks, total_tokens, chunk_token_counts = split_text(content, chunk_size)

        new_document = Document(
            user_id=current_user.id,
            title=title,
            author=author,
            total_tokens=total_tokens,
            created_at=datetime.utcnow()
        )
        db.session.add(new_document)
        db.session.flush()  # Flush the session to get the new ID

        # Create and store chunks in the database
        for i, (chunk_content, token_count) in enumerate(
                zip(chunks, chunk_token_counts)):
            chunk = DocumentChunk(
                document_id=new_document.id,
                chunk_index=i,
                content=chunk_content,
                tokens=token_count
            )
            db.session.add(chunk)
        embeddings = get_embedding_batch(chunks, client)
        store_embeddings(new_document.id, embeddings)
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': 'File uploaded and embedded successfully',
            'document_id': new_document.id,
            'chunk_count': len(chunks),
            'total_tokens': total_tokens
        }), 200
    except Exception as e:
        # If anything goes wrong, roll back the session
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        remove_temp_file(temp_path)


@bp.route('/delete/<int:document_id>', methods=['POST'])
@login_required
def delete_document(document_id):
    # Find the document by ID
    document = Document.query.get_or_404(document_id)

    # Verify if the current user owns the document
    if document.user_id != current_user.id:
        return jsonify({'error': 'Permission denied'}), 403

    # Delete the document
    db.session.delete(document)
    db.session.commit()

    return jsonify(
        {'status': 'success', 'message': 'Document deleted successfully'}), 200


@bp.route('/update/<int:document_id>', methods=['POST'])
@login_required
def update_document(document_id):
    document = Document.query.get_or_404(document_id)

    if document.user_id != current_user.id:
        return jsonify({'error': 'Permission denied'}), 403

    title = request.form.get('title')
    author = request.form.get('author')
    chunk_size = request.form.get('chunk_size', type=int)

    if title is not None:
        document.title = title
    if author is not None:
        document.author = author

    chunks_query = DocumentChunk.query.filter_by(document_id=document.id).order_by(
        DocumentChunk.chunk_index)
    content = ''.join(chunk.content for chunk in chunks_query)

    if chunk_size:
        # Recalculate chunks
        new_chunks, total_tokens, chunk_token_counts = split_text(content, chunk_size)

        # Delete old chunks
        chunks_query.delete()

        # Add new chunks
        for i, (chunk_content, token_count) in enumerate(
                zip(new_chunks, chunk_token_counts)):
            new_chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=i,
                content=chunk_content,
                tokens=token_count
            )
            db.session.add(new_chunk)

    db.session.commit()

    return jsonify({'status': 'success', 'message': 'Document updated successfully',
                    'document_id': document.id}), 200

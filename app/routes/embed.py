import pickle
from datetime import datetime
from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from openai import OpenAI
from app import db
from app.database import Document, DocumentChunk, UserAPIKey

from app.util.embeddings_util import split_text, extract_text_from_file, \
    remove_temp_file, get_embedding_batch, store_embeddings, save_temp_file
from app.util.forms_util import DocumentUploadForm, EditDocumentForm, DeleteDocumentForm
from app.util.session_util import decrypt_api_key
from app.util.usage_util import embedding_cost, update_usage_and_costs

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

    files = request.files.getlist('file')
    # Assume titles and authors are sent as a single string separated by a comma, or not sent at all
    titles = request.form.get('title', '').split(',') if 'title' in request.form else []
    authors = request.form.get('author', '').split(
        ',') if 'author' in request.form else []

    for i, file in enumerate(files):
        # Use the filename as the default title if no title is provided
        title = titles[i] if i < len(titles) and titles[i].strip() else secure_filename(
            file.filename)
        # Use None as the default author if no author is provided
        author = authors[i].strip() if i < len(authors) and authors[i].strip() else None

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
        text_pages = extract_text_from_file(
            temp_path)  # This should return a list of (text, page_number) tuples
        chunks, chunk_pages, total_tokens, chunk_token_counts = split_text(text_pages,
                                                                           chunk_size)

        new_document = Document(
            user_id=current_user.id,
            title=title,
            author=author,
            total_tokens=total_tokens,
            created_at=datetime.utcnow()
        )
        db.session.add(new_document)
        db.session.flush()  # Flush the session to get the new ID

        # Create and store chunks in the database, including page number information
        for i, (chunk_content, pages) in enumerate(zip(chunks, chunk_pages)):
            pages_str = ','.join(map(str,
                                     pages))  # Convert the set of page numbers to a comma-separated string

            chunk = DocumentChunk(
                document_id=new_document.id,
                chunk_index=i,
                content=chunk_content,
                tokens=chunk_token_counts[i],
                pages=pages_str  # Store the serialized page numbers
            )
            db.session.add(chunk)

        embeddings = get_embedding_batch(chunks, client)

        # Calculate the cost for embedding generation
        cost = embedding_cost(total_tokens)
        # Update the API key and APIUsage with the new cost
        update_usage_and_costs(user_id=current_user.id,
                               api_key_id=key_id,
                               usage_type='embedding',
                               cost=cost)

        # Now store the embeddings in the database
        store_embeddings(new_document.id, embeddings)

        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': 'File uploaded and embedded successfully. Please refresh to see changes'
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
    form = DeleteDocumentForm()
    document = Document.query.get_or_404(document_id)
    if document.user_id != current_user.id or not form.validate_on_submit():
        return jsonify({'error': 'Unauthorized or invalid form submission'}), 403

    try:
        db.session.delete(document)
        db.session.commit()
        return jsonify(
            {'status': 'success',
             'message': 'Document deleted successfully.\nPlease refresh to see changes'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@bp.route('/update', methods=['POST'])
@login_required
def update_document():
    form = EditDocumentForm()
    if not form.validate_on_submit():
        return jsonify({'error': 'Invalid form submission'}), 400

    document_id = form.document_id.data
    title = form.title.data
    author = form.author.data

    document = Document.query.get_or_404(document_id)
    if document.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        if title:
            document.title = title
        if author:
            document.author = author
        db.session.commit()
        return jsonify(
            {'status': 'success',
             'message': 'Document updated successfully.\nPlease refresh to see changes'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

import os

import pandas as pd
from flask import session, request, stream_with_context, Blueprint, current_app

from app.util.chat_util import ask

bp = Blueprint('query', __name__)


@bp.route('/query', methods=['POST'])
def query_endpoint():
    api_key = session.get('api_key')
    query = request.form.get('query')
    selected_docs = request.form.get('selected_docs')

    if selected_docs:
        selected_docs = selected_docs.split(',')

    df_path = session.get('EMBED_DATA')
    if df_path and os.path.exists(df_path):
        df = pd.read_json(df_path, orient='split')
    else:
        return "Error: Data not found.", 400

    def generate():
        for content in ask(query, df, api_key, specific_documents=selected_docs):
            yield content

    response = current_app.response_class(stream_with_context(generate()), content_type='text/plain')
    response.headers['X-Accel-Buffering'] = 'no'
    return response

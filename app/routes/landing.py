import os

from flask import Blueprint, render_template, current_app
from markdown2 import markdown

bp = Blueprint("landing", __name__)


@bp.route("/")
def landing_page():
    markdown_file_path = os.path.join(
        current_app.root_path, "static", "docs", "landing.md"
    )

    with open(markdown_file_path, "r") as file:
        markdown_content = file.read()
    docs_content = markdown(markdown_content)
    return render_template("landing.html", tooltip=docs_content)

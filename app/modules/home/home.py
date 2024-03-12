import os

from flask import Blueprint, render_template, current_app
from markdown2 import markdown

home_bp = Blueprint("home_bp", __name__, template_folder="templates", static_folder="static", url_prefix="/home")


@home_bp.route("/")
def landing_page():
    markdown_file_path = os.path.join(current_app.root_path, home_bp.static_folder, "home.md")
    with open(markdown_file_path, "r") as file:
        markdown_content = file.read()
    docs_content = markdown(markdown_content)
    return render_template("landing.html", tooltip=docs_content)

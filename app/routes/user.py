from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

# Define the Blueprint
bp = Blueprint('user', __name__, url_prefix='/user')


@bp.route('/dashboard')
@login_required  # Ensure that only logged-in users can access this route
def dashboard():
    return render_template('dashboard.html', user=current_user)

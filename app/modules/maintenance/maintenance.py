from flask import Blueprint, render_template

maintenance_bp = Blueprint(
    "maintenance_bp", __name__, template_folder="templates", static_folder="static", url_prefix="/maintenance"
)


@maintenance_bp.route("/", defaults={"path": ""})
@maintenance_bp.route("/<path:path>")
def maintenance(path):
    return render_template("maintenance.html")

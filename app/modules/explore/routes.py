from flask import jsonify, render_template, request

from app.modules.explore import explore_bp
from app.modules.explore.forms import ExploreForm
from app.modules.explore.services import ExploreService


@explore_bp.route("/explore", methods=["GET", "POST"])
def index():
    form = ExploreForm()

    if request.method == "GET":
        query = request.args.get("query", "")
        author = request.args.get("author", "")
        description = request.args.get("description", "")
        file = request.args.get("file", "")
        tags = request.args.get("tags", "")  
        date = request.args.get("date", "")

        return render_template("explore/index.html", 
                               form=form, 
                               query=query,
                               author = author,
                               description = description,
                               file = file,
                               tags =tags,
                               date = date
                               )

    if request.method == "POST":
        criteria = request.get_json()
        datasets = ExploreService().filter(**criteria)
        return jsonify([dataset.to_dict() for dataset in datasets])

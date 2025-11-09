from flask import render_template
from app.modules.uploader import uploader_bp


@uploader_bp.route('/uploader', methods=['GET'])
def index():
    return render_template('uploader/index.html')

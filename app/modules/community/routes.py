"""
Community routes - API endpoints
"""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.modules.community.forms import CommunityForm, MemberForm, ReviewSubmissionForm, SubmitDatasetForm
from app.modules.community.services import community_service

community_bp = Blueprint("community", __name__, url_prefix="/communities", template_folder="templates")

# ============================================================================
# PUBLIC VIEWS
# ============================================================================


@community_bp.route("/")
def index():
    """List all public communities"""
    communities = community_service.list_public_communities()
    return render_template("community/index.html", communities=communities)


@community_bp.route("/<slug>")
def detail(slug):
    """View community detail"""
    community = community_service.get_community_by_slug(slug)
    if not community:
        flash("Comunidad no encontrada", "error")
        return redirect(url_for("community.index"))

    # Get approved datasets
    datasets = community_service.get_approved_datasets(community.id)

    # Check if current user is a member
    is_member = False
    can_manage = False
    if current_user.is_authenticated:
        is_member = community_service.is_member(community.id, current_user.id)
        can_manage = community_service.is_curator_or_owner(community.id, current_user.id)

    return render_template(
        "community/detail.html", community=community, datasets=datasets, is_member=is_member, can_manage=can_manage
    )


@community_bp.route("/search")
def search():
    """Search communities"""
    query = request.args.get("q", "")
    communities = []

    if query:
        communities = community_service.search_communities(query)

    return render_template("community/search.html", communities=communities, query=query)


# ============================================================================
# COMMUNITY MANAGEMENT (OWNERS)
# ============================================================================


@community_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    """Create a new community"""
    form = CommunityForm()

    if form.validate_on_submit():
        community = community_service.create_community(
            name=form.name.data,
            slug=form.slug.data,
            owner_id=current_user.id,
            description=form.description.data,
            logo_url=form.logo_url.data,
            website=form.website.data,
            is_public=form.is_public.data,
        )

        if community:
            flash("Comunidad creada exitosamente", "success")
            return redirect(url_for("community.detail", slug=community.slug))
        else:
            flash("Error al crear la comunidad. El slug ya existe.", "error")

    return render_template("community/create.html", form=form)


@community_bp.route("/<slug>/edit", methods=["GET", "POST"])
@login_required
def edit(slug):
    """Edit community"""
    community = community_service.get_community_by_slug(slug)
    if not community:
        flash("Comunidad no encontrada", "error")
        return redirect(url_for("community.index"))

    # Check if user can manage
    if not community_service.is_curator_or_owner(community.id, current_user.id):
        flash("No tienes permisos para editar esta comunidad", "error")
        return redirect(url_for("community.detail", slug=slug))

    form = CommunityForm(obj=community)

    if form.validate_on_submit():
        updated = community_service.update_community(
            community.id,
            name=form.name.data,
            description=form.description.data,
            logo_url=form.logo_url.data,
            website=form.website.data,
            is_public=form.is_public.data,
        )

        if updated:
            flash("Comunidad actualizada", "success")
            return redirect(url_for("community.detail", slug=slug))
        else:
            flash("Error al actualizar", "error")

    return render_template("community/edit.html", form=form, community=community)


@community_bp.route("/<slug>/delete", methods=["POST"])
@login_required
def delete(slug):
    """Delete community"""
    community = community_service.get_community_by_slug(slug)
    if not community:
        flash("Comunidad no encontrada", "error")
        return redirect(url_for("community.index"))

    # Only owners can delete
    if not community_service.is_curator_or_owner(community.id, current_user.id):
        flash("No tienes permisos para eliminar esta comunidad", "error")
        return redirect(url_for("community.detail", slug=slug))

    if community_service.delete_community(community.id):
        flash("Comunidad eliminada", "success")
        return redirect(url_for("community.index"))
    else:
        flash("Error al eliminar", "error")
        return redirect(url_for("community.detail", slug=slug))


# ============================================================================
# MEMBER MANAGEMENT
# ============================================================================


@community_bp.route("/<slug>/members")
@login_required
def members(slug):
    """List community members"""
    community = community_service.get_community_by_slug(slug)
    if not community:
        flash("Comunidad no encontrada", "error")
        return redirect(url_for("community.index"))

    # Only members can view member list
    if not community_service.is_member(community.id, current_user.id):
        flash("Debes ser miembro para ver la lista de miembros", "error")
        return redirect(url_for("community.detail", slug=slug))

    members = community_service.get_community_members(community.id)
    can_manage = community_service.is_curator_or_owner(community.id, current_user.id)

    return render_template("community/members.html", community=community, members=members, can_manage=can_manage)


@community_bp.route("/<slug>/members/add", methods=["GET", "POST"])
@login_required
def add_member(slug):
    """Add member to community"""
    from app.modules.auth.models import User

    community = community_service.get_community_by_slug(slug)
    if not community:
        flash("Comunidad no encontrada", "error")
        return redirect(url_for("community.index"))

    # Check permissions
    if not community_service.is_curator_or_owner(community.id, current_user.id):
        flash("No tienes permisos para añadir miembros", "error")
        return redirect(url_for("community.detail", slug=slug))

    form = MemberForm()

    # Obtener usuarios que no son miembros de la comunidad
    current_member_ids = [m.user_id for m in community.memberships]
    available_users = User.query.filter(User.id.notin_(current_member_ids)).all()

    form.user_id.choices = [
        (u.id, f"{u.profile.name} {u.profile.surname} ({u.email})" if u.profile else u.email) for u in available_users
    ]

    if form.validate_on_submit():
        membership = community_service.add_member(community.id, form.user_id.data, form.role.data)

        if membership:
            flash("Miembro añadido", "success")
            return redirect(url_for("community.members", slug=slug))
        else:
            flash("El usuario ya es miembro", "error")

    return render_template("community/add_member.html", form=form, community=community)


@community_bp.route("/<slug>/members/<int:user_id>/remove", methods=["POST"])
@login_required
def remove_member(slug, user_id):
    """Remove member from community"""
    community = community_service.get_community_by_slug(slug)
    if not community:
        return jsonify({"error": "Comunidad no encontrada"}), 404

    # Check permissions
    if not community_service.is_curator_or_owner(community.id, current_user.id):
        return jsonify({"error": "Sin permisos"}), 403

    if community_service.remove_member(community.id, user_id):
        flash("Miembro eliminado", "success")
        return redirect(url_for("community.members", slug=slug))
    else:
        flash("Error al eliminar miembro", "error")
        return redirect(url_for("community.members", slug=slug))


# ============================================================================
# DATASET SUBMISSIONS
# ============================================================================


@community_bp.route("/<slug>/submit", methods=["GET", "POST"])
@login_required
def submit_dataset(slug):
    """Submit a dataset to the community"""
    from app.modules.dataset.models import DataSet

    community = community_service.get_community_by_slug(slug)
    if not community:
        flash("Comunidad no encontrada", "error")
        return redirect(url_for("community.index"))

    form = SubmitDatasetForm()

    # Obtener datasets del usuario actual
    user_datasets = DataSet.query.filter_by(user_id=current_user.id).all()

    # Llenar el dropdown con los datasets del usuario
    form.dataset_id.choices = [
        (ds.id, ds.ds_meta_data.title if ds.ds_meta_data else f"Dataset {ds.id}") for ds in user_datasets
    ]

    if form.validate_on_submit():
        submission = community_service.submit_dataset(
            dataset_id=form.dataset_id.data,
            community_id=community.id,
            submitter_id=current_user.id,
            message=form.message.data,
        )

        if submission:
            flash("Dataset propuesto exitosamente. Los curadores lo revisarán pronto.", "success")
            return redirect(url_for("community.detail", slug=slug))
        else:
            flash("Error: Este dataset ya fue propuesto a esta comunidad.", "error")

    return render_template("community/submit_dataset.html", form=form, community=community, user_datasets=user_datasets)


@community_bp.route("/<slug>/submissions")
@login_required
def submissions(slug):
    """List pending submissions (curators only)"""
    community = community_service.get_community_by_slug(slug)
    if not community:
        flash("Comunidad no encontrada", "error")
        return redirect(url_for("community.index"))

    # Check if user is curator or owner
    if not community_service.is_curator_or_owner(community.id, current_user.id):
        flash("No tienes permisos para ver las propuestas", "error")
        return redirect(url_for("community.detail", slug=slug))

    pending = community_service.get_pending_submissions(community.id)

    return render_template("community/submissions.html", community=community, submissions=pending)


@community_bp.route("/submissions/<int:submission_id>/review", methods=["GET", "POST"])
@login_required
def review_submission(submission_id):
    """Review a submission (approve or reject)"""
    from app.modules.community.repositories import DatasetCommunitySubmissionRepository

    submission_repo = DatasetCommunitySubmissionRepository()
    submission = submission_repo.get_by_id(submission_id)

    if not submission:
        flash("Propuesta no encontrada", "error")
        return redirect(url_for("community.index"))

    community = submission.community

    # Check permissions
    if not community_service.is_curator_or_owner(community.id, current_user.id):
        flash("No tienes permisos para revisar propuestas", "error")
        return redirect(url_for("community.detail", slug=community.slug))

    form = ReviewSubmissionForm()

    if form.validate_on_submit():
        action = form.action.data

        if action == "approve":
            community_service.approve_submission(submission.id, current_user.id)
            flash("Dataset aceptado en la comunidad", "success")
        elif action == "reject":
            community_service.reject_submission(submission.id, current_user.id, form.feedback.data)
            flash("Propuesta rechazada", "info")

        return redirect(url_for("community.submissions", slug=community.slug))

    return render_template("community/review_submission.html", submission=submission, form=form)


# ============================================================================
# API ENDPOINTS
# ============================================================================


@community_bp.route("/api/communities", methods=["GET"])
def api_list_communities():
    """API: List all public communities"""
    communities = community_service.list_public_communities()
    return jsonify(
        [
            {
                "id": c.id,
                "name": c.name,
                "slug": c.slug,
                "description": c.description,
                "logo_url": c.logo_url,
            }
            for c in communities
        ]
    )


@community_bp.route("/api/communities/<slug>", methods=["GET"])
def api_get_community(slug):
    """API: Get community details"""
    community = community_service.get_community_by_slug(slug)
    if not community:
        return jsonify({"error": "Community not found"}), 404

    return jsonify(
        {
            "id": community.id,
            "name": community.name,
            "slug": community.slug,
            "description": community.description,
            "logo_url": community.logo_url,
            "website": community.website,
            "is_public": community.is_public,
            "created_at": community.created_at.isoformat(),
        }
    )


@community_bp.route("/api/communities/<slug>/datasets", methods=["GET"])
def api_get_community_datasets(slug):
    """API: Get approved datasets in a community"""
    community = community_service.get_community_by_slug(slug)
    if not community:
        return jsonify({"error": "Community not found"}), 404

    datasets = community_service.get_approved_datasets(community.id)

    return jsonify(
        [
            {
                "id": d.dataset.id,
                "title": d.dataset.ds_meta_data.title if hasattr(d.dataset, "ds_meta_data") else "No title",
                "approved_at": d.reviewed_at.isoformat() if d.reviewed_at else None,
            }
            for d in datasets
        ]
    )

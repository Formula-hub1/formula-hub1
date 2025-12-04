"""
Community seeders - Sample data for development/testing
"""

from app import db
from app.modules.auth.models import User
from app.modules.community.models import Community, CommunityMembership, DatasetCommunitySubmission
from app.modules.dataset.models import DataSet


def seed_communities():
    """Seed sample communities"""

    print("Seeding communities...")

    # Get or create sample users
    user1 = User.query.filter_by(email="admin@uvlhub.com").first()
    user2 = User.query.filter_by(email="curator@uvlhub.com").first()
    user3 = User.query.filter_by(email="user@uvlhub.com").first()

    if not user1:
        print("Warning: No users found. Please seed users first.")
        return

    # Create communities
    communities_data = [
        {
            "name": "Machine Learning Research",
            "slug": "machine-learning",
            "description": "Comunidad dedicada a la investigación en Machine Learning y AI",
            "is_public": True,
            "owner": user1,
        },
        {
            "name": "Software Product Lines",
            "slug": "spl",
            "description": "Investigación y datasets sobre líneas de productos software",
            "is_public": True,
            "owner": user1,
        },
        {
            "name": "Data Science",
            "slug": "data-science",
            "description": "Comunidad de ciencia de datos y análisis predictivo",
            "is_public": True,
            "owner": user2 if user2 else user1,
        },
        {
            "name": "Universidad de Sevilla",
            "slug": "us",
            "description": "Comunidad institucional de la Universidad de Sevilla",
            "is_public": True,
            "owner": user1,
        },
    ]

    created_communities = []

    for data in communities_data:
        # Check if community already exists
        existing = Community.query.filter_by(slug=data["slug"]).first()
        if existing:
            print(f"Community '{data['name']}' already exists")
            created_communities.append(existing)
            continue

        owner = data.pop("owner")
        community = Community(**data)
        db.session.add(community)
        db.session.flush()  # Get the ID

        # Create owner membership
        membership = CommunityMembership(community_id=community.id, user_id=owner.id, role="owner")
        db.session.add(membership)

        created_communities.append(community)
        print(f"Created community: {community.name}")

    # Add additional members
    if len(created_communities) > 0 and user2:
        # Add user2 as curator to first community
        ml_community = created_communities[0]
        curator_membership = CommunityMembership(community_id=ml_community.id, user_id=user2.id, role="curator")
        db.session.add(curator_membership)
        print(f"Added curator to {ml_community.name}")

    if len(created_communities) > 1 and user3:
        # Add user3 as member to second community
        spl_community = created_communities[1]
        member_membership = CommunityMembership(community_id=spl_community.id, user_id=user3.id, role="member")
        db.session.add(member_membership)
        print(f"Added member to {spl_community.name}")

    db.session.commit()
    print(f"✓ Created {len(created_communities)} communities")

    return created_communities


def seed_submissions():
    """Seed sample dataset submissions"""

    print("Seeding submissions...")

    # Get communities and datasets
    ml_community = Community.query.filter_by(slug="machine-learning").first()
    spl_community = Community.query.filter_by(slug="spl").first()

    if not ml_community or not spl_community:
        print("Warning: Communities not found. Please seed communities first.")
        return

    # Get sample datasets (assuming they exist)
    datasets = DataSet.query.limit(3).all()

    if not datasets:
        print("Warning: No datasets found. Skipping submission seeding.")
        return

    # Get users
    user1 = User.query.filter_by(email="admin@uvlhub.com").first()
    user3 = User.query.filter_by(email="user@uvlhub.com").first()

    if not user1:
        print("Warning: No users found.")
        return

    submitter = user3 if user3 else user1

    # Create submissions
    submissions_data = [
        {
            "dataset": datasets[0],
            "community": ml_community,
            "submitter": submitter,
            "status": "pending",
            "message": "Este dataset contiene características importantes para clasificación ML",
        },
        {
            "dataset": datasets[1] if len(datasets) > 1 else datasets[0],
            "community": ml_community,
            "submitter": submitter,
            "status": "approved",
            "message": "Dataset de referencia en el campo",
            "reviewed_by": user1.id,
        },
    ]

    if len(datasets) > 2:
        submissions_data.append(
            {
                "dataset": datasets[2],
                "community": spl_community,
                "submitter": submitter,
                "status": "pending",
                "message": "Características relevantes para SPL",
            }
        )

    created_count = 0

    for data in submissions_data:
        # Check if submission already exists
        existing = DatasetCommunitySubmission.query.filter_by(
            dataset_id=data["dataset"].id, community_id=data["community"].id
        ).first()

        if existing:
            print(f"Submission for dataset {data['dataset'].id} to {data['community'].name} already exists")
            continue

        submission = DatasetCommunitySubmission(
            dataset_id=data["dataset"].id,
            community_id=data["community"].id,
            submitter_id=data["submitter"].id,
            status=data["status"],
            message=data["message"],
            reviewed_by=data.get("reviewed_by"),
        )

        db.session.add(submission)
        created_count += 1
        print(f"Created submission: dataset {data['dataset'].id} -> {data['community'].name}")

    db.session.commit()
    print(f"✓ Created {created_count} submissions")


def run_all_seeders():
    """Run all community seeders"""
    print("=" * 50)
    print("Running Community Seeders")
    print("=" * 50)

    try:
        seed_communities()
        seed_submissions()
        print("\n✓ All community seeders completed successfully!")
    except Exception as e:
        print(f"\n✗ Error running seeders: {str(e)}")
        db.session.rollback()
        raise


if __name__ == "__main__":
    # This allows running seeders directly
    from app import create_app

    app = create_app()
    with app.app_context():
        run_all_seeders()

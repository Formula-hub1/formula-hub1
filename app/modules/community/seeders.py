"""
Community seeders - Sample data for development/testing
"""

from app.modules.community.models import Community, CommunityMembership, CommunityRole
from core.seeders.BaseSeeder import BaseSeeder


class CommunitySeeder(BaseSeeder):
    """Seeder for communities"""

    priority = 10  # Run after users and datasets

    def run(self):
        """Seed sample communities"""
        from app.modules.auth.models import User

        print("Seeding communities...")

        # Get existing users (from AuthSeeder)
        user1 = User.query.filter_by(email="user1@example.com").first()
        user2 = User.query.filter_by(email="user2@example.com").first()

        if not user1:
            print("Warning: No users found. Please seed users first.")
            return

        # Create communities
        communities_data = [
            {
                "name": "Formula 1 Research",
                "slug": "f1-research",
                "description": "Comunidad dedicada a datasets de Fórmula 1 y motorsport",
                "is_public": True,
            },
            {
                "name": "Software Product Lines",
                "slug": "spl",
                "description": "Investigación y datasets sobre líneas de productos software",
                "is_public": True,
            },
            {
                "name": "Universidad de Sevilla",
                "slug": "us",
                "description": "Comunidad institucional de la Universidad de Sevilla",
                "is_public": True,
            },
        ]

        for i, data in enumerate(communities_data):
            # Check if community already exists
            existing = Community.query.filter_by(slug=data["slug"]).first()
            if existing:
                print(f"  Community '{data['name']}' already exists")
                continue

            # Create community
            community = Community(**data)
            self.db.session.add(community)
            self.db.session.flush()

            # Assign owner (alternate between users)
            owner = user1 if i % 2 == 0 else (user2 if user2 else user1)
            membership = CommunityMembership(
                community_id=community.id,
                user_id=owner.id,
                role=CommunityRole.OWNER
            )
            self.db.session.add(membership)

            # Add the other user as curator to first community
            if i == 0 and user2:
                curator = CommunityMembership(
                    community_id=community.id,
                    user_id=user2.id,
                    role=CommunityRole.CURATOR
                )
                self.db.session.add(curator)

            print(f"  Created community: {community.name}")

        self.db.session.commit()
        print("CommunitySeeder performed.")
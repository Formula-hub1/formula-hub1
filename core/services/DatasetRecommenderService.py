from datetime import datetime, timezone
from typing import Any, Dict, List, Set

from app.modules.dataset.models import DataSet
from app.modules.dataset.repositories import DataSetRepository, DSDownloadRecordRepository


class SimilarityCalculator:

    @staticmethod
    def jaccard_similarity(set_a: Set[Any], set_b: Set[Any]) -> float:
        intersection = len(set_a.intersection(set_b))
        union = len(set_a.union(set_b))
        return intersection / union if union > 0 else 0.0

    @staticmethod
    def normalize(value: float, max_value: float) -> float:
        return value / max_value if max_value > 0 else 0.0

    @staticmethod
    def calculate_tag_score(target_ds: DataSet, candidate_ds: DataSet) -> float:
        target_tags_str = target_ds.ds_meta_data.tags
        candidate_tags_str = candidate_ds.ds_meta_data.tags

        tags_a = set(target_tags_str.split(",")) if target_tags_str else set()
        tags_b = set(candidate_tags_str.split(",")) if candidate_tags_str else set()

        return SimilarityCalculator.jaccard_similarity(tags_a, tags_b)

    @staticmethod
    def calculate_author_score(target_ds: DataSet, candidate_ds: DataSet) -> float:
        authors_a = {a.id for a in target_ds.ds_meta_data.authors}
        authors_b = {a.id for a in candidate_ds.ds_meta_data.authors}
        return SimilarityCalculator.jaccard_similarity(authors_a, authors_b)

    @staticmethod
    def calculate_recency_score(ds: DataSet, max_age_days: int) -> float:

        age_seconds = (datetime.now(timezone.utc) - ds.created_at.replace(tzinfo=timezone.utc)).total_seconds()
        max_age_seconds = max_age_days * 24 * 3600

        normalized_age = SimilarityCalculator.normalize(age_seconds, max_age_seconds)
        return max(0.0, 1.0 - normalized_age)

    @staticmethod
    def calculate_final_score(
        target_ds: DataSet, candidate_ds: DataSet, max_downloads: int, downloads_count: int
    ) -> float:

        WEIGHT_TAGS = 0.30  # Similitud temática
        WEIGHT_AUTHORS = 0.20  # Relevancia autorial
        WEIGHT_DOWNLOADS = 0.25  # Popularidad
        WEIGHT_RECENCY = 0.25  # Actualidad

        score_tags = SimilarityCalculator.calculate_tag_score(target_ds, candidate_ds)
        score_authors = SimilarityCalculator.calculate_author_score(target_ds, candidate_ds)

        score_downloads = SimilarityCalculator.normalize(downloads_count, max_downloads)

        score_recency = SimilarityCalculator.calculate_recency_score(candidate_ds, max_age_days=365 * 2)

        final_score = (
            (WEIGHT_TAGS * score_tags)
            + (WEIGHT_AUTHORS * score_authors)
            + (WEIGHT_DOWNLOADS * score_downloads)
            + (WEIGHT_RECENCY * score_recency)
        )

        return final_score


class DatasetRecommenderService:

    def __init__(
        self, dataset_repository: DataSetRepository, ds_download_repository: DSDownloadRecordRepository, k: int = 5
    ):
        self.dataset_repository = dataset_repository
        self.ds_download_repository = ds_download_repository
        self.k = k

    def get_recommendations(self, target_dataset: DataSet) -> List[Dict[str, Any]]:

        all_datasets = self.dataset_repository.get_all_synchronized_datasets()
        max_downloads = self.ds_download_repository.total_dataset_downloads()

        recommendations = []

        for candidate_ds in all_datasets:
            if candidate_ds.id == target_dataset.id:
                continue

            downloads_count = self.ds_download_repository.count_downloads_for_dataset(candidate_ds.id)

            candidate_ds.downloads_count = downloads_count

            score = SimilarityCalculator.calculate_final_score(
                target_dataset, candidate_ds, max_downloads, downloads_count
            )

            candidate_title = (
                candidate_ds.ds_meta_data.title
                if candidate_ds.ds_meta_data
                else f"Suggested Dataset #{candidate_ds.id}"
            )

            recommendations.append({"ds_id": candidate_ds.id, "score": score, "title": candidate_title})

        recommendations.sort(key=lambda x: x["score"], reverse=True)
        return [{"id": rec["ds_id"], "title": rec["title"]} for rec in recommendations[: self.k]]

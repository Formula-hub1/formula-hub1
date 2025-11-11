import unittest
from unittest.mock import MagicMock
from datetime import datetime, timedelta, timezone
from typing import Set, Any
from core.services.DatasetRecommenderService import SimilarityCalculator, DatasetRecommenderService 
from app.modules.dataset.models import DataSet 
from app.modules.dataset.repositories import DataSetRepository, DSDownloadRecordRepository

# --- MOCKS DE ESTRUCTURA Y DATOS ---

# UTC para simular la fecha en la BD
NOW = datetime.now(timezone.utc)
RECENT_DATE = NOW - timedelta(days=30)
OLD_DATE = NOW - timedelta(days=300)
MAX_AGE_DAYS = 365 * 2 # 730 días para normalización

class MockAuthor:
    """Simula un objeto Author para la relación Many-to-Many."""
    def __init__(self, id):
        self.id = id

class MockDSMetaData:
    """Simula el objeto DSMetaData para tags y autores."""
    def __init__(self, tags, authors):
        self.tags = tags
        self.authors = authors

class MockDataSet:
    """Simula la instancia de DataSet con las relaciones necesarias."""
    def __init__(self, id, title, tags_str, author_ids, created_at, downloads_count=0):
        self.id = id
        self.created_at = created_at
        # Simular la estructura ORM:
        self.ds_meta_data = MockDSMetaData(
            tags=tags_str,
            authors=[MockAuthor(aid) for aid in author_ids]
        )
        # Campo temporal que se añade en el servicio de recomendación:
        self.downloads_count = downloads_count
        self.ds_meta_data.title = title # Añadir título para el resultado final


# --- TESTS DE CÁLCULO DE SIMILITUD (Lógica Matemática) ---

class TestSimilarityCalculator(unittest.TestCase):
    
    # 🎯 DATOS DE PRUEBA
    DS_TARGET = MockDataSet(100, "Target DS", "ux,dev,test", [1, 2], RECENT_DATE)
    DS_HIGH = MockDataSet(1, "High Match", "ux,dev,backend", [1], RECENT_DATE) # Tags: 2/4 (0.5). Autores: 1/2 (0.5)
    DS_LOW = MockDataSet(2, "Low Match", "ai,data", [99], OLD_DATE) # Similitud temática: 0.0

    def test_01_jaccard_similarity(self):
        """Verifica que el índice de Jaccard es correcto."""
        set_a = {"a", "b", "c"}
        set_b = {"b", "c", "d"}
        score = SimilarityCalculator.jaccard_similarity(set_a, set_b) # Intersection 2, Union 4
        self.assertAlmostEqual(score, 0.50, places=2)

    def test_02_recency_score_is_high_for_recent(self):
        """Verifica que los objetos recientes obtienen un score alto."""
        # Se asume que RECENT_DATE (30 días) es muy reciente comparado con 730 días
        score = SimilarityCalculator.calculate_recency_score(self.DS_TARGET, MAX_AGE_DAYS) 
        self.assertGreater(score, 0.95)

    def test_03_score_is_zero_if_no_metadata(self):
        """Verifica que el score de tags es 0.0 si no hay tags."""
        ds_empty = MockDataSet(3, "Empty Tags", None, [], RECENT_DATE)
        score_tags = SimilarityCalculator.calculate_tag_score(self.DS_TARGET, ds_empty)
        score_authors = SimilarityCalculator.calculate_author_score(self.DS_TARGET, ds_empty)
        
        self.assertAlmostEqual(score_tags, 0.0, places=2)
        self.assertAlmostEqual(score_authors, 0.0, places=2)


class TestDatasetRecommenderService(unittest.TestCase):

    def setUp(self):
        """Configura los mocks para el motor de recomendación."""
        
        self.mock_dataset_repo = MagicMock(spec=DataSetRepository)
        self.mock_download_repo = MagicMock(spec=DSDownloadRecordRepository)
        
        self.recommender = DatasetRecommenderService(
            dataset_repository=self.mock_dataset_repo,
            ds_download_repository=self.mock_download_repo
        )

        # 🎯 DATOS DE CANDIDATOS (Simulación de la BD)
        self.ds_target = MockDataSet(100, "Target DS", "web,js,api", [10], RECENT_DATE)

        self.candidate_A = MockDataSet(1, "API Tools", "web,api,http", [10, 11], RECENT_DATE, downloads_count=900) # Alta popularidad, tags en común
        self.candidate_B = MockDataSet(2, "Old Docs", "manual", [20], OLD_DATE, downloads_count=100) # Baja popularidad, antiguo
        self.candidate_C = MockDataSet(3, "UX Frontend", "ux,css", [10], RECENT_DATE, downloads_count=500) # Media popularidad, autor en común

        # Configurar los mocks de repositorio para que devuelvan los datos
        self.mock_dataset_repo.get_all_synchronized_datasets.return_value = [
            self.candidate_A, self.candidate_B, self.candidate_C
        ]
        self.mock_download_repo.total_dataset_downloads.return_value = 1000 # Máximo global de descargas
        
        # Configurar el conteo individual de descargas para el motor:
        def mock_count(ds_id):
            if ds_id == 1: return 900 
            if ds_id == 2: return 100 
            if ds_id == 3: return 500 
            return 0
        
        self.mock_download_repo.count_downloads_for_dataset.side_effect = mock_count

    def test_04_engine_returns_top_k_sorted_objects(self):
        """Verifica que el motor calcula los scores, ordena y devuelve los objetos con título."""
        
        recommendations = self.recommender.get_recommendations(self.ds_target)

        # El algoritmo debe funcionar con 3 candidatos y devolverlos todos
        self.assertEqual(len(recommendations), 3) 
        
        # 1. El formato de la respuesta debe ser una lista de diccionarios con ID y TÍTULO
        self.assertTrue(isinstance(recommendations[0], dict))
        self.assertIn('title', recommendations[0])
        
        # 2. Verificar el orden (A debería ser el mejor score por su popularidad extrema)
        self.assertEqual(recommendations[0]['id'], 1) # Candidato A (900 descargas, Reciente)
        self.assertEqual(recommendations[1]['id'], 3) # Candidato C (500 descargas, Reciente, Autor común)
        self.assertEqual(recommendations[2]['id'], 2) # Candidato B (100 descargas, Antiguo)
        
        # 3. Verificar que el título se devuelve correctamente
        self.assertEqual(recommendations[0]['title'], "API Tools")

    def test_05_target_dataset_is_excluded(self):
        """Verifica que el dataset target no se recomienda a sí mismo."""
        
        recommendations = self.recommender.get_recommendations(self.ds_target)
        self.assertNotIn(100, [rec['id'] for rec in recommendations])
import re

import unidecode
from sqlalchemy import any_, or_, and_
from sqlalchemy.orm import joinedload 

from app.modules.dataset.models import Author, DataSet, DSMetaData, PublicationType
from app.modules.featuremodel.models import FeatureModel, FMMetaData
from core.repositories.BaseRepository import BaseRepository


class ExploreRepository(BaseRepository):
    def __init__(self):
        super().__init__(DataSet)

    def filter(self, query="", sorting="newest", publication_type="any", tags=[], **kwargs):
        
        # Normalize and remove unwanted characters
        normalized_query = unidecode.unidecode(query).lower()
        # Permitimos el punto para buscar archivos (e.g., file.uvl)
        cleaned_query = re.sub(r'[,":\'()\[\]^;!¡¿?]', "", normalized_query).strip()

        # Inicia la consulta y las uniones (joins)
        datasets_query = (
            self.model.query.join(DataSet.ds_meta_data)
            .outerjoin(DSMetaData.authors)
            .outerjoin(DataSet.feature_models)
            .outerjoin(FeatureModel.fm_meta_data)
            .filter(DSMetaData.dataset_doi.isnot(None))
        )

        # -------------------------------------------------------------
        # 1. LÓGICA DE FILTRADO POR BÚSQUEDA (QUERY)
        # -------------------------------------------------------------
        if cleaned_query:
            
            final_filters = []
            words = cleaned_query.split()
            
            # --- Condición A: Búsqueda OR Amplia (Frase Completa) ---
            # Este es el filtro de búsqueda flexible: busca la frase exacta en CUALQUIER campo.
            # Funciona para "Author 4", "tag1", "file.uvl", y "sample dataset 3".
            phrase_match_in_any_field = or_(
                DSMetaData.title.ilike(f"%{cleaned_query}%"),
                DSMetaData.description.ilike(f"%{cleaned_query}%"),
                DSMetaData.tags.ilike(f"%{cleaned_query}%"),
                Author.name.ilike(f"%{cleaned_query}%"),
                Author.affiliation.ilike(f"%{cleaned_query}%"),
                FMMetaData.uvl_filename.ilike(f"%{cleaned_query}%"),
                FMMetaData.title.ilike(f"%{cleaned_query}%"),
                FMMetaData.description.ilike(f"%{cleaned_query}%"),
                FMMetaData.tags.ilike(f"%{cleaned_query}%"),
            )
            final_filters.append(phrase_match_in_any_field)
            
            # --- Condición B: Búsqueda Estricta AND (Solo para Títulos Multipalabra) ---
            # Si hay más de una palabra, añadimos el requisito estricto en el título para reducir resultados.
            if len(words) > 1:
                
                strict_title_and_words = [] 
                
                for word in words:
                    # Requerimos que TODAS las palabras estén presentes en el TÍTULO.
                    strict_title_and_words.append(DSMetaData.title.ilike(f"%{word}%"))

                # Agregamos la condición B (AND en título) al filtro final OR
                strict_title_and = and_(*strict_title_and_words)
                final_filters.append(strict_title_and)
            
            # Aplicamos la condición final: OR(Frase Completa) OR (AND en Título)
            # Con solo estas dos condiciones (A y B), cubrimos todos los casos:
            # - Búsqueda simple (Author 4): A se activa, B no se activa o falla, A encuentra.
            # - Búsqueda estricta (sample dataset 3): A y B se activan, B fuerza el filtro.
            datasets_query = datasets_query.filter(or_(*final_filters))

        # -------------------------------------------------------------
        # 2. FILTRADO POR TIPO DE PUBLICACIÓN
        # -------------------------------------------------------------
        if publication_type != "any":
            matching_type = None
            for member in PublicationType:
                if member.value.lower() == publication_type:
                    matching_type = member
                    break

            if matching_type is not None:
                datasets_query = datasets_query.filter(DSMetaData.publication_type == matching_type.name)

        # -------------------------------------------------------------
        # 3. FILTRADO POR TAGS (Usa la variable `tags` de los argumentos)
        # -------------------------------------------------------------
        if tags:
            # Esto asume que DSMetaData.tags es un campo de texto o array que soporta la función any_
            datasets_query = datasets_query.filter(DSMetaData.tags.ilike(any_(f"%{tag}%" for tag in tags)))

        # -------------------------------------------------------------
        # 4. ORDENAMIENTO
        # -------------------------------------------------------------
        if sorting == "oldest":
            datasets_query = datasets_query.order_by(self.model.created_at.asc())
        else:
            datasets_query = datasets_query.order_by(self.model.created_at.desc())

        # Aseguramos que solo se devuelvan resultados únicos.
        return datasets_query.distinct().all()
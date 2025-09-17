from django_elasticsearch_dsl import Document
from typing import List, Dict, Any, Optional


class FoodSearcher:
    """Класс-помощник для поиска и автокомплита продуктов"""

    @staticmethod
    def autocomplete(
        document: Document, query: str, user_id: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Автокомплит по названиям продуктов/рецептов

        Args:
            document: Документ Elasticsearch (BaseFoodDocument, CustomFoodDocument, RecipeDocument)
            query: Поисковый запрос
            user_id: ID пользователя для фильтрации
            limit: Лимит результатов

        Returns:
            Список результатов автокомплита
        """
        if limit <= 0 or limit > 100:
            raise ValueError(
                "Некорректное ограничение по количеству возвращаемых записей."
            )

        if not query or len(query) < 2:
            return []

        # Определяем поле для поиска в зависимости от типа документа
        field_mapping = {
            "BaseFoodDocument": "name.suggest",
            "CustomFoodDocument": "custom_name.suggest",
            "RecipeDocument": "name.suggest",
        }

        doc_type = document.__name__
        suggest_field = field_mapping.get(doc_type)

        if not suggest_field:
            raise ValueError(f"Unsupported document type: {doc_type}")

        # Создаем поисковый запрос
        search = document.search()

        # Добавляем фильтр по пользователю для CustomFood и Recipe
        if doc_type in ["CustomFoodDocument", "RecipeDocument"] and user_id:
            search = search.filter("term", user_id=user_id)

        # Выполняем suggest запрос
        suggestions = search.suggest(
            "autocomplete", query, completion={"field": suggest_field}
        ).execute()

        # Обрабатываем результаты
        results = []
        if hasattr(suggestions, "suggest") and suggestions.suggest:
            for suggestion in suggestions.suggest.autocomplete:
                for option in suggestion.options:
                    result = {
                        "text": option.text,
                        "type": doc_type.replace("Document", "").lower(),
                        "score": option._score,
                    }
                    results.append(result)

        # Сортируем по score и ограничиваем лимит
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    @staticmethod
    def search(
        document: Document,
        query: str,
        user_id: Optional[str] = None,
        fields: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Полнотекстовый поиск по продуктам/рецептам

        Args:
            document: Документ Elasticsearch
            query: Поисковый запрос
            user_id: ID пользователя для фильтрации
            fields: Поля для поиска (если None - используются по умолчанию)
            filters: Дополнительные фильтры
            limit: Лимит результатов
            offset: Смещение для пагинации

        Returns:
            Результаты поиска с метаданными
        """
        if limit <= 0 or limit > 100:
            raise ValueError(
                "Некорректное ограничение по количеству возвращаемых записей."
            )
        if offset < 0 or offset > 100:
            raise ValueError("Некорректный свдиг по списку возвращаемых записей.")
        if not query or len(query) < 2:
            return {
                "total": 0,
                "took_ms": 0,
                "results": [],
                "limit": limit,
                "offset": offset,
            }

        doc_type = document.__name__

        # Определяем поля для поиска по умолчанию
        default_fields_mapping = {
            "BaseFoodDocument": ["name^3"],
            "CustomFoodDocument": ["custom_name^3"],
            "RecipeDocument": ["name^3", "description"],
        }

        search_fields = fields or default_fields_mapping.get(doc_type, [])

        if not search_fields:
            raise ValueError(f"No search fields defined for document type: {doc_type}")

        # Создаем поисковый запрос
        search = document.search()

        # Основной поисковый запрос
        if len(search_fields) == 1:
            # Одно поле - используем match
            field = search_fields[0].split("^")[0]  # Убираем boost
            search = search.query(
                "match", **{field: {"query": query, "analyzer": "russian_analyzer"}}
            )
        else:
            # Несколько полей - используем multi_match
            search = search.query(
                "multi_match",
                query=query,
                fields=search_fields,
                analyzer="russian_analyzer",
            )

        # Фильтр по пользователю для CustomFood и Recipe
        if doc_type in ["CustomFoodDocument", "RecipeDocument"] and user_id:
            search = search.filter("term", user_id=user_id)

        # Дополнительные фильтры
        if filters:
            for field, value in filters.items():
                search = search.filter("term", **{field: value})

        # Применяем пагинацию
        search = search[offset : offset + limit]

        # Выполняем поиск
        results = search.execute()

        # Форматируем результаты
        formatted_results = []
        ids = []
        for hit in results:
            result_data = hit.to_dict()
            result_data["_score"] = hit.meta.score
            result_data["_type"] = doc_type.replace("Document", "").lower()
            ids.append(hit.id)
            formatted_results.append(result_data)

        return {
            "total": results.hits.total.value,
            "took_ms": results.took,
            "results": formatted_results,
            "ids": ids,
            "offset": offset,
            "limit": limit,
        }

    @staticmethod
    def get_document_fields(document: Document) -> List[str]:
        """
        Получить список полей документа для поиска

        Args:
            document: Документ Elasticsearch

        Returns:
            Список доступных полей
        """
        doc_type = document.__class__.__name__

        fields_mapping = {
            "BaseFoodDocument": ["name"],
            "CustomFoodDocument": ["custom_name", "user_id"],
            "RecipeDocument": ["name", "description", "user_id"],
        }

        return fields_mapping.get(doc_type, [])

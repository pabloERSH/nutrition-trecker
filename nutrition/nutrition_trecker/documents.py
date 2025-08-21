from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from .models import BaseFood, CustomFood, Recipe


@registry.register_document
class BaseFoodDocument(Document):
    """Документ Elasticsearch для модели BaseFood."""

    name = fields.TextField(
        analyzer="russian_analyzer",
        fields={"raw": fields.KeywordField(), "suggest": fields.CompletionField()},
    )

    class Index:
        name = "base_food"
        settings = {
            "number_of_shards": 1,
            "number_of_replicas": 1,
            "analysis": {
                "analyzer": {
                    "russian_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": [
                            "lowercase",
                            "russian_stop",
                            "russian_stemmer",
                            "ngram_filter",
                        ],
                    }
                },
                "filter": {
                    "russian_stop": {"type": "stop", "stopwords": "_russian_"},
                    "russian_stemmer": {"type": "stemmer", "language": "russian"},
                    "ngram_filter": {"type": "ngram", "min_gram": 3, "max_gram": 4},
                },
            },
        }

    class Django:
        model = BaseFood
        fields = [
            "id",
        ]

    def prepare_name(self, instance):
        """Подготовка поля name для индексации."""
        return instance.name.lower()

    def prepare_suggest(self, instance):
        """Подготовка поля suggest для автокомплита."""
        return {"input": [instance.name.lower()], "weight": 1}


@registry.register_document
class CustomFoodDocument(Document):
    """Документ Elasticsearch для модели CustomFood."""

    custom_name = fields.TextField(
        analyzer="russian_analyzer",
        fields={"raw": fields.KeywordField(), "suggest": fields.CompletionField()},
    )
    user_id = fields.KeywordField()

    class Index:
        name = "custom_food"
        settings = {
            "number_of_shards": 1,
            "number_of_replicas": 1,
            "analysis": {
                "analyzer": {
                    "russian_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": [
                            "lowercase",
                            "russian_stop",
                            "russian_stemmer",
                            "ngram_filter",
                        ],
                    }
                },
                "filter": {
                    "russian_stop": {"type": "stop", "stopwords": "_russian_"},
                    "russian_stemmer": {"type": "stemmer", "language": "russian"},
                    "ngram_filter": {"type": "ngram", "min_gram": 3, "max_gram": 4},
                },
            },
        }

    class Django:
        model = CustomFood
        fields = [
            "id",
        ]

    def prepare_custom_name(self, instance):
        """Подготовка поля custom_name для индексации."""
        return instance.custom_name.lower()

    def prepare_suggest(self, instance):
        """Подготовка поля suggest для автокомплита."""
        return {
            "input": [instance.custom_name.lower()],
            "weight": 1,
            "contexts": {"user_id": instance.user.id},  # Для фильтрации по пользователю
        }


@registry.register_document
class RecipeDocument(Document):
    """Документ Elasticsearch для модели Recipe."""

    name = fields.TextField(
        analyzer="russian_analyzer",
        fields={"raw": fields.KeywordField(), "suggest": fields.CompletionField()},
    )
    description = fields.TextField(
        analyzer="russian_analyzer", fields={"raw": fields.KeywordField()}
    )
    user_id = fields.KeywordField()

    class Index:
        name = "recipe"
        settings = {
            "number_of_shards": 1,
            "number_of_replicas": 1,
            "analysis": {
                "analyzer": {
                    "russian_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": [
                            "lowercase",
                            "russian_stop",
                            "russian_stemmer",
                            "ngram_filter",
                        ],
                    }
                },
                "filter": {
                    "russian_stop": {"type": "stop", "stopwords": "_russian_"},
                    "russian_stemmer": {"type": "stemmer", "language": "russian"},
                    "ngram_filter": {"type": "ngram", "min_gram": 3, "max_gram": 4},
                },
            },
        }

    class Django:
        model = Recipe
        fields = [
            "id",
        ]

    def prepare_name(self, instance):
        """Подготовка поля name для индексации."""
        return instance.name.lower()

    def prepare_description(self, instance):
        """Подготовка поля description для индексации."""
        return instance.description.lower() if instance.description else ""

    def prepare_suggest(self, instance):
        """Подготовка поля suggest для автокомплита."""
        return {
            "input": [instance.name.lower()],
            "weight": 1,
            "contexts": {"user_id": instance.user.id},  # Для фильтрации по пользователю
        }

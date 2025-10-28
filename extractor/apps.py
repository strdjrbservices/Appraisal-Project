from django.apps import AppConfig

class ExtractorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'extractor'

    def ready(self):
        """
        This method is called when the Django app is ready.
        """
        from . import genai_config
        genai_config.configure_genai()

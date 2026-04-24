from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name               = 'projects'

    def ready(self):
        """
        Import signals here so the receiver is registered
        when Django starts. Without this the signal never fires.
        """
        import projects.signals   # noqa: F401
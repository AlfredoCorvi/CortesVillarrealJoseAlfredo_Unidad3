"""La autenticación utiliza el modelo User de django.contrib.auth.

Sus migraciones crean auth_user (usuario, correo, hash de contraseña,
permisos y fechas) y django_session guarda las sesiones. No se duplica
el modelo ni se cambia AUTH_USER_MODEL en una base ya migrada.
Para acceder a los usuarios, usar django.contrib.auth.get_user_model().
"""

from django.db import models


class AuthRequestBucket(models.Model):
    """Shared rate-limit counters; identifiers are keyed hashes, never raw inputs."""
    key = models.CharField(max_length=64, primary_key=True)
    expires_at = models.PositiveBigIntegerField(db_index=True)
    attempts = models.PositiveIntegerField(default=0)

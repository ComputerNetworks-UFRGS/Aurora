import logging
from django.db import models

class BaseSingletonModel(models.Model):
    """Singleton Model
 
    Ensures there's always only one entry in the database, and can fix the
    table (by deleting extra entries) even if added via another mechanism.
 
    Also has a static load() method which always returns the object - from
    the database if possible, or a new empty (default) instance if the
    database is still empty. If your instance has sane defaults (recommended),
    you can use it immediately without worrying if it was saved to the
    database or not.
 
    Useful for things like system-wide user-editable settings.
    """

    class Meta:
        # Makes django recognize model in split modules
        app_label = 'cloud'
        # Turns this into an abstract model (does not create table for it)
        abstract = True

    # Allows only one instance of submodels
    def save(self, *args, **kwargs):
        """
        Save object to the database. Removes all other entries if there
        are any.
        """
        self.__class__.objects.exclude(id=self.id).delete()
        super(BaseSingletonModel, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        """
        Load object from the database. Failing that, create a new empty
        (default) instance of the object and return it (without saving it
        to the database).
        """
        try:
            return cls.objects.get()
        except cls.DoesNotExist:
            return cls()

    # Default exception for models in cloud
    class SingletonModelException(Exception):
        # Get an instance of a logger
        logger = logging.getLogger(__name__)

        def __init__(self, msg):
            self.msg = msg
            self.logger.warning(msg)

        def __str__(self):
            return repr(self.msg)

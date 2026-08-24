"""SQLAlchemy models.

Imported for their side effect of registering with the declarative metadata —
Alembic autogenerate only sees tables that have been imported.
"""

from itsc.models.contact import ContactMessage
from itsc.models.document import Document, DocumentCategory, DocumentFile
from itsc.models.media import MediaAsset
from itsc.models.novedad import Novedad
from itsc.models.user import User

__all__ = [
    "ContactMessage",
    "Document",
    "DocumentCategory",
    "DocumentFile",
    "MediaAsset",
    "Novedad",
    "User",
]

"""initial schema

Revision ID: 7c9ee233c544
Revises: 
Create Date: 2026-08-23 23:48:06.111309

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '7c9ee233c544'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # CITEXT backs case-insensitive usernames and emails, so "Admin" and
    # "admin" cannot both be registered. Autogenerate does not emit this.
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    op.create_table('document_categories',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=64), nullable=False),
    sa.Column('nombre', sa.String(length=120), nullable=False),
    sa.Column('descripcion', sa.Text(), server_default=sa.text("''"), nullable=False),
    sa.Column('icon', sa.String(length=64), server_default=sa.text("'file'"), nullable=False),
    sa.Column('orden', sa.SmallInteger(), server_default=sa.text('0'), nullable=False),
    sa.Column('has_vigencia', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('slug')
    )
    with op.batch_alter_table('document_categories', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_document_categories_created_at'), ['created_at'], unique=False)

    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', postgresql.CITEXT(), nullable=False),
    sa.Column('email', postgresql.CITEXT(), nullable=True),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('role', sa.String(length=16), server_default=sa.text("'editor'"), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('failed_login_count', sa.SmallInteger(), server_default=sa.text('0'), nullable=False),
    sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_login_ip', sa.String(length=64), nullable=True),
    sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("role IN ('admin', 'editor')", name='ck_users_role'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('username')
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index('ix_users_active', ['is_active'], unique=False)
        batch_op.create_index(batch_op.f('ix_users_created_at'), ['created_at'], unique=False)

    op.create_table('contact_messages',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('asunto', sa.String(length=200), nullable=False),
    sa.Column('nombre', sa.String(length=120), nullable=False),
    sa.Column('email', postgresql.CITEXT(), nullable=False),
    sa.Column('telefono', sa.String(length=40), nullable=True),
    sa.Column('motivo', sa.String(length=60), nullable=False),
    sa.Column('mensaje', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=16), server_default=sa.text("'new'"), nullable=False),
    sa.Column('ip_hash', sa.String(length=64), nullable=True),
    sa.Column('user_agent', sa.String(length=300), nullable=True),
    sa.Column('handled_by_id', sa.Integer(), nullable=True),
    sa.Column('handled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('new', 'read', 'answered', 'spam')", name='ck_contact_status'),
    sa.CheckConstraint('length(btrim(mensaje)) > 0', name='ck_contact_mensaje_nonempty'),
    sa.ForeignKeyConstraint(['handled_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('contact_messages', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_contact_messages_created_at'), ['created_at'], unique=False)
        batch_op.create_index('ix_contact_triage', ['status', 'created_at'], unique=False)

    op.create_table('documents',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('category_id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=200), nullable=False),
    sa.Column('titulo', sa.String(length=300), nullable=False),
    sa.Column('descripcion', sa.Text(), server_default=sa.text("''"), nullable=False),
    sa.Column('numero', sa.String(length=60), nullable=True),
    sa.Column('fecha_documento', sa.Date(), nullable=False),
    sa.Column('vigente_desde', sa.Date(), nullable=True),
    sa.Column('vigente_hasta', sa.Date(), nullable=True),
    sa.Column('status', sa.String(length=16), server_default=sa.text("'draft'"), nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('author_id', sa.Integer(), nullable=True),
    sa.Column('search_vector', postgresql.TSVECTOR(), sa.Computed("to_tsvector('spanish', coalesce(titulo,'') || ' ' || coalesce(numero,'') || ' ' || coalesce(descripcion,''))", persisted=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status <> 'published' OR published_at IS NOT NULL", name='ck_documents_published_has_date'),
    sa.CheckConstraint("status IN ('draft', 'published', 'archived')", name='ck_documents_status'),
    sa.CheckConstraint('length(btrim(titulo)) > 0', name='ck_documents_titulo_nonempty'),
    sa.CheckConstraint('vigente_hasta IS NULL OR vigente_desde IS NULL OR vigente_hasta >= vigente_desde', name='ck_documents_vigencia_ordered'),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['category_id'], ['document_categories.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('category_id', 'numero', name='uq_documents_category_numero'),
    sa.UniqueConstraint('category_id', 'slug', name='uq_documents_category_slug')
    )
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_documents_created_at'), ['created_at'], unique=False)
        batch_op.create_index('ix_documents_listing', ['category_id', 'status', 'fecha_documento'], unique=False)
        batch_op.create_index('ix_documents_search', ['search_vector'], unique=False, postgresql_using='gin')

    op.create_table('media_assets',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('public_id', sa.UUID(), nullable=False),
    sa.Column('original_filename', sa.String(length=255), nullable=False),
    sa.Column('storage_key', sa.String(length=255), nullable=False),
    sa.Column('mime_type', sa.String(length=64), nullable=False),
    sa.Column('byte_size', sa.Integer(), nullable=False),
    sa.Column('width', sa.Integer(), nullable=True),
    sa.Column('height', sa.Integer(), nullable=True),
    sa.Column('checksum_sha256', sa.String(length=64), nullable=False),
    sa.Column('alt_text', sa.String(length=255), server_default=sa.text("''"), nullable=False),
    sa.Column('uploaded_by_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("mime_type IN ('image/webp', 'image/jpeg', 'image/png', 'application/pdf')", name='ck_media_mime'),
    sa.CheckConstraint('byte_size > 0', name='ck_media_size_positive'),
    sa.ForeignKeyConstraint(['uploaded_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('checksum_sha256'),
    sa.UniqueConstraint('public_id'),
    sa.UniqueConstraint('storage_key')
    )
    with op.batch_alter_table('media_assets', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_media_assets_created_at'), ['created_at'], unique=False)
        batch_op.create_index('ix_media_created', ['created_at'], unique=False)

    op.create_table('document_files',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('document_id', sa.BigInteger(), nullable=False),
    sa.Column('media_asset_id', sa.BigInteger(), nullable=False),
    sa.Column('label', sa.String(length=160), server_default=sa.text("''"), nullable=False),
    sa.Column('orden', sa.SmallInteger(), server_default=sa.text('0'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['media_asset_id'], ['media_assets.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('document_id', 'media_asset_id', name='uq_document_files_pair')
    )
    with op.batch_alter_table('document_files', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_document_files_created_at'), ['created_at'], unique=False)

    op.create_table('novedades',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('slug', sa.String(length=200), nullable=False),
    sa.Column('titulo', sa.String(length=200), nullable=False),
    sa.Column('resumen', sa.String(length=400), server_default=sa.text("''"), nullable=False),
    sa.Column('cuerpo', sa.Text(), server_default=sa.text("''"), nullable=False),
    sa.Column('imagen_id', sa.BigInteger(), nullable=True),
    sa.Column('status', sa.String(length=16), server_default=sa.text("'draft'"), nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('author_id', sa.Integer(), nullable=True),
    sa.Column('search_vector', postgresql.TSVECTOR(), sa.Computed("to_tsvector('spanish', coalesce(titulo,'') || ' ' || coalesce(resumen,'') || ' ' || coalesce(cuerpo,''))", persisted=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status <> 'published' OR published_at IS NOT NULL", name='ck_novedades_published_has_date'),
    sa.CheckConstraint("status IN ('draft', 'published', 'archived')", name='ck_novedades_status'),
    sa.CheckConstraint('length(btrim(titulo)) > 0', name='ck_novedades_titulo_nonempty'),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['imagen_id'], ['media_assets.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('slug')
    )
    with op.batch_alter_table('novedades', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_novedades_created_at'), ['created_at'], unique=False)
        batch_op.create_index('ix_novedades_listing', ['status', 'published_at'], unique=False)
        batch_op.create_index('ix_novedades_search', ['search_vector'], unique=False, postgresql_using='gin')



def downgrade():
    # NOTE: the citext extension is intentionally left in place.
    with op.batch_alter_table('novedades', schema=None) as batch_op:
        batch_op.drop_index('ix_novedades_search', postgresql_using='gin')
        batch_op.drop_index('ix_novedades_listing')
        batch_op.drop_index(batch_op.f('ix_novedades_created_at'))

    op.drop_table('novedades')
    with op.batch_alter_table('document_files', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_document_files_created_at'))

    op.drop_table('document_files')
    with op.batch_alter_table('media_assets', schema=None) as batch_op:
        batch_op.drop_index('ix_media_created')
        batch_op.drop_index(batch_op.f('ix_media_assets_created_at'))

    op.drop_table('media_assets')
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.drop_index('ix_documents_search', postgresql_using='gin')
        batch_op.drop_index('ix_documents_listing')
        batch_op.drop_index(batch_op.f('ix_documents_created_at'))

    op.drop_table('documents')
    with op.batch_alter_table('contact_messages', schema=None) as batch_op:
        batch_op.drop_index('ix_contact_triage')
        batch_op.drop_index(batch_op.f('ix_contact_messages_created_at'))

    op.drop_table('contact_messages')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_created_at'))
        batch_op.drop_index('ix_users_active')

    op.drop_table('users')
    with op.batch_alter_table('document_categories', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_document_categories_created_at'))

    op.drop_table('document_categories')

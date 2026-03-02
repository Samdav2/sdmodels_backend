"""Migrate all IDs from integer to UUID

Revision ID: 002
Revises: 001
Create Date: 2026-02-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    """
    Migrate all integer IDs to UUIDs
    
    IMPORTANT: This is a breaking change!
    - All existing data will be preserved
    - Integer IDs will be converted to UUIDs
    - Foreign key relationships will be maintained
    """
    
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Step 1: Add new UUID columns
    print("Adding UUID columns...")
    
    # Users table
    op.add_column('users', sa.Column('uuid_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE users SET uuid_id = uuid_generate_v4()")
    
    # User profiles
    op.add_column('user_profiles', sa.Column('uuid_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('user_profiles', sa.Column('uuid_user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE user_profiles SET uuid_id = uuid_generate_v4()")
    op.execute("""
        UPDATE user_profiles up
        SET uuid_user_id = u.uuid_id
        FROM users u
        WHERE up.user_id = u.id
    """)
    
    # Payment methods
    op.add_column('payment_methods', sa.Column('uuid_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('payment_methods', sa.Column('uuid_user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE payment_methods SET uuid_id = uuid_generate_v4()")
    op.execute("""
        UPDATE payment_methods pm
        SET uuid_user_id = u.uuid_id
        FROM users u
        WHERE pm.user_id = u.id
    """)
    
    # User followers
    op.add_column('user_followers', sa.Column('uuid_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('user_followers', sa.Column('uuid_follower_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('user_followers', sa.Column('uuid_following_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE user_followers SET uuid_id = uuid_generate_v4()")
    op.execute("""
        UPDATE user_followers uf
        SET uuid_follower_id = u.uuid_id
        FROM users u
        WHERE uf.follower_id = u.id
    """)
    op.execute("""
        UPDATE user_followers uf
        SET uuid_following_id = u.uuid_id
        FROM users u
        WHERE uf.following_id = u.id
    """)
    
    # Models table
    op.add_column('models', sa.Column('uuid_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('models', sa.Column('uuid_creator_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE models SET uuid_id = uuid_generate_v4()")
    op.execute("""
        UPDATE models m
        SET uuid_creator_id = u.uuid_id
        FROM users u
        WHERE m.creator_id = u.id
    """)
    
    # Model likes
    op.add_column('model_likes', sa.Column('uuid_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('model_likes', sa.Column('uuid_user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('model_likes', sa.Column('uuid_model_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE model_likes SET uuid_id = uuid_generate_v4()")
    op.execute("""
        UPDATE model_likes ml
        SET uuid_user_id = u.uuid_id
        FROM users u
        WHERE ml.user_id = u.id
    """)
    op.execute("""
        UPDATE model_likes ml
        SET uuid_model_id = m.uuid_id
        FROM models m
        WHERE ml.model_id = m.id
    """)
    
    # Model comments
    op.add_column('model_comments', sa.Column('uuid_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('model_comments', sa.Column('uuid_user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('model_comments', sa.Column('uuid_model_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('model_comments', sa.Column('uuid_parent_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE model_comments SET uuid_id = uuid_generate_v4()")
    op.execute("""
        UPDATE model_comments mc
        SET uuid_user_id = u.uuid_id
        FROM users u
        WHERE mc.user_id = u.id
    """)
    op.execute("""
        UPDATE model_comments mc
        SET uuid_model_id = m.uuid_id
        FROM models m
        WHERE mc.model_id = m.id
    """)
    op.execute("""
        UPDATE model_comments mc1
        SET uuid_parent_id = mc2.uuid_id
        FROM model_comments mc2
        WHERE mc1.parent_id = mc2.id
    """)
    
    # Step 2: Drop old foreign key constraints
    print("Dropping old foreign key constraints...")
    
    # User profiles
    op.drop_constraint('user_profiles_user_id_fkey', 'user_profiles', type_='foreignkey')
    
    # Payment methods
    op.drop_constraint('payment_methods_user_id_fkey', 'payment_methods', type_='foreignkey')
    
    # User followers
    op.drop_constraint('user_followers_follower_id_fkey', 'user_followers', type_='foreignkey')
    op.drop_constraint('user_followers_following_id_fkey', 'user_followers', type_='foreignkey')
    
    # Models
    op.drop_constraint('models_creator_id_fkey', 'models', type_='foreignkey')
    
    # Model likes
    op.drop_constraint('model_likes_user_id_fkey', 'model_likes', type_='foreignkey')
    op.drop_constraint('model_likes_model_id_fkey', 'model_likes', type_='foreignkey')
    
    # Model comments
    op.drop_constraint('model_comments_user_id_fkey', 'model_comments', type_='foreignkey')
    op.drop_constraint('model_comments_model_id_fkey', 'model_comments', type_='foreignkey')
    op.drop_constraint('model_comments_parent_id_fkey', 'model_comments', type_='foreignkey')
    
    # Step 3: Drop old primary keys and columns
    print("Dropping old primary keys and columns...")
    
    # Users
    op.drop_constraint('users_pkey', 'users', type_='primary')
    op.drop_column('users', 'id')
    op.alter_column('users', 'uuid_id', new_column_name='id', nullable=False)
    op.create_primary_key('users_pkey', 'users', ['id'])
    
    # User profiles
    op.drop_constraint('user_profiles_pkey', 'user_profiles', type_='primary')
    op.drop_column('user_profiles', 'id')
    op.drop_column('user_profiles', 'user_id')
    op.alter_column('user_profiles', 'uuid_id', new_column_name='id', nullable=False)
    op.alter_column('user_profiles', 'uuid_user_id', new_column_name='user_id', nullable=False)
    op.create_primary_key('user_profiles_pkey', 'user_profiles', ['id'])
    
    # Payment methods
    op.drop_constraint('payment_methods_pkey', 'payment_methods', type_='primary')
    op.drop_column('payment_methods', 'id')
    op.drop_column('payment_methods', 'user_id')
    op.alter_column('payment_methods', 'uuid_id', new_column_name='id', nullable=False)
    op.alter_column('payment_methods', 'uuid_user_id', new_column_name='user_id', nullable=False)
    op.create_primary_key('payment_methods_pkey', 'payment_methods', ['id'])
    
    # User followers
    op.drop_constraint('user_followers_pkey', 'user_followers', type_='primary')
    op.drop_column('user_followers', 'id')
    op.drop_column('user_followers', 'follower_id')
    op.drop_column('user_followers', 'following_id')
    op.alter_column('user_followers', 'uuid_id', new_column_name='id', nullable=False)
    op.alter_column('user_followers', 'uuid_follower_id', new_column_name='follower_id', nullable=False)
    op.alter_column('user_followers', 'uuid_following_id', new_column_name='following_id', nullable=False)
    op.create_primary_key('user_followers_pkey', 'user_followers', ['id'])
    
    # Models
    op.drop_constraint('models_pkey', 'models', type_='primary')
    op.drop_column('models', 'id')
    op.drop_column('models', 'creator_id')
    op.alter_column('models', 'uuid_id', new_column_name='id', nullable=False)
    op.alter_column('models', 'uuid_creator_id', new_column_name='creator_id', nullable=False)
    op.create_primary_key('models_pkey', 'models', ['id'])
    
    # Model likes
    op.drop_constraint('model_likes_pkey', 'model_likes', type_='primary')
    op.drop_column('model_likes', 'id')
    op.drop_column('model_likes', 'user_id')
    op.drop_column('model_likes', 'model_id')
    op.alter_column('model_likes', 'uuid_id', new_column_name='id', nullable=False)
    op.alter_column('model_likes', 'uuid_user_id', new_column_name='user_id', nullable=False)
    op.alter_column('model_likes', 'uuid_model_id', new_column_name='model_id', nullable=False)
    op.create_primary_key('model_likes_pkey', 'model_likes', ['id'])
    
    # Model comments
    op.drop_constraint('model_comments_pkey', 'model_comments', type_='primary')
    op.drop_column('model_comments', 'id')
    op.drop_column('model_comments', 'user_id')
    op.drop_column('model_comments', 'model_id')
    op.drop_column('model_comments', 'parent_id')
    op.alter_column('model_comments', 'uuid_id', new_column_name='id', nullable=False)
    op.alter_column('model_comments', 'uuid_user_id', new_column_name='user_id', nullable=False)
    op.alter_column('model_comments', 'uuid_model_id', new_column_name='model_id', nullable=False)
    op.alter_column('model_comments', 'uuid_parent_id', new_column_name='parent_id', nullable=True)
    op.create_primary_key('model_comments_pkey', 'model_comments', ['id'])
    
    # Step 4: Recreate foreign key constraints
    print("Creating new foreign key constraints...")
    
    op.create_foreign_key('user_profiles_user_id_fkey', 'user_profiles', 'users', ['user_id'], ['id'])
    op.create_foreign_key('payment_methods_user_id_fkey', 'payment_methods', 'users', ['user_id'], ['id'])
    op.create_foreign_key('user_followers_follower_id_fkey', 'user_followers', 'users', ['follower_id'], ['id'])
    op.create_foreign_key('user_followers_following_id_fkey', 'user_followers', 'users', ['following_id'], ['id'])
    op.create_foreign_key('models_creator_id_fkey', 'models', 'users', ['creator_id'], ['id'])
    op.create_foreign_key('model_likes_user_id_fkey', 'model_likes', 'users', ['user_id'], ['id'])
    op.create_foreign_key('model_likes_model_id_fkey', 'model_likes', 'models', ['model_id'], ['id'])
    op.create_foreign_key('model_comments_user_id_fkey', 'model_comments', 'users', ['user_id'], ['id'])
    op.create_foreign_key('model_comments_model_id_fkey', 'model_comments', 'models', ['model_id'], ['id'])
    op.create_foreign_key('model_comments_parent_id_fkey', 'model_comments', 'model_comments', ['parent_id'], ['id'])
    
    print("✅ Migration to UUID complete!")


def downgrade():
    """
    Downgrade is not supported for this migration.
    Converting UUIDs back to integers would lose data integrity.
    """
    raise NotImplementedError("Downgrade from UUID to integer is not supported")

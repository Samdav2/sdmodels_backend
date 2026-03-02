"""create bounty tables

Revision ID: 001_bounty_system
Revises: 
Create Date: 2024-02-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create bounties table
    op.create_table(
        'bounties',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('budget', sa.Float(), nullable=False),
        sa.Column('deadline', sa.Date(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('difficulty', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='open'),
        sa.Column('requirements', sa.JSON(), nullable=False),
        sa.Column('poster_id', sa.Integer(), nullable=False),
        sa.Column('claimed_by_id', sa.Integer(), nullable=True),
        sa.Column('claimed_at', sa.DateTime(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['poster_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['claimed_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("difficulty IN ('easy', 'medium', 'hard')", name='check_difficulty'),
        sa.CheckConstraint("status IN ('open', 'claimed', 'in_progress', 'submitted', 'completed', 'cancelled')", name='check_status')
    )
    op.create_index(op.f('ix_bounties_id'), 'bounties', ['id'], unique=False)
    op.create_index(op.f('ix_bounties_status'), 'bounties', ['status'], unique=False)
    op.create_index(op.f('ix_bounties_category'), 'bounties', ['category'], unique=False)
    op.create_index(op.f('ix_bounties_poster_id'), 'bounties', ['poster_id'], unique=False)
    op.create_index(op.f('ix_bounties_claimed_by_id'), 'bounties', ['claimed_by_id'], unique=False)

    # Create bounty_applications table
    op.create_table(
        'bounty_applications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bounty_id', sa.Integer(), nullable=False),
        sa.Column('applicant_id', sa.Integer(), nullable=False),
        sa.Column('proposal', sa.Text(), nullable=False),
        sa.Column('estimated_delivery', sa.Date(), nullable=False),
        sa.Column('portfolio_links', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['bounty_id'], ['bounties.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['applicant_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name='check_application_status'),
        sa.UniqueConstraint('bounty_id', 'applicant_id', name='uq_bounty_applicant')
    )
    op.create_index(op.f('ix_bounty_applications_id'), 'bounty_applications', ['id'], unique=False)
    op.create_index(op.f('ix_bounty_applications_bounty_id'), 'bounty_applications', ['bounty_id'], unique=False)
    op.create_index(op.f('ix_bounty_applications_applicant_id'), 'bounty_applications', ['applicant_id'], unique=False)

    # Create bounty_submissions table
    op.create_table(
        'bounty_submissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bounty_id', sa.Integer(), nullable=False),
        sa.Column('artist_id', sa.Integer(), nullable=False),
        sa.Column('model_url', sa.String(length=500), nullable=False),
        sa.Column('preview_images', sa.JSON(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['bounty_id'], ['bounties.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['artist_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected', 'revision_requested')", name='check_submission_status'),
        sa.UniqueConstraint('bounty_id', name='uq_bounty_submission')
    )
    op.create_index(op.f('ix_bounty_submissions_id'), 'bounty_submissions', ['id'], unique=False)
    op.create_index(op.f('ix_bounty_submissions_bounty_id'), 'bounty_submissions', ['bounty_id'], unique=True)

    # Create escrow_transactions table
    op.create_table(
        'escrow_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bounty_id', sa.Integer(), nullable=False),
        sa.Column('buyer_id', sa.Integer(), nullable=False),
        sa.Column('artist_id', sa.Integer(), nullable=True),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('platform_fee', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='held'),
        sa.Column('held_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('released_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['bounty_id'], ['bounties.id'], ),
        sa.ForeignKeyConstraint(['buyer_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['artist_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('held', 'released', 'refunded')", name='check_escrow_status')
    )
    op.create_index(op.f('ix_escrow_transactions_id'), 'escrow_transactions', ['id'], unique=False)
    op.create_index(op.f('ix_escrow_transactions_bounty_id'), 'escrow_transactions', ['bounty_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_escrow_transactions_bounty_id'), table_name='escrow_transactions')
    op.drop_index(op.f('ix_escrow_transactions_id'), table_name='escrow_transactions')
    op.drop_table('escrow_transactions')
    
    op.drop_index(op.f('ix_bounty_submissions_bounty_id'), table_name='bounty_submissions')
    op.drop_index(op.f('ix_bounty_submissions_id'), table_name='bounty_submissions')
    op.drop_table('bounty_submissions')
    
    op.drop_index(op.f('ix_bounty_applications_applicant_id'), table_name='bounty_applications')
    op.drop_index(op.f('ix_bounty_applications_bounty_id'), table_name='bounty_applications')
    op.drop_index(op.f('ix_bounty_applications_id'), table_name='bounty_applications')
    op.drop_table('bounty_applications')
    
    op.drop_index(op.f('ix_bounties_claimed_by_id'), table_name='bounties')
    op.drop_index(op.f('ix_bounties_poster_id'), table_name='bounties')
    op.drop_index(op.f('ix_bounties_category'), table_name='bounties')
    op.drop_index(op.f('ix_bounties_status'), table_name='bounties')
    op.drop_index(op.f('ix_bounties_id'), table_name='bounties')
    op.drop_table('bounties')

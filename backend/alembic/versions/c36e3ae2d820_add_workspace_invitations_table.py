"""add_workspace_invitations_table

Revision ID: c36e3ae2d820
Revises: 8de592097e5e
Create Date: 2026-01-26 15:21:35.962755

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'c36e3ae2d820'
down_revision = '8de592097e5e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create InvitationStatus enum if it doesn't exist (PostgreSQL requires explicit enum creation)
    # Use a DO block to check and create the enum atomically to avoid conflicts
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'invitationstatus') THEN
                CREATE TYPE invitationstatus AS ENUM ('PENDING', 'ACCEPTED', 'EXPIRED', 'CANCELLED');
            END IF;
        END $$;
    """)
    
    # Create workspace_invitations table
    invitation_status_enum = postgresql.ENUM('PENDING', 'ACCEPTED', 'EXPIRED', 'CANCELLED', name='invitationstatus', create_type=False)
    
    op.create_table('workspace_invitations',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('workspace_id', sa.UUID(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('role', postgresql.ENUM('OWNER', 'ADMIN', 'EDITOR', 'VIEWER', name='workspacerole', create_type=False), nullable=False),
    sa.Column('invitation_token', sa.String(length=255), nullable=False),
    sa.Column('invited_by', sa.UUID(), nullable=False),
    sa.Column('status', invitation_status_enum, nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes (removed duplicates)
    op.create_index('idx_workspace_invitations_workspace_id', 'workspace_invitations', ['workspace_id'], unique=False)
    op.create_index('idx_workspace_invitations_email', 'workspace_invitations', ['email'], unique=False)
    op.create_index('idx_workspace_invitations_status', 'workspace_invitations', ['status'], unique=False)
    op.create_index('idx_workspace_invitations_token', 'workspace_invitations', ['invitation_token'], unique=True)
    op.create_index('idx_workspace_invitations_expires_at', 'workspace_invitations', ['expires_at'], unique=False)
    op.create_index('idx_workspace_invitations_invited_by', 'workspace_invitations', ['invited_by'], unique=False)
    
    # Create partial unique constraint: only one pending invitation per workspace/email
    # Using raw SQL since Alembic doesn't support partial unique constraints directly
    op.execute("""
        CREATE UNIQUE INDEX idx_workspace_invitations_unique_pending 
        ON workspace_invitations (workspace_id, email) 
        WHERE status = 'PENDING'
    """)
    # ### end Alembic commands ###


def downgrade() -> None:
    # Drop partial unique constraint
    op.execute("DROP INDEX IF EXISTS idx_workspace_invitations_unique_pending")
    
    # Drop indexes
    op.drop_index('idx_workspace_invitations_invited_by', table_name='workspace_invitations')
    op.drop_index('idx_workspace_invitations_expires_at', table_name='workspace_invitations')
    op.drop_index('idx_workspace_invitations_token', table_name='workspace_invitations')
    op.drop_index('idx_workspace_invitations_status', table_name='workspace_invitations')
    op.drop_index('idx_workspace_invitations_email', table_name='workspace_invitations')
    op.drop_index('idx_workspace_invitations_workspace_id', table_name='workspace_invitations')
    
    # Drop table
    op.drop_table('workspace_invitations')
    
    # Drop enum (only if no other tables use it)
    # Note: We don't drop the enum here as it might be used elsewhere
    # op.execute("DROP TYPE IF EXISTS invitationstatus")

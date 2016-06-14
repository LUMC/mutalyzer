"""Index on Reference.accession and Reference.version

Revision ID: 4b7c33f3c85d
Revises: 0d9a434c70b1
Create Date: 2016-06-13 15:47:42.915567

"""

from __future__ import unicode_literals

# revision identifiers, used by Alembic.
revision = '4b7c33f3c85d'
down_revision = u'0d9a434c70b1'

from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql


def upgrade():
    # Populate `version` using the values in `accession`.
    connection = op.get_bind()

    # Inline table definition we can use in this migration.
    references = sql.table(
        'references',
        sql.column('id', sa.Integer()),
        sql.column('accession', sa.String(20)),
        sql.column('version', sa.Integer()))

    # Get all rows.
    result = connection.execute(
        references.select().with_only_columns([
            references.c.id,
            references.c.accession,
            references.c.version
        ]))

    # Generate parameter values for the UPDATE query below.
    def update_params(r):
        try:
            version = int(r.accession.split('.', 1)[1])
        except (IndexError, ValueError):
            version = None
        return {'r_id': r.id, 'r_version': version}

    # Process a few rows at a time, since they will be read in memory.
    while True:
        chunk = result.fetchmany(1000)
        if not chunk:
            break

        # Populate `version` based on existing `accession` values.
        statement = references.update().where(
            references.c.id == sql.bindparam('r_id')
        ).values({'version': sql.bindparam('r_version')})

        # Execute UPDATE query for fetched rows.
        connection.execute(statement, [update_params(r) for r in chunk])

    # Create a new combined index on `accession` and `version`.
    op.create_index('reference_accession_version', 'references', ['accession', 'version'], unique=True)

    # Drop the old index.
    op.drop_index('ix_references_accession', table_name='references')


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_index('ix_references_accession', 'references', ['accession'], unique=True)
    op.drop_index('reference_accession_version', table_name='references')
    ### end Alembic commands ###

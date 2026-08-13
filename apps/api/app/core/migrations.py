import os
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.migration import MigrationContext
from sqlalchemy.engine import Connection

def check_migration_status(connection: Connection) -> dict:
    """
    Checks whether the database schema is up-to-date with Alembic migrations.
    Returns a dictionary with current_revision, head_revision, and is_up_to_date.
    """
    api_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ini_path = os.path.join(api_dir, "alembic.ini")
    
    alembic_cfg = Config(ini_path)
    alembic_cfg.set_main_option("script_location", os.path.join(api_dir, "alembic"))
    
    script = ScriptDirectory.from_config(alembic_cfg)
    head_revision = script.get_current_head()

    context = MigrationContext.configure(connection)
    current_revision = context.get_current_revision()

    return {
        "current_revision": current_revision,
        "head_revision": head_revision,
        "is_up_to_date": (current_revision == head_revision) and (current_revision is not None)
    }

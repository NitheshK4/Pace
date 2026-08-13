import os
import tempfile
import pytest
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, inspect
from app.core.migrations import check_migration_status

def test_fresh_database_alembic_migration():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        sync_url = f"sqlite:///{db_path}"
        
        api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ini_path = os.path.join(api_dir, "alembic.ini")
        
        alembic_cfg = Config(ini_path)
        alembic_cfg.set_main_option("script_location", os.path.join(api_dir, "alembic"))
        alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
        
        # Run alembic upgrade head on fresh database
        command.upgrade(alembic_cfg, "head")
        
        # Verify tables created via migration
        engine = create_engine(sync_url)
        with engine.connect() as conn:
            status = check_migration_status(conn)
            assert status["is_up_to_date"] is True
            assert status["current_revision"] is not None
            assert status["current_revision"] == status["head_revision"]
            
            inspector = inspect(conn)
            tables = inspector.get_table_names()
            assert "users" in tables
            assert "projects" in tables
            assert "usage_events" in tables
            assert "pricing_rates" in tables
            assert "alembic_version" in tables
        engine.dispose()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

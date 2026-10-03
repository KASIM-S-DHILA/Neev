from alembic import context
from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL
from studylens_service.schema import metadata

config = context.config
engine = create_engine(URL.create("sqlite", database=str(config.attributes["database_path"])))

@event.listens_for(engine, "connect")
def pragmas(connection, _record):
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=5000")
    connection.execute("PRAGMA journal_mode=WAL")

try:
    with engine.connect() as connection:
        # Serialize startup migrations and make SQLite DDL rollback on failure.
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        context.configure(connection=connection, target_metadata=metadata, render_as_batch=True, transactional_ddl=True)
        with context.begin_transaction():
            context.run_migrations()
        connection.commit()
finally:
    engine.dispose()

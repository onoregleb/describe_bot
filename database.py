from sqlalchemy import create_engine, Column, BigInteger, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import os

# Define a default SQLite database URL if DATABASE_URL is not set
from config import DATABASE_URL

# Create SQLAlchemy engine with a fallback to SQLite
db_url = DATABASE_URL if DATABASE_URL else "sqlite:///./bot_database.db"
engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define models
class UrlChat(Base):
    __tablename__ = "url_chat"
    
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    dialog_id = Column(BigInteger, index=True, nullable=False)
    website = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Define unique constraint
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )

# Create tables
def create_tables():
    Base.metadata.create_all(bind=engine)

# Get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 
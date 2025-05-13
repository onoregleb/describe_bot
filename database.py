from sqlalchemy import create_engine, Column, BigInteger, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

from config import DATABASE_URL

db_url = DATABASE_URL if DATABASE_URL else "sqlite:///./bot_database.db"
engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ConferenceBot(Base):
    __tablename__ = "conference_bot"

    # Use user_id as the primary key since it's already the PK in the database
    user_id = Column(String(255), primary_key=True, nullable=False)
    user_name = Column(String(255), nullable=False, default="Не указано")
    sphere = Column(String(255), nullable=False, default="Не указано")
    user_position = Column(String(255), nullable=False, default="Не указано")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    site_url = Column(String(255), default="Не указано")
    title = Column(Text, default="Не указано")
    cleaned_content = Column(Text)

def create_tables():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
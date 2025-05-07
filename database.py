from sqlalchemy import create_engine, Column, BigInteger, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

from config import DATABASE_URL

db_url = DATABASE_URL if DATABASE_URL else "sqlite:///./bot_database.db"
engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UrlChat(Base):
    __tablename__ = "url_chat"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    dialog_id = Column(BigInteger, index=True, nullable=False)
    website = Column(String, nullable=False)
    cleaned_content = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        {'sqlite_autoincrement': True},
    )

def create_tables():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
"""
Database models — SQLAlchemy + SQLite
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime, timezone
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/infinity.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    nome = Column(String, default="DJ Jose Silva")
    role = Column(String, default="user")  # user | admin
    deepseek_key = Column(String, default="")
    login_count = Column(Integer, default=0)
    last_login = Column(DateTime, nullable=True)
    system_message = Column(String, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)


class Production(Base):
    __tablename__ = "productions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    nome = Column(String, default="Sem titulo")
    conceito = Column(Text, default="")
    estilo = Column(String, default="")
    bpm = Column(Integer, default=120)
    key = Column(String, default="Cm")
    lyrics = Column(Text, default="")
    suno_package = Column(Text, default="")
    abc = Column(Text, default="")
    critic = Column(String, default="")
    negative = Column(Text, default="")
    agent_outputs = Column(JSON, default={})
    metadata_json = Column(JSON, default={})
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Certificate(Base):
    __tablename__ = "certificates"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    production_id = Column(Integer, nullable=False)
    track_id = Column(String, unique=True, index=True)
    hash_sha256 = Column(String)
    titulo = Column(String)
    file_path = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class APIKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    service = Column(String)  # deepseek, spotify, youtube
    key_encrypted = Column(Text)
    is_active = Column(Boolean, default=True)
    last_validated = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

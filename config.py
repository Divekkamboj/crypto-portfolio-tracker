from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Ab hum SQLite use karenge jo Render par bina kisi error ke chalega
DATABASE_URL = "sqlite:///./crypto_portfolio.db"

# SQLite ke liye 'check_same_thread': False zaroori hai
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Database session dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

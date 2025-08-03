from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,declarative_base,Session

engine = create_engine("postgresql://postgres:1234@localhost/proySuper",echo=False)
Base = declarative_base()
SessionLocal = sessionmaker(autocommit = False, bind = engine)
session = SessionLocal()

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
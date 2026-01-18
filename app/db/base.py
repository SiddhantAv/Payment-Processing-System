"""
Database base configuration.
Defines the SQLAlchemy declarative base for all models.
"""
from sqlalchemy.ext.declarative import declarative_base

# Create declarative base for all models
Base = declarative_base()

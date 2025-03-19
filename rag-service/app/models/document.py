from sqlalchemy import Column, Integer, String, JSON, Text
from sqlalchemy.sql.sqltypes import DateTime
from sqlalchemy.sql import func
from app.database import Base

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(String, unique=True, index=True)  
    title = Column(String, index=True)
    content = Column(Text)  
    doc_metadata = Column(JSON) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) 
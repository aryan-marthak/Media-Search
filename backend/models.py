from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    images = relationship("Image", back_populates="owner", cascade="all, delete-orphan")
    shares_given = relationship("Share", foreign_keys="Share.owner_id", back_populates="owner")
    shares_received = relationship("Share", foreign_keys="Share.shared_with_id", back_populates="shared_with")


class Image(Base):
    __tablename__ = "images"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    thumbnail_path = Column(String(512), nullable=True)
    file_size = Column(String(20), nullable=True)
    mime_type = Column(String(50), nullable=True)
    width = Column(String(10), nullable=True)
    height = Column(String(10), nullable=True)
    
    # Processing status
    processing_status = Column(String(20), default="pending")  # pending, processing, completed, failed
    processing_error = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    owner = relationship("User", back_populates="images")
    shares = relationship("Share", back_populates="image", cascade="all, delete-orphan")


class SharePermission(enum.Enum):
    VIEW = "view"
    DOWNLOAD = "download"


class Share(Base):
    __tablename__ = "shares"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    image_id = Column(UUID(as_uuid=True), ForeignKey("images.id"), nullable=False, index=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    shared_with_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    permission = Column(SQLEnum(SharePermission), default=SharePermission.VIEW)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    image = relationship("Image", back_populates="shares")
    owner = relationship("User", foreign_keys=[owner_id], back_populates="shares_given")
    shared_with = relationship("User", foreign_keys=[shared_with_id], back_populates="shares_received")


class FaceCluster(Base):
    __tablename__ = "face_clusters"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=True)  # User-assigned name
    representative_face_path = Column(String(512), nullable=True)  # Thumbnail of the face
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Face(Base):
    __tablename__ = "faces"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    image_id = Column(UUID(as_uuid=True), ForeignKey("images.id"), nullable=False, index=True)
    cluster_id = Column(UUID(as_uuid=True), ForeignKey("face_clusters.id"), nullable=True, index=True)
    face_path = Column(String(512), nullable=True)  # Cropped face image
    bbox_x = Column(String(10), nullable=True)
    bbox_y = Column(String(10), nullable=True)
    bbox_width = Column(String(10), nullable=True)
    bbox_height = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

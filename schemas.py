"""
Database Schemas for the Cabaret Theater website

Each Pydantic model represents a collection in MongoDB. The collection name is the lowercase of the class name.
"""
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime

# Core domain schemas

class Event(BaseModel):
    title: str = Field(..., description="Event title")
    description: str = Field(..., description="Short description of the show")
    genre: str = Field(..., description="e.g., Kabarett, Impro, Workshop")
    date: datetime = Field(..., description="Start datetime of the event")
    duration_minutes: int = Field(..., ge=10, le=300, description="Duration in minutes")
    price_eur: float = Field(..., ge=0, description="Ticket price in EUR")
    seats_total: int = Field(..., ge=1, description="Total number of seats")
    seats_available: int = Field(..., ge=0, description="Remaining seats available")
    image_url: Optional[str] = Field(None, description="Poster or thumbnail image URL")

class Reservation(BaseModel):
    event_id: str = Field(..., description="ID of the reserved event")
    name: str = Field(..., description="Full name of the guest")
    email: EmailStr = Field(..., description="Email of the guest")
    tickets: int = Field(..., ge=1, le=10, description="Number of tickets to reserve")
    note: Optional[str] = Field(None, description="Optional note or seating preference")

class Ownerprofile(BaseModel):
    name: str = Field(..., description="Owner name")
    role: str = Field(..., description="Role at the theater")
    bio: str = Field(..., description="Short artistic biography")
    image_url: Optional[str] = Field(None, description="Portrait image URL")
    instagram: Optional[str] = Field(None)
    website: Optional[str] = Field(None)

class Theater(BaseModel):
    name: str = Field(...)
    tagline: str = Field(...)
    story: str = Field(..., description="History / story of the theater")
    address: str = Field(...)
    phone: str = Field(...)
    email: EmailStr = Field(...)
    opening_hours: Optional[str] = None
    transport_howto: Optional[str] = None

class Contactmessage(BaseModel):
    name: str = Field(...)
    email: EmailStr = Field(...)
    subject: str = Field(...)
    message: str = Field(..., min_length=5)

class Video(BaseModel):
    month_key: str = Field(..., description="Format YYYY-MM identifying the month")
    video_url: str = Field(..., description="Public video URL to show in background")
    caption: Optional[str] = None

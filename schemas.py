"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

# MMA Math Schemas

class Fighter(BaseModel):
    """
    Fighters collection schema
    Collection name: "fighter"
    """
    name: str = Field(..., description="Fighter display name")
    slug: str = Field(..., description="Lowercase unique slug for the fighter")

class Fight(BaseModel):
    """
    Fights collection schema
    Collection name: "fight"
    Direction: winner -> loser (edge from winner to loser)
    """
    winner: str = Field(..., description="Winner fighter slug")
    loser: str = Field(..., description="Loser fighter slug")
    event: Optional[str] = Field(None, description="Event name")
    method: Optional[str] = Field(None, description="Finish method or decision")
    round: Optional[int] = Field(None, ge=1, le=10, description="Round number")
    fight_date: Optional[date] = Field(None, description="Date of the fight")

# Example schemas (kept for reference, not used by app)
class User(BaseModel):
    name: str
    email: str
    address: str
    age: Optional[int] = None
    is_active: bool = True

class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True

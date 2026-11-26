"""Pydantic schemas for customers."""
from datetime import time

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CustomerCreate(BaseModel):
    """Used for both creating and updating (PUT replaces all fields)."""
    customer_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=20)
    town: str = Field(min_length=1, max_length=50)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    open_time: int
    close_time: int

    @model_validator(mode="after")
    def check_time_window(self):
        """The shop must close after it opens."""
        if self.close_time <= self.open_time:
            raise ValueError("close_time must be later than open_time")
        return self


class CustomerOut(CustomerCreate):
    model_config = ConfigDict(from_attributes=True)

    customer_id: int

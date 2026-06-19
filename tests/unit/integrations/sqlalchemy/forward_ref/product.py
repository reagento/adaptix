from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .tag import Tag


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]

    tags: Mapped[list[Tag]] = relationship(back_populates="product")

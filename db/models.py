
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import  Integer, String, ForeignKey, Double, BigInteger
from sqlalchemy import create_engine
from typing import List, Optional



class Base(DeclarativeBase):
    pass



class BearingData(Base):
    __tablename__ = "bearingdata"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    ueberstand: Mapped[float] = mapped_column(Double, nullable=True)
    breite: Mapped[float] = mapped_column(Double, nullable=True)
    aussenR: Mapped[int] = mapped_column(Integer, nullable=True)
    innenR: Mapped[int] = mapped_column(Integer, nullable=True)
    rueckmeldenummer: Mapped[int] = mapped_column(Integer, nullable=True)



    def __repr__(self) -> str:
        return f"Lager(id={self.id!r}, ueberstand={self.ueberstand!r}, breite={self.breite!r}, aussenR={self.aussenR!r}, innenR_={self.innenR!r}, rueckmeldenummer={self.rueckmeldenummer!r})"
    

if __name__ == "__main__":
    from sqlalchemy import create_engine
    #engine = create_engine("postgresql+psycopg2://admin:%HUJD290@10.0.0.70/dev", echo=True)
    #engine = create_engine("postgresql+psycopg2://postgres:s5hs4L%HA3_Ma@localhost/slf", echo=True)
    engine = create_engine(f"postgresql+psycopg2://postgres:%HUJD290@localhost/postgres", echo=False)
    Base.metadata.create_all(engine)

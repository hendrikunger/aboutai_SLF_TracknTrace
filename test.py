#%%
from sqlalchemy import create_engine, select
from sqlalchemy import text, MetaData, Table, Column, Integer, String, ForeignKey
from sqlalchemy.orm import Session, DeclarativeBase, Mapped, mapped_column, relationship
from typing import List, Optional


#%%
#engine = create_engine("sqlite+pysqlite:///:memory:", echo=True)

engine = create_engine("postgresql+psycopg2://admin:%HUJD290@10.0.0.70/dev", echo=True)
# %%

with engine.begin() as conn:
    conn.execute(text("Create Table some_table (x int, y int)"))
    conn.execute(text("Insert Into some_table (x, y) Values (:x, :y)"),
                      [{"x": 1, "y": 1}, {"x": 2, "y": 4}]
                )

# %%
b=2
with Session(engine) as session:
    result = session.execute(text("SELECT x, y FROM some_table WHERE y > :z"), {"z": b})
    for row in result:
        print(f"x: {row.x}  y: {row.y}")
# %%
metadata_obj = MetaData()

user_table = Table(
    "user_account",
    metadata_obj,
    Column("id", Integer, primary_key=True),
    Column("name", String(30)),
    Column("fullname", String),
)
# %%
address_table = Table(
    "address",
    metadata_obj,
    Column("id", Integer, primary_key=True),
    Column("user_id", ForeignKey("user_account.id"), nullable=False),
    Column("email_address", String, nullable=False),
)
# %%
metadata_obj.create_all(engine)
# %%
metadata_obj.drop_all(engine)
# %%

class Base(DeclarativeBase):
    pass



class User(Base):
    __tablename__ = "user_account"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    fullname: Mapped[Optional[str]]
    addresses: Mapped[List["Address"]] = relationship(back_populates="user")
    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, fullname={self.fullname!r})"

class Address(Base):
    __tablename__ = "address"
    id: Mapped[int] = mapped_column(primary_key=True)
    email_address: Mapped[str]
    user_id = mapped_column(ForeignKey("user_account.id"))
    user: Mapped[User] = relationship(back_populates="addresses")
    def __repr__(self) -> str:
        return f"Address(id={self.id!r}, email_address={self.email_address!r})"
    
# %%
Base.metadata.create_all(engine)
# %%
session = Session(engine)
# %%
squidward = User(name="Suidward", fullname="Squidward Tentacles")
krabs = User(name="Krabs", fullname="Eugene Krabs")
squidward
# %%
session.add(squidward)
session.add(krabs)


# %%
session.commit()
# %%
krabs2 = session.execute(select(User).where(User.name == "Krabs")).scalar_one()
# %%
session.delete(krabs2)
session.flush()
#%%
krabs2 in session

#%%
session.execute(select(User).where(User.name == "Suidward")).first()


# %%
session.close()

#%%
squidward.name = "Klaus2"
# %%
squidward
# %%


# %%
squidward.addresses.extend(
    [
        Address(email_address="jkkBNJ"),
        Address(email_address="jkkBNJ2"),
    ])

# %%
squidward.addresses

# %%
squidward.addresses

# %%
with Session(engine) as session:
    squidward = session.execute(select(User).where(User.name == "Klaus2")).scalar_one()
    print(squidward.addresses)
 
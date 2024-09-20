from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models import BearingData


engine = create_engine(f"postgresql+psycopg2://slf_trace:slf_trace@192.168.133.249/slf", echo=False)

session = Session(engine)
try:
    for i in range(240000100, 240010000):
        newEntry = BearingData(id=i)
        session.add(newEntry)
    session.flush()
except IntegrityError:
    session.rollback()
    pn.state.notifications.error(f'DMC schon in der Datenbank:', duration=0)
else:
    session.commit()
session.close()
import json
import os
import sys
import panel as pn
import random
import asyncio
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound, DataError
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from threading import Thread, Event

main_project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if main_project_dir not in sys.path:
    sys.path.append(main_project_dir)

from components import FocusedInput
from db.models import BearingData

class FileWatcher:
    def __init__(self, filename, directory="."):
        self.filename = filename
        self.directory = directory
        self.observer = None
        self.thread = None
        self.file_created_event = Event()
        self.event_handler = FileCreatedHandler(self.filename, self.file_created)

    def start_watching(self):
        if not self.observer:
            self.observer = Observer()
            self.observer.schedule(self.event_handler, path=self.directory, recursive=False)
            self.thread = Thread(target=self._run_observer)
            self.thread.start()
            print(f"Started watching for {self.filename} in {self.directory}", flush=True)

    def stop_watching(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            self.thread = None
            print(f"Stopped watching for {self.filename}", flush=True)

    def _run_observer(self):
        self.observer.start()
        self.file_created_event.wait()
        self.observer.stop()
        self.observer.join()

    def file_created(self, path):
        print(f"File {path} has been created!", flush=True)
        self.file_created_event.set()  # Signal that the file has been created

class FileCreatedHandler(FileSystemEventHandler):
    def __init__(self, filename, callback):
        self.filename = filename
        self.callback = callback

    def on_created(self, event):
        if event.src_path.endswith(self.filename):
            self.callback(event.src_path)

watcher = FileWatcher("test.csv", directory=".")  




TITLE = "Fertig messen"

with open("config.json", "r") as f:
    config = json.load(f)


pn.extension(notifications=True)
pn.state.notifications.position = 'top-right'
engine = create_engine(f"postgresql+psycopg2://{config["DATABASE"]}", echo=False)

currentMeasurement = pn.rx("")


#read links from json file
with open("links.json", "r") as f:
    links = json.load(f)
    text="\n".join([f"- [{key}]({value})" for key,value in links.items()])

linklist = pn.pane.Markdown(
    "\n".join([f"## [{key}]({value})" for key,value in links.items()]),
    sizing_mode="stretch_width",
)


def write_to_DB(bearing_id, measurement):
    session = Session(engine)
    try:
        EntrytoUpdate = session.get_one(BearingData, bearing_id)
        print(F"Updating: {EntrytoUpdate}", flush=True)
        EntrytoUpdate.ueberstand = measurement
        session.flush()
    except NoResultFound:
        session.rollback()
        pn.state.notifications.error(f'DMC nicht in der Datenbank {bearing_id}', duration=2000)
    except DataError:
        session.rollback()
        pn.state.notifications.error(f'Messwert ist keine Zahl', duration=2000)
    else:
        session.commit()
    session.close()



async def getMeasurement(event):
    #watch for test.csv file and read the first line after it is created
    if not os.path.exists("test.csv"):
        watcher.start_watching()
        watcher.file_created_event.wait()
        watcher.stop_watching()
        
    with open("test.csv", "r") as f:
        f.readline()
        line = f.readline()
        currentMeasurement.rx.value = line.split(";")[1]
    os.remove("test.csv")

async def createTestData(event):
    #write csv test file with one line of fake data
    with open("test.csv", "w") as f:
        f.write("DMC;Messwert\n")
        f.write("123456;"+str(random.randint(0, 100))+"\n")



async def process(event):
    if event.new == "": return
    if not event.new.isdigit():
        pn.state.notifications.error('DMC ist keine Zahl', duration=2000)
        ti_Barcode.value = ""
        return   
    running_indicator.value = running_indicator.visible = True
    running_indicator.name = "Warte auf Messwert csv Datei"
    await getMeasurement(None)
    running_indicator.value = running_indicator.visible = False
    running_indicator.name = ""
    ti_Barcode.focus = False
    b_Reload.disabled = False
    b_Save.disabled = False

def button_save_function(event):
    running_indicator.value = running_indicator.visible = True
    write_to_DB(ti_Barcode.value, currentMeasurement.rx.value)
    running_indicator.value = running_indicator.visible = False
    b_Save.disabled = True
    b_Reload.disabled = True
    ti_Barcode.focus = True
    currentMeasurement.rx.value = ""


b_test = pn.widgets.Button(name='Test', button_type='primary', height=80, sizing_mode="stretch_width")
b_test.on_click(lambda event: asyncio.create_task(createTestData()))


b_Save = pn.widgets.Button(name='Messung speichern',
                           button_type='primary',
                           height=80,
                           sizing_mode="stretch_width",
                           disabled=True,)
b_Save.rx.watch(button_save_function)


b_Reload = pn.widgets.ButtonIcon(icon="refresh", 
                                 active_icon="refresh-dot",
                                 toggle_duration=1000,
                                 disabled=True,
                                 height=80,
                                 )
b_Reload.on_click(getMeasurement)


ti_Barcode = FocusedInput(name="Barcode", value="",)
ti_Barcode.param.watch(process, "value")

text_currentSerialID = pn.rx("{currentSerialID}").format(currentSerialID=ti_Barcode.param.value)
md_currentSerialID = pn.pane.Markdown(text_currentSerialID,
                                      width=250,
                                      styles={'text-align': 'center',
                                      'font-size': '24px'})
serialCardID = pn.Card(pn.Row(pn.Spacer(sizing_mode="stretch_width"),
                                        md_currentSerialID,
                                        pn.Spacer(sizing_mode="stretch_width")),
                                        width=250,
                                        height=80,
                                        hide_header=True)

text_currentMeasurement = pn.rx("{currentMeasurement}").format(currentMeasurement=currentMeasurement)
md_currentMeasurement = pn.pane.Markdown(text_currentMeasurement,
                                         width=250,
                                         styles={'text-align': 'center',
                                         'font-size': '24px'})
serialCardMeasurement = pn.Card(pn.Row(pn.Spacer(sizing_mode="stretch_width"), md_currentMeasurement, pn.Spacer(sizing_mode="stretch_width")),
                                       width=250,
                                       height=80,
                                       hide_header=True)
   

running_indicator = pn.indicators.LoadingSpinner(value=False,
                                                 height=100,
                                                 width=100,
                                                 color="secondary",
                                                 visible=False,
                                                 margin=50)


column = pn.Column(pn.Row(pn.Spacer(sizing_mode="stretch_width"),pn.pane.Markdown("# Aktuelle Seriennummer:"), pn.Spacer(sizing_mode="stretch_width")),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"), serialCardID, pn.Spacer(sizing_mode="stretch_width")),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"),pn.pane.Markdown("# Aktueller Messwert:"), pn.Spacer(sizing_mode="stretch_width")),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"), serialCardMeasurement, pn.Row(b_Reload, pn.Spacer(sizing_mode="stretch_width"))),
                   pn.Spacer(sizing_mode="stretch_width", height=100),
                   b_Save,
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"), running_indicator, pn.Spacer(sizing_mode="stretch_width")),
                   pn.Spacer(sizing_mode="stretch_width", height=100),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"), ti_Barcode, pn.Spacer(sizing_mode="stretch_width")),
                   )

pn.template.BootstrapTemplate(
    title=TITLE,
    sidebar=[linklist,b_test],
    main=column,
    header_background=config["ACCENT"],
    theme=config["THEME"],
    logo=config["LOGO"],
    collapsed_sidebar=config["SIDEBAR_OFF"],
    sidebar_width = 200,
).servable()
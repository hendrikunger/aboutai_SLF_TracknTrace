import json
import os
import sys
import panel as pn
from os.path import isfile
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound
import serial_asyncio
import serial

main_project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if main_project_dir not in sys.path:
    sys.path.append(main_project_dir)

from components import FocusedInput
from db.models import BearingData

TITLE = "Breite messen"

# Load config file
configPath = "config.json"
if not isfile(configPath):
    configPath = "default_config.json"
    
with open(configPath, "r") as f:
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
        EntrytoUpdate.breite = measurement
        session.flush()
    except NoResultFound:
        session.rollback()
        pn.state.notifications.error(f'DMC nicht in der Datenbank {bearing_id}', duration=0)
    else:
        session.commit()
    session.close()
    return

async def getMeasurement(event):
    reader, writer = await serial_asyncio.open_serial_connection(url="Com5", 
                                                                baudrate=4800,
                                                                bytesize=serial.SEVENBITS,
                                                                parity=serial.PARITY_EVEN,
                                                                stopbits=serial.STOPBITS_TWO,
                                                                )
    print(f"Waiting for measurement", flush=True)
    message = f'?\r'
    print(f'Sending:\n{message}', flush=True)
    writer.write(message.encode())
    await writer.drain()
    line = await reader.readline()
    data = line.decode('utf8').rstrip()
    print(f'Received: {data}', flush=True)
    try:
        data = float(data)
    except ValueError:
        pn.state.notifications.error(f'Messwert {data} ist keine Gleitkommazahl', duration=2000)
        return
    writer.close()
    await writer.wait_closed()
    currentMeasurement.rx.value =  data
    return


async def process(event):
    if event.new == "": return
    if not event.new.isdigit():
        pn.state.notifications.error('DMC ist keine Zahl', duration=2000)
        ti_Barcode.value = ""
        return   
    running_indicator.value = running_indicator.visible = True
    running_indicator.name = "Warte auf Messgerät"
    
    running_indicator.value = running_indicator.visible = False
    running_indicator.name = ""
    ti_Barcode.focus = False
    b_Save.disabled = False

async def button_save_function(event):
    running_indicator.value = running_indicator.visible = True
    write_to_DB(ti_Barcode.value, currentMeasurement.rx.value)
    b_Save.disabled = True
    ti_Barcode.focus = True
    running_indicator.value = running_indicator.visible = False
    currentMeasurement.rx.value = ""



b_Save = pn.widgets.Button(name='Messung speichern',
                           button_type='primary',
                           height=80,
                           sizing_mode="stretch_width",
                           disabled=True,)
b_Save.rx.watch(button_save_function)

b_Measure = pn.widgets.Button(   name="Laden",
                                 button_type='primary',
                                 disabled=False,
                                 height=80,
                                 )
b_Measure.rx.watch(getMeasurement)


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
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"), serialCardMeasurement, pn.Row(b_Measure, pn.Spacer(sizing_mode="stretch_width"))),
                   pn.Spacer(sizing_mode="stretch_width", height=100),
                   b_Save,
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"), running_indicator, pn.Spacer(sizing_mode="stretch_width")),
                   pn.Spacer(sizing_mode="stretch_width", height=100),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"), ti_Barcode, pn.Spacer(sizing_mode="stretch_width")),
                   )

pn.template.BootstrapTemplate(
    title=TITLE,
    sidebar=[linklist],
    main=column,
    header_background=config["ACCENT"],
    theme=config["THEME"],
    logo=config["LOGO"],
    collapsed_sidebar=config["SIDEBAR_OFF"],
    sidebar_width = 200,
).servable()
import json
import os
import sys
import asyncio
import panel as pn
from os.path import isfile
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound

main_project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if main_project_dir not in sys.path:
    sys.path.append(main_project_dir)

from components import FocusedInput
from db.models import BearingData

TITLE = "Endmarkieren"

# Load config file
configPath = "config.json"
if not isfile(configPath):
    configPath = "default_config.json"
    
with open(configPath, "r") as f:
    config = json.load(f)


pn.extension(notifications=True)
pn.state.notifications.position = 'top-right'
engine = create_engine(f"postgresql+psycopg2://{config["DATABASE"]}", echo=False)

ueberstand = pn.rx("")
breite = pn.rx("")
aussenR = pn.rx("")
innenR = pn.rx("")


#read links from json file
with open("links.json", "r") as f:
    links = json.load(f)
    text="\n".join([f"- [{key}]({value})" for key,value in links.items()])

linklist = pn.pane.Markdown(
    "\n".join([f"## [{key}]({value})" for key,value in links.items()]),
    sizing_mode="stretch_width",
)




def read_DB(bearing_id):
    session = Session(engine)
    try:
        EntrytoReturn = session.get_one(BearingData, bearing_id)
    except NoResultFound:
        session.rollback()
        pn.state.notifications.error(f'DMC nicht in der Datenbank {bearing_id}', duration=0)

    ueberstand.rx.value = EntrytoReturn.ueberstand
    breite.rx.value = EntrytoReturn.breite
    aussenR.rx.value = EntrytoReturn.aussenR
    innenR.rx.value = EntrytoReturn.innenR
    
    session.close()
    return



def process(event):
    if event.new == "": return
    if not event.new.isdigit():
        pn.state.notifications.error('DMC ist keine Zahl', duration=2000)
        ti_Barcode.value = ""
        return   
    running_indicator.value = running_indicator.visible = True
    read_DB(ti_Barcode.value)
    running_indicator.value = running_indicator.visible = False
    ti_Barcode.focus = False
    b_Save.disabled = False


async def doTCP_Transaction(reader, writer, message):
    print(f'Sending:\n{message}', flush=True)
    writer.write(message.encode())
    await writer.drain()
    line = await reader.readline()
    data = line.decode('utf8').rstrip()
    returncode = data.split(":")[1]
    print(f'Received: {data}', flush=True)
    print(f'Returncode: {returncode}', flush=True)
    if returncode != "1":
        pn.state.notifications.error(f'TCP IP Laser Fehler mit Fehlercode {returncode}', duration=5000)
        ti_Barcode.value = ""
        return


async def laser_tcp_ip_communication():
    reader, writer = await asyncio.open_connection('192.168.255.7', 3000)
    print(f"send to Laser: {ti_Barcode.value}, {ueberstand.rx.value}, {breite.rx.value}, {aussenR.rx.value}, {innenR.rx.value}", flush=True)
    
    ##TODO prüfen 0b Job schon geladen ist, der Laser will nicht, dass der Job ständig nachgeladen wird (GetJobName)

    #Load Job Variables
    message = f'LOADJOB:TEST FOBA\r\n'
    await doTCP_Transaction(reader,writer, message)


    #Set Variables
    #message = f'SETVARS:DMC;{ti_Barcode.value};ueberstand;{ueberstand.rx.value};breite;{breite.rx.value};ARUR;{aussenR.rx.value}/{innenR.rx.value}\r\n'
    message = f'SETVARS:TEST FOBA;{ti_Barcode.value}\r\n'
    await doTCP_Transaction(reader,writer, message)

    #Start Job
    #message = f'STARTJOB\r\n'
    #await doTCP_Transaction(reader,writer, message)

    writer.close()
    await writer.wait_closed()


async def button_save_function(event):
    running_indicator.value = running_indicator.visible = True
    await laser_tcp_ip_communication()
    running_indicator.value = running_indicator.visible = False
    b_Save.disabled = True
    ti_Barcode.focus = True
    ueberstand.rx.value = ""
    breite.rx.value = ""
    aussenR.rx.value = ""
    innenR.rx.value = ""



b_Save = pn.widgets.Button(name='An Laser senden',
                           button_type='primary',
                           height=80,
                           sizing_mode="stretch_width",
                           disabled=True,)
b_Save.rx.watch(button_save_function)





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
                                        height=60,
                                        hide_header=True)

md_AR_IR_Paarung = pn.pane.Markdown(pn.rx("{aussenR}/{innenR}").format(aussenR=aussenR, innenR=innenR),
                                         width=250,
                                         styles={'text-align': 'center',
                                         'font-size': '24px'})
card_AR_IR_Paarung = pn.Card(pn.Row(pn.Spacer(sizing_mode="stretch_width"), md_AR_IR_Paarung, pn.Spacer(sizing_mode="stretch_width")),
                                       width=250,
                                       height=60,
                                       hide_header=True)



md_ueberstand = pn.pane.Markdown(pn.rx("{ueberstand}").format(ueberstand=ueberstand),
                                         width=250,
                                         styles={'text-align': 'center',
                                         'font-size': '24px'})
card_ueberstand = pn.Card(pn.Row(pn.Spacer(sizing_mode="stretch_width"), md_ueberstand, pn.Spacer(sizing_mode="stretch_width")),
                                       width=250,
                                       height=60,
                                       hide_header=True)


md_breite = pn.pane.Markdown(pn.rx("{breite}").format(breite=breite),
                                         width=250,
                                         styles={'text-align': 'center',
                                         'font-size': '24px'})
card_breite = pn.Card(pn.Row(pn.Spacer(sizing_mode="stretch_width"), md_breite, pn.Spacer(sizing_mode="stretch_width")),
                                       width=250,
                                       height=60,
                                       hide_header=True)
   

running_indicator = pn.indicators.LoadingSpinner(value=False,
                                                 height=100,
                                                 width=100,
                                                 color="secondary",
                                                 visible=False,
                                                 margin=50)


column = pn.Column(pn.Row(pn.Spacer(sizing_mode="stretch_width"),pn.pane.Markdown("# Aktuelle Seriennummer:"), pn.Spacer(sizing_mode="stretch_width")),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"), serialCardID, pn.Spacer(sizing_mode="stretch_width")),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"),pn.pane.Markdown("# Außenring / Innenring:"), pn.Spacer(sizing_mode="stretch_width")),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"), card_AR_IR_Paarung, pn.Spacer(sizing_mode="stretch_width")),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"),pn.pane.Markdown("# Überstandsmessung:"), pn.Spacer(sizing_mode="stretch_width")),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"), card_ueberstand, pn.Spacer(sizing_mode="stretch_width")),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"),pn.pane.Markdown("# Breitenmessung:"), pn.Spacer(sizing_mode="stretch_width")),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"), card_breite, pn.Spacer(sizing_mode="stretch_width")),
                   pn.Spacer(sizing_mode="stretch_width", height=30),
                   b_Save,
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"), running_indicator, pn.Spacer(sizing_mode="stretch_width")),
                   pn.Spacer(sizing_mode="stretch_width", height=30),
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
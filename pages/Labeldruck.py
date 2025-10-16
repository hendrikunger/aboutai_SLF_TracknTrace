import json
import os
import sys
import asyncio
import panel as pn
from os.path import isfile
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound
import serial_asyncio
import serial
#import win32print

main_project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if main_project_dir not in sys.path:
    sys.path.append(main_project_dir)

from components import FocusedInput
from db.models import BearingData

TITLE = "Labeldruck"

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


def zeroValues():
    ueberstand.rx.value = 0
    breite.rx.value = 0
    aussenR.rx.value = 0
    innenR.rx.value = 0
    return False


def read_DB(bearing_id):
    session = Session(engine)
    try:
        EntrytoReturn = session.get_one(BearingData, bearing_id)
    except NoResultFound:
        session.rollback()
        pn.state.notifications.error(f'DMC nicht in der Datenbank {bearing_id}', duration=0)
        return zeroValues()

    if not EntrytoReturn.ueberstand:
        pn.state.notifications.error(f'Fehlender Wert für DMC {bearing_id}. Keine Überstandsmessung', duration=0)
        return zeroValues()
    if not EntrytoReturn.breite:
        pn.state.notifications.error(f'Fehlender Wert für DMC {bearing_id}. Keine Breitenmessung', duration=0)
        return zeroValues()
    if not EntrytoReturn.aussenR or not EntrytoReturn.innenR:
        pn.state.notifications.error(f'Fehlender Wert für DMC {bearing_id}. Keine IR / AR Paarung', duration=0)
        return zeroValues()


    ueberstand.rx.value = EntrytoReturn.ueberstand
    breite.rx.value = EntrytoReturn.breite
    aussenR.rx.value = EntrytoReturn.aussenR
    innenR.rx.value = EntrytoReturn.innenR
    
    session.close()
    return True



def process(event):
    if event.new == "": return
    if not event.new.isdigit():
        pn.state.notifications.error('DMC ist keine Zahl', duration=2000)
        ti_Barcode.value = ""
        return   
    running_indicator.value = running_indicator.visible = True
    if read_DB(ti_Barcode.value):
        ti_Barcode.focus = False
        b_Save.disabled = False
        running_indicator.value = running_indicator.visible = False
    else:
        ti_Barcode.focus = True
        b_Save.disabled = True
        running_indicator.value = running_indicator.visible = False


async def doTCP_Transaction(reader, writer, message):
    writer.write(message.encode())
    await writer.drain()
    # line = await reader.readline()
    # data = line.decode('utf8').rstrip()
    # returncode = data.split(":")[1]
    # print(f'Received: {data}', flush=True)
    # print(f'Returncode: {returncode}', flush=True)
    # if returncode != "1":
    #     pn.state.notifications.error(f'TCP IP Drucker Fehler mit Fehlercode {returncode}', duration=5000)
    #     ti_Barcode.value = ""
    #     return


async def create_label():
    with open("SLF_81x36.prn", "r",  encoding="cp1252") as file:
        data = file.read()
    
    data = data.replace("BM[2]4035804439790", "BM[2]4035804439790")
    data = data.replace("BM[13]-3", f"BM[13]{innenR.rx.value}")
    data = data.replace("BM[14]-5", f"BM[14]{aussenR.rx.value}")
    data = data.replace("BM[15]-283", f"BM[15]{breite.rx.value}")
    data = data.replace("BM[16]1,5", f"BM[16]{ueberstand.rx.value}")
     
    return data


async def printer_tcp_ip_communication():

    reader, writer = await asyncio.open_connection('192.168.133.221', 9100)
    print(f"send to Printer: {ti_Barcode.value}, {ueberstand.rx.value}, {breite.rx.value}, {aussenR.rx.value}, {innenR.rx.value}", flush=True)

    data = await create_label()


    #Load Job Variables
    message = f'{data}\r\n'
    await doTCP_Transaction(reader,writer, message)

    writer.close()
    await writer.wait_closed()

async def printer_win32_communication():

    printer_handle = win32print.OpenPrinter("Vario III 107/12")
    try:
        job = win32print.StartDocPrinter(printer_handle, 1, ("RAW print job", None, "RAW"))
        win32print.StartPagePrinter(printer_handle)
        text = await create_label()
        win32print.WritePrinter(printer_handle, text.encode("cp1252"))
        win32print.EndPagePrinter(printer_handle)
        win32print.EndDocPrinter(printer_handle)
    except Exception as e:
        print(f"Error {e}")
    finally:
        win32print.ClosePrinter(printer_handle)

async def button_save_function(event):
    running_indicator.value = running_indicator.visible = True
    #await printer_win32_communication()
    pn.state.notifications.success(f'Erfolgreich zum Drucker gesendet', duration=3000)
    running_indicator.value = running_indicator.visible = False
    ueberstand.rx.value = ""
    breite.rx.value = ""
    aussenR.rx.value = ""
    innenR.rx.value = ""
    b_Save.disabled = True
    ti_Barcode.focus = True


b_Save = pn.widgets.Button(name='An Drucker senden',
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

md_AR_IR_Paarung = pn.pane.Markdown(pn.rx("{innenR}/{aussenR}").format(aussenR=aussenR, innenR=innenR),
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
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"),pn.pane.Markdown("# Innenring / Außenring:"), pn.Spacer(sizing_mode="stretch_width")),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"), card_AR_IR_Paarung, pn.Spacer(sizing_mode="stretch_width")),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"),pn.pane.Markdown("# Breitenmessung:"), pn.Spacer(sizing_mode="stretch_width")),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"), card_breite, pn.Spacer(sizing_mode="stretch_width")),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"),pn.pane.Markdown("# Überstandsmessung:"), pn.Spacer(sizing_mode="stretch_width")),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"), card_ueberstand, pn.Spacer(sizing_mode="stretch_width")),
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
import panel as pn
import json
#panel serve pages/*.py --autoreload --port 80 --admin  --static-dirs assets=./assets

TITLE = "AR DMC Lasern"

pn.extension(sizing_mode="stretch_width")


#read links from json file
with open("links.json", "r") as f:
    links = json.load(f)
    text="\n".join([f"- [{key}]({value})" for key,value in links.items()])
    print(text, flush=True)

linklist = pn.pane.Markdown(
    "\n".join([f"## [{key}]({value})" for key,value in links.items()]),
    sizing_mode="stretch_width",
)

with open("config.json", "r") as f:
    config = json.load(f)



pn.template.BootstrapTemplate(
    title=TITLE,
    sidebar=[linklist],
    main=["# bound_plot"],
    header_background=config["ACCENT"],
    theme=config["THEME"],
    logo=config["LOGO"],
    collapsed_sidebar=config["SIDEBAR_OFF"],
    sidebar_width = 200,
).servable()
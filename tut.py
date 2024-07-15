import panel as pn
import numpy as np
import time
import asyncio

pn.extension('echarts', 'floatpanel', design="bootstrap", notifications=True)

alert = pn.pane.Alert("""
## Markdown Sample

This sample text is from [The Markdown Guide](https://www.markdownguide.org)!
""", alert_type="warning")




number = pn.indicators.Number(
    name="Wind Speed",
    value=15,
    format="{value} m/s",
    colors=[(10, "green"), (100, "red")],
)



def button_function(event):
    alert.visible = not alert.visible

button = pn.widgets.Button(name="Refresh", icon="refresh", button_type="primary", description="Click me!")

pn.bind(button_function, button, watch=True)

link = pn.pane.Markdown("This is a link to [Google](/test)", width=200)


column = pn.Column("# Wind Turbine",link, number, button)

pn.Row(column).servable()

floatpanel = pn.FloatPanel(alert, name="Free Floating FloatPanel", contained=False, position='center')
floatpanel.servable()




image = pn.pane.PNG("https://assets.holoviz.org/panel/tutorials/wind_turbine.png", height=150, sizing_mode="scale_width")

card1 = pn.Card(image, title='Turbine 1', width=200, align="center")
card2 = pn.Card(image, title='Turbine 2', width=200, align="center")

pn.Column(
    card1, card2,
    sizing_mode="fixed", width=400, height=400, styles={"border": "1px solid black"}
).servable()






# Declare state of application
is_stopped = pn.rx(True)

rx_name = is_stopped.rx.where("Start the wind turbine", "Stop the wind turbine")

submit = pn.widgets.Button(name=rx_name)

def toggle_wind_turbine(clicked):
    is_stopped.rx.value = not is_stopped.rx.value

submit.rx.watch(toggle_wind_turbine)

pn.Column(submit).servable()


def calculate_power(wind_speedd, efficiency):
    power_generation = wind_speedd * efficiency
    return (
        f"Wind Speed: {wind_speedd} m/s, "
        f"Efficiency: {efficiency}, "
        f"Power Generation: {power_generation:.1f} kW"
    )



myValue = pn.rx(0.0)

wind_speed_w = pn.widgets.FloatSlider(
    value=5.0, start=0, end=20, step=1, name="Wind Speed (m/s)"
)
efficiency_w = pn.widgets.FloatInput(value=0.3, start=0.0, end=100.0, name="Efficiency (kW/(m/s))", page_step_multiplier = 10)

power = pn.bind(
    calculate_power, wind_speed_w, efficiency_w
)

myValue = wind_speed_w.rx()

gauge = pn.indicators.Gauge(name='Failure Rate', value=myValue, bounds=(-50, 50))

klaus = pn.Column(wind_speed_w, efficiency_w, power, gauge)

klaus.servable()



import param

import panel as pn

from panel.viewable import Viewer






class GoogleMapViewer(Viewer):

    map_iframe = """
<iframe width="100%" height="100%" src="https://maps.google.com/maps?q={country}&z=6&output=embed"
frameborder="0" scrolling="no" marginheight="0" marginwidth="0"></iframe>
"""
    country = param.String(allow_refs=True)
    def __init__(self, **params):
        super().__init__(**params)

        map_iframe_rx = pn.rx(self.map_iframe).format(country=self.param.country)
        self._layout = pn.pane.HTML(map_iframe_rx)

    def __panel__(self):
        return self._layout


country = pn.widgets.Select(options=["Germany", "Nigeria", "Thailand"], name="Country")
view = GoogleMapViewer(name="Google Map viewer", country=country)
pn.Column(country, view).servable()
import panel as pn
import param

class FocusedInput(pn.reactive.ReactiveHTML):
    value = param.String()
    focus = param.Boolean(default=True)

    _template = """
    <input id="entry" autofocus
    onchange="${script('syncclear')}"
    onfocusout="${script('focus')}"></input>
    <input id="focus" hidden value="${focus}"></input>
    """

    _scripts = {
        "syncclear": "data.value=entry.value; entry.value='';",
        "focus": """if(data.focus) {
                        setTimeout(function () {
                        entry.focus();
                        }, 0);
                    }
        """
    }

    _dom_events = {'entry': ['change']}

    def __init__(self, **params):
        super().__init__(**params)
        # Firefox ignores autofocus attribute...
        def onload(self):
            self.focus = False
            self.focus = True
        from functools import partial
        pn.state.onload(partial(onload, self))

    def _entry_change(self, d):
        # print(d.model.data.value)
        pass
# https://www.askpython.com/python-modules/state-machines-python

from statemachine import StateMachine, State, Transition


class LightBulb(StateMachine):

    # creating states
    offState = State("off", initial=True)
    onState = State("on")

    # transitions of the state
    switchOn = offState.to(onState)
    switchOff = onState.to(offState)


if __name__ == "__main__":

    bulb = LightBulb()
    print(bulb.current_state)
    bulb.switchOn()
    print(bulb.current_state)

    print(bulb.is_onState)

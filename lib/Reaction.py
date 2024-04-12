from abc import ABC, abstractmethod


class Reaction(ABC):
    def __init__(self):
        self.menu = None

    def print_event(self, event):
        if self.menu is not None:
            self.menu.print_event(event)
        else:
            print(event)

    def attach_menu(self, _menu):
        self.menu = _menu

    @abstractmethod
    def react(self, _metal):
        """
        Specify the reaction of a metal to a change in parameter specified
        by the user.

        This will be called everytime a parameter is changed.
        """
        pass

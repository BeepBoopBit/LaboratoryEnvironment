from abc import ABC, abstractmethod


class Reaction(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def react(self, _metal):
        """
        Specify the reaction of a metal to a change in parameter specified
        by the user.

        This will be called everytime a parameter is changed.
        """
        pass

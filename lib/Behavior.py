from abc import ABC, abstractmethod


class Behavior(ABC):
    """
    Specify the behavior of the environment.
    """

    def __init__(self):
        self.env = None

    def attach(self, _env):
        """
        Attach the environment to the behavior.
        """
        self.env = _env

    @abstractmethod
    def trigger(self):
        """
        Will be called by the simulate method of the environment
        every epoch.
        """
        pass


class Behaviors:
    """
    A collection of behaviors.
    """

    def __init__(self):
        self.behaviors = {}

    def add(self, _name, _behavior):
        """
        Add a behavior to the collection.
        """
        self.behaviors[_name] = _behavior

    def get(self, _name):
        """
        Get a behavior from the collection.
        """
        return self.behaviors[_name]

    def remove(self, _name):
        """
        Remove a behavior from the collection.
        """
        del self.behaviors[_name]

    def trigger(self, _name):
        """
        Trigger a behavior from the collection.
        """
        self.behaviors[_name].trigger()

    def compile(self, _env):
        """
        Attach the environment to all the behaviors in the collection.
        """
        for key in self.behaviors.keys():
            behavior = self.behaviors[key]
            behavior.attach(_env)

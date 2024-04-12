from abc import ABC, abstractmethod


class Behavior(ABC):
    """
    Specify the behavior of the environment.
    """

    def __init__(self, _will_run=True):
        self.env = None
        self.will_run = _will_run   # Will the behavior run or not each epoch

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
        self.behaviors = {}  # Runnables
        self.pBehaviors = {}  # Pending Behaviors

    def set_runnable(self, _name, _bool):
        """
        Toggle the behavior.
        """

        # If we want to set the behavior to runnable
        if _bool:
            self.behaviors[_name] = self.pBehaviors[_name]
            del self.pBehaviors[_name]

        # Otherwise
        else:
            self.pBehaviors[_name] = self.behaviors[_name]
            del self.behaviors[_name]

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
        if _name in self.behaviors.keys():
            self.behaviors[_name].trigger()
        elif _name in self.pBehaviors.keys():
            self.pBehaviors[_name].trigger()

    def run(self):
        """
        Run all the behaviors in the collection.
        """
        for key in self.behaviors.keys():
            self.behaviors[key].trigger()

    def compile(self, _env):
        """
        Attach the environment to all the behaviors in the collection.
        """
        deletables = []
        for key in self.behaviors.keys():
            behavior = self.behaviors[key]
            behavior.attach(_env)
            if not behavior.will_run:
                self.pBehaviors[key] = behavior
                deletables.append(key)

        for key in deletables:
            del self.behaviors[key]

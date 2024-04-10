from abc import ABC, abstractmethod


class EntityParameter(ABC):
    """
    A Parameter of a metal entity that can react to changes in its value.
    """

    def __init__(self, _value, _reaction):
        self.value = _value
        self.reaction = _reaction
        self.metal = None

    def attach(self, _metal):
        """
        Attach the parameter to the metal entity.
        """
        self.metal = _metal

    def run(self, _operation, _value):
        """
        Run the operation on the parameter.
        """
        self.operate(_operation, _value)
        # We allow 'None' reaction for parameters that don't need to trigger
        if self.reaction is not None:
            # self.metal is passed so that any reaction can perform cascading
            # operation to other parameters of the metal.
            self.reaction.react(self.metal)

    def operate(self, _operation, _value):
        """
        Override this method if you want a custom operation to be performed.
        """
        if _operation == "add":
            self.value += _value
        elif _operation == "sub":
            self.value -= _value
        elif _operation == "mul":
            self.value *= _value
        elif _operation == "div":
            self.value /= _value
        elif _operation == "set":
            self.value = _value
        else:
            raise ValueError("Invalid operation")

    def __str__(self):
        """
        Used for printing the parameter.
        """
        return str(self.value)

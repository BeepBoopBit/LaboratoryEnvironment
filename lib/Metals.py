from abc import ABC, abstractmethod
from lib.EntityParameter import *
from lib.Utils import *


class Metal(ABC):
    """
    A metal entity.
    """

    def __init__(self, _parameters):
        self.parameters = _parameters
        self.verbose = 1

    def compile(self, _verbose, _env, _menu):
        """
        Attach the necessary parameters to the metal entity.
        """
        self.verbose = _verbose
        for key in self.parameters.keys():
            parameter = self.parameters[key]
            if isinstance(parameter, EntityParameter):
                parameter.attach(self)
                if parameter.reaction is not None:
                    parameter.reaction.attach_menu(_menu)

                print_if_verbose(
                    self.verbose,
                    "INFO",
                    "Metal",
                    f"Attached {key} to the {type(self).__name__}."
                )
            else:
                print_if_verbose(
                    self.verbose,
                    "INFO",
                    "Metal",
                    "Parameter is not an EntityParameter... moving on..."
                )

    def __str__(self):
        return_str = "{\n"
        for key in self.parameters.keys():
            return_str += f"\t{key}: {self.parameters[key]}\n"
        return_str += "}\n"
        return return_str

from abc import ABC, abstractmethod


# Helper Function to print if verbose is set
def print_if_verbose(_verbose, _type, _from, _message):
    if _from is None:
        _from = ""

    if _verbose == 1:
        print(f"[{_type}.{_from}] {_message}")


class LaboratoryEnvironment(ABC):
    """
    An environment that simulates the behavior of a metal in different
    laboratory conditions.
    """

    def __init__(self, _parameters, _metal, _behaviors, _verbose=1, _sleep_ms=100):
        self.parameters = _parameters
        self.metal = _metal
        self.behaviors = _behaviors
        self.verbose = _verbose
        self.sleep_ms = _sleep_ms
        self.is_simulate_continue = True  # Used for Early Stop if needed
        self.callbacks = []

    def compile(self):
        """
        Attach the necessary parmaeters to all the entities involved in the
        environment.

        Should be called before the simulate method.
        """

        # Compile Environment(this) Parameter
        for key in self.parameters.keys():

            # Get the parameter Value
            parameter = self.parameters[key]

            # Check if the parameter is a POD or EntityParameter
            if isinstance(parameter, EntityParameter):

                # compile the parameter if it is an EntityParameter
                parameter.attach(self.metal)
                print_if_verbose(
                    self.verbose,
                    "INFO",
                    "LaboratoryEnvironment",
                    f"Attached {key} to the {type(self).__name__}."
                )
            else:

                # Otherwise, if move on
                print_if_verbose(
                    self.verbose,
                    "INFO",
                    "LaboratoryEnvironment",
                    "Parameter is not an EntityParameter... moving on..."
                )

        # Will attach the environment to all the Behaviors
        self.behaviors.compile(self)

        # Will attach the environment to the metal
        self.metal.compile(self.verbose, self)

        # Attach environment to the callbacks
        for callback in self.callbacks:
            callback.attach(self)

    def add_callback(self, _callback):
        """
        Add a callback to the environment. The callback will be called
        every end of the epoch.
        """
        self.callbacks.append(_callback)

    def simulate(self, epoch):
        """
        Simulate the environment for a given number of epochs.

        Sleeps for the given number of milliseconds after each epoch to simulate
        real-time behavior.

        Will call the trigger method of each behavior at the end of each epoch.

        Will call the run method of each callback at the end of each epoch.
        """

        # Used for the sleep method
        import time
        from datetime import datetime

        # Epoch Counter
        epoch_count = 0
        while (epoch_count < epoch) and (self.is_simulate_continue):
            # Logging: Epoch
            print("#"*50)
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"Epoch: {epoch_count} ({current_time})")

            # Trigger each behavior
            for key in self.behaviors.behaviors.keys():

                # Will Call the Callbacks if the condition is met
                self.behaviors.trigger(key)

            # Logging: Metal
            print(f"Metal: {self.metal}\n")
            print("#"*50)
            print("\n")

            # Sleep
            time.sleep(self.sleep_ms / 1000)

            # Increment Epoch
            epoch_count += 1

            # Call the Callbacks
            for callback in self.callbacks:
                callback.run()


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


class LaboratoryCallback(ABC):
    def __init__(self):
        self.env = None

    def attach(self, env):
        """
        Attach the environment to the callback.

        Environment is used to access all the entities and parameters that
        the user can use to define any possible callbacks.
        """
        self.env = env

    @abstractmethod
    def run(self):
        """
        Specify the callback to be run when the condition is met.

        Note: Only use this method for callbacks and not for behaviors or
        reactions.
        """
        pass


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


#########################################
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


#########################################


#########################################
class Metal(ABC):
    """
    A metal entity.
    """

    def __init__(self, _parameters):
        self.parameters = _parameters
        self.verbose = 1

    def compile(self, _verbose, _env):
        """
        Attach the necessary parameters to the metal entity.
        """
        self.verbose = _verbose
        for key in self.parameters.keys():
            parameter = self.parameters[key]
            if isinstance(parameter, EntityParameter):
                parameter.attach(self)
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
#########################################


#  Testing
if __name__ == "__main__":

    class ChangingPHBehavior(Behavior):
        def trigger(self):
            import random
            random_change = random.uniform(-0.2, 0.2)
            self.env.parameters['ph'].run("add", random_change)

    class RustingBehavior(Behavior):

        # Custom Functions
        def calculate_rate(self, pH):
            import random
            from datetime import datetime
            random.seed(datetime.now().microsecond)
            fv = random.uniform(-0.39, 0.39)
            sv = random.uniform(-0.05, 0.05)
            return (-3.74 + fv) + ((0.97 + sv)*pH)

        # Required Functions
        def trigger(self):
            self.env.metal.parameters['rusting_level'].run(
                "add", self.calculate_rate(self.env.parameters['ph'].value))

    class TemperatureBehavior(Behavior):

        def process_data(self, _env):
            k = _env.parameters['conductivity']
            A = _env.metal.parameters['area']
            d = _env.parameters['distance']
            T1 = _env.parameters['temperature'].value
            T2 = _env.metal.parameters['temperature'].value
            return k*A*(T1-T2)/d

        def trigger(self):
            value = self.process_data(_env)
            self.env.metal.parameters['temperature'].run("add", value)

    class TemperatureReaction(Reaction):
        def react(self, _metal):
            if _metal.parameters["temperature"].value >= _metal.parameters["melting_point"]:
                _metal.parameters["is_melting"].run("set", True)
                print("[!] Metal is melting...")

    class RustingReaction(Reaction):
        def react(self, _metal):
            if _metal.parameters["rusting_level"].value >= 15:
                _metal.parameters["is_rusting"].run("set", True)
                print("[!] Metal is rusting...")

    class EarlyStopCallback(LaboratoryCallback):
        def run(self):
            if self.env.metal.parameters["is_melting"].value:
                self.env.is_simulate_continue = False
                print("[!] Metal is melting... Stopping Simulation...")
            if self.env.metal.parameters["is_rusting"].value:
                self.env.is_simulate_continue = False
                print("[!] Metal is rusting... Stopping Simulation...")

    class CoolingBehavior(Behavior):
        def trigger(self):
            import random
            random_change = random.uniform(1.0, 3.0)
            self.env.parameters['temperature'].run("sub", random_change)

    _metal = Metal({
        "name": "Iron",
        "temperature": EntityParameter(100, TemperatureReaction()),
        "melting_point": 1538,
        "rusting_level": EntityParameter(0, RustingReaction()),
        "area": 5,
        "is_melting": EntityParameter(False, None),
        "is_rusting": EntityParameter(False, None)
    })

    _behaviors = Behaviors()
    _behaviors.add("Rusting", RustingBehavior())
    _behaviors.add("Temperature", TemperatureBehavior())
    _behaviors.add("ChangingPH", ChangingPHBehavior())
    _behaviors.add("Cooling", CoolingBehavior())

    _parameters = {
        "ph": EntityParameter(7, None),
        "temperature": EntityParameter(2000, None),
        "distance": 1,
        "conductivity": 0.024,
    }

    _env = LaboratoryEnvironment(
        _parameters, _metal, _behaviors, _verbose=1
    )

    _env.add_callback(EarlyStopCallback())
    _env.compile()
    _env.simulate(500)

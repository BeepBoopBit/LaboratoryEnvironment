from abc import ABC, abstractmethod
from lib.EntityParameter import *
from lib.Utils import *


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
        self.thread = None

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

    def simulate_data_stream(self, data):
        """
        Simulate the environment forever with the data stream.

        Make sure the mark your behaviors as either runnable or not
        using the set_runnable method of the Behaviors class.
        """
        if "operation" not in data.keys():
            print("[!] Invalid Data Format...continuing...")
            return

        operation = data["operation"]
        if "parameter_name" in data.keys():
            parameter_name = data["parameter_name"]

            value = None
            if "value" not in data.keys():
                print("[!] Invalid Data Format...continuing...")
                return

            value = data["value"]
            self.metal.parameters[parameter_name].run(operation, value)
            print("[!] Parameter Updated...")
        elif "behavior_name" in data.keys():
            behavior_name = data["behavior_name"]
            if operation == "run":
                self.behaviors.set_runnable(behavior_name, True)
            elif operation == "stop":
                self.behaviors.set_runnable(behavior_name, False)
            elif operation == "trigger":
                self.behaviors.trigger(behavior_name)
            else:
                print("[!] Invalid Operation...continuing...")
        else:
            print("[!] Invalid Data Format...continuing...")

    def simulate_thread(self, epoch=1, infinite=False):
        """
        Simulate the environment in a thread

        Make sure the mark your behaviors as either runnable or not
        using the set_runnable method of the Behaviors class.
        """

        # create a thread for the data stream
        from threading import Thread
        simulate_thread = Thread(target=self.simulate, args=(epoch, infinite,))
        self.thread = simulate_thread
        simulate_thread.start()

    def wait(self):
        """
        Wait for the thread to finish.
        """
        if self.thread is not None:
            self.thread.join()
        else:
            print("[/] No Thread to wait for...")

    def simulate(self, epoch=1, infinite=False):
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
        while ((epoch_count < epoch) or infinite) and (self.is_simulate_continue):
            # Logging: Epoch
            print("#"*50)
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"Epoch: {epoch_count} ({current_time})")

            # Run all runnable behaviors
            self.behaviors.run()

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

import curses
from abc import ABC, abstractmethod
from lib.EntityParameter import *
from lib.Utils import *


class LaboratoryEnvironment(ABC):
    """
    An environment that simulates the behavior of a metal in different
    laboratory conditions.
    """

    def __init__(self, _parameters, _metal, _behaviors, _menu=None, _verbose=1, _sleep_ms=100):
        self.behaviors = _behaviors
        self.callbacks = []
        self.is_simulate_continue = True  # Used for Early Stop if needed
        self.menu = _menu
        self.metal = _metal
        self.parameters = _parameters
        self.sim_count = 0
        self.sleep_ms = _sleep_ms
        self.thread = None
        self.verbose = _verbose

        # Kafka Information
        self.kafka_topic = None
        self.kafka_server = None
        self.kafka_thread = None

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
                if parameter.reaction is not None:
                    parameter.reaction.attach(self.menu)
                print_if_verbose(
                    self.verbose,
                    "INFO",
                    "LaboratoryEnvironment",
                    f"Attached {key} to the {type(self).__name__}."
                )
            else:

                # Otherwise, move on
                print_if_verbose(
                    self.verbose,
                    "INFO",
                    "LaboratoryEnvironment",
                    "Parameter is not an EntityParameter... moving on..."
                )

        # Will attach the environment to all the Behaviors
        self.behaviors.compile(self)

        # Will attach the environment to the metal
        self.metal.compile(self.verbose, self, self.menu)

        # Attach environment to the callbacks
        for callback in self.callbacks:
            callback.attach(self)

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

        # Epoch Counter
        epoch_count = 0
        while ((epoch_count < epoch) or infinite) and (self.is_simulate_continue):

            # Run all runnable behaviors
            self.behaviors.run()
            self.print_information()

            # Sleep
            time.sleep(self.sleep_ms / 1000)

            # Increment Epoch
            epoch_count += 1

            self.sim_count += 1

            # Call the Callbacks
            for callback in self.callbacks:
                callback.run()

    def simulate_thread(self, epoch=1, infinite=False):
        """
        Simulate the environment in a thread

        Make sure the mark your behaviors as either runnable or not
        using the set_runnable method of the Behaviors class.
        """

        # Check if the thread already exists to avoid
        # creating multiple threads
        if self.thread is not None:
            print("[/] Thread already exists...")

        # Create the thread for the simulation
        from threading import Thread
        simulate_thread = Thread(target=self.simulate, args=(epoch, infinite,))
        self.thread = simulate_thread
        simulate_thread.start()

    def simulate_with_kafka(self, _topic, _server="localhost:9092"):
        """
        Simulate the environment with the Kafka Server.
        """
        self.run_kafka(_topic, _server)
        self.simulate_thread(infinite=True)

    def simulate_data_stream(self, data):
        """
        Used to simulate the data from the kafka server.

        Note: This function should only be used by the kafka server.
        Note: Any additional data that is not in the format will be ignored.

        The data should be in the following format:
        {
            "operation": "set" | "add" | "sub" | "mul" | "div",
            "object_type": "env" | "metal",
            "parameter_name" | "behavior_name": "<parameter_name>",
            "value": "<value>"
        }

        Example:
        {
            "operation": "set",
            "object_type": "env",
            "parameter_name": "temperature",
            "value": 100
        }
        """

        # Check if the operation present in the data
        if "operation" not in data.keys():
            self.print("[!] Invalid Data Format...continuing...")
            return

        # Get the operation
        operation = data["operation"]

        # Check if the object_type is present in the data
        if "object_type" not in data.keys():
            self.print("[!] Invalid Data Format...continuing...")
            return

        # Get the object_type
        object_type = data["object_type"]

        # Check if the parameter_name is present in the data
        if "parameter_name" in data.keys():

            # Get the parameter_name
            parameter_name = data["parameter_name"]

            # Check if the value is present in the data
            if "value" not in data.keys():
                self.print("[!] Invalid Data Format...continuing...")
                return

            # Get the value
            value = data["value"]

            # Perform the manual operation
            # Logging is done inside this method
            self.do_manual_operation(
                object_type, parameter_name, operation, value)

        # Check if the behavior_name is present in the data
        elif "behavior_name" in data.keys():

            # Get the behavior_name
            behavior_name = data["behavior_name"]

            # Check and perform the operation base on its type
            if operation == "run":
                self.behaviors.set_runnable(behavior_name, True)
            elif operation == "stop":
                self.behaviors.set_runnable(behavior_name, False)
            elif operation == "trigger":
                self.behaviors.trigger(behavior_name)
            else:
                self.print("[!] Invalid Operation...continuing...")
                return

            # Log the event
            self.print("[!] Behavior Updated...")

        # If the data is not in the correct format
        else:
            self.print("[!] Invalid Data Format...continuing...")

    def run_kafka(self, _topic, _server="localhost:9092"):
        """
        Run the Kafka Server for the Environment in a thread.
        """

        # Initialize the kafka server information
        self.kafka_topic = _topic
        self.kafka_server = _server

        # Check if the thread already exists to avoid
        # creating multiple threads
        if self.kafka_thread is not None:
            self.print("[/] Kafka Thread already exists...")
            return

        # Create the thread for the kafka server
        from threading import Thread
        kafka_thread = Thread(target=self.my_kafka_server, args=())
        kafka_thread.start()
        self.print("[/] Kafka Thread Started...")
        self.kafka_thread = kafka_thread

    def my_kafka_server(self):
        """
        Used to abstract the kafka server from the run_kafka method for
        threading purposes.
        """

        # Creat Kafka Consumer
        from kafka import KafkaConsumer
        consumer = KafkaConsumer(
            self.kafka_topic, bootstrap_servers=self.kafka_server)

        # TODO: Change this to use 'poll' instead to give more
        # contorl over the simulation and to exit safely
        import json
        for message in consumer:

            # Decode the message from the kafka server
            message = message.value.decode('utf-8')

            # Log the message
            self.print("[/] Kafka Message: " + message)

            # Tryto parse the message as a json
            try:
                message = json.loads(message)
                self.print("[/] Kafka Json Message: " + str(message))

            # If the message is not a valid json, continue
            except:
                self.print("[!] Invalid Json Message...continuing...")
                continue

            # If everything is correct, simulate the data stream
            else:
                self.simulate_data_stream(message)

    def stop(self):
        """
        Stop the simulation. Only useful for threads
        """
        self.is_simulate_continue = False

    def start(self):
        """
        Start the simulation. Only useful for threads
        """
        self.is_simulate_continue = True

    def wait(self):
        """
        Wait for the thread to finish. Only useful for threads
        """
        if self.thread is not None:
            self.thread.join()
        else:
            print("[/] No Thread to wait for...")

    def attach_menu(self, _menu):
        """
        Attach the menu to the environment.
        """
        self.menu = _menu

    def add_callback(self, _callback):
        """
        Add a callback to the environment. The callback will be called
        every end of the epoch.
        """
        self.callbacks.append(_callback)

    def do_manual_operation(self, object_type, parameter_name, operation, value):
        """
        Perform a manual operation on the environment.

        Can be used to test the environment manually.

        Is used by the menu and the kafka server to upate the parmaeters
        """

        # Check if the object_type is valid
        if object_type == "env":

            # Check if the parameter is a string
            if not isinstance(self.parameters[parameter_name], str):
                value = float(value)

            # Check if the parameter is an EntityParameter
            if isinstance(self.parameters[parameter_name], EntityParameter):
                self.parameters[parameter_name].run(operation, value)

            # Otherwise, perform the operation
            else:
                if operation == "set":
                    self.parameters[parameter_name] = value
                elif operation == "add":
                    self.parameters[parameter_name] += value
                elif operation == "sub":
                    self.parameters[parameter_name] -= value
                elif operation == "mul":
                    self.parameters[parameter_name] *= value
                elif operation == "div":
                    self.parameters[parameter_name] /= value
                else:
                    self.print("[!] Invalid Operation...continuing...")
                    return

        # Check if the object_type is valid
        else:

            # Check if the parameter is a string
            if not isinstance(self.metal.parameters[parameter_name], str):
                value = float(value)

            # Check if the parameter is an EntityParameter
            if isinstance(self.metal.parameters[parameter_name], EntityParameter):
                self.metal.parameters[parameter_name].run(operation, value)

            # Otherwise, perform the operation
            else:
                if operation == "set":
                    self.metal.parameters[parameter_name] = value
                elif operation == "add":
                    self.metal.parameters[parameter_name] += value
                elif operation == "sub":
                    self.metal.parameters[parameter_name] -= value
                elif operation == "mul":
                    self.metal.parameters[parameter_name] *= value
                elif operation == "div":
                    self.metal.parameters[parameter_name] /= value
                else:
                    self.print("[!] Invalid Operation...continuing...")
                    return

        # Log the event
        self.print("[!] Parameter Updated...")

    def print(self, value):
        """
        Print the value to the console or the menu if it's attached.
        """
        if self.menu is not None:
            self.menu.print_event(value)
        else:
            print(value)

    def print_information(self):
        """
        Print the information of the environment to the console or the menu
        """
        if (self.menu is not None):
            self.menu.print_simulation(self.return_information())
        else:
            print(self.return_information())

    def return_information(self):
        """
        Return the information of the environment as a string.

        Used for the menu to display the information.
        """
        from datetime import datetime
        str = "-----Parameter Inforamtion-----\n"
        str += "Metal Parameters: \n{"
        str += f"Epoch: ({self.sim_count})\n"
        str += f"Time: ({datetime.now().strftime('%H:%M:%S')})\n"
        str += "Metal: "
        str += self.return_metal_parameters()
        str += "Environment Parameters\n{"
        str += self.return_environment_parameters()
        str += "}\n\n"
        return str

    def parameter_keys(self):
        """
        Return the keys of the parameters of the environment.
        """
        return self.parameters.keys()

    def metal_parameter_keys(self):
        """
        Return the keys of the parameters of the metal.
        """
        return self.metal.parameters.keys()

    def return_metal_parameters(self):
        """
        Return the parameters of the metal as a string.
        """
        return str(self.metal)

    def return_environment_parameters(self):
        """
        Return the parameters of the environment as a string.
        """
        str = ""
        for key in self.parameters.keys():
            str += f"\t{key}: {self.parameters[key]}\n"
        return str


class LaboratoryCallback(ABC):
    """
    A callback that can be run at the end of each epoch.
    """

    def __init__(self):
        self.env = None

    def attach(self, env):
        """
        Attach the environment to the callback.

        Environment is used to access all the entities and parameters that
        the user can use to define any possible callbacks.

        This is done automatically when the callback is added to the
        environment after compilation
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


class LaboratoryEnvironmentMenu:
    def __init__(self, env):
        self.env = env
        self.event_count = 0
        self.event_dict = {}
        self.is_menu_open = True
        self.menu_queue = []
        self.params = {}
        self.stdscr = None

    def draw_sim(self):
        """
        Wrapper for the curses library to draw the simulation menu.
        """
        curses.wrapper(self.draw)

    # Reference: https://stackoverflow.com/questions/67386382/python-curses-splitting-terminal-window-in-4-pads-prefresh-returned-err
    def draw(self, stdscr):
        """
        Draw the simulation menu using the curses library.
        """

        # Set up the screen
        self.stdscr = stdscr

        # Clear and refresh the screen for a blank canvas
        stdscr.clear()
        stdscr.refresh()

        # Initialization of the screen
        height, width = stdscr.getmaxyx()

        # Total Columns and Rows
        cols_tot = width
        rows_tot = height
        self.cols_tot = cols_tot
        self.rows_tot = rows_tot

        # Middle Columns and Rows
        # Used for splitting the screen
        cols_mid = int(width/2)
        rows_mid = int(height/2)
        self.cols_mid = cols_mid
        self.rows_mid = rows_mid

        # Create the pads
        pad11 = curses.newpad(rows_tot, cols_mid)       # Half of the screen
        # Upper Half of the screen
        pad21 = curses.newpad(rows_mid, cols_mid-40)
        # Half of the Upper Half of the screen
        pad22 = curses.newpad(rows_mid, 40)
        # Lower Half of the screen
        pad31 = curses.newpad(rows_mid, cols_mid)

        # Print the title of the pads for reference
        pad11.addstr(0, 0, "*** Main Menu ***")
        pad21.addstr(0, 0, "*** Parameter Menu ***")
        pad22.addstr(0, 0, "*** Event Logs ***")
        pad31.addstr(0, 0, "*** Simulation Logs ***")

        # Refresh the pads to display the title
        pad11.refresh(0, 0, 0, 0, rows_tot, cols_tot)
        pad21.refresh(0, 0, 0, cols_mid, rows_tot, cols_tot)
        pad22.refresh(0, 0, 0, cols_mid+40, rows_tot, cols_tot)
        pad31.refresh(0, 0, rows_mid, cols_mid, rows_tot, cols_tot)

        # Set the pads to the class variables
        self.pad11 = pad11
        self.pad21 = pad21
        self.pad22 = pad22
        self.pad31 = pad31

        # Start the menu
        while self.is_menu_open:
            self.start_queue()

        # Ensure that the threads in the simulation are stopped
        self.env.stop()
        self.env.wait()

    def print_event(self, parameter):
        """
        Print the event in t he event log pad.

        Each event is counted and printed on the same line
        of their first occurence.
        """

        # Clear the pad if the event count is greater than the middle rows
        # TODO: Change this to a scrollable pad
        if self.event_count >= self.rows_mid-1:
            self.event_count = 0
            self.pad22.clear()

        # Check if the parameter is already in the event_dict
        if parameter in self.event_dict.keys():

            # Increment the count of the parameter
            self.event_dict[parameter]['count'] += 1

            # Get the location and the count of the parameter
            count = self.event_dict[parameter]['count']
            loc = self.event_dict[parameter]['index']

            # Print the parameter with the count
            self.pad22.addstr(loc, 0, parameter + f" ({count})")
            self.pad22.refresh(0, 0, 0, self.cols_mid+40,
                               self.rows_tot, self.cols_tot)
            return

        # Otherwise, add the parameter to the event_dict
        self.event_dict[parameter] = {'count': 1, 'index': self.event_count}

        # then print the parameter
        self.pad22.addstr(self.event_count, 0, parameter)
        self.pad22.refresh(0, 0, 0, self.cols_mid+40,
                           self.rows_tot, self.cols_tot)
        self.event_count += 1

    def print_event_info(self, event):
        """
        Print the event in the event log pad.
        """

        self.pad21.clear()
        self.pad21.addstr(0, 0, event)
        self.pad21.refresh(0, 0, 0, self.cols_mid,
                           self.rows_tot, self.cols_tot)

    def print_simulation(self, simulation):
        """
        Print the simulation information in the simulation log pad.
        """

        self.pad21.clear()
        self.pad21.addstr(0, 0, simulation)
        self.pad21.refresh(0, 0, self.rows_mid, self.cols_mid,
                           self.rows_tot, self.cols_tot)

    def print_console(self, console):
        """
        Print the console in the console pad.
        """

        self.pad11.addstr(self.rows_tot-2, 0, console)
        self.pad11.refresh(0, 0, 0, 0, self.rows_tot, self.cols_tot)

    def print_title(self, title):
        """
        Print the title in the menu pad.
        """

        self.pad11.clear()
        self.pad11.addstr(0, 0, f"----- {title} -----")
        self.pad11.refresh(0, 0, 0, 0, self.rows_tot, self.cols_tot)

    def print_menu(self, menu):
        """
        Print the menu in the menu pad.
        """

        self.pad11.addstr(1, 0, menu)
        self.pad11.refresh(0, 0, 0, 0, self.rows_tot, self.cols_tot)

    def get_str_input(self, input_text):
        """
        Used to get the string input from the user.
        """
        self.print_console(input_text + "\n> ")
        return self.stdscr.getstr(0, 0, 5).decode('utf-8')

    def get_int_input(self):
        """
        Used to get the integer input from the user.
        """

        self.print_console("> ")
        ch = chr(self.stdscr.getch())
        return ch

    def get_choice_from(self, options, callables, return_value=None):
        """
        Get the choice from the user and return the callable.

        Used mainly by menu to easily get the choice from the user without
        having to write the same code over and over again.
        """

        while True:

            # Used to store the string of options
            my_str = ""

            # Store the options in a string
            for i, name in enumerate(options):
                my_str += f"{i+1}. {name}\n"

            # Print the options
            self.print_menu(my_str)

            # Try to get the choice from the user and check if it's valid
            try:

                # Get the user input and convert it to an integer
                choice = int(self.get_int_input())

                # Logs the choice
                self.print_console(f"Choice: {choice}")

                # Check if the choice is valid
                if choice < 1 or choice > len(options):
                    raise Exception("Invalid Choice...")
                    continue
                break

            # If the choice is not an integer. Repeat the process
            except:
                self.print_console("Invalid Choice...")

        # Otherwise, get the choice
        callable_index = choice

        # Check if the options and callables are the same length
        if len(options) != len(callables):

            # This is done for special cases where the
            # option and the callable are not the same length
            # As the next function is always going to be the same.

            # If not, check if the choice is the last option
            if choice == len(options):

                # This is done for the back option

                # return for popping
                callable_index = 2
            else:

                # return the function
                callable_index = 1

        # Decrement the callable index for the correct callable
        callable_index -= 1

        # Return with the return_value if it's present
        if return_value is not None:
            return [callables[callable_index], return_value[choice-1]]

        # Otherwise, return the callable with continue index
        return [callables[callable_index], -1]

    def start_queue(self):
        """
        Start the menu queue for the simulation menu.
        """

        # We implemented a menu queue so that
        # we can easily go back to the previous menu
        # and to make sure that the program stack
        # does not overflow
        self.menu_queue.append(self.start)

        # While there are items in the menu queue
        while len(self.menu_queue) > 0:

            # Get the last item in the queue
            queue = self.menu_queue[-1]

            # Check if the queue is a function or an integer

            # If the queue is an integer and it's 0
            if queue == 0:

                # Pop the last two items from the queue
                self.menu_queue.pop()
                self.menu_queue.pop()

            # If the queue is an integer and it's 2
            elif queue == 1:

                # Stop the Menu
                break

            # If the queue is an integer and it's 2
            elif queue == 2:

                # Restart the Menu to the start
                self.menu_queue = []
                self.menu_queue.append(self.start)

            # Otherwise, call the function
            else:
                queue()

    def run(self, _kafka_topic, _kafka_server):
        """
        Run the simulation menu with the kafka server
        """

        self.kafka_topic = _kafka_topic
        self.kafka_server = _kafka_server
        self.draw_sim()

    def start(self):
        """
        Start the simulation menu with the 'starting' options.
        """

        self.print_title("Laboratory Environment")
        choice_func = self.get_choice_from(
            ["Simulate", "Check Parameters", "Modify Parameter", "Exit"],
            [self.menu_simulate, self.menu_check_parameters,
                self.menu_modify, self.exit]
        )
        self.menu_queue.append(choice_func[0])

    def exit(self):
        """
        Exit the simulation menu
        """

        # Since loops are base on the length of the menu_queue, we can just
        # Remove everything from the queue to exit the loop
        self.menu_queue = []
        self.is_menu_open = False

    def menu_simulate(self):
        """
        Simulation menu that shows the options to simulate the environment.
        """

        # Print the title of the menu
        self.print_title("Simulation Menu")

        # Get the choice from the user
        choice_func = self.get_choice_from(
            ["Run", "Stop", "Back"],
            [self.menu_simulate_type, self.stop_simulation, 0]
        )

        # Call the appropriate function based on the choice
        self.menu_queue.append(choice_func[0])

    def menu_simulate_type(self):
        """
        Simulation menu that shows the options of how to simulate the environment.
        """

        # Print the title of the menu
        self.print_title("Simulation Menu")

        # Get the choice from the user
        choice_func = self.get_choice_from(
            ["Run Infinite", "Run Epoch", "Run with Kafka", "Back"],
            [self.simulate, self.run_epoch, self.simulate_with_kafka, 0]
        )

        # Call the appropriate function based on the choice
        self.menu_queue.append(choice_func[0])

    def simulate(self):
        """
        Run the simulation infinitely.
        """

        self.env.start()
        self.env.simulate_thread(infinite=True)
        self.menu_queue.append(2)

    def simulate_with_kafka(self):
        """
        Run the simulation with the kafka server.
        """

        self.env.start()
        self.env.simulate_with_kafka(self.kafka_topic, self.kafka_server)
        self.menu_queue.append(2)

    def stop_simulation(self):
        """
        Stop the simulation.
        """

        self.env.stop()
        self.menu_queue.append(2)

    def run_epoch(self):
        """
        Run the simulation for a given number of epochs.
        """

        # Get the number of epochs from the user
        while True:
            try:
                epoch = int(self.get_str_input("Enter the number of epochs: "))
                break
            except:
                self.print_console("Invalid Epoch...")
                self.menu_queue.append(self.run_epoch)
                return

        # Run the simulation for the given number of epochs
        self.env.start()
        self.env.simulate_thread(epoch=epoch)
        self.menu_queue.append(2)

    def menu_check_parameters(self):
        """
        Check and print the parameters of the environment.
        """

        # Print the parameters in the event log
        self.print_event_info(self.env.return_information())

        # Go back to the start menu
        self.menu_queue.append(2)

    def menu_modify(self):
        """
        Menu that shows the option of whom to modify the parameters.
        """

        # Print the title of the menu
        self.print_title("Modification Menu")

        # Get the choice from the user
        choice_func = self.get_choice_from(
            ["Environment", "Metal", "Back"],
            [self.menu_modify_type, self.menu_modify_type, self.start],
            ["env", "object", 0]
        )

        # Call the appropriate function based on the choice
        self.menu_queue.append(choice_func[0])

        # Set the object_type to the choice
        self.params["object_type"] = choice_func[1]

    def menu_modify_type(self):
        """
        Menu that shows the option of what to modify in the environment.
        """

        # Print the title of the menu
        self.print_title("Modification Menu")

        # Get the choice from the user
        choice = self.get_choice_from(
            ["Parameters", "Behaviors", "Back"],
            [self.menu_modify_parameters,
             self.menu_modify_behaviors, 0]
        )

        # Call the appropriate function based on the choice
        self.menu_queue.append(choice[0])

    def menu_modify_behaviors(self):
        """
        Menu that shows the option of modifying the behaviors of the environment.
        """

        # Check if the object_type is env
        if self.params["object_type"] != "env":
            self.print_event(
                "[!] Behaviors can only be modified for the Environment...")

            # Go back to the start menu
            self.menu_queue.append(2)
            return

        # Get all the options
        runnables = list(self.env.behaviors.runnables())
        pendings = list(self.env.behaviors.pendings())
        all = runnables + pendings + ["Back"]

        # Print the title of the menu
        self.print_title("Modify Behaviors")

        # Get the choice from the user
        choice = self.get_choice_from(
            all,
            [self.menu_modify_behavior_type, 0],
            all
        )

        # Either go back or continue to the menu_modify_behavior_type
        self.menu_queue.append(choice[0])

        # If the choice is not back, continue to the next menu
        self.params["behavior_name"] = choice[1]

    def menu_modify_behavior_type(self):
        """
        Menu that shows the option of how to modify the behaviors of the environment.
        """

        # Print the title of the menu
        self.print_title("Modify Behaviors")

        # The list of options for the menu
        options = ["Run", "Stop", "Trigger", "Back"]

        # Get the choice from the user
        choice = self.get_choice_from(
            options,
            [2, 0],
            ['run', 'stop', 'trigger', 0]
        )

        # Either go back to the start menu or continue to the next menu
        self.menu_queue.append(choice[0])

        # Get the behavior name
        behavior_name = self.params["behavior_name"]

        # Perform the operation based on the choice
        if choice[1] == "run":
            self.env.behaviors.set_runnable(behavior_name, True)
        elif choice[1] == "stop":
            self.env.behaviors.set_runnable(behavior_name, False)
        elif choice[1] == "trigger":
            self.env.behaviors.trigger(behavior_name)

    def menu_modify_parameters(self):
        """
        Menu that shows the option of what specific parameters of the environment to modify
        """

        # Print the title of the menu
        self.print_title("Modify Parameters")

        # Get the parameters based on the object type
        parameters = None
        if self.params["object_type"] == "env":
            parameters = self.env.parameter_keys()
        else:
            parameters = self.env.metal_parameter_keys()

        # Add the back option in the menu
        parameters = list(parameters) + ["Back"]

        # Get the choice from the user
        choice = self.get_choice_from(
            parameters,
            [self.menu_modify_operation_type, 0],
            parameters
        )

        # Either go back or continue to the menu_modify_operation_type
        self.menu_queue.append(choice[0])

        # Set the parameter name to the choice
        self.params["parameter_name"] = choice[1]

    def menu_modify_operation_type(self):
        """
        Menu that shows the operations that can be done on the parameters.
        """

        # Print the title of the menu
        self.print_title("Operation Type")

        # The list of options for the menu
        options = ["Add", "Subtract", "Set", "Back"]

        # Get the choice from the user
        choice = self.get_choice_from(
            options,
            [self.menu_modify_value, 0],
            ['add', 'sub', 'set', 0]
        )

        # Either go back or continue to the menu_modify_value
        self.menu_queue.append(choice[0])

        # Set the operation to the choice
        self.params["operation"] = choice[1]

    def menu_modify_value(self):
        """
        Menu that gets the value to be used for the operation.
        """

        while True:

            # Enable the echo to see what the user is typing
            curses.echo()

            # Get the value from the user
            value = self.get_str_input("Enter the value")

            # Check if the value should be casted into float
            if self.params['operation'] != "set":
                try:
                    value = float(value)
                except:
                    print("Invalid Value...")
                    continue

            self.params["value"] = value
            break

        # Turn off the echo
        curses.noecho()

        # Go to the operate_parameter function
        self.menu_queue.append(self.operate_parameter)

    def operate_parameter(self):
        """
        Do the operation on the parameter.
        """

        # Get all the necessary parameters
        object_type = self.params["object_type"]
        parameter_name = self.params["parameter_name"]
        operation = self.params["operation"]
        value = self.params["value"]

        # Do the manual operation
        self.env.do_manual_operation(
            object_type, parameter_name, operation, value)

        # Log the event
        self.print_event("[!] Parameter Updated...")

        # Go back to the start menu
        self.menu_queue.append(2)

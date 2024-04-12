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
        self.parameters = _parameters
        self.metal = _metal
        self.behaviors = _behaviors
        self.verbose = _verbose
        self.sleep_ms = _sleep_ms
        self.is_simulate_continue = True  # Used for Early Stop if needed
        self.callbacks = []
        self.thread = None
        self.sim_count = 0
        self.menu = _menu

        # Kafka Information
        self.kafka_topic = None
        self.kafka_server = None
        self.kafka_thread = None

    def run_kafka(self, _topic, _server="localhost:9092"):
        """
        Run the Kafka Server for the Environment.
        """
        self.kafka_topic = _topic
        self.kafka_server = _server

        if self.kafka_thread is not None:
            self.print("[/] Kafka Thread already exists...")
            return

        from threading import Thread
        kafka_thread = Thread(target=self.my_kafka_server, args=())
        kafka_thread.start()
        self.print("[/] Kafka Thread Started...")
        self.kafka_thread = kafka_thread

    def my_kafka_server(self):
        from kafka import KafkaConsumer
        consumer = KafkaConsumer(
            self.kafka_topic, bootstrap_servers=self.kafka_server)

        for message in consumer:
            message = message.value.decode('utf-8')
            self.print("[/] Kafka Message: " + message)

            try:
                message = json.loads(message)
                self.print("[/] Kafka Json Message: " + str(message))
            except:
                self.print("[!] Invalid Json Message...continuing...")
                continue
            else:
                self.simulate_data_stream(message)

    def simulate_with_kafka(self, _topic, _server="localhost:9092"):
        """
        Simulate the environment with the Kafka Server.
        """
        self.run_kafka(_topic, _server)
        self.simulate_thread(infinite=True)

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
        self.metal.compile(self.verbose, self, self.menu)

        # Attach environment to the callbacks
        for callback in self.callbacks:
            callback.attach(self)

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
        """

        if object_type == "env":
            if not isinstance(self.parameters[parameter_name], str):
                value = float(value)

            if isinstance(self.parameters[parameter_name], EntityParameter):
                self.parameters[parameter_name].run(operation, value)
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
            if not isinstance(self.metal.parameters[parameter_name], str):
                value = float(value)
            if isinstance(self.metal.parameters[parameter_name], EntityParameter):
                self.metal.parameters[parameter_name].run(operation, value)
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
        object_type = data["object_type"]
        if "parameter_name" in data.keys():
            parameter_name = data["parameter_name"]

            value = None
            if "value" not in data.keys():
                print("[!] Invalid Data Format...continuing...")
                return

            value = data["value"]

            self.do_manual_operation(
                object_type, parameter_name, operation, value)
            self.print("[!] Parameter Updated...")
        elif "behavior_name" in data.keys():
            behavior_name = data["behavior_name"]
            if operation == "run":
                self.behaviors.set_runnable(behavior_name, True)
            elif operation == "stop":
                self.behaviors.set_runnable(behavior_name, False)
            elif operation == "trigger":
                self.behaviors.trigger(behavior_name)
            else:
                self.print("[!] Invalid Operation...continuing...")
        else:
            self.print("[!] Invalid Data Format...continuing...")

    def print(self, value):
        if self.menu is not None:
            self.menu.print_event(value)
        else:
            print(value)

    def simulate_thread(self, epoch=1, infinite=False):
        """
        Simulate the environment in a thread

        Make sure the mark your behaviors as either runnable or not
        using the set_runnable method of the Behaviors class.
        """

        # create a thread for the data stream

        if self.thread is not None:
            print("[/] Thread already exists...")

        from threading import Thread
        simulate_thread = Thread(target=self.simulate, args=(epoch, infinite,))
        self.thread = simulate_thread
        simulate_thread.start()

    def stop(self):
        """
        Stop the simulation.
        """
        self.is_simulate_continue = False

    def start(self):
        """
        Start the simulation.
        """
        self.is_simulate_continue = True

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

    def print_information(self):
        if (self.menu is not None):
            self.menu.print_simulation(self.return_information())
        else:
            print(self.return_information())

    def attach_menu(self, _menu):
        self.menu = _menu

    def return_information(self):
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
        return self.parameters.keys()

    def metal_parameter_keys(self):
        return self.metal.parameters.keys()

    def print_metal_parameters(self):
        print(self.metal)

    def return_metal_parameters(self):
        return str(self.metal)

    def print_environment_parameters(self):
        for key in self.parameters.keys():
            print(f"\t{key}: {self.parameters[key]}")

    def return_environment_parameters(self):
        str = ""
        for key in self.parameters.keys():
            str += f"\t{key}: {self.parameters[key]}\n"
        return str


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


class LabEnvironmentMenu:
    def __init__(self, env):
        self.env = env
        self.menu_queue = []
        self.params = {}
        self.stdscr = None
        self.event_count = 0
        self.is_menu_open = True
        self.event_dict = {}

    def draw_sim(self):
        curses.wrapper(self.draw)

    def draw(self, stdscr):
        self.stdscr = stdscr
        # curses.echo()
        # Clear and refresh the screen for a blank canvas
        stdscr.clear()
        stdscr.refresh()

        # Initialization
        height, width = stdscr.getmaxyx()

        cols_tot = width
        rows_tot = height
        self.cols_tot = cols_tot
        self.rows_tot = rows_tot

        cols_mid = int(width/2)
        rows_mid = int(height/2)
        self.cols_mid = cols_mid
        self.rows_mid = rows_mid

        pad11 = curses.newpad(rows_tot, cols_mid)
        pad21 = curses.newpad(rows_mid, cols_mid-40)
        pad22 = curses.newpad(rows_mid, 40)
        pad31 = curses.newpad(rows_mid, cols_mid)

        pad11.addstr(0, 0, "*** Main Menu ***")
        pad21.addstr(0, 0, "*** Parameter Menu ***")
        pad22.addstr(0, 0, "*** Event Logs ***")
        pad31.addstr(0, 0, "*** Simulation Logs ***")

        pad11.refresh(0, 0, 0, 0, rows_tot, cols_tot)
        pad21.refresh(0, 0, 0, cols_mid, rows_tot, cols_tot)
        pad22.refresh(0, 0, 0, cols_mid+40, rows_tot, cols_tot)
        pad31.refresh(0, 0, rows_mid, cols_mid, rows_tot, cols_tot)

        self.pad11 = pad11
        self.pad21 = pad21
        self.pad22 = pad22
        self.pad31 = pad31

        while self.is_menu_open:
            self.start_queue()

        self.env.stop()
        self.env.wait()

    def print_event(self, parameter):
        if self.event_count >= self.rows_mid-1:
            self.event_count = 0
            self.pad22.clear()

        if parameter in self.event_dict.keys():
            self.event_dict[parameter]['count'] += 1
            count = self.event_dict[parameter]['count']
            loc = self.event_dict[parameter]['index']
            self.pad22.addstr(loc, 0, parameter + f" ({count})")
            self.pad22.refresh(0, 0, 0, self.cols_mid+40,
                               self.rows_tot, self.cols_tot)
            return

        self.event_dict[parameter] = {'count': 1, 'index': self.event_count}
        self.pad22.addstr(self.event_count, 1, parameter)
        self.pad22.refresh(0, 0, 0, self.cols_mid+40,
                           self.rows_tot, self.cols_tot)
        self.event_count += 1

    def print_event_info(self, event):
        self.pad21.clear()
        self.pad21.addstr(0, 0, event)
        self.pad21.refresh(0, 0, 0, self.cols_mid,
                           self.rows_tot, self.cols_tot)

    def print_simulation(self, simulation):
        self.pad21.clear()
        self.pad21.addstr(0, 0, simulation)
        self.pad21.refresh(0, 0, self.rows_mid, self.cols_mid,
                           self.rows_tot, self.cols_tot)

    def print_console(self, console):
        self.pad11.addstr(self.rows_tot-2, 0, console)
        self.pad11.refresh(0, 0, 0, 0, self.rows_tot, self.cols_tot)

    def print_title(self, title):
        self.pad11.clear()
        self.pad11.addstr(0, 0, f"----- {title} -----")
        self.pad11.refresh(0, 0, 0, 0, self.rows_tot, self.cols_tot)

    def print_menu(self, menu):
        self.pad11.addstr(1, 0, menu)
        self.pad11.refresh(0, 0, 0, 0, self.rows_tot, self.cols_tot)

    def get_str_input(self, input_text):
        self.print_console(input_text + "\n> ")
        return self.stdscr.getstr(0, 0, 5).decode('utf-8')

    def get_int_input(self):
        self.print_console("> ")
        ch = chr(self.stdscr.getch())
        return ch

    def get_choice_from(self, options, callables, return_value=None):
        while True:
            str = ""
            for i, name in enumerate(options):
                str += f"{i+1}. {name}\n"
            self.print_menu(str)
            try:
                choice = int(self.get_int_input())
                self.print_console(f"Choice: {choice}")
                if choice < 1 or choice > len(options):
                    self.print_console("Invalid Choice...")
                    continue
                break
            except:
                self.print_console("Invalid Choice...")

        callable_index = choice
        if len(options) != len(callables):
            if choice == len(options):
                # return for popping
                callable_index = 2

            # return the function
            callable_index = 1

        callable_index -= 1

        # Return with the return_value if it's present
        if return_value is not None:
            return [callables[callable_index], return_value[choice-1]]

        # Otherwise, return the callable with continue index
        return [callables[callable_index], -1]

    def start_queue(self):

        # We implemented a menu queue so that
        # we can easily go back to the previous menu
        # and to make sure that the program stack
        # does not overflow
        self.menu_queue.append(self.start)

        while len(self.menu_queue) > 0:

            queue = self.menu_queue[-1]
            if queue == 0:
                self.menu_queue.pop()
                self.menu_queue.pop()
                continue
            elif queue == 1:
                break
            elif queue == 2:
                self.menu_queue = []
                self.menu_queue.append(self.start)
            else:
                queue()

    def run(self, _kafka_topic, _kafka_server):
        self.kafka_topic = _kafka_topic
        self.kafka_server = _kafka_server
        self.draw_sim()

    def exit(self):
        # Since loops are base on the length of the menu_queue, we can just
        # Remove everything from the queue to exit the loop
        self.menu_queue = []
        self.is_menu_open = False

    def start(self):
        self.print_title("Laboratory Environment")
        choice_func = self.get_choice_from(
            ["Simulate", "Check Parameters", "Modify Parameter", "Exit"],
            [self.menu_simulate, self.menu_check_parameters,
                self.menu_modify, self.exit]
        )
        self.menu_queue.append(choice_func[0])

    def menu_simulate(self):
        self.print_title("Simulation Menu")
        choice_func = self.get_choice_from(
            ["Run", "Stop", "Back"],
            [self.menu_simulate_type, self.stop_simulation, 0]
        )
        self.menu_queue.append(choice_func[0])

    def menu_simulate_type(self):
        self.print_title("Simulation Menu")
        choice_func = self.get_choice_from(
            ["Run Infinite", "Run Epoch", "Run with Kafka", "Back"],
            [self.simulate, self.run_epoch, self.simulate_with_kafka, 0]
        )
        self.menu_queue.append(choice_func[0])

    def run_epoch(self):
        while True:
            try:
                epoch = int(self.get_str_input("Enter the number of epochs: "))
                break
            except:
                self.print_console("Invalid Epoch...")

        self.env.simulate_thread(epoch=epoch)
        self.menu_queue.append(2)

    def simulate_with_kafka(self):
        self.print_event_info("[/] Running Kafka Server...")
        self.env.simulate_with_kafka(self.kafka_topic, self.kafka_server)
        self.menu_queue.append(2)

    def simulate(self):
        self.env.start()
        self.env.simulate_thread(infinite=True)
        self.menu_queue.append(2)

    def stop_simulation(self):
        self.env.stop()
        self.menu_queue.append(2)

    def menu_check_parameters(self):
        self.print_event_info(self.env.return_information())
        self.menu_queue.append(0)

    def menu_modify(self):
        self.print_title("Modification Menu")
        choice_func = self.get_choice_from(
            ["Environment", "Metal", "Back"],
            [self.menu_modify_type, self.menu_modify_type, self.start],
            ["env", "object", 0]
        )
        self.menu_queue.append(choice_func[0])
        self.params["object_type"] = choice_func[1]

    def menu_modify_type(self):
        self.print_title("Modification Menu")
        choice = self.get_choice_from(
            ["Parameters", "Behaviors", "Back"],
            [self.menu_modify_parameters,
             self.menu_modify_behaviors, 0]
        )
        self.menu_queue.append(choice[0])

    def menu_modify_behaviors(self):
        if self.params["object_type"] != "env":
            self.print_event(
                "[!] Behaviors can only be modified for the Environment...")

        runnables = list(self.env.behaviors.runnables())
        pendings = list(self.env.behaviors.pendings())
        all = runnables + pendings + ["Back"]

        self.print_title("Modify Behaviors")
        choice = self.get_choice_from(
            all,
            [self.menu_modify_behavior_type, 0],
            all
        )

        self.menu_queue.append(choice[0])
        self.params["behavior_name"] = choice[1]

    def menu_modify_behavior_type(self):
        self.print_title("Modify Behaviors")
        options = ["Run", "Stop", "Trigger", "Back"]
        choice = self.get_choice_from(
            options,
            [2, 0],
            ['run', 'stop', 'trigger', 0]
        )

        self.menu_queue.append(choice[0])

        behavior_name = self.params["behavior_name"]

        if choice[1] == "run":
            self.env.behaviors.set_runnable(behavior_name, True)
        elif choice[1] == "stop":
            self.env.behaviors.set_runnable(behavior_name, False)
        elif choice[1] == "trigger":
            self.env.behaviors.trigger(behavior_name)

    def menu_modify_parameters(self):
        self.print_title("Modify Parameters")
        parameters = None

        if self.params["object_type"] == "env":
            parameters = self.env.parameter_keys()
        else:
            parameters = self.env.metal_parameter_keys()
        parameters = list(parameters) + ["Back"]

        choice = self.get_choice_from(
            parameters,
            [self.menu_modify_operation_type, 0],
            parameters
        )

        self.menu_queue.append(choice[0])
        self.params["parameter_name"] = choice[1]

    def menu_modify_operation_type(self):
        self.print_title("Operation Type")
        options = ["Add", "Subtract", "Set", "Back"]
        choice = self.get_choice_from(
            options,
            [self.menu_modify_value, 0],
            ['add', 'sub', 'set', 0]
        )

        self.menu_queue.append(choice[0])
        self.params["operation"] = choice[1]

    def menu_modify_value(self):
        while True:
            curses.echo()
            value = self.get_str_input("Enter the value")
            if self.params['operation'] != "set":
                try:
                    value = float(value)
                except:
                    print("Invalid Value...")
                    continue

            self.params["value"] = value
            break
        curses.noecho()
        self.menu_queue.append(self.operate_parameter)

    def operate_parameter(self):
        object_type = self.params["object_type"]
        parameter_name = self.params["parameter_name"]
        operation = self.params["operation"]
        value = self.params["value"]

        self.env.do_manual_operation(
            object_type, parameter_name, operation, value)
        self.print_event("[!] Parameter Updated...")
        self.menu_queue.append(2)

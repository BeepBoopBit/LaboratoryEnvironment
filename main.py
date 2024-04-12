from lib.Behavior import *
from lib.LaboratoryEnvironment import *
from lib.Metals import *
from lib.Reaction import *


def get_test_env():
    class ChangingPHBehavior(Behavior):
        def trigger(self):
            import random
            random_change = random.uniform(-0.2, 0.2)
            self.env.parameters['ph'].run("add", random_change)

    class RustingBehavior(Behavior):

        # Custom Functions
        def calculate_rate(self, pH):
            """
            The oxidation of iron(II) nanomolar with H2O2 in seawater
            The equations for the reaction is:
                d[Fe(II)]/dt = -k1[Fe(II)]
                where
                k1 = k * [H2O2]

            Reference Paper: https://zero.sci-hub.se/1659/0dfdfe39b6002febd301fbec100dd9c6/10.1016@j.gca.2004.05.043.pdf#page=10&zoom=100,0,0
            """

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
                self.print_event("[!] Metal is melting...")

    class RustingReaction(Reaction):
        def react(self, _metal):
            if _metal.parameters["rusting_level"].value >= 15:
                _metal.parameters["is_rusting"].run("set", True)
                self.print_event("[!] Metal is rusting...")

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
        # http://hyperphysics.phy-astr.gsu.edu/hbase/Tables/thrcn.html
        "conductivity": 0.024,
    }

    _env = LaboratoryEnvironment(
        _parameters, _metal, _behaviors, _verbose=1, _sleep_ms=50
    )
    return _env


def test_01():
    _env = get_test_env()
    _env.compile()
    _env.simulate(15)

if __name__ == "__main__":
    # test_01_kafka()
    # test_01()
    _env = get_test_env()
    lab_menu = LaboratoryEnvironmentMenu(_env)
    _env.attach_menu(lab_menu)
    _env.compile()
    lab_menu.run("quickstart-events", "localhost:9092")

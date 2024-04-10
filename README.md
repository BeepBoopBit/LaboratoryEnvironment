# Laboratory Environment

A Simple Extensible Environmenet Library for Simulation. (Student Project)

## Classes

### Environment

An environment abstracts all of the classes and provides interfaces for
easier interaction

> Note: This is not an abstract class, but you can override functions if you want to.
> Note: You can use this library to simulate even non-metal entities. For now I just used metal to create the proof of concept.

### Example Code

```py
from lib.Behavior import *
from lib.LaboratoryEnvironment import *
from lib.Metals import *
from lib.Reaction import *

class WaterPHChanging(Behavior):
    def trigger(self):
        # Add +-0.75 to the 'ph' value of the metal every epoch
        import random
        value = random.uniform(-0.75, 0.75)
        self.env.metal.parameters['ph'].run('add', value)

class WaterReactionToPH(Reaction):
    def react(self, _metal):
        # Get the ph value of the metal
        ph_value = _metal.parameters['ph'].value

        # Check for Conditions
        if  ph_value <= -1:
            print("[!] Water is moving toward being acidic")
        if ph_value >= 1:
            print("[!] Water is moving toward being a base")
        if ph_value > -1 and ph_value < 1:
            print("[!] Water is Nuetral")

# Create the metal with the 'ph' parameter
_metal = Metal({
    "ph": EntityParameter(0, WaterReactionToPH())
})

# Create the behavior container
_behaviors = Behaviors()

# Add the behavior we've created
_behaviors.add("Ph_Change",WaterPHChanging())

# Create the environment with not environmental parameters
_env = LaboratoryEnvironment( {}, _metal, _behaviors, _verbose=1)
_env.compile()
_env.simulate(15)
```


### Behaviors

A Behavior specifies how an environment should change a parameter.

- Behaviors
    - Container of Behaviors
- Behaior
    - Specifiy the Behavior of the Environment
    - Requires the `trigger()` method

#### Example Usage

```py
class MyBehavior(Behavior):
    def trigger(self):
        # ... some code here ...

class MyOtherBehavior(Behavior):
    def trigger(self):
        # ... some code here ...

_behaviors = Behaviors()
_behaviors.add("BehaviorName", MyBehavior())
_behaviors.add("OtherBehaviorName", MyOtherBehavior())
```


### Parameters

A parameter is an abstracted value that contains methods for environment
interaction.

- EntityParameter
    - Specify a parameter that reacts on certain parameter changes

### Example Usage

```py
class MyReaction(Reaction):
    def react(self, _metal):
        #my code here

some_value = 10
_metal = Metal({
    "ParameterName": EntityParameter(some_value, MyReaction())
})
```

### Reactions

A Reaction specify how a parameter reacts base on certain conditions.

- Reaction
    - Requires `react()` method

> Example Usage: [Parameters](###Parameters)

### Metal

A Metal is an abstraction of an object that you want to simulate



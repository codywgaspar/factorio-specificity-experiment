from __future__ import annotations

import os
from pathlib import Path

import fle.eval.inspect.integration.solver_variants as solver_variants

from inspect_ai import Task, task
from inspect_ai.dataset import Sample

from fle.eval.inspect.integration.scorers import (
    achievements,
    automated_production_score,
    code,
    production_score,
    technologies,
)
from fle.eval.inspect.integration.solver_variants import (
    factorio_hud_text_only_solver,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROMPT_DIR = PROJECT_ROOT / "prompts" / "fixed"

EXECUTION_CONTRACT = """
Execution requirements:

- Each response must contain one executable Python code block.
- Put executable statements at the top level of the code block.
- Do not import fle.
- Use only functions, classes, prototypes, resources, and technologies available in the Factorio environment.
- Do not invent helper functions or APIs.
- Make concrete progress in the game on every turn.
- Inspect the current state when uncertain, then act using the result.

Common environment functions:

- inspect_inventory()
- nearest(Resource.IronOre)
- nearest(Resource.CopperOre)
- nearest(Resource.Coal)
- nearest(Resource.Stone)
- nearest(Resource.Water)
- move_to(position)
- harvest_resource(position, quantity)
- craft_item(Prototype.ItemName, quantity)
- place_entity(Prototype.EntityName, position=position)
- insert_item(Prototype.ItemName, entity, quantity)
- get_entities()
- get_prototype_recipe(Prototype.ItemName)
- set_research(Technology.TechnologyName)
- sleep(number_of_seconds)
- print(value)

Important API facts:

- Use Position(x=number, y=number) for explicit positions.
- Do not use coordinate tuples such as (20, 10).
- Use set_research(Technology.TechnologyName) to begin research.
- research_technology does not exist.
- Prototype.WoodenChest and Prototype.IronChest are basic chests.
- Prototype.StorageChest is an advanced logistics chest and requires research.
- Use get_prototype_recipe(Prototype.ItemName) when uncertain about ingredients or requirements.
- place_production_unit and similarly named convenience functions do not exist.

Example of a valid basic action:

iron_position = nearest(Resource.IronOre)
move_to(iron_position)
harvest_resource(iron_position, 20)
print(inspect_inventory())

Briefly state your current plan in normal text before the Python code block.
The plan should explain the immediate goal, such as locating resources,
crafting required components, or constructing the next part of the factory.
""".strip()



COMPACT_FLE_SYSTEM_PROMPT = """
You control a real Factorio game through a preloaded Python API.

Every response must contain exactly one executable Python code block.
Briefly state the immediate plan before the code block.

Execution rules:
- Do not import modules.
- Do not define fake APIs, simulation classes, or helper interfaces.
- Do not use infinite loops.
- Use only the preloaded Factorio functions and enums listed below.
- Executable statements must occur at the top level.
- Inspect uncertainty, respond to program errors, and make concrete progress.

Core functions:
- inspect_inventory()
- nearest(Resource.IronOre)
- nearest(Resource.CopperOre)
- nearest(Resource.Coal)
- nearest(Resource.Stone)
- nearest(Resource.Water)
- move_to(position)
- harvest_resource(position, quantity)
- craft_item(prototype, quantity)
- place_entity(
    prototype,
    position=position,
    exact=True_or_False
  )
- insert_item(item_prototype, entity, quantity)
- get_entities()
- get_prototype_recipe(prototype)
- set_research(technology)
- sleep(seconds)
- print(value)

Position format:
- Use positions returned by nearest when practical.
- For explicit coordinates, use Position(x=number, y=number).
- Never use coordinate tuples.

Common prototypes:
- Prototype.IronOre
- Prototype.CopperOre
- Prototype.Coal
- Prototype.Stone
- Prototype.Wood
- Prototype.IronPlate
- Prototype.CopperPlate
- Prototype.IronGearWheel
- Prototype.StoneFurnace
- Prototype.BurnerMiningDrill
- Prototype.ElectricMiningDrill
- Prototype.BurnerInserter
- Prototype.Inserter
- Prototype.TransportBelt
- Prototype.WoodenChest
- Prototype.IronChest
- Prototype.AssemblingMachine1
- Prototype.SmallElectricPole
- Prototype.Boiler
- Prototype.SteamEngine
- Prototype.OffshorePump
- Prototype.Pipe
- Prototype.Lab
- Prototype.AutomationSciencePack

Valid patterns:

resource_position = nearest(Resource.IronOre)
move_to(resource_position)
harvest_resource(resource_position, 20)
print(inspect_inventory())

drill = place_entity(
    Prototype.BurnerMiningDrill,
    position=resource_position
)
insert_item(Prototype.Coal, drill, 5)

Important:
- The Factorio API is already loaded.
- Never import fle, fle_api, or time.
- FLEApi, ResourceType, ItemType, ProductType, collect_resource,
  harvest_wood, automate_collection, automate_production, and
  inspect_environment do not exist.
- Use set_research(Technology.Name); research_technology does not exist.
- Use get_prototype_recipe when uncertain about requirements.
""".strip()


class CompactSystemPromptGenerator:
    def __init__(self, *args, **kwargs):
        pass

    def generate_for_agent(self, agent_idx: int, num_agents: int) -> str:
        return COMPACT_FLE_SYSTEM_PROMPT


solver_variants.SystemPromptGenerator = CompactSystemPromptGenerator


_original_build_hud_user_message = (
    solver_variants.build_hud_user_message
)


def compact_hud_user_message(*args, **kwargs):
    message = _original_build_hud_user_message(*args, **kwargs)

    reminder = """
MANDATORY RESPONSE RULES:

The Factorio functions are already loaded directly into Python.

- Do not import anything.
- Do not use fle, fle.api, fle_api, FLEClient, or FLEApi.
- Do not define classes, functions, clients, or simulations.
- Do not use coordinate tuples.
- Your code must immediately call the preloaded Factorio functions.
- Return exactly one executable Python code block.

When starting with an empty inventory, use these exact actions:

iron_position = nearest(Resource.IronOre)
move_to(iron_position)
harvest_resource(iron_position, 20)
print(inspect_inventory())

If the previous program reports that a path request timed out,
do not repeat the identical route. Move to a nearby intermediate
position, recalculate the resource location, and try again:

move_to(Position(x=5, y=0))
iron_position = nearest(Resource.IronOre)
move_to(iron_position)
harvest_resource(iron_position, 20)
print(inspect_inventory())

ERROR RECOVERY AND API RULES:

- Read the previous program output before writing new code.
- If the previous program produced an error, fix the failing line.
- Never repeat an unchanged program that produced an error.
- Keep each program small so one failure does not waste the entire turn.
- nearest() accepts a Resource or Prototype value.
- Use nearest(Resource.IronOre), nearest(Resource.Coal),
  nearest(Resource.CopperOre), or nearest(Resource.Stone) to find resources.
- Use nearest(Prototype.EntityName) only to locate an existing entity.
- Never call nearest() with a Position.
- nearest() does not select an open construction location.
- inspect_inventory() returns an Inventory object.
- Check quantities with inventory.get("iron-ore", 0),
  inventory.get("coal", 0), or inventory.get("stone", 0).
- Do not use inventory.iron_ore or inventory[0].iron_ore.
- craft_item() and place_entity() require Prototype values, not strings.
- Correct: craft_item(Prototype.StoneFurnace, 1)
- Correct: place_entity(
      Prototype.BurnerMiningDrill,
      position=nearest(Resource.IronOre)
  )
- Incorrect: place_entity("iron-ore-mine", position)
- A burner mining drill is the basic automated mining entity.
- Never guess recipe ingredients.
- Before crafting an unfamiliar item, use:
  print(get_prototype_recipe(Prototype.ItemName))
- If the previous output mentions recipe, smelting, required ingredient,
  or sub-ingredient, do not repeat the failed crafting call.
- The next program must inspect the affected recipe or gather the explicitly
  named missing raw resource.
- Raw resources such as iron ore, copper ore, coal, and stone must be
  harvested; they cannot be crafted.
- Iron ore cannot be hand-crafted directly into iron plates.
- Smelting requires a placed furnace, fuel, ore, waiting time, and extraction.

TOOL SEMANTICS AND EXECUTION RULES:

Use the HUD as the authoritative current state. Reevaluate the next action
after every turn.

Each response must perform exactly one primary phase:
- inspect
- gather
- craft
- place
- load
- wait
- extract
- verify

Keep the program short and direct.

Do not write a large decision tree.
Do not use if, elif, else, while, for, or try/except to select the next phase.
Use the HUD to select one action before writing the program.
Do not repeat unchanged code after an error or state change.
Do not submit a program that can finish without performing an action.

TYPE RULES:

Resource values describe natural resource patches. Use them only with
nearest() and harvest_resource():

iron_patch = nearest(Resource.IronOre)
move_to(iron_patch)
harvest_resource(iron_patch, 10)
print(inspect_inventory())

Prototype values describe items and entities. Use Prototype values with:
- craft_item()
- place_entity()
- insert_item()
- extract_item()
- get_entity()
- nearest() when searching for an entity already placed in the world

Correct:
insert_item(Prototype.Coal, furnace, quantity=5)

Incorrect:
insert_item(Resource.Coal, furnace, quantity=5)

INVENTORY AND WORLD STATE:

An entity listed in inspect_inventory() is being carried by the player.
It does not exist in the world yet.

nearest(Prototype.StoneFurnace) only finds a furnace that has already been
placed in the world. It cannot find a furnace still in player inventory.

Before crafting infrastructure, inspect the HUD inventory.
If the required entity is already in inventory, place that entity instead of
crafting another one.

Crafting pattern:

print(get_prototype_recipe(Prototype.StoneFurnace))

On a later turn, after obtaining the ingredients:

crafted = craft_item(Prototype.StoneFurnace, 1)
print(crafted)
print(inspect_inventory())

Placement pattern for a carried entity:

iron_patch = nearest(Resource.IronOre)
move_to(iron_patch)
build_position = Position(
    x=iron_patch.x + 5,
    y=iron_patch.y
)
furnace = place_entity(
    Prototype.StoneFurnace,
    position=build_position,
    exact=False
)
print(furnace)

place_entity() requires the entity to already exist in player inventory.
place_entity() does not craft the entity.

SMELTING SEMANTICS:

Iron plates and copper plates cannot be hand-crafted.
Do not call craft_item(Prototype.IronPlate, ...).
Ore must be inserted into a placed furnace with fuel.

After a furnace has been placed, it can be found with:

furnace_position = nearest(Prototype.StoneFurnace)
furnace = get_entity(
    Prototype.StoneFurnace,
    furnace_position
)
print(inspect_inventory(furnace))

Load fuel in one turn:

furnace_position = nearest(Prototype.StoneFurnace)
furnace = get_entity(
    Prototype.StoneFurnace,
    furnace_position
)
insert_item(Prototype.Coal, furnace, quantity=5)
print(inspect_inventory(furnace))

Load ore in a later turn:

furnace_position = nearest(Prototype.StoneFurnace)
furnace = get_entity(
    Prototype.StoneFurnace,
    furnace_position
)
insert_item(Prototype.IronOre, furnace, quantity=10)
print(inspect_inventory(furnace))

Wait in a later turn:

sleep(10)
print(get_entities())

Extract completed plates in a later turn:

furnace_position = nearest(Prototype.StoneFurnace)
furnace = get_entity(
    Prototype.StoneFurnace,
    furnace_position
)
extract_item(Prototype.IronPlate, furnace, quantity=5)
print(inspect_inventory())

MINING-DRILL SEMANTICS:

A burner mining drill must be crafted before it can be placed.
It requires iron plates, so inspect its recipe before attempting to craft it.

A placed burner mining drill mines a resource patch beneath it.
Do not insert ore into a mining drill.
Insert fuel such as Prototype.Coal into it.

Do not attempt to find or operate a drill until it has been crafted and placed.

ERROR RECOVERY:

Read the previous program output before selecting the next action.

- If crafting reports missing ingredients, obtain or produce those ingredients.
- nearest(Prototype.Name) raises an exception when no matching placed
  entity exists. It does not return None.
- Never use `if nearest(Prototype.Name) is None`.
- Use the HUD entity list to decide whether an entity has been placed.
- Before place_entity(), move within 10 tiles of the intended build position.
- Do not rely on a saved resource position after moving elsewhere.
- Recalculate the resource position, move to it, and then place nearby.
- If placement fails because the target is too far away, move closer before
  trying placement again.
- If placement fails because the tile is blocked, choose a nearby offset
  position and use exact=False.
- If movement times out, move to a nearby intermediate Position, then
  recalculate the destination on the following turn.
- Never repeat the identical failing program.

The examples above explain API mechanics. They do not replace the task
objective or prescribe the overall factory strategy.


Verified function signatures:

- inspect_inventory(entity=None)
- nearest(resource_or_prototype)
- move_to(position)
- harvest_resource(position, quantity)
- craft_item(prototype, quantity)
- place_entity(prototype, position=position)
- insert_item(prototype, target, quantity)
- extract_item(prototype, source, quantity)
- pickup_entity(entity, position=None)
- get_entities(prototype_or_set, position=None, radius=1000)
- get_entity(prototype, position)
- get_prototype_recipe(prototype)
- set_research(technology)
- get_research_progress(technology=None)
- sleep(seconds)
- print(value)

Allowed functions include inspect_inventory, nearest, move_to,
harvest_resource, craft_item, place_entity, insert_item, extract_item,
pickup_entity, get_entities, get_entity, get_prototype_recipe,
set_research, get_research_progress, sleep, and print.
""".strip()

    return f"{message}\n\n---\n{reminder}"


solver_variants.build_hud_user_message = compact_hud_user_message


def load_cumulative_prompt():
    level = int(
        os.environ.get("FLE_SPECIFICITY_LEVEL", "1")
    )

    configured_directory = os.environ.get(
        "FLE_PROMPT_DIR"
    )

    if configured_directory:
        prompt_directory = Path(
            configured_directory
        ).expanduser()

        if not prompt_directory.is_absolute():
            prompt_directory = (
                Path.cwd() / prompt_directory
            )

        prompt_directory = prompt_directory.resolve()
    else:
        prompt_directory = (
            Path(__file__).resolve().parents[1]
            / "prompts"
            / "levels"
        )

    sections = []

    for number in range(1, level + 1):
        prompt_path = (
            prompt_directory
            / f"level_{number:02d}.txt"
        )

        if not prompt_path.is_file():
            raise FileNotFoundError(
                f"Missing prompt file: {prompt_path}"
            )

        sections.append(
            prompt_path.read_text(
                encoding="utf-8"
            ).strip()
        )

    return level, "\n\n".join(sections).strip()



@task
def specificity_experiment() -> Task:
    level, experimental_prompt = load_cumulative_prompt()

    trajectory_length = int(
        os.getenv("FLE_TRAJECTORY_LENGTH", "20")
    )

    complete_prompt = (
        f"{experimental_prompt}\n\n"
        f"{EXECUTION_CONTRACT}"
    )

    return Task(
        dataset=[
            Sample(
                input=f"Begin task:\n\n{complete_prompt}",
                target=experimental_prompt,
                metadata={
                    "env_id": "open_play_production",
                    "trajectory_length": trajectory_length,
                    "goal_description": complete_prompt,
                    "experimental_prompt": experimental_prompt,
                    "task_type": "unbounded_production",
                    "specificity_level": level,
                    "context_strategy": "hud_text_only",
                },
                id=f"specificity_level_{level:02d}",
            )
        ],
        solver=factorio_hud_text_only_solver(),
        scorer=[
            production_score(),
            technologies(),
            achievements(),
            automated_production_score(),
            code(),
        ],
        name=f"specificity_level_{level:02d}",
    )

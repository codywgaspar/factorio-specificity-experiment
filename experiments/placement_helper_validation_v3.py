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
DEFAULT_PROMPT_DIR = PROJECT_ROOT / "prompts" / "levels"

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

# Temporary placement-helper validation material
COMPACT_FLE_SYSTEM_PROMPT += '\n\nPLACEMENT-HELPER LIVE VALIDATION\n\nThis is a short diagnostic run. Continue making useful factory progress,\nbut prioritize demonstrating that the placement-helper tools work.\n\nDuring this validation:\n\n1. Gather and craft the materials needed for at least one placeable\n   production entity and one adjacent supporting entity.\n2. Before an explicit place_entity call, call can_place_entity and print\n   its result.\n3. Use nearest_buildable when searching for an open construction area.\n   Preserve the exact coordinates it returns; never round them.\n4. Use place_entity_next_to for at least one entity that belongs beside\n   existing infrastructure.\n5. Print the returned entities or positions so tool behavior is visible.\n6. Do not repeatedly guess coordinates after a placement failure.\n7. If a helper call reports an error, inspect that error and correct the\n   function arguments on the following turn.\n\nThe purpose is to test actual calls, not merely discuss these functions.\nDo not import modules or create substitute helper functions.\n\nDOCUMENTATION FROM agent.md:\n# can_place_entity\n\n## Overview\n\n`can_place_entity` is a utility function that checks whether an entity can be placed at a specific position in Factorio. It verifies various placement conditions including:\n\n- Player reach distance\n- Entity existence in inventory\n- Collision with other entities\n- Terrain compatibility (e.g., water for offshore pumps)\n- Space requirements\n\n## Basic Usage\n\n```python\n# Basic syntax\ncan_place = can_place_entity(\n    entity: Prototype,  # The entity type to place\n    direction: Direction = Direction.UP,  # Optional direction\n    position: Position = Position(x=0, y=0)  # Position to check\n) -> bool\n```\n\n## Examples\n\n1. Basic placement check:\n\n```python\n# Check before attempting to place large entities\ntarget_pos = Position(x=10, y=10)\nmove_to(target_pos)\nif can_place_entity(Prototype.SteamEngine, position=target_pos, direction=Direction.DOWN):\n    place_entity(Prototype.SteamEngine, position=target_pos, direction=Direction.DOWN)\nelse:\n    print("Cannot place steam engine at target position")\n```\n\n## Important Considerations\n\n1. Player Distance\n\n- Checks fail if the target position is beyond the player\'s reach\n- Always move close enough before checking placement\n\n2. Entity Collisions\n\n- Checks for existing entities in the target area\n- Returns False if there would be a collision\n\n3. Special Cases\n\n- Offshore pumps require water tiles\n- Some entities have specific placement requirements\n\nDOCUMENTATION FROM agent.md:\n# nearest_buildable\n\nThe `nearest_buildable` tool helps find valid positions to place entities while respecting space requirements and resource coverage. This guide explains how to use it effectively.\n\n## Basic Usage\n\n```python\nnearest_buildable(\n    entity: Prototype,\n    building_box: BuildingBox,\n    center_position: Position\n) -> BoundingBox\n```\n\nThe function returns a BoundingBox object containing buildable area coordinates.\n\n### Parameters\n\n- `entity`: Prototype of entity to place\n- `building_box`: BuildingBox defining required area dimensions\n- `center_position`: Position to search around\n\n### Return Value\n\nReturns a BoundingBox with these attributes:\n\n- `left_top`: Top-left corner Position\n- `right_bottom`: Bottom-right corner Position\n- `left_bottom`: Bottom-left corner Position\n- `right_top`: Top-right corner Position\n- `center`: Center position\n\n## Common Use Cases\n\n### 1. Basic Entity Placement\n\n```python\n# Find place for chest near the origin\nchest_box = BuildingBox(height=Prototype.WoodenChest.HEIGHT, width=Prototype.WoodenChest.WIDTH)\nbuildable_area = nearest_buildable(\n    Prototype.WoodenChest,\n    chest_box,\n    Position(x=0, y=0)\n)\n\n# Place at center of buildable area\nmove_to(buildable_area.center)\nchest = place_entity(Prototype.WoodenChest, position=buildable_area.center)\n```\n\n### 2. Mining Drill Placement\n\n```python\n# Setup mining drill on ore patch\nresource_pos = nearest(Resource.IronOre)\n# Define area for drill\ndrill_box = BuildingBox(height=Prototype.ElectricMiningDrill.HEIGHT, width=Prototype.ElectricMiningDrill.WIDTH)\n\n# Find buildable area\nbuildable_area = nearest_buildable(\n    Prototype.ElectricMiningDrill,\n    drill_box,\n    resource_pos\n)\n\n# Place drill\nmove_to(buildable_area.center)\ndrill = place_entity(\n    Prototype.ElectricMiningDrill,\n    position=buildable_area.center\n)\n```\n\n## Common Patterns\n\n1. **Multiple Entity Placement**\n   Example: Create a copper plate mining line with 3 drills with inserters for future integration\n\n```python\n# log your general idea what you will do next\nprint(f"I will create a single line of 3 drills to mine copper ore")\n# Find space for a line of 3 miners\nmove_to(source_position)\n# define the BuildingBox for the drill.\n# We need 3 drills so width is 3*drill.WIDTH, height is drill.HEIGHT + furnace.HEIGHT, 3 for drill, one for furnace\nbuilding_box = BuildingBox(width = 3 * Prototype.ElectricMiningDrill.WIDTH, height = Prototype.ElectricMiningDrill.HEIGHT + Prototype.StoneFurnace.HEIGHT)\n# get the nearest buildable area around the source_position\nbuildable_coordinates = nearest_buildable(Prototype.BurnerMiningDrill, building_box, source_position)\n\n# Place miners in a line\n# we first get the leftmost coordinate of the buildingbox to start building from\nleft_top = buildable_coordinates.left_top\n# first lets move to the left_top to ensure building\nmove_to(left_top)\nfor i in range(3):\n    # we now iterate from the leftmost point towards the right\n    # take steps of drill.WIDTH\n    drill_pos = Position(x=left_top.x + Prototype.ElectricMiningDrill.WIDTH*i, y=left_top.y)\n    # Place the drill facing down as we start from top coordinate\n    # The drop position will be below the drill as the direction is DOWN\n    drill = place_entity(Prototype.ElectricMiningDrill, position=drill_pos, direction = Direction.DOWN)\n    print(f"Placed ElectricMiningDrill {i} at {drill.position} to mine copper ore")\n    # place a furnace to catch the ore\n    # We use the Direction.DOWN as the direction, as the drill direction is DOWN which means the drop position is below the drill\n    # NB: We also need to use drill.position, not drill.drop_position for placement. FUrnaces are multiple tiles wide and using drill.drop_pos will break the placement. VERY IMPORTANT CONSIDERATION\n    furnace = place_entity_next_to(Prototype.StoneFurnace, reference_position=drill.position, direction = Direction.DOWN)\n    print(f"Placed furnace at {furnace.position} to smelt the copper ore for drill {i} at {drill.position}")\n    # add inserters for future potential integartion\n    # put them below the furnace as the furnace is below the drill\n    inserter = place_entity_next_to(Prototype.Inserter, reference_position=furnace.position, direction = Direction.DOWN)\n    print(f"Placed inserter at {inserter.position} to get the plates from furnace {i} at {furnace.position}")\n\n# sleep for 5 seconds and check a furnace has plates in it\nsleep(5)\n# update furnace entity\nfurnace = game.get_entity(Prototype.StoneFurnace, furnace.position)\nassert inspect_inventory(entity=furnace).get(Prototype.CopperPlate, 0) > 0, f"No copper plates found in furnace at {furnace.position}"\n```\n\n## Best practices\n\nDOCUMENTATION FROM agent.md:\n# place_entity_next_to\n\nThe `place_entity_next_to` tool enables placement of entities relative to other entities. It automatically handles spacing and alignment based on entity dimensions and types.\n\n## Basic Usage\n\n```python\nplace_entity_next_to(\n    entity: Prototype,\n    reference_position: Position,\n    direction: Direction = Direction.RIGHT,\n    spacing: int = 0\n) -> Entity\n```\n\nReturns the placed Entity object.\n\n### Parameters\n\n- `entity`: Prototype of entity to place\n- `reference_position`: Position of reference entity/point\n- `direction`: Which direction to place from reference (UP/DOWN/LEFT/RIGHT)\n- `spacing`: Additional tiles of space between entities (0 or more)\n\n### Examples\n\n```python\n\n# Place inserter next to a furnace to input items into the furnace\ninserter = place_entity_next_to(\n    Prototype.BurnerInserter,\n    furnace.position,\n    direction=Direction.UP,\n    spacing=0\n)\n```\n\n## Common Entity Combinations\n\n### 1. Getting items from a chemical plant\n\n```python\ndef create_assembly_line(chemical_plant):\n    # Place inserter next to machine to take items from it\n    output_inserter = place_entity_next_to(\n        Prototype.BurnerInserter,\n        chemical_plant.position,\n        direction=Direction.LEFT,\n        spacing=0\n    )\n    # insert coal to inserter\n    output_inserter = insert_item(Prototype.Coal, output_inserter, quantity = 10)\n    # Place chest at inserters drop position to get the items\n    output_chest = place_entity(\n        Prototype.WoodenChest,\n        position = output_inserter.position,\n    )\n    # log your actions\n    print(f"Placed chest at {output_chest.position} to get items from a chemical_plant at {chemical_plant.position}. Inserter that puts items into the chest is at {output_inserter.position}")\n```\n\n## Best Practices\n\n1. **Spacing Guidelines**\n\n# Use 0 spacing for:\n\n- Inserters\n- Adjacent belts\n- Direct connections\n\n# Use 1+ spacing for:\n\n- Leaving room for inserters\n- Future expansion\n- Entity access\n\n# Use 3+ spacing for:\n\n- Room for pipe connections\n- Major factory sections\n\n## Smart Placement Feedback\n\nThe tool provides feedback about placement decisions:\n\n```python\ninserter = place_entity_next_to(Prototype.BurnerInserter, assembler.position, Direction.LEFT)\n\n# Check if placement was optimal\nif hasattr(inserter, \'_placement_feedback\'):\n    feedback = inserter._placement_feedback\n    print(f"Placement: {feedback[\'reason\']}")\n    if feedback[\'auto_oriented\']:\n        print("Inserter was auto-oriented for optimal flow")\n```'



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


# This validation-only wrapper places the helper requirement at the
# end of every HUD message, after the normal examples and reminders.
_helper_validation_original_hud = (
    solver_variants.build_hud_user_message
)


def placement_helper_validation_hud(*args, **kwargs):
    message = _helper_validation_original_hud(
        *args,
        **kwargs,
    )

    validation_reminder = """
PLACEMENT-HELPER VALIDATION — REQUIRED

This diagnostic overrides any earlier placement example when you are
ready to place an entity.

Do not call place_entity with a manually guessed position until the
following helper sequence has been demonstrated.

When a placeable entity is available in inventory:

PHASE A — FIND AND VALIDATE
- Construct the appropriate BuildingBox using the entity prototype's
  WIDTH and HEIGHT.
- Call nearest_buildable to find an open area.
- Preserve the exact BoundingBox and center returned.
- Move to that exact center.
- Call can_place_entity for the same prototype and exact center.
- Print the BoundingBox, center, and validation result.
- Do not place the entity during this phase.

Example structure:

placement_box = BuildingBox(
    width=Prototype.StoneFurnace.WIDTH,
    height=Prototype.StoneFurnace.HEIGHT
)
buildable_area = nearest_buildable(
    Prototype.StoneFurnace,
    placement_box,
    nearest(Resource.IronOre)
)
move_to(buildable_area.center)
print(buildable_area)
print(
    can_place_entity(
        Prototype.StoneFurnace,
        position=buildable_area.center
    )
)

PHASE B — PLACE AT THE VALIDATED POSITION
- On the following turn, use the saved buildable_area.center exactly.
- Do not round or manually alter either coordinate.
- Place the entity and print the returned entity.

PHASE C — RELATIVE PLACEMENT
- When another placeable entity is available, call
  place_entity_next_to using the first placed entity's exact position.
- Print the returned entity.
- Do not replace this call with another manually calculated coordinate.

For this diagnostic, helper validation and printing count as one
primary phase. These requirements supersede earlier generic placement
examples. Actual helper calls are required; discussing them is not
sufficient.
""".strip()

    return (
        f"{message}\n\n"
        f"=== CURRENT VALIDATION REQUIREMENT ===\n"
        f"{validation_reminder}"
    )


solver_variants.build_hud_user_message = (
    placement_helper_validation_hud
)



def load_cumulative_prompt() -> tuple[int, str]:
    level = int(os.environ["FLE_SPECIFICITY_LEVEL"])

    if not 1 <= level <= 12:
        raise ValueError(
            "FLE_SPECIFICITY_LEVEL must be between 1 and 12"
        )

    prompt_dir = Path(
        os.getenv("FLE_PROMPT_DIR", str(DEFAULT_PROMPT_DIR))
    ).resolve()

    sections: list[str] = []

    for number in range(1, level + 1):
        prompt_path = prompt_dir / f"level_{number:02d}.txt"

        if not prompt_path.is_file():
            raise FileNotFoundError(
                f"Missing prompt file: {prompt_path}"
            )

        text = prompt_path.read_text(encoding="utf-8").strip()

        if not text:
            raise ValueError(
                f"Prompt file is empty: {prompt_path}"
            )

        sections.append(text)

    return level, "\n\n".join(sections)


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

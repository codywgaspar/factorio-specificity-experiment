# Adaptive Level 3 Completed Review

Status: completed
Decision: advance to adaptive Level 4 with a structured objective and placement-control correction.

## Level 3 results

- Mean production increased 20%, from approximately 2,097 to 2,518.
- Mean automated production increased 23%, from 471 to 577.
- Placement errors decreased 22%, from 199 to 156.
- Recovery within three turns improved from 6.1% to 28.3%.
- Average longest error streak decreased from 54.3 to 36 turns.
- Productive-turn rate increased from 60.2% to 63.8%.

## Remaining problem

Placement still accounted for 156 of the 198 Level 3 errors.
The model often inspected an inventory that did not contain the intended entity but attempted placement anyway.
It treated failures as coordinate problems, changed locations or chest types, and continued pursuing the same objective.
One run reached a 61-turn consecutive error streak.

The strongest run achieved 3,792 production and 1,021 automated production because it avoided the placement loop until approximately turn 130.

## Level 4 intervention

At the beginning of every response, state one immediate objective using this format:

Objective: [verb + desired factory outcome]

Describe the intended outcome, not merely an item, entity, coordinate, or action. For example, "maintain continuous iron-plate production" is an objective; "wooden chest," "place at (2, -58)," or "use place_entity" are not objectives.

Keep the same objective wording while pursuing the same factory outcome. Changing coordinates, quantities, code, or entity types does not create a new objective when the intended outcome remains the same. If an objective is abandoned, state why and select a different productive outcome.

Before every place_entity action, execute inspect_inventory() and confirm that the exact finished entity to be placed is present with a quantity of at least one. The inventory check and place_entity call must appear in the same executable code block and refer to the same entity. Raw materials such as wood, stone, iron plates, or gears do not count as the finished entity.

If the exact entity is absent, do not attempt placement. Gather its required materials, craft it, or continue productive work using existing infrastructure.

If placement fails, inspect the relevant entities and surrounding area before making one corrected attempt. No more than two placement attempts may serve the same objective. Changing coordinates or substituting another chest, furnace, drill, or similar entity still counts toward the same two-attempt limit.

After two failed placement attempts, abandon that objective until inventory or entity state has materially changed. The next objective must service or expand a functioning production process without repeating the failed placement.

## Expected effect

- Clearer continuity across turns through a stated outcome-based objective
- Better alignment between the stated objective and executed code
- Fewer placement attempts without the required finished entity
- Fewer coordinate and entity substitutions serving the same failed objective
- Shorter placement-related error streaks
- More productive fallback behavior after placement failure

## Primary Level 4 measures

- Placement errors
- Longest consecutive error streak
- Recovery within three turns
- Productive-turn rate
- Production score
- Automated-production score
- Objective persistence
- Objective-action alignment

# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

MapleRoyals (MapleStory private server) players planning HP washing for a character. Two groups use it side by side:

- Players who know they should HP wash but not the formulas; they follow the guide and want a plan they can execute.
- Experienced washers who know Method 1 / Method 2 and MP washing, and tune parameters to compare policies and squeeze APR.

## Product Purpose

Compute a low-APR (AP Reset) HP washing plan for a target HP / MP / level: search base INT and MP wash end level across policies (Optimize), or check one fixed plan level by level (Simulate), then export the level-by-level plan as CSV. Success is a plan the player trusts enough to follow in game, with the fewest APR spent.

## Positioning

Shares its calculation core with the project's Python desktop app (parity-tested), covers job-specific formulas for all supported jobs, and plans from an arbitrary mid-game character state (Resume), not only from level 1.

## Operating Context

Used on a desktop computer alongside the running game client, often switching windows back and forth while leveling, frequently in the evening. Players set gear once, run Optimize, then read the plan table or CSV while playing.

## Capabilities and Constraints

- Tabs: Guide, Optimize, Simulate, Equipment, Job reference, Strategy guide (Actions), Contact Author.
- Jobs: Hero, Paladin, Dark Knight, Bowmaster/Marksman, Night Lord/Shadower, Buccaneer, Corsair, Beginner. Thief compares policies A/B/C/D; other jobs use Policy D.
- Settings and equipment persist in browser localStorage.
- Calculation logic is shared with the Python desktop app; changes to it must keep both test suites passing.
- Game terminology stays in English (APR, MP wash, Method 1/2, base INT).

## Brand Commitments

- Bilingual Traditional Chinese / English, with a language switch.
- Light and dark appearance, with a switch.
- The disclaimer that results are estimates to verify in game stays visible.
- The name "MapleRoyals HP Washing APR Optimizer".

## Evidence on Hand

No testimonials, user counts, or benchmarks exist; do not fabricate any. Author contact: Discord `fuhuo`, GitHub repository Liang0218/mapleroyals-hp-washing.

## Product Principles

1. The answer first: the plan's key numbers before the detail.
2. Trust through honesty: say clearly when a target is not reached and what the closest result is.
3. Serve both the follower and the tuner without making either wade through the other's controls.
4. Readable beside a game window, at a glance, at any hour.

# Lobby Template — Ground Floor (Bird's Eye View)

## Overview

The lobby is a rectangular room. The entrance is at the bottom. The elevator is at the top center. Room entrances are along the walls. The bodyguard stands near the entrance.

## Elements

| Element | Location | Description |
|---------|----------|-------------|
| **Entrance** | Bottom center, 3 tiles wide | Double doors. The user walks in here. |
| **Bodyguard** | Bottom right, 1 tile | Stands just inside the entrance, facing the door. Watches everyone who walks in. |
| **Elevator** | Top center, 3 tiles wide | Goes up to floors 2, 3, 4, and Penthouse. |
| **Room 1 (Research)** | Left wall, middle | Sign above door says "ROOM 1: RESEARCH". Doormat says "1". Door on the wall. |
| **Room 7 (Sentiment)** | Left wall, lower | Sign above door says "ROOM 7: SENTIMENT". Doormat says "7". Door on the wall. |
| **Room 13 (Alt Data)** | Right wall, middle | Sign above door says "ROOM 13: ALT DATA". Doormat says "13". Door on the wall. |
| **Furniture** | Along walls | Chairs, small tables, a plant. Sparse — this is a lobby, not an office. |

## Grid Layout

Each cell is one tile. `W` = wall, `.` = walkable floor.

```
W W W W W W W W W W W W W W W W W W W W W W W W W W W W W W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . [ELEVATOR] . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W W W W W W W W W W W W W W W W W W W W W W W W W W W W W W
```

## Lobby — Detailed Template

```
W W W W W W W W W W W W W W W W W W W W W W W W W W W W W W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . E L E V . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W . . . . . . . . . . . . . . . . . . . . . . . . . . . . W
W W W W W W W W W W W W W W W W W W W W W W W W W W W W W W
```

## Placement Guide

- **Elevator**: Place at top center. 3 tiles wide. Leads to floors 2, 3, 4, PH.
- **Entrance**: Place at bottom center. 3 tiles wide. This is where the user spawns.
- **Bodyguard**: Place at bottom right, 1 tile from the entrance. Always facing the door.
- **Room doors**: Place along the walls. Each door has:
  - A **sign** above it (label: room name)
  - A **doormat** in front (label: room number)
  - A **door** (walkable tile that transitions to the room)
- **Furniture**: Optional. A few chairs or small tables along the walls. Sparse — this is a lobby.

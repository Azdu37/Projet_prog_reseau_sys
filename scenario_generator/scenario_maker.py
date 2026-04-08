import random
import math
import os

MIN_DISTANCE = 2.5


def is_valid(pos, others):
    """Check minimum distance against all existing units"""
    x, y = pos
    for ox, oy in others:
        if math.hypot(x - ox, y - oy) < MIN_DISTANCE:
            return False
    return True


def main():
    print("=== Unit Map Generator ===")
    
    p = int(input("Map square size (MAX: 220): "))

    print(" /!\ Keep number of units under 110 or suffer (very) slow runs")

    counts = {}
    for t in ["K", "C", "P", "L", "S"]:
        counts[t] = int(input(f"Number of {t} units: "))

    filename = input("Output file name: ")
    # add extension if missing
    if not filename.endswith(".txt"):
        filename += ".txt"

    x_max = int((p / 2) - 20)
    y_max = p-5

    placed_positions = []
    units = []

    for unit_type, amount in counts.items():
        for _ in range(amount):

            attempts = 0
            while True:
                attempts += 1
                if attempts > 10_000:
                    raise RuntimeError(
                        "Cannot place units: map too small or too many units."
                    )

                x = random.uniform(2, x_max)
                y = random.uniform(5, y_max)

                if is_valid((x, y), placed_positions):
                    placed_positions.append((x, y))
                    units.append((x, y, unit_type))
                    break

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    SCENARIO_DIR = os.path.join(BASE_DIR, "data", "scenario")

    os.makedirs(SCENARIO_DIR, exist_ok=True)

    path = os.path.join(SCENARIO_DIR, filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"{p},{p}\n")
        for x, y, t in units:
            f.write(f"{x:.2f},{y:.2f},{t}\n")

    print(f"\nFile '{filename}' created")
    print(f"Location: {path}")
    print(f"Units placed: {len(units)}")
    print(f"Minimum distance guaranteed: {MIN_DISTANCE}")


if __name__ == "__main__":
    main()
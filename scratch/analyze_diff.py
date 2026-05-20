with open("scratch/diff.txt", "r", encoding="utf-8") as f:
    diff_lines = f.readlines()

print("Diff lines count:", len(diff_lines))

# Print only lines starting with '+' or '-' to see the exact edits, excluding metadata lines
for i, line in enumerate(diff_lines):
    if line.startswith(('+', '-')) and not line.startswith(('+++', '---')):
        print(f"L{i+1}: {line.strip()}")

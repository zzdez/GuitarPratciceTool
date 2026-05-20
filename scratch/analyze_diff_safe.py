with open("scratch/diff.txt", "r", encoding="utf-8") as f:
    diff_lines = f.readlines()

# Let's count actual changes in chunks
print("Diff lines count:", len(diff_lines))

chunk_info = []
for i, line in enumerate(diff_lines):
    if line.startswith("@@"):
        chunk_info.append((i, line))

print("Found chunks:")
for idx, info in chunk_info:
    print(f"Line {idx+1}: {info.strip()}")
    # Let's print 15 lines after this @@ to see the diff hunk header and content safely
    for j in range(idx+1, min(len(diff_lines), idx + 25)):
        line_to_print = diff_lines[j].strip()
        # strip non-ascii to avoid unicode encode errors in terminal
        clean_line = "".join([c if ord(c) < 128 else '?' for c in line_to_print])
        print(f"  {j+1}: {clean_line}")

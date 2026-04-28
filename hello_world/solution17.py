n = int(input())
results = []

for _ in range(n):
    word = input()
    replacements = 0

    # run_length tracks how many consecutive identical characters we've seen in a row.
    # e.g. in "aaabbc", the runs are: "aaa" (length 3), "bb" (length 2), "c" (length 1)
    # A run of length k needs k // 2 replacements to break it up.
    # e.g. "aaa" -> change the middle 'a' -> "aba" (1 fix, not 2)
    run_length = 1

    for i in range(1, len(word)):
        if word[i] == word[i - 1]:
            # Same character as previous — extend the current run
            run_length += 1
        else:
            # Different character — the run just ended, count its replacements
            replacements += run_length // 2
            run_length = 1  # Start a new run

    # The last run doesn't end with a character change, so count it here
    replacements += run_length // 2
    results.append(replacements)

print(results)

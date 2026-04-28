n = int(input())
numbers = [int(input()) for _ in range(n)]

numbers.sort()

# After sorting, the smallest absolute difference is always between adjacent elements
min_diff = min(numbers[i+1] - numbers[i] for i in range(n - 1))

# Collect all adjacent pairs that have the minimum difference
for i in range(n - 1):
    if numbers[i+1] - numbers[i] == min_diff:
        print(numbers[i], numbers[i+1])

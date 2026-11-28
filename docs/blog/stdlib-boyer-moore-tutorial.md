# Boyer-Moore String Search Algorithm Tutorial

## Introduction

The Boyer-Moore string search algorithm, developed by Robert S. Boyer and J Strother Moore in 1977, is an efficient string-searching algorithm that utilizes information gathered during the preprocessing phase to skip sections of the text, resulting in sublinear (n/m) average search efficiency.

## Algorithm Overview

Unlike naive string search algorithms that check each character position sequentially, Boyer-Moore:

1. Scans the pattern from right to left
2. Uses preprocessing to create skip tables
3. Jumps ahead when mismatches occur
4. Achieves average-case efficiency better than O(n)

## Bad Character Heuristic

The bad character heuristic is the key optimization in Boyer-Moore:

- When a mismatch occurs, we look at the mismatched character in the text
- We check if this character appears anywhere in the pattern to the right of the current position
- If it does, we shift the pattern to align this character with its rightmost occurrence
- If it doesn't, we shift the pattern past the mismatched character entirely

## Implementation Steps

### 1. Preprocessing: Building the Bad Character Table

```python
def build_bad_char_table(pattern):
    bad_char = {}
    length = len(pattern)
    
    # Initialize all characters with -1
    for char in pattern:
        bad_char[char] = -1
    
    # Fill the table with rightmost positions
    for i in range(length):
        bad_char[pattern[i]] = i
    
    return bad_char
```

### 2. The Search Algorithm

```python
def boyer_moore_search(text, pattern):
    m = len(pattern)
    n = len(text)
    
    if m == 0 or n == 0 or m > n:
        return []
    
    bad_char = build_bad_char_table(pattern)
    occurrences = []
    
    # Shift the pattern to align with text
    s = 0
    while s <= n - m:
        j = m - 1  # Start from the end of the pattern
        
        # Compare pattern with text from right to left
        while j >= 0 and pattern[j] == text[s + j]:
            j -= 1
        
        # If pattern is found
        if j < 0:
            occurrences.append(s)
            # Shift pattern using bad character heuristic
            s += (m - bad_char.get(text[s + m], -1) if s + m < n else 1)
        else:
            # Shift pattern based on bad character
            shift = j - bad_char.get(text[s + j], -1)
            s += max(1, shift)
    
    return occurrences
```

## Example Usage

```python
text = "ABAAABCDABABABACABABABA"
pattern = "ABABABA"

occurrences = boyer_moore_search(text, pattern)
print(f"Pattern found at positions: {occurrences}")
# Output: Pattern found at positions: [10, 14]
```

## Performance Analysis

- **Best Case**: O(n/m) - when many characters are skipped
- **Average Case**: O(n/m) - sublinear time
- **Worst Case**: O(nm) - rare, occurs with specific patterns like "AAAAA"

## Comparison with KMP

| Feature | Boyer-Moore | KMP |
|---------|-------------|-----|
| Direction | Right-to-left | Left-to-right |
| Preprocessing | Bad character table | Partial match table |
| Average Case | O(n/m) | O(n) |
| Worst Case | O(nm) | O(n) |
| Space Complexity | O(k) | O(m) |
| Practical Performance | Faster for large alphabets | More consistent |

## Practical Applications

1. **Source Code Search**: Efficiently finding function definitions or variable names in large codebases
2. **Log File Analysis**: Quickly scanning through large log files for error patterns
3. **DNA Sequence Matching**: Finding genetic patterns in biological sequences
4. **Text Editors**: Implementing efficient "Find" functionality

## Conclusion

The Boyer-Moore algorithm remains one of the most efficient string-searching algorithms, particularly for large alphabets and long patterns. Its bad character heuristic allows it to skip ahead significantly when mismatches occur, resulting in sublinear average-case performance.

While its worst-case performance is linear, the practical efficiency and simplicity of implementation make it a preferred choice for many real-world applications.
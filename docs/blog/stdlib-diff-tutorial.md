# Myers Diff Algorithm: Theory and Implementation

## Introduction

The Myers diff algorithm, developed by Eugene Myers in 1986, provides an efficient $O(ND)$ solution for finding the shortest edit script (SES) between two sequences. This tutorial explores the theoretical foundations of the algorithm, its relationship to the longest common subsequence (LCS), and practical implementation for generating unified diffs.

## Theoretical Foundations

### Edit Graph and Diagonal Exploration

The Myers algorithm operates on an edit graph where each point $(x, y)$ represents a possible alignment between the first sequence (length $X$) and the second sequence (length $Y$). The key insight is that we can parameterize this exploration using diagonals defined by $k = x - y$.

Each diagonal represents a set of points where the difference between indices is constant. The algorithm explores these diagonals in order of increasing absolute value of $k$, ensuring that we find the shortest possible edit script.

### Greedy Snakes

A "snake" is a path in the edit graph that moves either horizontally (deletion) or vertically (insertion) after an initial diagonal move. The Myers algorithm finds the furthest-reaching point on each diagonal, which corresponds to the longest possible snake.

The greedy nature of the algorithm ensures that once we find a snake on a diagonal, we don't need to consider shorter paths on the same diagonal.

### SES vs LCS Duality

The shortest edit script (SES) represents the minimal sequence of insertions and deletions required to transform one sequence into another. The longest common subsequence (LCS) represents the longest sequence of elements that appear in both sequences in the same order.

These concepts are dual:
- The length of the SES is $X + Y - 2|LCS|$
- The length of the LCS is $(X + Y - |SES|)/2$

This duality allows us to solve either problem and derive the solution to the other.

## Unified Diff Generation

When generating unified diffs, we need to consider several invariants:

1. **Context lines**: Include surrounding context to make the diff more readable
2. **Minimal changes**: Only show the actual differences between files
3. **Line numbering**: Maintain correct line numbers before and after changes
4. **Change grouping**: Group related changes together where possible

The Myers algorithm provides the foundation for determining which lines have changed, while additional logic is needed to format these changes according to unified diff standards.

## Implementation Strategy

The implementation follows these steps:

1. Compute the edit graph using diagonal exploration
2. Extract the shortest edit script from the graph
3. Convert the SES to a unified diff format
4. Add context lines and formatting

This approach ensures that we maintain the theoretical guarantees of the Myers algorithm while producing practical, readable diffs.

## Conclusion

The Myers diff algorithm provides an elegant and efficient solution to the problem of finding differences between sequences. By understanding its theoretical foundations and implementing it carefully, we can create robust diff tools that are both correct and performant.

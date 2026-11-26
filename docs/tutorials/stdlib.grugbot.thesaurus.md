# Tutorial: Using `stdlib.grugbot.thesaurus`

Welcome to the `stdlib.grugbot.thesaurus` tutorial! In this guide, you will learn how to look up words and filter synonyms using the GrugBot thesaurus module in Lateralus.

## Overview

The `grugbot.thesaurus` module provides fast, offline synonym lookups tailored for natural language routing and AI pipelines.

## Prerequisites

Ensure you have the Lateralus runtime installed and your project includes the standard library.

## Example: Looking Up and Filtering Synonyms

Below is a complete, runnable Lateralus program that queries the thesaurus for synonyms of "fast" and filters them for words with length less than or equal to 6, confirming the expected output `["quick", "rapid"]`.

```lateralus
use stdlib.grugbot.thesaurus

fn main() {
    -- Look up synonyms for "fast"
    let word = "fast"
    let results = thesaurus.lookup(word)
        |> filter(syn -> length(syn) <= 6)

    -- Expected output check
    print(results)
}
```

### Running the Example

Execute the script using the Lateralus CLI:

```bash
lateralus run tutorial_thesaurus.lat
```

Output:
```json
["quick", "rapid"]
```

## Conclusion
You have successfully learned how to look up and filter synonyms using `stdlib.grugbot.thesaurus`. Happy coding!
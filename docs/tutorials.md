**FULL TURORIAL:** https://realpython.com/python-project-documentation-with-mkdocs/

mkdocs serve -> command to build the documentation (can open it on localhost)

mkdocs build -> to prepare for hosting on GitHub Pages

mkdocs gh-deploy -> deploy the documentation (may take some time) + rerunning it will rebuild existing documentation


**FUNCTION:**

from typing import Union

def add(a: Union[float, int], b: Union[float, int]) -> float:
    """Compute and return the sum of two numbers.

    Examples:
        >>> add(4.0, 2.0)
        6.0
        >>> add(4, 2)
        6.0

    Args:
        a: A number representing the first addend in the addition.
        b: A number representing the second addend in the addition.

    Returns:
        A number representing the arithmetic sum of `a` and `b`.
    """
    return float(a + b)


**MODULE:**

*calculator/calculations.py*

"""Provide several sample math calculations.

This module allows the user to make mathematical calculations.

The module contains the following functions:

- `add(a, b)` - Returns the sum of two numbers.
- `subtract(a, b)` - Returns the difference of two numbers.
- `multiply(a, b)` - Returns the product of two numbers.
- `divide(a, b)` - Returns the quotient of two numbers.
"""

from typing import Union
...
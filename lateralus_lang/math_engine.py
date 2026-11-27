import math

class Vector:
    def __init__(self, components):
        self.components = list(components)

    def norm(self):
        return math.hypot(*self.components)

    def normalize(self):
        n = self.norm()
        if n == 0.0:
            raise ValueError("cannot normalize zero vector")
        return (c / n for c in self.components)
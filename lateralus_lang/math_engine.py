class Vector:
    def __init__(self, coordinates):
        self.coordinates = list(coordinates)

    def __len__(self):
        return len(self.coordinates)

    def __repr__(self):
        return f"⟨{', '.join(map(str, self.coordinates))}⟩"

    def __add__(self, other):
        if len(self) != len(other):
            raise ValueError(f"Vector dimensions must match for addition: {len(self)} != {len(other)}")
        return Vector(a + b for a, b in zip(self.coordinates, other.coordinates))

    def __sub__(self, other):
        if len(self) != len(other):
            raise ValueError(f"Vector dimensions must match for subtraction: {len(self)} != {len(other)}")
        return Vector(a - b for a, b in zip(self.coordinates, other.coordinates))

    def dot(self, other):
        if len(self) != len(other):
            raise ValueError(f"Vector dimensions must match for dot product: {len(self)} != {len(other)}")
        return sum(a * b for a, b in zip(self.coordinates, other.coordinates))
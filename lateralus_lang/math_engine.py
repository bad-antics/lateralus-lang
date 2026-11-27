class Matrix:
    def __init__(self, data, rows, cols):
        self.data = data
        self.shape = (rows, cols)

    @classmethod
    def from_flat(cls, data, rows, cols):
        if rows <= 0 or cols <= 0:
            raise ValueError("Matrix dimensions must be positive integers.")
        if len(data) != rows * cols:
            raise ValueError(f"Data length ({len(data)}) does not match dimensions {rows}x{cols} ({rows * cols}).")
        
        # Reshape flat data into a 2D list of lists
        nested = [data[i * cols:(i + 1) * cols] for i in range(rows)]
        return cls(nested, rows, cols)
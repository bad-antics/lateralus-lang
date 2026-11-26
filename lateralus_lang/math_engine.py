class Matrix:
    def __init__(self, data):
        if not data or not data[0]:
            raise ValueError("Matrix cannot be empty")
        cols = len(data[0])
        for row in data:
            if len(row) != cols:
                raise ValueError("All rows must have the same length")
        self.data = [list(row) for row in data]
        self.rows = len(self.data)
        self.cols = cols

    @property
    def shape(self):
        return (self.rows, self.cols)

    def __setitem__(self, index, row):
        if not isinstance(index, int):
            raise TypeError("Matrix row index must be an integer")
        if index < 0:
            index += self.rows
        if index < 0 or index >= self.rows:
            raise IndexError("Matrix row index out of range")
        
        row_list = list(row)
        if len(row_list) != self.cols:
            raise ValueError(f"Replacement row must have length {self.cols}, got {len(row_list)}")
        
        self.data[index] = row_list

    def transpose(self):
        new_data = [[self.data[r][c] for r in range(self.rows)] for c in range(self.cols)]
        return Matrix(new_data)
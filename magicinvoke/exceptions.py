class SaveReturnvalueError(Exception):
    """Failed to save the return-value of a disk-cached function."""

    # Returnvalue to avoid mistaking for a ..ValueError
    pass


class DerivingArgsError(Exception):
    pass

# TODO: cannot use this

def find_stationary(times: list[int], averages: list[float], epsilon: float, epochs: int) -> int | None:
    """Devuelve el primer t a partir del cual la serie queda a menos de epsilon de la media del sufijo. `epochs` es la longitud mínima de ese sufijo.
    """
    if epsilon < 0:
        raise ValueError("epsilon debe ser no negativo")
    if epochs < 1:
        raise ValueError("epochs debe ser al menos 1")

    length = len(averages)
    if length < epochs:
        return None
    for index in range(length - epochs + 1):
        rest = averages[index:]
        suffix_mean = sum(rest) / len(rest)
        if all(abs(value - suffix_mean) <= epsilon for value in rest):
            return times[index]
    return None

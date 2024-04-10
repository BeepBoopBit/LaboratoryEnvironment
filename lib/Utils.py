# Helper Function to print if verbose is set
def print_if_verbose(_verbose, _type, _from, _message):
    if _from is None:
        _from = ""

    if _verbose == 1:
        print(f"[{_type}.{_from}] {_message}")

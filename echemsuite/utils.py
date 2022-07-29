def deprecation_warning(old: str, new: str = "") -> None:
    """
    Print a worning to the terminal informing the user that the called function will be discontinued
    in the upcoming versions of the code.

        Parameters
        ----------
            old : str
                name of the obsolete object
            new : str
                name of the object that will substitute the obsolete function
    """
    print(
        f"\u001b[35;1mWARNING\u001b[0m: the object '{old}' is being deprecated and will no longer be available in future releases!"
    )

    if new != "":
        print(
            f" -> SOLUTION: Please update your script and replace all occurrences of '{old}' with the new '{new}' object."
        )

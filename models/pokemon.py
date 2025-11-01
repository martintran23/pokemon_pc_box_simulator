class Pokemon:
    def __init__(self, name, level, type_):
        """
        Represents a Pokémon with basic info.
        """
        self.name = name
        self.level = level
        self.type_ = type_

    def summary(self):
        """
        Returns a formatted string summary of the Pokémon's data.
        """
        return f"{self.name}\nLv.{self.level}\nType: {self.type_}"
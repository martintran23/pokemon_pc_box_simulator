class PCBox:
    def __init__(self, name="Box 1", capacity=30):
        """
        Represents a single PC Box that can store Pokémon.
        """
        self.name = name
        self.capacity = capacity
        self.pokemon = [None] * capacity  # 30 slots by default

    def add_pokemon(self, pokemon, slot):
        """
        Adds a Pokémon to a specific slot in the box.
        """
        if 0 <= slot < self.capacity:
            self.pokemon[slot] = pokemon
        else:
            raise IndexError("Invalid box slot number.")

    def remove_pokemon(self, slot):
        """
        Removes a Pokémon from a specific slot.
        """
        if 0 <= slot < self.capacity:
            self.pokemon[slot] = None
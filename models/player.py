from .box import PCBox

class Player:
    def __init__(self):
        """
        Represents the player and their stored Pokémon.
        """
        self.party = [None] * 6  # Player's active team
        self.boxes = [PCBox(f"Box {i+1}") for i in range(3)]  # 3 boxes for now
        self.current_box = 0     # Which box the player is currently viewing

    def get_current_box(self):
        """
        Returns the currently active PC box.
        """
        return self.boxes[self.current_box]
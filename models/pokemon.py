class Pokemon:
    def __init__(self, name, level, ptype, sprite=None, moves=None, item=None):
        self.name = name
        self.level = level
        self.ptype = ptype
        self.sprite = sprite or f"assets/sprites/{self.name.lower()}.png"
        self.moves = moves or []  # default empty list
        self.item = item  # default None

    def summary(self):
        move_list = "\n".join(self.moves) if self.moves else "No moves"
        item_info = self.item if self.item else "None"
        return (
            f"Name: {self.name}\n"
            f"Level: {self.level}\n"
            f"Type: {self.ptype}\n"
            f"Item: {item_info}\n"
            f"Moves:\n{move_list}"
        )

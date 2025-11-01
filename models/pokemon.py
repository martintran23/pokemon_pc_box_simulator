class Pokemon:
    def __init__(self, name, level, ptype, sprite=None):
        self.name = name
        self.level = level
        self.ptype = ptype
        self.sprite = sprite or f"assets/sprites/{self.name.lower()}.png"

    def summary(self):
        return f"{self.name} (Lvl {self.level}) - Type: {self.ptype}"
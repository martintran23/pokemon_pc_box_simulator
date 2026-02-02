class Pokemon:
    def __init__(
        self,
        name,
        level,
        ptype,
        sprite=None,
        moves=None,
        item=None,
        alt_form_name=None,
        alt_sprite=None,
    ):
        self.name = name
        self.level = level
        self.ptype = ptype

        # Base form sprite
        self.sprite = sprite or f"assets/sprites/{self.name.lower()}.png"

        self.moves = moves or []
        self.item = item

        # Alternate form (optional)
        self.alt_form_name = alt_form_name      # e.g. "Mega", "Gigantamax"
        self.alt_sprite = alt_sprite            # path string or None

    def get_sprite_path(self, show_alt=False):
        """Returns the correct sprite path based on form toggle."""
        if show_alt and self.alt_sprite:
            return self.alt_sprite
        return self.sprite

    def summary(self, show_alt=False):
        move_list = "\n".join(self.moves) if self.moves else "No moves"
        item_info = self.item if self.item else "None"

        form_info = ""
        if self.alt_form_name:
            form_info = f"\nAlternate Form: {self.alt_form_name}"

        return (
            f"Name: {self.name}\n"
            f"Level: {self.level}\n"
            f"Type: {self.ptype}\n"
            f"Item: {item_info}"
            f"{form_info}\n"
            f"Moves:\n{move_list}"
        )

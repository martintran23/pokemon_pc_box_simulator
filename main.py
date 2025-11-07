import tkinter as tk
from tkinter import messagebox, simpledialog
from PIL import Image, ImageTk, ImageDraw
import json, os

from models.pokemon import Pokemon
from models.box import PCBox
from models.player import Player

SAVE_PATH = "data/save.json"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class PCApp(tk.Tk):
    def __init__(self, player):
        super().__init__()
        self.title("Pokémon PC Box System")
        self.geometry("850x600")
        self.resizable(False, False)

        self.player = player
        self.drag_data = {"widget": None, "pokemon": None, "origin_index": None, "origin_area": None, "floating": None}

        # --- Load images ---
        bg_path = os.path.join(BASE_DIR, "assets", "bg", "box_bg.png")
        try:
            bg_raw = Image.open(bg_path).resize((650, 550))
            self.bg_image = ImageTk.PhotoImage(bg_raw)
        except Exception:
            # fallback plain background
            tmp = Image.new("RGBA", (650, 550), (255, 255, 255, 255))
            self.bg_image = ImageTk.PhotoImage(tmp)

        add_icon_path = os.path.join(BASE_DIR, "assets", "icons", "add_icon.png")
        if os.path.exists(add_icon_path):
            self.add_icon = ImageTk.PhotoImage(Image.open(add_icon_path).resize((60, 60)))
        else:
            # Draw a fallback plus icon so app still runs if missing
            temp_img = Image.new("RGBA", (60, 60), (240, 240, 240, 255))
            draw = ImageDraw.Draw(temp_img)
            draw.line((30, 8, 30, 52), fill=(200, 0, 0), width=6)
            draw.line((8, 30, 52, 30), fill=(200, 0, 0), width=6)
            self.add_icon = ImageTk.PhotoImage(temp_img)

        # Sprite cache
        self.sprite_cache = {}

        # Ensure player has 3 boxes (backwards-safe)
        while len(player.boxes) < 3:
            player.boxes.append(PCBox(f"Box {len(player.boxes) + 1}"))

        self.create_widgets()
        self.load_game()
        self.update_display()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------------- Widgets ----------------
    def create_widgets(self):
        # Left: Party
        self.party_frame = tk.Frame(self, bg="#f0f0f0", width=200)
        self.party_frame.pack(side="left", fill="y")

        tk.Label(
            self.party_frame, text="Your Party", font=("Arial", 14, "bold"), bg="#f0f0f0"
        ).pack(pady=10)

        self.party_labels = []
        for i in range(6):
            lbl = tk.Label(
                self.party_frame,
                text="(empty)",
                width=20,
                height=2,
                bd=2,
                relief="raised",
                bg="#ffffff",
                compound="top",
            )
            lbl.pack(pady=5)
            # binds
            lbl.bind("<Button-1>", lambda e, i=i: self.start_drag(e, "party", i))
            lbl.bind("<ButtonRelease-1>", self.end_drag)
            lbl.bind("<Button-3>", lambda e, i=i: self.right_click("party", i))
            self.party_labels.append(lbl)

        # Right: PC Box Area
        self.pc_area = tk.Frame(self, bg="#ff9b9b")
        self.pc_area.pack(side="right", expand=True, fill="both")

        self.box_frame = tk.Frame(self.pc_area, bg="#ff9b9b", padx=20, pady=20)
        self.box_frame.pack(expand=True)

        self.box_canvas = tk.Canvas(
            self.box_frame, width=650, height=550, highlightthickness=0, bg="#ffffff"
        )
        self.box_canvas.pack()
        self.box_canvas.create_image(0, 0, anchor="nw", image=self.bg_image)

        # 30 slot labels (used like buttons)
        self.slot_buttons = []
        self.slot_positions = []
        start_x, start_y = 60, 60
        gap_x, gap_y = 90, 85
        for i in range(30):
            x = start_x + (i % 6) * gap_x
            y = start_y + (i // 6) * gap_y
            btn = tk.Label(self.box_canvas, image=self.add_icon, bd=2, relief="raised", bg="#ffffff", compound="top")
            self.box_canvas.create_window(x, y, anchor="nw", window=btn)
            btn.bind("<Button-1>", lambda e, i=i: self.start_drag(e, "box", i))
            btn.bind("<ButtonRelease-1>", self.end_drag)
            btn.bind("<Button-3>", lambda e, i=i: self.right_click("box", i))
            self.slot_buttons.append(btn)
            self.slot_positions.append((x, y))

        # Navigation buttons
        nav_frame = tk.Frame(self.box_frame, bg="#ff9b9b")
        nav_frame.pack(pady=10)
        tk.Button(nav_frame, text="< Prev", command=self.prev_box).grid(row=0, column=0, padx=10)
        self.box_name_lbl = tk.Label(nav_frame, text="", bg="#ff9b9b", font=("Arial", 12, "bold"))
        self.box_name_lbl.grid(row=0, column=1)
        tk.Button(nav_frame, text="Next >", command=self.next_box).grid(row=0, column=2, padx=10)

    # ---------------- Save/Load ----------------
    def save_game(self):
        data = {
            "party": [mon.__dict__ if mon else None for mon in self.player.party],
            "boxes": [
                [mon.__dict__ if mon else None for mon in box.pokemon]
                for box in self.player.boxes
            ],
            "current_box": getattr(self.player, "current_box", 0),
        }
        os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
        try:
            with open(SAVE_PATH, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print("⚠️ Failed to save:", e)

    def load_game(self):
        if not os.path.exists(SAVE_PATH):
            return
        try:
            with open(SAVE_PATH, "r") as f:
                content = f.read().strip()
                if not content:
                    print("⚠️ Empty save file, starting fresh.")
                    return
                data = json.loads(content)
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠️ Failed to load save: {e}")
            return

        # party
        self.player.party = [
            Pokemon(**mon) if mon else None for mon in data.get("party", [])
        ]

        # boxes
        for i, box_data in enumerate(data.get("boxes", [])):
            if i < len(self.player.boxes):
                self.player.boxes[i].pokemon = [
                    Pokemon(**mon) if mon else None for mon in box_data
                ]

        # current box index
        self.player.current_box = data.get("current_box", 0)

    def on_close(self):
        self.save_game()
        self.destroy()

    # ---------------- Sprite Loader ----------------
    def get_sprite(self, pokemon, size=(60, 60)):
        if not pokemon:
            return self.add_icon
        key = f"{pokemon.name}_{size[0]}x{size[1]}"
        if key in self.sprite_cache:
            return self.sprite_cache[key]
        try:
            img_path = pokemon.sprite
            # if path is relative, make absolute relative to BASE_DIR
            if not os.path.isabs(img_path):
                img_path = os.path.join(BASE_DIR, img_path)
            if not os.path.exists(img_path):
                # try default sprite path
                alt = os.path.join(BASE_DIR, "assets", "sprites", f"{pokemon.name.lower()}.png")
                if os.path.exists(alt):
                    img_path = alt
                else:
                    print(f"⚠️ Sprite not found for {pokemon.name}: {img_path}")
                    return self.add_icon
            img_raw = Image.open(img_path).convert("RGBA")
            img_raw = img_raw.resize(size, Image.Resampling.LANCZOS)
            img = ImageTk.PhotoImage(img_raw)
            self.sprite_cache[key] = img
            return img
        except Exception as e:
            print(f"⚠️ Failed to load sprite for {pokemon.name}: {e}")
            return self.add_icon

    # ---------------- Update Display ----------------
    def update_display(self):
        # Party
        for i, mon in enumerate(self.player.party):
            sprite_img = self.get_sprite(mon)
            self.party_labels[i].image = sprite_img
            # show name under sprite if present
            if mon:
                self.party_labels[i].config(text=mon.name, image=sprite_img)
            else:
                self.party_labels[i].config(text="(empty)", image=sprite_img)

        # Box
        box = self.player.get_current_box()
        if box:
            self.box_name_lbl.config(text=box.name)
            for i, mon in enumerate(box.pokemon):
                sprite_img = self.get_sprite(mon)
                self.slot_buttons[i].image = sprite_img
                if mon:
                    self.slot_buttons[i].config(text=mon.name, image=sprite_img)
                else:
                    self.slot_buttons[i].config(text="", image=sprite_img)

    # ---------------- Pokémon Actions ----------------
    def add_pokemon(self, index, area="box"):
        name = simpledialog.askstring("Add Pokémon", "Enter Pokémon name:")
        if not name:
            return
        level = simpledialog.askinteger("Level", "Enter level:", minvalue=1, maxvalue=100)
        ptype = simpledialog.askstring("Type", "Enter type:")
        sprite_filename = simpledialog.askstring(
            "Sprite Filename", "Optional: enter sprite filename (e.g., bulbasaur.png):"
        )
        item = simpledialog.askstring("Held Item", "Optional: enter held item:")

        moves = []
        for i in range(4):
            move = simpledialog.askstring("Move", f"Enter move {i+1} (leave blank to skip):")
            if move:
                moves.append(move)

        if name and level and ptype:
            sprite_path = os.path.join("assets", "sprites", sprite_filename) if sprite_filename else os.path.join("assets", "sprites", f"{name.lower()}.png")
            new_mon = Pokemon(name, level, ptype, sprite=sprite_path, moves=moves, item=item)

            if area == "box":
                box = self.player.get_current_box()
                if box:
                    box.add_pokemon(new_mon, index)
            else:
                # ensure party length
                while len(self.player.party) < 6:
                    self.player.party.append(None)
                self.player.party[index] = new_mon

            self.update_display()
            self.save_game()

    def remove_pokemon(self, index, area="box"):
        if area == "box":
            box = self.player.get_current_box()
            mon = box.pokemon[index]
            if not mon:
                return
            confirm = messagebox.askyesno("Remove Pokémon", f"Release {mon.name}?")
            if confirm:
                box.remove_pokemon(index)
        else:
            mon = self.player.party[index]
            if not mon:
                return
            confirm = messagebox.askyesno("Remove Pokémon", f"Release {mon.name}?")
            if confirm:
                self.player.party[index] = None
        self.update_display()
        self.save_game()

    # ---------------- Info (view only) ----------------
    def show_pokemon(self, area, index):
        mon = self.player.party[index] if area == "party" else self.player.get_current_box().pokemon[index]
        if mon:
            summary = f"{mon.name} (Lvl {mon.level}) - Type: {mon.ptype}"
            if hasattr(mon, "item") and mon.item:
                summary += f"\nHeld Item: {mon.item}"
            if hasattr(mon, "moves") and mon.moves:
                summary += "\nMoves:\n" + "\n".join(f"- {move}" for move in mon.moves)
            messagebox.showinfo("Pokémon Info", summary)
        else:
            messagebox.showinfo("Empty Slot", "No Pokémon here!")

    # ---------------- Edit popup (single-window editor) ----------------
    def edit_pokemon(self, area, index):
        mon = self.player.party[index] if area == "party" else self.player.get_current_box().pokemon[index]
        if not mon:
            messagebox.showinfo("Empty Slot", "No Pokémon here!")
            return

        # Create edit window
        win = tk.Toplevel(self)
        win.title(f"Edit {mon.name}")
        win.resizable(False, False)

        # Basic info frame
        basic_frame = tk.Frame(win, padx=10, pady=8)
        basic_frame.pack(fill="x")
        tk.Label(basic_frame, text="Name:").grid(row=0, column=0, sticky="w")
        name_entry = tk.Entry(basic_frame)
        name_entry.insert(0, mon.name)
        name_entry.grid(row=0, column=1, sticky="ew", padx=6)

        tk.Label(basic_frame, text="Level:").grid(row=1, column=0, sticky="w")
        level_entry = tk.Entry(basic_frame)
        level_entry.insert(0, str(mon.level))
        level_entry.grid(row=1, column=1, sticky="ew", padx=6)

        tk.Label(basic_frame, text="Type:").grid(row=2, column=0, sticky="w")
        type_entry = tk.Entry(basic_frame)
        type_entry.insert(0, mon.ptype)
        type_entry.grid(row=2, column=1, sticky="ew", padx=6)

        basic_frame.columnconfigure(1, weight=1)

        # Sprite preview (if available)
        sprite_frame = tk.Frame(win, padx=10, pady=6)
        sprite_frame.pack(fill="x")
        tk.Label(sprite_frame, text="Sprite Preview:").pack(anchor="w")
        try:
            preview_img = self.get_sprite(mon, size=(96, 96))
            preview_lbl = tk.Label(sprite_frame, image=preview_img)
            preview_lbl.image = preview_img
            preview_lbl.pack(pady=4)
        except Exception:
            tk.Label(sprite_frame, text="[no sprite]").pack()

        # Moves editor
        moves_frame = tk.Frame(win, padx=10, pady=6)
        moves_frame.pack(fill="x")
        tk.Label(moves_frame, text="Moves (up to 4):").pack(anchor="w")
        move_entries = []
        # ensure mon.moves has up to 4 elements
        while len(mon.moves) < 4:
            mon.moves.append("")
        for i in range(4):
            ent = tk.Entry(moves_frame, width=30)
            ent.insert(0, mon.moves[i])
            ent.pack(pady=2)
            move_entries.append(ent)

        # Held item
        item_frame = tk.Frame(win, padx=10, pady=6)
        item_frame.pack(fill="x")
        tk.Label(item_frame, text="Held Item:").pack(anchor="w")
        item_entry = tk.Entry(item_frame, width=30)
        item_entry.insert(0, mon.item if getattr(mon, "item", None) else "")
        item_entry.pack(pady=4)

        # Buttons
        btn_frame = tk.Frame(win, pady=8)
        btn_frame.pack(fill="x")
        def on_save():
            # validate and save
            new_name = name_entry.get().strip()
            if new_name:
                mon.name = new_name
            try:
                mon.level = int(level_entry.get())
            except Exception:
                mon.level = mon.level  # keep old if invalid
            mon.ptype = type_entry.get().strip()
            # moves: keep exactly 4 entries (store non-empty only or all? keep as list of non-empty)
            new_moves = [e.get().strip() for e in move_entries if e.get().strip()]
            mon.moves = new_moves
            new_item = item_entry.get().strip()
            mon.item = new_item if new_item != "" else None

            self.update_display()
            self.save_game()
            win.destroy()

        def on_cancel():
            win.destroy()

        tk.Button(btn_frame, text="Save", command=on_save, bg="#4CAF50", fg="white").pack(side="left", padx=8)
        tk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side="right", padx=8)

        win.transient(self)
        win.grab_set()
        self.wait_window(win)

    # ---------------- Drag and Drop ----------------
    def start_drag(self, event, area, index):
        widget = event.widget
        mon = self.player.party[index] if area == "party" else self.player.get_current_box().pokemon[index]
        if not mon:
            # If empty, allow adding Pokémon
            self.add_pokemon(index, area)
            return

        sprite_img = self.get_sprite(mon, size=(60, 60))

        # Floating image under cursor
        floating = tk.Toplevel(self)
        floating.overrideredirect(True)
        floating.attributes("-topmost", True)
        lbl = tk.Label(floating, image=sprite_img, bg="white")
        lbl.pack()
        x_root = self.winfo_pointerx() - 30
        y_root = self.winfo_pointery() - 30
        floating.geometry(f"+{x_root}+{y_root}")

        self.drag_data = {
            "widget": widget,
            "pokemon": mon,
            "origin_index": index,
            "origin_area": area,
            "floating": floating
        }

        self.bind("<Motion>", self.on_motion)

    def on_motion(self, event):
        floating = self.drag_data.get("floating")
        if not floating:
            return
        x_root = self.winfo_pointerx() - 30
        y_root = self.winfo_pointery() - 30
        floating.geometry(f"+{x_root}+{y_root}")

    def end_drag(self, event):
        floating = self.drag_data.get("floating")
        if not floating:
            return

        x_root = self.winfo_pointerx()
        y_root = self.winfo_pointery()

        target_index = None
        target_area = None

        # Check party slots
        for i, lbl in enumerate(self.party_labels):
            x1, y1 = lbl.winfo_rootx(), lbl.winfo_rooty()
            x2, y2 = x1 + lbl.winfo_width(), y1 + lbl.winfo_height()
            if x1 <= x_root <= x2 and y1 <= y_root <= y2:
                target_index = i
                target_area = "party"
                break

        # Check box slots
        if target_index is None:
            for i, lbl in enumerate(self.slot_buttons):
                x1, y1 = lbl.winfo_rootx(), lbl.winfo_rooty()
                x2, y2 = x1 + lbl.winfo_width(), y1 + lbl.winfo_height()
                if x1 <= x_root <= x2 and y1 <= y_root <= y2:
                    target_index = i
                    target_area = "box"
                    break

        origin_area = self.drag_data["origin_area"]
        origin_index = self.drag_data["origin_index"]
        mon = self.drag_data["pokemon"]

        # Swap only if valid target
        if target_area is not None:
            if target_area == "party":
                target_list = self.player.party
            else:
                target_list = self.player.get_current_box().pokemon
            if origin_area == "party":
                origin_list = self.player.party
            else:
                origin_list = self.player.get_current_box().pokemon
            # perform swap
            target_list[target_index], origin_list[origin_index] = origin_list[origin_index], target_list[target_index]

        floating.destroy()
        self.drag_data = {"widget": None, "pokemon": None, "origin_index": None, "origin_area": None, "floating": None}
        self.unbind("<Motion>")
        self.update_display()
        self.save_game()

    def right_click(self, area, index):
        mon = self.player.party[index] if area == "party" else self.player.get_current_box().pokemon[index]
        if mon:
            # custom menu dialog to choose Info, Release, or Edit
            choice = messagebox.askquestion(
                "Pokémon Action",
                "What do you want to do?\nYes = Info  |  No = Release  |  Cancel = Edit",
                icon="question",
                type="yesnocancel",
                default="yes",
            )
            if choice == "yes":
                self.show_pokemon(area, index)
            elif choice == "no":
                self.remove_pokemon(index, area)
            else:  # Cancel -> Edit
                self.edit_pokemon(area, index)

    # ---------------- Box Navigation ----------------
    def next_box(self):
        self.player.current_box = (self.player.current_box + 1) % len(self.player.boxes)
        self.update_display()
        self.save_game()

    def prev_box(self):
        self.player.current_box = (self.player.current_box - 1) % len(self.player.boxes)
        self.update_display()
        self.save_game()


# --- MAIN ---
if __name__ == "__main__":
    player = Player()
    app = PCApp(player)
    app.mainloop()

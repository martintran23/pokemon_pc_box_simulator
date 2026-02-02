import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
from PIL import Image, ImageTk, ImageDraw
import json, os

from models.pokemon import Pokemon
from models.box import PCBox
from models.player import Player

SAVE_PATH = "data/save.json"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SPRITE_DIR = "assets/sprites/"

# Level bounds (change if desired)
MIN_LEVEL = 1
MAX_LEVEL = 100


class PCApp(tk.Tk):
    def __init__(self, player):
        super().__init__()
        self.title("Pokémon PC Box System")
        self.geometry("900x700")
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
                bd=2,
                relief="raised",
                bg="#ffffff",
                compound="top",
            )
            lbl.config(width=75, height=75)
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
        start_x, start_y = 50, 50
        gap_x, gap_y = 100, 90
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
            img_path = pokemon.get_sprite_path(show_alt=False)
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

    def get_display_sprite(self, mon, size=(96, 96), use_alt=False):
        """
        Returns a Tkinter PhotoImage for the Pokémon.
        If use_alt is True and mon.alt_sprite exists, returns the alternate sprite.
        """
        from PIL import Image, ImageTk

        path = mon.alt_sprite if use_alt and mon.alt_sprite else getattr(mon, "sprite", None)
        if not path:
            raise FileNotFoundError("No sprite available")
        img = Image.open(path).resize(size, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(img)

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

    def ask_field(self, title, prompt, required=False, to_int=False, min_val=None, max_val=None, **kwargs):
        """
        Unified input dialog with optional integer conversion and bounds.
        Accepts:
        - required: bool (re-ask until non-empty)
        - to_int: bool (convert input -> int)
        - min_val / max_val: numeric bounds
        Also accepts alias names min_value / max_value via kwargs so old calls won't break.
        Returns:
        - int (if to_int True and valid)
        - str (if to_int False)
        - None if user cancels
        """
        import tkinter.simpledialog as sd
        import tkinter.messagebox as mb

        # support alternate alias names
        if min_val is None and "min_value" in kwargs:
            min_val = kwargs.get("min_value")
        if max_val is None and "max_value" in kwargs:
            max_val = kwargs.get("max_value")

        while True:
            value = sd.askstring(title, prompt, parent=self)
            if value is None:
                # user pressed Cancel
                return None

            # trim
            v = value.strip()

            if required and v == "":
                mb.showerror("Error", "This field is required.")
                continue

            if to_int:
                if v == "":
                    # empty not allowed for required integers
                    if required:
                        mb.showerror("Error", "This field is required and must be an integer.")
                        continue
                    else:
                        return ""  # allow empty if not required (caller must handle)
                try:
                    iv = int(v)
                except ValueError:
                    mb.showerror("Error", "Please enter a valid integer.")
                    continue

                if (min_val is not None) and (iv < min_val):
                    mb.showerror("Error", f"Value must be ≥ {min_val}.")
                    continue
                if (max_val is not None) and (iv > max_val):
                    mb.showerror("Error", f"Value must be ≤ {max_val}.")
                    continue

                return iv

            # not integer mode: return stripped string (could be empty if allowed)
            return v

    # ---------------- Pokémon Actions ----------------
    def add_pokemon(self, index, area="box"):
        # name (required)
        name = self.ask_field("Add Pokémon", "Enter Pokémon name:", required=True)
        if name is None:
            return  # cancelled

        # level (required int, with bounds)
        level = self.ask_field(
            "Level",
            f"Enter level ({MIN_LEVEL}-{MAX_LEVEL}):",
            required=True,
            to_int=True,
            min_val=MIN_LEVEL,
            max_val=MAX_LEVEL,
        )
        if level is None:
            return  # cancelled

        # type (required)
        ptype = self.ask_field("Type", "Enter type(s) (e.g. 'Grass' or 'Grass,Poison'):", required=True)
        if ptype is None:
            return

        # sprite optional
        sprite_filename = self.ask_field("Sprite", "Optional: enter sprite filename (e.g., bulbasaur.png):", required=False)
        if sprite_filename is None:
            return  # cancelled

        # item optional
        item = self.ask_field("Held Item", "Optional: enter held item:", required=False)
        if item is None:
            return  # cancelled

        # moves (4 optional)
        moves = []
        for i in range(4):
            mv = self.ask_field("Move", f"Enter move {i+1} (leave blank to skip):", required=False)
            if mv is None:
                return  # cancelled
            if mv != "":
                moves.append(mv)

        sprite_path = os.path.join("assets", "sprites", sprite_filename) if sprite_filename else os.path.join("assets", "sprites", f"{name.lower()}.png")
        new_mon = Pokemon(name, level, ptype, sprite=sprite_path, moves=moves, item=item)
        if area == "box":
            box = self.player.get_current_box()
            if box:
                box.add_pokemon(new_mon, index)
        else:
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
        if not mon:
            messagebox.showinfo("Empty Slot", "No Pokémon here!")
            return

        win = tk.Toplevel(self)
        win.title(f"{mon.name} Info")
        win.resizable(False, False)

        # ---- Basic Info ----
        basic_frame = tk.Frame(win, padx=10, pady=8)
        basic_frame.pack(fill="x")

        tk.Label(basic_frame, text="Name:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(basic_frame, text=mon.name).grid(row=0, column=1, sticky="w", padx=6)

        tk.Label(basic_frame, text="Level:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w")
        tk.Label(basic_frame, text=str(mon.level)).grid(row=1, column=1, sticky="w", padx=6)

        tk.Label(basic_frame, text="Type:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="w")
        tk.Label(basic_frame, text=mon.ptype).grid(row=2, column=1, sticky="w", padx=6)

        # ---- Sprite Preview ----
        sprite_frame = tk.Frame(win, padx=10, pady=6)
        sprite_frame.pack(fill="x")
        tk.Label(sprite_frame, text="Sprite Preview:", font=("Arial", 10, "bold")).pack(anchor="w")

        try:
            img = self.get_sprite(mon, size=(96, 96))
            lbl = tk.Label(sprite_frame, image=img)
            lbl.image = img
            lbl.pack(pady=4)
        except Exception:
            tk.Label(sprite_frame, text="[No sprite]").pack()

        # ---- Moves ----
        moves_frame = tk.Frame(win, padx=10, pady=6)
        moves_frame.pack(fill="x")
        tk.Label(moves_frame, text="Moves:", font=("Arial", 10, "bold")).pack(anchor="w")

        if mon.moves:
            for mv in mon.moves:
                tk.Label(moves_frame, text=f"• {mv}").pack(anchor="w")
        else:
            tk.Label(moves_frame, text="(No moves)").pack(anchor="w")

        # ---- Held Item ----
        item_frame = tk.Frame(win, padx=10, pady=6)
        item_frame.pack(fill="x")
        tk.Label(item_frame, text="Held Item:", font=("Arial", 10, "bold")).pack(anchor="w")
        tk.Label(item_frame, text=mon.item if mon.item else "(None)").pack(anchor="w")

        # ---- Close Button ----
        btn_frame = tk.Frame(win, pady=10)
        btn_frame.pack(fill="x")
        tk.Button(btn_frame, text="Close", command=win.destroy).pack()

        win.transient(self)
        win.grab_set()
        self.wait_window(win)

    # ---------------- Edit popup (single-window editor) ----------------
    def edit_pokemon(self, area, index):
        mon = self.player.party[index] if area == "party" else self.player.get_current_box().pokemon[index]
        if not mon:
            messagebox.showinfo("Empty Slot", "No Pokémon here!")
            return

        # Ensure alt attributes exist (safe for old saves)
        if not hasattr(mon, "alt_form_name"):
            mon.alt_form_name = None
        if not hasattr(mon, "alt_sprite"):
            mon.alt_sprite = None

        # Create edit window
        win = tk.Toplevel(self)
        win.title(f"Edit {mon.name}")
        win.resizable(False, False)

        # =====================
        # Basic info frame
        # =====================
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

        # =====================
        # Sprite preview (BASE + ALT toggle)
        # =====================
        sprite_frame = tk.Frame(win, padx=10, pady=6)
        sprite_frame.pack(fill="x")
        tk.Label(sprite_frame, text="Sprite Preview:").pack(anchor="w")

        show_alt = tk.BooleanVar(value=False)

        def update_preview():
            use_alt = show_alt.get() and mon.alt_sprite
            sprite_path = mon.alt_sprite if use_alt else mon.sprite

            # Normalize the path
            if not os.path.isabs(sprite_path):
                if os.path.exists(sprite_path):
                    # already a valid relative path
                    full_path = sprite_path
                else:
                    # prepend sprites folder
                    full_path = os.path.join(SPRITE_DIR, os.path.basename(sprite_path))
            else:
                full_path = sprite_path

            try:
                from PIL import Image, ImageTk
                img = Image.open(full_path).resize((96, 96), Image.Resampling.LANCZOS)
                tk_img = ImageTk.PhotoImage(img)
                sprite_label.config(image=tk_img, text="")
                sprite_label.image = tk_img
            except FileNotFoundError:
                sprite_label.config(text="[Sprite not found]", image="")
            except Exception as e:
                sprite_label.config(text=f"[Error: {e}]", image="")

        # Initial preview
        sprite_label = tk.Label(sprite_frame)
        sprite_label.pack(pady=4)
        update_preview()

        if mon.alt_sprite:
            tk.Checkbutton(
                sprite_frame,
                text=f"Show {mon.alt_form_name}",
                variable=show_alt,
                command=update_preview
            ).pack()

        # =====================
        # Alternate Form Editor (NEW)
        # =====================
        alt_frame = tk.LabelFrame(win, text="Alternate Form", padx=10, pady=6)
        alt_frame.pack(fill="x", padx=10, pady=4)

        tk.Label(alt_frame, text="Form Name:").grid(row=0, column=0, sticky="w")
        alt_name_entry = tk.Entry(alt_frame)
        alt_name_entry.insert(0, mon.alt_form_name or "")
        alt_name_entry.grid(row=0, column=1, sticky="ew", padx=6)

        def choose_alt_sprite():
            filename = simpledialog.askstring("Alternate Sprite", "Enter sprite filename (e.g., pikachu.png):")
            if not filename:
                return
            mon.alt_sprite = filename  # store filename only, folder handled in update_preview()
            mon.alt_form_name = alt_name_entry.get().strip() or "Alternate Form"
            show_alt.set(True)
            update_preview()

        tk.Button(
            alt_frame,
            text="Set Alt Sprite",
            command=choose_alt_sprite
        ).grid(row=1, column=0, columnspan=2, pady=4)

        alt_frame.columnconfigure(1, weight=1)

        # =====================
        # Moves editor
        # =====================
        moves_frame = tk.Frame(win, padx=10, pady=6)
        moves_frame.pack(fill="x")
        tk.Label(moves_frame, text="Moves (up to 4):").pack(anchor="w")

        move_entries = []
        while len(mon.moves) < 4:
            mon.moves.append("")

        for i in range(4):
            ent = tk.Entry(moves_frame, width=30)
            ent.insert(0, mon.moves[i])
            ent.pack(pady=2)
            move_entries.append(ent)

        # =====================
        # Held item
        # =====================
        item_frame = tk.Frame(win, padx=10, pady=6)
        item_frame.pack(fill="x")
        tk.Label(item_frame, text="Held Item:").pack(anchor="w")
        item_entry = tk.Entry(item_frame, width=30)
        item_entry.insert(0, mon.item if getattr(mon, "item", None) else "")
        item_entry.pack(pady=4)

        # =====================
        # Buttons
        # =====================
        btn_frame = tk.Frame(win, pady=8)
        btn_frame.pack(fill="x")

        def on_save():
            new_name = name_entry.get().strip()
            if new_name:
                mon.name = new_name

            try:
                lvl_val = int(level_entry.get().strip())
            except ValueError:
                messagebox.showerror("Invalid Level", "Level must be an integer.")
                return

            if not (MIN_LEVEL <= lvl_val <= MAX_LEVEL):
                messagebox.showerror("Invalid Level", f"Level must be {MIN_LEVEL}–{MAX_LEVEL}.")
                return

            mon.level = lvl_val

            new_type = type_entry.get().strip()
            if not new_type:
                messagebox.showerror("Invalid Type", "You must enter at least one type.")
                return
            mon.ptype = new_type

            mon.moves = [e.get().strip() for e in move_entries if e.get().strip()]
            mon.item = item_entry.get().strip() or None
            mon.alt_form_name = alt_name_entry.get().strip() or mon.alt_form_name

            self.update_display()
            self.save_game()
            win.destroy()

        tk.Button(btn_frame, text="Save", command=on_save, bg="#4CAF50", fg="white").pack(side="left", padx=8)
        tk.Button(btn_frame, text="Cancel", command=win.destroy).pack(side="right", padx=8)

        win.transient(self)
        win.grab_set()
        self.wait_window(win)

    # ---------------- Drag and Drop ----------------
    def start_drag(self, event, area, index):
        widget = event.widget
        mon = self.player.party[index] if area == "party" else self.player.get_current_box().pokemon[index]
        if not mon:
            self.add_pokemon(index, area)
            return

        sprite_img = self.get_sprite(mon, size=(60, 60))
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

        for i, lbl in enumerate(self.party_labels):
            x1, y1 = lbl.winfo_rootx(), lbl.winfo_rooty()
            x2, y2 = x1 + lbl.winfo_width(), y1 + lbl.winfo_height()
            if x1 <= x_root <= x2 and y1 <= y_root <= y2:
                target_index = i
                target_area = "party"
                break

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

        if target_area is not None:
            if target_area == "party":
                target_list = self.player.party
            else:
                target_list = self.player.get_current_box().pokemon
            if origin_area == "party":
                origin_list = self.player.party
            else:
                origin_list = self.player.get_current_box().pokemon
            target_list[target_index], origin_list[origin_index] = origin_list[origin_index], target_list[target_index]

        floating.destroy()
        self.drag_data = {"widget": None, "pokemon": None, "origin_index": None, "origin_area": None, "floating": None}
        self.unbind("<Motion>")
        self.update_display()
        self.save_game()

    def right_click(self, area, index):
        mon = self.player.party[index] if area == "party" else self.player.get_current_box().pokemon[index]
        if mon:
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
            else:
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

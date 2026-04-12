import json
import os
import tkinter as tk
import tkinter.messagebox as messagebox
import tkinter.filedialog as filedialog

import customtkinter as ctk

try:
    from PIL import Image as PilImage
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    PilImage = None

from database import (
    create_table, add_character, update_character,
    delete_character, get_all_characters, get_characters_by_type,
    default_attributes,
)
from logic import Encounter, Participant

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# ── Paleta de Cores ──────────────────────────────────────────────────────────
RED_DARK   = "#6B1010"
RED_MID    = "#8B1A1A"
GOLD       = "#C9A84C"
GOLD_LIGHT = "#E8C878"
CARD_BG    = "#16213E"


# ── Utilitários D&D ─────────────────────────────────────────────────────────
def calc_mod(score) -> int:
    try:
        return (int(score) - 10) // 2
    except (ValueError, TypeError):
        return 0


def mod_str(mod: int) -> str:
    return f"+{mod}" if mod >= 0 else str(mod)


# ── Helpers de formulário (reutilizados em várias partes) ───────────────────
def _make_section(parent, title: str):
    """Cabeçalho de seção com linha decorativa vermelha."""
    ctk.CTkLabel(
        parent, text=title,
        font=ctk.CTkFont(size=13, weight="bold"),
        text_color=GOLD,
    ).pack(anchor="w", padx=8, pady=(10, 2))
    ctk.CTkFrame(parent, height=2, fg_color=RED_MID).pack(
        fill="x", padx=8, pady=(0, 6)
    )


def _make_field(parent, label: str, default="",
                trace_fn=None, width=200) -> tk.StringVar:
    """Cria label + Entry e retorna a StringVar associada."""
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", pady=2)
    ctk.CTkLabel(
        row, text=label, width=150, anchor="w",
        font=ctk.CTkFont(size=11),
    ).pack(side="left", padx=(6, 4))
    var = tk.StringVar(value=str(default))
    if trace_fn:
        var.trace_add("write", trace_fn)
    ctk.CTkEntry(row, textvariable=var, width=width).pack(
        side="left", fill="x", expand=True, padx=(0, 6)
    )
    return var


# ════════════════════════════════════════════════════════════════════════════
#  CharacterCard — ficha completa estilo D&D
# ════════════════════════════════════════════════════════════════════════════
class CharacterCard(ctk.CTkScrollableFrame):
    """Exibe a ficha completa de um personagem inspirada na ficha oficial D&D."""

    _ATTR_ORDER = [
        ("FOR", "str",  "str_mod"),
        ("DES", "dex",  "dex_mod"),
        ("CON", "con",  "con_mod"),
        ("INT", "int",  "int_mod"),
        ("SAB", "wis",  "wis_mod"),
        ("CAR", "cha",  "cha_mod"),
    ]

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._char_data = None
        self._show_placeholder()

    def _show_placeholder(self):
        ctk.CTkLabel(
            self,
            text="Selecione um personagem\npara ver a ficha.",
            text_color="gray",
            font=ctk.CTkFont(size=12),
        ).pack(pady=40)

    def clear(self):
        self._char_data = None
        for w in self.winfo_children():
            w.destroy()
        self._show_placeholder()

    def load(self, char_data: dict):
        self._char_data = char_data
        for w in self.winfo_children():
            w.destroy()
        self._build()

    # ── Build ────────────────────────────────────────────────────────────────
    def _build(self):
        c     = self._char_data
        attrs = c.get("attributes", {})

        # ── Cabeçalho ───────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=6, pady=(6, 3))

        ctk.CTkLabel(
            header, text=str(c.get("name", "?")).upper(),
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="white",
        ).pack(anchor="w", padx=4)

        sub_parts = []
        sr = f"{c.get('size', '')} {c.get('race', '')}".strip()
        if sr:
            sub_parts.append(sr)
        if c.get("alignment"):
            sub_parts.append(c["alignment"])
        if sub_parts:
            ctk.CTkLabel(
                header,
                text=" - ".join(sub_parts),
                font=ctk.CTkFont(size=12),
                text_color="#AAAAAA",
            ).pack(anchor="w", padx=4, pady=(0, 8))

        # ── Corpo (Imagem + Status) ─────────────────────────────────────────
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="x", padx=6, pady=4)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        # Imagem (coluna esquerda)
        img_frame = ctk.CTkFrame(body, fg_color="white", corner_radius=8)
        img_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        
        img_path = c.get("image_path", "")
        if img_path and os.path.exists(img_path) and PIL_AVAILABLE:
            try:
                pil = PilImage.open(img_path)
                pil.thumbnail((220, 220))
                ctk_img = ctk.CTkImage(
                    light_image=pil, dark_image=pil, size=pil.size
                )
                lbl = ctk.CTkLabel(img_frame, image=ctk_img, text="")
                lbl.image = ctk_img        # keep reference
                lbl.pack(pady=6, padx=6, expand=True)
            except Exception as e:
                print(f"[CharacterCard] Erro ao carregar imagem: {e}")
                ctk.CTkLabel(img_frame, text="Sem Imagem", text_color="gray").pack(expand=True)
        else:
            ctk.CTkLabel(img_frame, text="Sem Imagem", text_color="gray").pack(expand=True)

        # Status Stack (coluna direita)
        stats_col = ctk.CTkFrame(body, fg_color="transparent")
        stats_col.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        stat_defs = [
            ("🛡️", "Armadura Classe", str(c.get("armor_class", 0)), c.get("armor_desc", "")),
            ("❤️", "Pontos Vida",  str(c.get("hit_points",  0)), c.get("hit_dice",   "")),
            ("👢", "Velocidade",    c.get("speed", "—"),          ""),
        ]
        
        for i, (icon, lbl, val, sub) in enumerate(stat_defs):
            box = ctk.CTkFrame(stats_col, fg_color="#181818", corner_radius=6)
            box.pack(fill="both", expand=True, pady=(0 if i==0 else 6, 0))
            
            # Icon
            ctk.CTkLabel(box, text=icon, font=ctk.CTkFont(size=28)).pack(side="left", padx=12)
            
            # Textos
            text_frame = ctk.CTkFrame(box, fg_color="transparent")
            text_frame.pack(side="left", fill="both", expand=True, pady=8)
            
            ctk.CTkLabel(text_frame, text=lbl, font=ctk.CTkFont(size=11), text_color="#AAAAAA").pack(anchor="w")
            ctk.CTkLabel(text_frame, text=val, font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", pady=(0, 2))
            if sub:
                ctk.CTkLabel(text_frame, text=sub, font=ctk.CTkFont(size=10), text_color="gray").pack(anchor="w")

        # ── Atributos ────────────────────────────────────────────────────────
        ag = ctk.CTkFrame(self, fg_color="transparent")
        ag.pack(fill="x", padx=6, pady=10)

        for col_i, (lbl, k, mk) in enumerate(self._ATTR_ORDER):
            ag.columnconfigure(col_i, weight=1)
            val = attrs.get(k, 10)
            mod = attrs.get(mk, calc_mod(val))
            box = ctk.CTkFrame(ag, fg_color="#181818", corner_radius=6, border_color="#333", border_width=1)
            box.grid(row=0, column=col_i, padx=2, sticky="ew")
            ctk.CTkLabel(box, text=lbl,
                         font=ctk.CTkFont(size=10),
                         text_color="#AAAAAA").pack(pady=(4, 0))
            ctk.CTkLabel(box, text=str(val),
                         font=ctk.CTkFont(size=16, weight="bold")).pack()
            mod_bg = ctk.CTkFrame(box, fg_color="#222", corner_radius=4)
            mod_bg.pack(fill="x", padx=4, pady=(0,4))
            ctk.CTkLabel(mod_bg, text=mod_str(mod),
                         font=ctk.CTkFont(size=11),
                         text_color="white").pack(pady=2)

        # ── Sentidos / Extra ─────────────────────────────────────
        senses = c.get("senses", "")
        if senses:
            ctk.CTkLabel(
                self, text=f"* Sentidos {senses}",
                font=ctk.CTkFont(size=11, slant="italic"),
                text_color="#888", anchor="w"
            ).pack(fill="x", padx=10, pady=(0, 10))
            
        traits = c.get("special_traits", [])
        actions = c.get("actions", [])
        if traits or actions:
            self._sep()
        
        if traits:
            for t in traits:
                tf = ctk.CTkFrame(self, fg_color="transparent")
                tf.pack(fill="x", padx=10, pady=2)
                ctk.CTkLabel(tf, text=f"• {t.get('name', '')}", font=ctk.CTkFont(size=11, weight="bold"), text_color=GOLD_LIGHT, anchor="w").pack(anchor="w")
                ctk.CTkLabel(tf, text=t.get("desc", ""), font=ctk.CTkFont(size=10), wraplength=260, justify="left", anchor="w", text_color="#CCC").pack(anchor="w")
                
        if actions:
            if traits: self._sep()
            ctk.CTkLabel(self, text="AÇÕES", font=ctk.CTkFont(size=11, weight="bold"), text_color=RED_MID, anchor="w").pack(fill="x", padx=10, pady=(4, 0))
            for a in actions:
                af = ctk.CTkFrame(self, fg_color="transparent")
                af.pack(fill="x", padx=10, pady=2)
                ctk.CTkLabel(af, text=f"⚔️ {a.get('name', '')}", font=ctk.CTkFont(size=11, weight="bold"), text_color=GOLD_LIGHT, anchor="w").pack(anchor="w")
                ctk.CTkLabel(af, text=a.get("desc", ""), font=ctk.CTkFont(size=10), wraplength=260, justify="left", anchor="w", text_color="#CCC").pack(anchor="w")

    def _sep(self):
        ctk.CTkFrame(self, height=1, fg_color="#222").pack(
            fill="x", padx=10, pady=4
        )


# ════════════════════════════════════════════════════════════════════════════
#  EditModal — edição completa com dirty-state check
# ════════════════════════════════════════════════════════════════════════════
class EditModal(ctk.CTkToplevel):
    """Modal de edição completa de um personagem."""

    _ATTR_DEFS = [
        ("FOR", "str",  "str_mod"),
        ("DES", "dex",  "dex_mod"),
        ("CON", "con",  "con_mod"),
        ("INT", "int",  "int_mod"),
        ("SAB", "wis",  "wis_mod"),
        ("CAR", "cha",  "cha_mod"),
    ]

    def __init__(self, master, char_data: dict, on_save_cb):
        super().__init__(master)
        self.char_data  = char_data
        self.on_save_cb = on_save_cb
        self._dirty     = False
        self.vars       = {}      # campo → StringVar
        self.attr_vars  = {}      # 'str', 'str_mod', ... → StringVar

        self.title(f"Editar — {char_data.get('name', '?')}")
        self.geometry("600x700")
        self.resizable(True, True)
        self.grab_set()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build()
        # Reseta dirty depois que as traces dispararem durante a construção
        self.after(400, lambda: setattr(self, "_dirty", False))

    # ── Dirty state ──────────────────────────────────────────────────────────
    def _mark_dirty(self, *_):
        self._dirty = True

    def _on_close(self):
        if self._dirty:
            if not messagebox.askyesno(
                "Alterações não salvas",
                "Há alterações não salvas.\nDeseja fechar sem salvar?",
                parent=self,
            ):
                return
        self.destroy()

    # ── Build form ────────────────────────────────────────────────────────────
    def _build(self):
        c     = self.char_data
        attrs = c.get("attributes", {})
        md    = self._mark_dirty

        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=8, pady=8)

        # ── Básico ──────────────────────────────────────────────────────────
        _make_section(scroll, "📋 Informações Básicas")
        self.vars["name"] = _make_field(scroll, "Nome", c.get("name", ""), md)

        # Tipo — OptionMenu
        tr = ctk.CTkFrame(scroll, fg_color="transparent")
        tr.pack(fill="x", pady=2)
        ctk.CTkLabel(tr, text="Tipo", width=150, anchor="w",
                     font=ctk.CTkFont(size=11)).pack(side="left", padx=(6, 4))
        type_var = tk.StringVar(value=c.get("type", "Monstro"))
        type_var.trace_add("write", md)
        ctk.CTkOptionMenu(tr, values=["Jogador", "Monstro"],
                          variable=type_var, width=160).pack(side="left")
        self.vars["type"] = type_var

        self.vars["size"]      = _make_field(scroll, "Tamanho",         c.get("size",      "Médio"), md)
        self.vars["race"]      = _make_field(scroll, "Raça / Tipo",     c.get("race",      ""),      md)
        self.vars["alignment"] = _make_field(scroll, "Alinhamento",     c.get("alignment", ""),      md)

        # Imagem + botão browse
        ir = ctk.CTkFrame(scroll, fg_color="transparent")
        ir.pack(fill="x", pady=2)
        ctk.CTkLabel(ir, text="Imagem (path)", width=150, anchor="w",
                     font=ctk.CTkFont(size=11)).pack(side="left", padx=(6, 4))
        img_var = tk.StringVar(value=c.get("image_path", ""))
        img_var.trace_add("write", md)
        self.vars["image_path"] = img_var
        ctk.CTkEntry(ir, textvariable=img_var, width=260).pack(
            side="left", fill="x", expand=True, padx=(0, 4)
        )
        ctk.CTkButton(ir, text="📂", width=36,
                      command=lambda: self._browse_image(img_var)).pack(side="left")

        # ── Combate ──────────────────────────────────────────────────────────
        _make_section(scroll, "⚔️ Estatísticas de Combate")
        self.vars["armor_class"] = _make_field(scroll, "Classe de Armadura (CA)", c.get("armor_class", 10), md)
        self.vars["armor_desc"]  = _make_field(scroll, "Descrição da Armadura",   c.get("armor_desc",  ""), md)
        self.vars["hit_points"]  = _make_field(scroll, "Pontos de Vida (HP)",     c.get("hit_points",   1), md)
        self.vars["hit_dice"]    = _make_field(scroll, "Dado de Vida",            c.get("hit_dice",    ""), md)
        self.vars["speed"]       = _make_field(scroll, "Velocidade",              c.get("speed",      "9m"), md)
        self.vars["challenge"]   = _make_field(scroll, "Desafio (CR)",            c.get("challenge",  "0"), md)
        self.vars["xp"]          = _make_field(scroll, "XP",                      c.get("xp",          0), md)

        # ── Atributos ────────────────────────────────────────────────────────
        _make_section(scroll, "💪 Atributos")
        ag = ctk.CTkFrame(scroll, fg_color="transparent")
        ag.pack(fill="x", padx=6, pady=4)
        for col in range(3):
            ag.columnconfigure(col, weight=1)

        for i, (lbl, k, mk) in enumerate(self._ATTR_DEFS):
            row_i = i // 3
            col_i = i % 3
            box = ctk.CTkFrame(ag, fg_color=CARD_BG, corner_radius=8)
            box.grid(row=row_i, column=col_i, padx=4, pady=4, sticky="nsew")

            ctk.CTkLabel(box, text=lbl,
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=GOLD).pack(pady=(8, 2))

            val_var = tk.StringVar(value=str(attrs.get(k, 10)))
            val_var.trace_add("write", md)
            ctk.CTkEntry(box, textvariable=val_var, width=70,
                         justify="center",
                         font=ctk.CTkFont(size=14)).pack(padx=10, pady=2)

            mod_var = tk.StringVar(
                value=str(attrs.get(mk, calc_mod(attrs.get(k, 10))))
            )
            mod_var.trace_add("write", md)
            ctk.CTkLabel(box, text="mod",
                         font=ctk.CTkFont(size=9),
                         text_color="#AAAAAA").pack()
            ctk.CTkEntry(box, textvariable=mod_var, width=60,
                         justify="center").pack(padx=10, pady=(0, 8))

            self.attr_vars[k]  = val_var
            self.attr_vars[mk] = mod_var

        # ── Info Adicional ────────────────────────────────────────────────────
        _make_section(scroll, "📖 Informações Adicionais")
        self.vars["senses"]       = _make_field(scroll, "Sentidos",                    c.get("senses",       ""), md)
        self.vars["languages"]    = _make_field(scroll, "Idiomas",                     c.get("languages",    ""), md)
        self.vars["dex_modifier"] = _make_field(scroll, "Mod. de Iniciativa (Dex)",    c.get("dex_modifier",  0), md)

        # ── Habilidades Especiais (JSON) ──────────────────────────────────────
        _make_section(scroll, "✨ Habilidades Especiais")
        ctk.CTkLabel(
            scroll,
            text='Formato: [{"name": "Nome", "desc": "Descrição"}, ...]',
            font=ctk.CTkFont(size=9), text_color="gray",
        ).pack(anchor="w", padx=8)
        self.traits_tb = ctk.CTkTextbox(scroll, height=100)
        self.traits_tb.pack(fill="x", padx=8, pady=4)
        self.traits_tb.insert(
            "0.0",
            json.dumps(c.get("special_traits", []), indent=2, ensure_ascii=False)
        )
        self.traits_tb.bind("<Key>", lambda e: self._mark_dirty())

        # ── Ações (JSON) ──────────────────────────────────────────────────────
        _make_section(scroll, "⚔️ Ações")
        ctk.CTkLabel(
            scroll,
            text='Formato: [{"name": "Nome", "desc": "Descrição"}, ...]',
            font=ctk.CTkFont(size=9), text_color="gray",
        ).pack(anchor="w", padx=8)
        self.actions_tb = ctk.CTkTextbox(scroll, height=130)
        self.actions_tb.pack(fill="x", padx=8, pady=4)
        self.actions_tb.insert(
            "0.0",
            json.dumps(c.get("actions", []), indent=2, ensure_ascii=False)
        )
        self.actions_tb.bind("<Key>", lambda e: self._mark_dirty())

        # ── Botões ────────────────────────────────────────────────────────────
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(
            btn_bar, text="💾  Salvar",
            fg_color="#1A5C2A", hover_color="#216E33",
            font=ctk.CTkFont(weight="bold"), width=120,
            command=self._save,
        ).pack(side="right", padx=4)
        ctk.CTkButton(
            btn_bar, text="Cancelar",
            fg_color="#444", hover_color="#555", width=100,
            command=self._on_close,
        ).pack(side="right", padx=4)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _browse_image(self, var: tk.StringVar):
        path = filedialog.askopenfilename(
            parent=self,
            title="Selecionar Imagem do Personagem",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.webp"), ("Todos", "*.*")],
        )
        if path:
            var.set(path)

    def _save(self):
        fields = {}
        int_keys = {"armor_class", "hit_points", "xp", "dex_modifier"}

        for key, var in self.vars.items():
            val = var.get().strip()
            if key in int_keys:
                try:
                    val = int(val)
                except ValueError:
                    pass
            fields[key] = val

        # Atributos
        attr_dict = {}
        for key, var in self.attr_vars.items():
            try:
                attr_dict[key] = int(var.get())
            except ValueError:
                attr_dict[key] = 0
        fields["attributes"] = attr_dict

        # Sincroniza dex_modifier
        try:
            fields["dex_modifier"] = int(self.vars["dex_modifier"].get())
        except (ValueError, KeyError):
            fields["dex_modifier"] = attr_dict.get("dex_mod", 0)

        # Habilidades Especiais (JSON ou texto livre)
        raw_traits = self.traits_tb.get("0.0", "end").strip()
        if not raw_traits or raw_traits == "[]":
            fields["special_traits"] = []
        else:
            try:
                parsed = json.loads(raw_traits)
                if not isinstance(parsed, list):
                    raise ValueError("Deve ser uma lista")
                fields["special_traits"] = parsed
            except (json.JSONDecodeError, ValueError):
                # Aceita texto livre: cada parágrafo vira uma entrada
                entries = [p.strip() for p in raw_traits.split("\n\n") if p.strip()]
                if not entries:
                    entries = [raw_traits]
                fields["special_traits"] = [
                    {"name": "Habilidade", "desc": e} for e in entries
                ]

        # Ações (JSON ou texto livre)
        raw_actions = self.actions_tb.get("0.0", "end").strip()
        if not raw_actions or raw_actions == "[]":
            fields["actions"] = []
        else:
            try:
                parsed = json.loads(raw_actions)
                if not isinstance(parsed, list):
                    raise ValueError("Deve ser uma lista")
                fields["actions"] = parsed
            except (json.JSONDecodeError, ValueError):
                # Aceita texto livre: cada parágrafo vira uma entrada
                entries = [p.strip() for p in raw_actions.split("\n\n") if p.strip()]
                if not entries:
                    entries = [raw_actions]
                fields["actions"] = [
                    {"name": "Ação", "desc": e} for e in entries
                ]

        update_character(self.char_data["id"], fields)
        # Devolve o char_data atualizado para o callback
        updated = {**self.char_data, **fields}
        self._dirty = False
        self.on_save_cb(updated)
        self.destroy()


# ════════════════════════════════════════════════════════════════════════════
#  App Principal
# ════════════════════════════════════════════════════════════════════════════
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("D&D 5.5e — Tracker de Iniciativa")
        self.geometry("1200x750")
        self.minsize(1000, 620)

        create_table()
        self.encounter     = Encounter()
        self._active_modal = None   # EditModal aberto atualmente
        self._card_char_id = None   # ID do personagem atualmente no card

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(padx=12, pady=12, fill="both", expand=True)

        self.tab_cadastro = self.tabview.add("📋  Cadastro")
        self.tab_combate  = self.tabview.add("⚔️  Combate / Iniciativa")

        self.build_cadastro_tab()
        self.build_combate_tab()

        self.protocol("WM_DELETE_WINDOW", self._on_app_close)

    def _on_app_close(self):
        if self._active_modal and self._active_modal.winfo_exists():
            if self._active_modal._dirty:
                if not messagebox.askyesno(
                    "Alterações não salvas",
                    "Há alterações não salvas no editor.\nDeseja fechar mesmo assim?",
                ):
                    return
        self.destroy()

    # ══════════════════════════════════════════════════════════════════════════
    #  ABA DE CADASTRO
    # ══════════════════════════════════════════════════════════════════════════
    def build_cadastro_tab(self):
        self.tab_cadastro.grid_columnconfigure(0, weight=0, minsize=265)
        self.tab_cadastro.grid_columnconfigure(1, weight=1)
        self.tab_cadastro.grid_rowconfigure(0, weight=1)

        # ── Formulário rápido (esquerda) ──────────────────────────────────────
        form_outer = ctk.CTkFrame(self.tab_cadastro, width=270)
        form_outer.grid(row=0, column=0, sticky="nsew", padx=(6, 3), pady=6)
        form_outer.grid_propagate(False)

        ctk.CTkLabel(
            form_outer, text="Novo Personagem",
            font=ctk.CTkFont(size=16, weight="bold"), text_color=GOLD,
        ).pack(pady=(12, 4))
        ctk.CTkFrame(form_outer, height=2, fg_color=RED_MID).pack(
            fill="x", padx=10, pady=(0, 4)
        )

        form_scroll = ctk.CTkScrollableFrame(form_outer)
        form_scroll.pack(fill="both", expand=True, padx=4, pady=2)

        self.fv = {}     # form vars

        # Tipo
        tr = ctk.CTkFrame(form_scroll, fg_color="transparent")
        tr.pack(fill="x", pady=2)
        ctk.CTkLabel(tr, text="Tipo", width=100, anchor="w",
                     font=ctk.CTkFont(size=11)).pack(side="left", padx=(6, 4))
        type_var = tk.StringVar(value="Monstro")
        ctk.CTkOptionMenu(tr, values=["Jogador", "Monstro"],
                          variable=type_var, width=130).pack(side="left")
        self.fv["type"] = type_var

        # Campos de texto simples
        for label, key, default in [
            ("Nome",         "name",        ""),
            ("Tamanho",      "size",        "Médio"),
            ("Raça / Tipo",  "race",        ""),
            ("Alinhamento",  "alignment",   ""),
            ("CA",           "armor_class", "10"),
            ("HP",           "hit_points",  "10"),
            ("Dado de Vida", "hit_dice",    ""),
            ("Velocidade",   "speed",       "9m"),
            ("Desafio (CR)", "challenge",   "0"),
            ("XP",           "xp",          "0"),
            ("Sentidos",     "senses",      ""),
            ("Idiomas",      "languages",   ""),
        ]:
            self.fv[key] = _make_field(form_scroll, label, default, width=130)

        # Imagem + browse
        ir = ctk.CTkFrame(form_scroll, fg_color="transparent")
        ir.pack(fill="x", pady=2)
        ctk.CTkLabel(ir, text="Imagem", width=100, anchor="w",
                     font=ctk.CTkFont(size=11)).pack(side="left", padx=(6, 4))
        img_var = tk.StringVar()
        self.fv["image_path"] = img_var
        ctk.CTkEntry(ir, textvariable=img_var, width=90).pack(
            side="left", fill="x", expand=True, padx=(0, 2)
        )
        ctk.CTkButton(ir, text="📂", width=30,
                      command=lambda: self._browse_form_img(img_var)).pack(side="left")

        # Grid de atributos
        ctk.CTkLabel(form_scroll, text="Atributos",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=GOLD).pack(anchor="w", padx=6, pady=(8, 2))
        self.form_attr_vars = {}
        ag = ctk.CTkFrame(form_scroll, fg_color="transparent")
        ag.pack(fill="x", padx=4, pady=2)
        for col_i, (lbl, k) in enumerate(
            [("FOR","str"),("DES","dex"),("CON","con"),
             ("INT","int"),("SAB","wis"),("CAR","cha")]
        ):
            ag.columnconfigure(col_i, weight=1)
            box = ctk.CTkFrame(ag, fg_color=CARD_BG, corner_radius=6)
            box.grid(row=0, column=col_i, padx=1, sticky="ew")
            ctk.CTkLabel(box, text=lbl,
                         font=ctk.CTkFont(size=8, weight="bold"),
                         text_color=GOLD).pack(pady=(3, 0))
            v = tk.StringVar(value="10")
            ctk.CTkEntry(box, textvariable=v, width=36, justify="center").pack(
                pady=(0, 3), padx=2
            )
            self.form_attr_vars[k] = v

        # Botão adicionar
        ctk.CTkButton(
            form_outer, text="➕  Adicionar",
            fg_color=RED_MID, hover_color=RED_DARK,
            font=ctk.CTkFont(weight="bold"),
            command=self.save_new_character,
        ).pack(pady=10, padx=10, fill="x")

        # ── Lista de personagens (direita) ────────────────────────────────────
        list_outer = ctk.CTkFrame(self.tab_cadastro)
        list_outer.grid(row=0, column=1, sticky="nsew", padx=(3, 6), pady=6)

        hdr = ctk.CTkFrame(list_outer, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(12, 4))
        ctk.CTkLabel(
            hdr, text="Personagens Cadastrados",
            font=ctk.CTkFont(size=16, weight="bold"), text_color=GOLD,
        ).pack(side="left")

        self.scrollable_list = ctk.CTkScrollableFrame(list_outer)
        self.scrollable_list.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.refresh_character_list()

    # ── Form helpers ──────────────────────────────────────────────────────────
    def _browse_form_img(self, var: tk.StringVar):
        path = filedialog.askopenfilename(
            parent=self, title="Selecionar Imagem",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.webp"), ("Todos", "*.*")],
        )
        if path:
            var.set(path)

    def save_new_character(self):
        name = self.fv["name"].get().strip()
        if not name:
            messagebox.showwarning("Aviso", "O nome não pode estar vazio.")
            return

        # Atributos com cálculo de modificadores
        attr_dict = {}
        for k, var in self.form_attr_vars.items():
            try:
                score = int(var.get())
            except ValueError:
                score = 10
            attr_dict[k]          = score
            attr_dict[f"{k}_mod"] = calc_mod(score)

        def _int(key, fallback=0):
            try:
                return int(self.fv.get(key, tk.StringVar(value=str(fallback))).get())
            except ValueError:
                return fallback

        def _str(key, fallback=""):
            return self.fv.get(key, tk.StringVar(value=fallback)).get()

        fields = {
            "name":           name,
            "type":           self.fv["type"].get(),
            "image_path":     _str("image_path"),
            "size":           _str("size", "Médio") or "Médio",
            "race":           _str("race"),
            "alignment":      _str("alignment"),
            "armor_class":    _int("armor_class", 10),
            "armor_desc":     "",
            "hit_points":     _int("hit_points", 10),
            "hit_dice":       _str("hit_dice"),
            "speed":          _str("speed", "9m") or "9m",
            "challenge":      _str("challenge", "0") or "0",
            "xp":             _int("xp", 0),
            "senses":         _str("senses"),
            "languages":      _str("languages"),
            "attributes":     attr_dict,
            "dex_modifier":   attr_dict.get("dex_mod", 0),
            "special_traits": [],
            "actions":        [],
        }

        add_character(fields)
        self._clear_form()
        self.refresh_character_list()
        self.refresh_combate_selectors()

    def _clear_form(self):
        defaults = {
            "type": "Monstro", "size": "Médio",
            "armor_class": "10", "hit_points": "10",
            "speed": "9m", "challenge": "0", "xp": "0",
        }
        for key, var in self.fv.items():
            var.set(defaults.get(key, ""))
        for var in self.form_attr_vars.values():
            var.set("10")

    # ── CRUD callbacks ────────────────────────────────────────────────────────
    def delete_char(self, char_id: int):
        if messagebox.askyesno("Confirmar", "Deseja realmente excluir este personagem?"):
            delete_character(char_id)
            self.refresh_character_list()
            self.refresh_combate_selectors()

    def edit_char(self, char_data: dict):
        if self._active_modal and self._active_modal.winfo_exists():
            self._active_modal.lift()
            return
        self._active_modal = EditModal(self, char_data, self._on_edit_saved)

    def _on_edit_saved(self, updated_data: dict):
        self.refresh_character_list()
        self.refresh_combate_selectors()
        # Se o card estava mostrando este personagem, atualiza com os dados novos
        if self._card_char_id == updated_data.get("id"):
            self.char_card.load(updated_data)

    def refresh_character_list(self):
        for w in self.scrollable_list.winfo_children():
            w.destroy()

        chars = get_all_characters()
        if not chars:
            ctk.CTkLabel(
                self.scrollable_list,
                text="Nenhum personagem cadastrado ainda.",
                text_color="gray",
            ).pack(pady=20)
            return

        for c in chars:
            row = ctk.CTkFrame(self.scrollable_list, corner_radius=8)
            row.pack(fill="x", pady=3, padx=3)

            # Barra lateral colorida por tipo
            bar_col = "#1A4A6E" if c.get("type") == "Jogador" else "#4E1A1A"
            ctk.CTkFrame(row, fg_color=bar_col, width=6, corner_radius=3).pack(
                side="left", fill="y", padx=(4, 8), pady=4
            )

            # Informações
            info_f = ctk.CTkFrame(row, fg_color="transparent")
            info_f.pack(side="left", fill="x", expand=True, pady=4)

            ctk.CTkLabel(
                info_f, text=c.get("name", "?"),
                font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
            ).pack(anchor="w")


            attrs = c.get("attributes", {})
            dex_m = attrs.get("dex_mod", c.get("dex_modifier", 0))
            sub = (
                f"{c.get('type', '')}  •  "
                f"CA {c.get('armor_class', '?')}  •  "
                f"HP {c.get('hit_points', '?')}  •  "
                f"Dex {mod_str(dex_m)}"
            )
            ctk.CTkLabel(
                info_f, text=sub,
                font=ctk.CTkFont(size=10), text_color="#AAAAAA", anchor="w",
            ).pack(anchor="w")

            # Botões
            ctk.CTkButton(
                row, text="✏️ Editar", width=80, height=28,
                fg_color="#2C4A6E", hover_color="#3A6090",
                command=lambda cd=c: self.edit_char(cd),
            ).pack(side="right", padx=4, pady=4)

            ctk.CTkButton(
                row, text="🗑", width=36, height=28,
                fg_color=RED_DARK, hover_color="#7B0000",
                command=lambda cid=c["id"]: self.delete_char(cid),
            ).pack(side="right", padx=(0, 2), pady=4)

    # ══════════════════════════════════════════════════════════════════════════
    #  ABA DE COMBATE
    # ══════════════════════════════════════════════════════════════════════════
    def build_combate_tab(self):
        self.tab_combate.grid_columnconfigure(0, weight=0, minsize=215)
        self.tab_combate.grid_columnconfigure(1, weight=1)
        self.tab_combate.grid_columnconfigure(2, weight=1)
        self.tab_combate.grid_rowconfigure(0, weight=1)

        # ── Col 0: Painel de seleção ──────────────────────────────────────────
        sel = ctk.CTkFrame(self.tab_combate, width=220)
        sel.grid(row=0, column=0, sticky="nsew", padx=(6, 3), pady=6)
        sel.grid_propagate(False)

        ctk.CTkLabel(
            sel, text="Montar Combate",
            font=ctk.CTkFont(size=14, weight="bold"), text_color=GOLD,
        ).pack(pady=(12, 4))
        ctk.CTkFrame(sel, height=2, fg_color=RED_MID).pack(
            fill="x", padx=10, pady=(0, 10)
        )

        # Jogadores
        ctk.CTkLabel(sel, text="🧙 Jogadores",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#7DADE2").pack(anchor="w", padx=10, pady=(4, 0))
        self.combo_jogadores = ctk.CTkComboBox(
            sel, values=["Nenhum"], command=self._on_player_select
        )
        self.combo_jogadores.pack(padx=10, pady=4, fill="x")
        ctk.CTkButton(
            sel, text="Adicionar Jogador", height=28,
            fg_color="#1A4A6E", hover_color="#2C6090",
            command=lambda: self.add_to_encounter("jogador"),
        ).pack(padx=10, pady=2, fill="x")

        ctk.CTkFrame(sel, height=1, fg_color="#444").pack(
            fill="x", padx=10, pady=10
        )

        # Monstros
        ctk.CTkLabel(sel, text="💀 Monstros",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#E57373").pack(anchor="w", padx=10, pady=(4, 0))
        self.combo_monstros = ctk.CTkComboBox(
            sel, values=["Nenhum"], command=self._on_monster_select
        )
        self.combo_monstros.pack(padx=10, pady=4, fill="x")

        qty_row = ctk.CTkFrame(sel, fg_color="transparent")
        qty_row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(qty_row, text="Qtd:", font=ctk.CTkFont(size=11)).pack(side="left")
        self.entry_qtd = ctk.CTkEntry(qty_row, width=55, justify="center")
        self.entry_qtd.pack(side="right")
        self.entry_qtd.insert(0, "1")

        ctk.CTkButton(
            sel, text="Adicionar Monstro(s)", height=28,
            fg_color=RED_DARK, hover_color="#7B0000",
            command=lambda: self.add_to_encounter("monstro"),
        ).pack(padx=10, pady=2, fill="x")

        ctk.CTkFrame(sel, height=1, fg_color="#444").pack(
            fill="x", padx=10, pady=10
        )

        # Ações de combate
        ctk.CTkButton(
            sel, text="🎲  ROLAR INICIATIVA", height=42,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#1A5C2A", hover_color="#216E33",
            command=self.roll_initiative,
        ).pack(padx=10, pady=2, fill="x")
        ctk.CTkButton(
            sel, text="🗑  Limpar Combate", height=32,
            fg_color="#3A3A3A", hover_color="#555",
            command=self.clear_encounter,
        ).pack(padx=10, pady=6, fill="x")

        # ── Col 1: Ficha do personagem selecionado ────────────────────────────
        card_panel = ctk.CTkFrame(self.tab_combate)
        card_panel.grid(row=0, column=1, sticky="nsew", padx=3, pady=6)

        ctk.CTkLabel(
            card_panel, text="Ficha do Personagem",
            font=ctk.CTkFont(size=14, weight="bold"), text_color=GOLD,
        ).pack(pady=(10, 4))
        ctk.CTkFrame(card_panel, height=2, fg_color=RED_MID).pack(
            fill="x", padx=10, pady=(0, 6)
        )
        self.char_card = CharacterCard(card_panel, fg_color="transparent")
        self.char_card.pack(fill="both", expand=True, padx=4, pady=(0, 6))

        # ── Col 2: Ordem de Iniciativa ────────────────────────────────────────
        res_panel = ctk.CTkFrame(self.tab_combate)
        res_panel.grid(row=0, column=2, sticky="nsew", padx=(3, 6), pady=6)

        ctk.CTkLabel(
            res_panel, text="Ordem de Iniciativa",
            font=ctk.CTkFont(size=14, weight="bold"), text_color=GOLD,
        ).pack(pady=(10, 4))
        ctk.CTkFrame(res_panel, height=2, fg_color=RED_MID).pack(
            fill="x", padx=10, pady=(0, 6)
        )
        self.encounter_list = ctk.CTkScrollableFrame(res_panel)
        self.encounter_list.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.refresh_combate_selectors()

    # ── Seletor callbacks ─────────────────────────────────────────────────────
    def _on_player_select(self, value: str):
        if value and value != "Nenhum" and value in self.players_map:
            char = self.players_map[value]
            self._card_char_id = char.get("id")
            self.char_card.load(char)

    def _on_monster_select(self, value: str):
        if value and value != "Nenhum" and value in self.monsters_map:
            char = self.monsters_map[value]
            self._card_char_id = char.get("id")
            self.char_card.load(char)

    def refresh_combate_selectors(self):
        players  = get_characters_by_type("Jogador")
        monsters = get_characters_by_type("Monstro")

        self.players_map  = {c["name"]: c for c in players}
        self.monsters_map = {c["name"]: c for c in monsters}

        p_names = list(self.players_map.keys()) or ["Nenhum"]
        m_names = list(self.monsters_map.keys()) or ["Nenhum"]

        self.combo_jogadores.configure(values=p_names)
        self.combo_jogadores.set(p_names[0])
        self.combo_monstros.configure(values=m_names)
        self.combo_monstros.set(m_names[0])

    # ── Encounter actions ─────────────────────────────────────────────────────
    def add_to_encounter(self, category: str):
        if category == "jogador":
            sel      = self.combo_jogadores.get()
            char_map = self.players_map
            qty      = 1
        else:
            sel      = self.combo_monstros.get()
            char_map = self.monsters_map
            try:
                qty = max(1, int(self.entry_qtd.get()))
            except ValueError:
                qty = 1

        if not sel or sel == "Nenhum" or sel not in char_map:
            messagebox.showinfo("Aviso", "Selecione um personagem válido.")
            return

        self.encounter.add_multiple_participants(char_map[sel], count=qty)
        self.refresh_encounter_view(show_rolls=False)

    def clear_encounter(self):
        self.encounter.clear()
        self.refresh_encounter_view(show_rolls=False)

    def roll_initiative(self):
        if not self.encounter.participants:
            messagebox.showinfo("Combate Vazio", "Adicione participantes antes de rolar.")
            return
        self.encounter.roll_all()
        self.refresh_encounter_view(show_rolls=True)

    def refresh_encounter_view(self, show_rolls: bool = False):
        for w in self.encounter_list.winfo_children():
            w.destroy()

        if not self.encounter.participants:
            ctk.CTkLabel(
                self.encounter_list,
                text="Nenhum participante adicionado.\nUse os seletores à esquerda.",
                text_color="gray",
            ).pack(pady=20)
            return

        for idx, p in enumerate(self.encounter.participants):
            is_player = p.char_type == "Jogador"
            row_bg    = "#181818" # Darker background
            
            row = ctk.CTkFrame(self.encounter_list, fg_color=row_bg, corner_radius=8, border_width=1, border_color="#333")
            row.pack(fill="x", pady=4, padx=4)

            # Badge de posição amarela (fita)
            badge_bg  = "#D4AF37" if show_rolls else "#555" # Gold yellow
            if is_player and show_rolls:
                badge_bg = "#4A90E2" # Blue for player
            badge_tc  = "black" if show_rolls else "white"
            
            badge = ctk.CTkFrame(row, fg_color=badge_bg, width=45, corner_radius=6)
            badge.pack(side="left", fill="y", padx=2, pady=2)
            badge.pack_propagate(False)
            
            ctk.CTkLabel(
                badge, text=str(idx + 1),
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=badge_tc,
            ).pack(expand=True)

            # Informações
            inf = ctk.CTkFrame(row, fg_color="transparent")
            inf.pack(side="left", fill="x", expand=True, padx=12, pady=10)

            ctk.CTkLabel(
                inf, text=p.name.upper(),
                font=ctk.CTkFont(size=14, weight="bold"), anchor="w",
                text_color="white"
            ).pack(anchor="w")

            if show_rolls:
                detail = (
                    f"Iniciativa: {p.initiative_total}  "
                    f"(@ {p.roll_result} + Dex {mod_str(p.dex_modifier)})"
                )
                ctk.CTkLabel(
                    inf, text=detail,
                    font=ctk.CTkFont(size=11), text_color="#AAAAAA", anchor="w",
                ).pack(anchor="w")
            else:
                ctk.CTkLabel(
                    inf,
                    text=f"{p.char_type}  •  Aguardando rolagem...",
                    font=ctk.CTkFont(size=11), text_color="gray", anchor="w",
                ).pack(anchor="w")

            # Clique na linha → exibe ficha no card lateral
            def _make_handler(participant):
                def handler(_event):
                    self._card_char_id = participant.char_data.get("id")
                    self.char_card.load(participant.char_data)
                return handler

            cb = _make_handler(p)
            row.bind("<Button-1>", cb)
            for child in row.winfo_children():
                child.bind("<Button-1>", cb)


if __name__ == "__main__":
    app = App()
    app.mainloop()

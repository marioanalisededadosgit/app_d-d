import json
import os

DB_FILENAME = "dnd_data.json"


def _load_data():
    if not os.path.exists(DB_FILENAME):
        return []
    with open(DB_FILENAME, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _save_data(data):
    with open(DB_FILENAME, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def create_table():
    """Inicializa o arquivo de dados se não existir."""
    if not os.path.exists(DB_FILENAME):
        _save_data([])


def default_attributes():
    return {
        "str": 10, "str_mod": 0,
        "dex": 10, "dex_mod": 0,
        "con": 10, "con_mod": 0,
        "int": 10, "int_mod": 0,
        "wis": 10, "wis_mod": 0,
        "cha": 10, "cha_mod": 0,
    }


def add_character(fields: dict):
    """
    Adiciona um novo personagem com schema completo.

    Campos esperados em `fields`:
        name, type, image_path, size, race, alignment,
        armor_class, armor_desc, hit_points, hit_dice, speed,
        challenge, xp, senses, languages, attributes (dict),
        dex_modifier, special_traits (list), actions (list)
    """
    data = _load_data()
    new_id = 1 if not data else max(c.get('id', 0) for c in data) + 1

    new_char = {
        "id":             new_id,
        "name":           fields.get("name", "Sem Nome"),
        "type":           fields.get("type", "Monstro"),
        "image_path":     fields.get("image_path", ""),
        "size":           fields.get("size", "Médio"),
        "race":           fields.get("race", ""),
        "alignment":      fields.get("alignment", ""),
        "armor_class":    fields.get("armor_class", 10),
        "armor_desc":     fields.get("armor_desc", ""),
        "hit_points":     fields.get("hit_points", 1),
        "hit_dice":       fields.get("hit_dice", ""),
        "speed":          fields.get("speed", "9m"),
        "challenge":      fields.get("challenge", "0"),
        "xp":             fields.get("xp", 0),
        "senses":         fields.get("senses", ""),
        "languages":      fields.get("languages", ""),
        "attributes":     fields.get("attributes", default_attributes()),
        "dex_modifier":   fields.get("dex_modifier", 0),
        "special_traits": fields.get("special_traits", []),
        "actions":        fields.get("actions", []),
    }
    data.append(new_char)
    _save_data(data)
    return new_char


def update_character(char_id: int, fields: dict):
    """Atualiza incrementalmente apenas os campos fornecidos em `fields`."""
    data = _load_data()
    for char in data:
        if char['id'] == char_id:
            for key, value in fields.items():
                char[key] = value
            break
    _save_data(data)


def delete_character(char_id: int):
    data = _load_data()
    data = [c for c in data if c['id'] != char_id]
    _save_data(data)


def get_all_characters():
    data = _load_data()
    return sorted(data, key=lambda c: c['name'].lower())


def get_characters_by_type(char_type: str):
    """Retorna apenas os personagens do tipo especificado ('Jogador' ou 'Monstro')."""
    data = _load_data()
    filtered = [c for c in data if c.get('type') == char_type]
    return sorted(filtered, key=lambda c: c['name'].lower())

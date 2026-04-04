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
    # Inicializa o arquivo vazio se não existir
    if not os.path.exists(DB_FILENAME):
        _save_data([])

def add_character(name: str, char_type: str, dex_modifier: int):
    data = _load_data()
    
    # Gerar um ID numérico simples (maior id atual + 1)
    new_id = 1 if not data else max(c.get('id', 0) for c in data) + 1
    
    new_char = {
        "id": new_id,
        "name": name,
        "type": char_type,
        "dex_modifier": dex_modifier
    }
    data.append(new_char)
    _save_data(data)

def update_character(char_id: int, name: str, char_type: str, dex_modifier: int):
    data = _load_data()
    for char in data:
        if char['id'] == char_id:
            char['name'] = name
            char['type'] = char_type
            char['dex_modifier'] = dex_modifier
            break
    _save_data(data)

def delete_character(char_id: int):
    data = _load_data()
    data = [char for char in data if char['id'] != char_id]
    _save_data(data)

def get_all_characters():
    data = _load_data()
    # Ordenar por nome insensível a maiúsculas (simulando ORDER BY name COLLATE NOCASE)
    return sorted(data, key=lambda c: c['name'].lower())

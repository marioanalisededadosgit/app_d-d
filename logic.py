import random


def roll_d20():
    return random.randint(1, 20)


class Participant:
    def __init__(self, char_data: dict, quantity_index: int = None):
        """
        :param char_data:       Dict completo do personagem (lido do JSON).
        :param quantity_index:  Índice para cópias de monstros (ex.: Goblin 2).
        """
        self.char_data    = char_data
        self.char_id      = char_data.get('id')
        self.char_type    = char_data.get('type', 'Monstro')
        self.dex_modifier = char_data.get('dex_modifier', 0)
        self.max_hp       = char_data.get('hit_points', 1)
        self.current_hp   = self.max_hp
        self.roll_result  = 0
        self.initiative_total = 0

        base_name = char_data.get('name', 'Desconhecido')
        if quantity_index is not None and quantity_index > 0:
            self.name = f"{base_name} {quantity_index}"
        else:
            self.name = base_name

    def roll_initiative(self):
        self.roll_result = roll_d20()
        self.initiative_total = self.roll_result + self.dex_modifier


class Encounter:
    def __init__(self):
        self.participants = []

    def add_participant(self, participant: Participant):
        self.participants.append(participant)

    def add_multiple_participants(self, char_data: dict, count: int = 1):
        if count == 1:
            self.add_participant(Participant(char_data))
        else:
            for i in range(1, count + 1):
                self.add_participant(Participant(char_data, quantity_index=i))

    def clear(self):
        self.participants.clear()

    def roll_all(self):
        for p in self.participants:
            p.roll_initiative()

        # Desempate: iniciativa total → dex_modifier → aleatório
        for p in self.participants:
            p._tie_breaker = random.random()

        self.participants.sort(
            key=lambda p: (p.initiative_total, p.dex_modifier, p._tie_breaker),
            reverse=True,
        )

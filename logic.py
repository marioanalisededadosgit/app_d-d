import random

def roll_d20():
    return random.randint(1, 20)

class Participant:
    def __init__(self, char_id, name, char_type, dex_modifier, quantity_index=None):
        self.char_id = char_id
        
        # Se for um monstro com várias cópias, adicionamos o índice (ex: Goblin 1, Goblin 2)
        if quantity_index is not None and quantity_index > 0:
            self.name = f"{name} {quantity_index}"
        else:
            self.name = name
            
        self.char_type = char_type
        self.dex_modifier = dex_modifier
        self.roll_result = 0
        self.initiative_total = 0
        
    def roll_initiative(self):
        self.roll_result = roll_d20()
        self.initiative_total = self.roll_result + self.dex_modifier
        
class Encounter:
    def __init__(self):
        self.participants = []
        
    def add_participant(self, participant: Participant):
        self.participants.append(participant)
        
    def add_multiple_participants(self, char_id, name, char_type, dex_modifier, count=1):
        if count == 1:
            self.add_participant(Participant(char_id, name, char_type, dex_modifier))
        else:
            for i in range(1, count + 1):
                self.add_participant(Participant(char_id, name, char_type, dex_modifier, quantity_index=i))
                
    def clear(self):
        self.participants.clear()

    def roll_all(self):
        for p in self.participants:
            p.roll_initiative()
            
        # Ordenação oficial: Maior iniciativa primeiro. Em caso de empate, Maior destreza. Se ainda empatar, aleatório.
        # Nós usamos (initiative_total, dex_modifier, random) para critério de ordenação (descendente).
        for p in self.participants:
            p._tie_breaker = random.random() # Um valor aleatório apenas para desempatar no final
            
        self.participants.sort(
            key=lambda p: (p.initiative_total, p.dex_modifier, p._tie_breaker),
            reverse=True
        )

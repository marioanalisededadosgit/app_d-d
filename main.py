import customtkinter as ctk
import tkinter.messagebox as messagebox
from database import create_table, add_character, update_character, delete_character, get_all_characters
from logic import Encounter, Participant

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("D&D 5.5e - Tracker de Iniciativa")
        self.geometry("900x600")
        
        create_table()
        
        self.encounter = Encounter()
        
        # Tabs
        self.tabview = ctk.CTkTabview(self, width=850, height=550)
        self.tabview.pack(padx=20, pady=20, fill="both", expand=True)
        
        self.tab_cadastro = self.tabview.add("Cadastro de Personagens")
        self.tab_combate = self.tabview.add("Combate / Iniciativa")
        
        self.build_cadastro_tab()
        self.build_combate_tab()
        
    # ==========================
    # ABA DE CADASTRO
    # ==========================
    def build_cadastro_tab(self):
        # Frame Esquerdo: Formulário
        self.form_frame = ctk.CTkFrame(self.tab_cadastro)
        self.form_frame.pack(side="left", fill="y", padx=10, pady=10)
        
        ctk.CTkLabel(self.form_frame, text="Novo Personagem", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
        ctk.CTkLabel(self.form_frame, text="Nome:").pack(anchor="w", padx=10)
        self.entry_nome = ctk.CTkEntry(self.form_frame, width=200)
        self.entry_nome.pack(padx=10, pady=5)
        
        ctk.CTkLabel(self.form_frame, text="Tipo:").pack(anchor="w", padx=10)
        self.opt_tipo = ctk.CTkOptionMenu(self.form_frame, values=["Jogador", "Monstro"])
        self.opt_tipo.pack(padx=10, pady=5)
        
        ctk.CTkLabel(self.form_frame, text="Modificador de Destreza:").pack(anchor="w", padx=10)
        self.entry_dex = ctk.CTkEntry(self.form_frame, width=200)
        self.entry_dex.pack(padx=10, pady=5)
        self.entry_dex.insert(0, "0")
        
        self.btn_salvar = ctk.CTkButton(self.form_frame, text="Salvar", command=self.save_character)
        self.btn_salvar.pack(pady=20)
        
        # Frame Direito: Lista
        self.list_frame = ctk.CTkFrame(self.tab_cadastro)
        self.list_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(self.list_frame, text="Personagens Cadastrados", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
        self.scrollable_list = ctk.CTkScrollableFrame(self.list_frame)
        self.scrollable_list.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.refresh_character_list()
        
    def save_character(self):
        nome = self.entry_nome.get().strip()
        tipo = self.opt_tipo.get()
        dex_str = self.entry_dex.get().strip()
        
        if not nome:
            messagebox.showwarning("Aviso", "O nome não pode estar vazio.")
            return
            
        try:
            dex = int(dex_str)
        except ValueError:
            messagebox.showwarning("Aviso", "A destreza deve ser um número inteiro.")
            return
            
        add_character(nome, tipo, dex)
        self.entry_nome.delete(0, 'end')
        self.entry_dex.delete(0, 'end')
        self.entry_dex.insert(0, "0")
        
        self.refresh_character_list()
        self.refresh_combate_selectors()
        
    def delete_char(self, char_id):
        if messagebox.askyesno("Confirmar", "Deseja realmente excluir este personagem?"):
            delete_character(char_id)
            self.refresh_character_list()
            self.refresh_combate_selectors()
            
    def refresh_character_list(self):
        for widget in self.scrollable_list.winfo_children():
            widget.destroy()
            
        chars = get_all_characters()
        for c in chars:
            row = ctk.CTkFrame(self.scrollable_list)
            row.pack(fill="x", pady=2, padx=2)
            
            lbl = ctk.CTkLabel(row, text=f"{c['name']} ({c['type']}) | Dex: {c['dex_modifier']}", anchor="w")
            lbl.pack(side="left", padx=10, fill="x", expand=True)
            
            btn_del = ctk.CTkButton(row, text="Excluir", fg_color="red", hover_color="darkred", width=60, 
                                    command=lambda cid=c['id']: self.delete_char(cid))
            btn_del.pack(side="right", padx=5, pady=5)
            
    # ==========================
    # ABA DE COMBATE
    # ==========================
    def build_combate_tab(self):
        self.tab_combate.grid_columnconfigure(0, weight=1)
        self.tab_combate.grid_columnconfigure(1, weight=1)
        self.tab_combate.grid_rowconfigure(0, weight=1)
        
        # Esquerda: Seleção
        self.selecao_frame = ctk.CTkFrame(self.tab_combate)
        self.selecao_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        ctk.CTkLabel(self.selecao_frame, text="Montar Combate", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
        self.combobox_chars = ctk.CTkComboBox(self.selecao_frame, values=["Nenhum"])
        self.combobox_chars.pack(padx=10, pady=10, fill="x")
        
        qtd_frame = ctk.CTkFrame(self.selecao_frame, fg_color="transparent")
        qtd_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(qtd_frame, text="Quantidade (Monstros):").pack(side="left")
        self.entry_qtd = ctk.CTkEntry(qtd_frame, width=50)
        self.entry_qtd.pack(side="right")
        self.entry_qtd.insert(0, "1")
        
        btn_add = ctk.CTkButton(self.selecao_frame, text="Adicionar ao Combate", command=self.add_to_encounter)
        btn_add.pack(pady=10)
        
        # Direita: Lista e Resultados
        self.resultado_frame = ctk.CTkFrame(self.tab_combate)
        self.resultado_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        ctk.CTkLabel(self.resultado_frame, text="Ordem de Iniciativa", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
        btn_rolar = ctk.CTkButton(self.resultado_frame, text="ROLAR INICIATIVA", height=40, font=ctk.CTkFont(weight="bold"), fg_color="green", hover_color="darkgreen", command=self.roll_initiative)
        btn_rolar.pack(pady=10, fill="x", padx=20)
        
        btn_limpar = ctk.CTkButton(self.resultado_frame, text="Limpar Combate", fg_color="gray", command=self.clear_encounter)
        btn_limpar.pack(pady=5, fill="x", padx=20)
        
        self.encounter_list = ctk.CTkScrollableFrame(self.resultado_frame)
        self.encounter_list.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.refresh_combate_selectors()
        
    def refresh_combate_selectors(self):
        chars = get_all_characters()
        self.all_chars_map = {f"{c['name']} (Dex: {c['dex_modifier']})": c for c in chars}
        
        nomes = list(self.all_chars_map.keys())
        if not nomes:
            nomes = ["Nenhum"]
            
        self.combobox_chars.configure(values=nomes)
        if nomes:
            self.combobox_chars.set(nomes[0])
            
    def add_to_encounter(self):
        selecao = self.combobox_chars.get()
        if selecao == "Nenhum" or selecao not in self.all_chars_map:
            return
            
        char_data = self.all_chars_map[selecao]
        try:
            qtd = int(self.entry_qtd.get().strip())
        except ValueError:
            qtd = 1
            
        self.encounter.add_multiple_participants(char_data['id'], char_data['name'], char_data['type'], char_data['dex_modifier'], count=qtd)
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
        
    def refresh_encounter_view(self, show_rolls=False):
        for widget in self.encounter_list.winfo_children():
            widget.destroy()
            
        for idx, p in enumerate(self.encounter.participants):
            row = ctk.CTkFrame(self.encounter_list)
            row.pack(fill="x", pady=2, padx=2)
            
            # Formatação baseada se já rolou ou não
            if show_rolls:
                txt = f"{idx+1}º | {p.name} - Total: {p.initiative_total} (D20: {p.roll_result} + Dex: {p.dex_modifier})"
                # Destaque de cores (opcional)
                cor_texto = "yellow" if p.char_type == "Jogador" else "white"
            else:
                txt = f"- {p.name} ({p.char_type}) | Esperando rolagem..."
                cor_texto = "white"
                
            lbl = ctk.CTkLabel(row, text=txt, text_color=cor_texto, anchor="w", font=ctk.CTkFont(size=14))
            lbl.pack(side="left", padx=10, pady=8, fill="x", expand=True)

if __name__ == "__main__":
    app = App()
    app.mainloop()

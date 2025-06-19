import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
import toml
import os
from chat_ui import ChatClientUI

class ChatUIVisualizer:
    def __init__(self, master):
        self.master = master
        self.chat_ui = ChatClientUI()

        master.title("Chat-Client Benutzeroberfläche")
        master.geometry("1000x500")  # Breite erhöht für zusätzliche Benutzerliste

        self.setup_ui()

    def setup_ui(self):
        main_frame = tk.Frame(self.master)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # === Konfiguration (links) ===
        config_frame = tk.Frame(main_frame, bd=2, relief="groove")
        config_frame.pack(side="left", fill="y", padx=5, pady=5)

        tk.Label(config_frame, text="Konfiguration", font=("Arial", 12, "bold")).pack(pady=5)
        self.entries = {}

        for key, value in self.chat_ui.config.items():
            tk.Label(config_frame, text=key).pack(anchor="w", padx=5)
            entry = tk.Entry(config_frame, width=25)
            entry.insert(0, str(value))

            # 🔒 whoisport darf nicht bearbeitet werden
            if key == "whoisport":
                entry.config(state="disabled")

            entry.pack(padx=5, pady=2)
            self.entries[key] = entry

        tk.Button(config_frame, text="Konfiguration speichern", command=self.save_config).pack(pady=5)
        tk.Button(config_frame, text="Konfiguration anzeigen", command=self.show_config).pack(pady=2)

        # === Chatbereich (Mitte) ===
        chat_frame = tk.Frame(main_frame, bd=2, relief="groove")
        chat_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.chat_display = scrolledtext.ScrolledText(chat_frame, font=("Arial", 10), state="disabled")
        self.chat_display.pack(fill="both", expand=True, padx=5, pady=5)

        # === Eingabezeile ===
        input_frame = tk.Frame(chat_frame)
        input_frame.pack(fill="x", padx=5, pady=5)

        self.message_entry = tk.Entry(input_frame, width=60)
        self.message_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.message_entry.bind("<Return>", lambda e: self.send_message())

        send_btn = tk.Button(input_frame, text="Senden", command=self.send_message)
        send_btn.pack(side="right", padx=(5, 0))

        image_btn = tk.Button(input_frame, text="📁 Bild wählen", command=self.choose_image)
        image_btn.pack(side="right", padx=(0, 5))

        # === Benutzerliste (rechts) ===
        user_list_frame = tk.Frame(main_frame, bd=2, relief="groove")
        user_list_frame.pack(side="right", fill="y", padx=5, pady=5)

        tk.Label(user_list_frame, text="🟢 Online-Nutzer", font=("Arial", 12, "bold")).pack(pady=5)

        self.user_listbox = tk.Listbox(user_list_frame, height=15)
        self.user_listbox.pack(padx=5, pady=5, fill="y")
        self.user_listbox.bind("<<ListboxSelect>>", self.user_selected)

        # Dummy-Benutzerliste
        users = ["Alice", "Bob", "Charlie"]
        for user in users:
            self.user_listbox.insert(tk.END, user)

    def choose_image(self):
        filepath = filedialog.askopenfilename(title="Bild auswählen", filetypes=[("Bilder", "*.jpg *.jpeg *.png *.gif")])
        if filepath:
            filename = os.path.basename(filepath)
            self.add_system_message(f"Bild ausgewählt: {filename}")
            # Übergabe an Team für echten Versand möglich

    def save_config(self):
        for key, entry in self.entries.items():
            if key == "whoisport":
                continue
            value = entry.get().strip()
            if key == "port":
                self.chat_ui.config[key] = int(value)
            else:
                self.chat_ui.config[key] = value
        self.chat_ui.save_config(self.chat_ui.config)
        self.add_system_message("Konfiguration gespeichert.")

    def show_config(self):
        text = "\n--- Aktuelle Konfiguration ---\n"
        for key, value in self.chat_ui.config.items():
            text += f"{key}: {value}\n"
        self.add_system_message(text)

    def send_message(self):
        message = self.message_entry.get().strip()
        if message:
            self.chat_display.config(state="normal")
            self.chat_display.insert(tk.END, f"[Du] {message}\n")
            self.chat_display.config(state="disabled")
            self.chat_display.see(tk.END)
            self.message_entry.delete(0, tk.END)

    def add_system_message(self, message):
        self.chat_display.config(state="normal")
        self.chat_display.insert(tk.END, f"[System] {message}\n")
        self.chat_display.config(state="disabled")
        self.chat_display.see(tk.END)

    def user_selected(self, event):
        selection = event.widget.curselection()
        if selection:
            selected_user = event.widget.get(selection[0])
            self.add_system_message(f"Chat mit {selected_user} geöffnet.")

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatUIVisualizer(root)
    root.mainloop()
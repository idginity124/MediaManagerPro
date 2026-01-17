from PySide6.QtWidgets import QMessageBox

from plugin_interface import PluginInterface, PluginAction


class Plugin(PluginInterface):
    name = "Merhaba Eklentisi"
    version = "1.2"
    description = "Ekrana basit bir mesaj kutusu çıkarır (örnek eklenti)."

    def get_actions(self, main_window):
        # Bir eklenti tek bir aksiyonla sınırlı olmak zorunda değil.
        return [
            PluginAction(text="Merhaba de", callback=self.run, icon='fa5s.smile'),
            PluginAction(
                text="Hakkında",
                callback=lambda mw: QMessageBox.information(
                    mw,
                    "Merhaba Eklentisi",
                    "Bu sadece örnek bir eklenti.\n\nKendi eklentilerini 'plugins/' klasörüne koyabilirsin.",
                ),
                icon='fa5s.info-circle',
            ),
        ]

    def run(self, main_window):
        main_window.log("🔌 Merhaba Eklentisi çalıştırıldı!")
        QMessageBox.information(main_window, "Plugin", "Merhaba! Ben sonradan eklenen bir kodum :)")



class FolderPickerWindow:
    def __init__(self, selected_paths):
        self.selected_paths = selected_paths
        self.dialog_type = None
        self.directory = None

    def create_file_dialog(self, dialog_type, directory=""):
        self.dialog_type = dialog_type
        self.directory = directory
        return self.selected_paths

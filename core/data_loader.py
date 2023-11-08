import json


class DataLoader:
    @staticmethod
    def load_card_data(file):
        # Load card data from a file (e.g., JSON)
        with open(file, "rb") as f:
            card_data = json.loads(f.read())
        return card_data

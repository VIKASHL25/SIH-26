from pathlib import Path
import cantools

DBC_PATH = Path(__file__).with_name("engine_can.dbc")

def load_db():
    return cantools.database.load_file(str(DBC_PATH))

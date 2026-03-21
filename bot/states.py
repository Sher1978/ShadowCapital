from aiogram.fsm.state import State, StatesGroup

class AdminRegistration(StatesGroup):
    waiting_for_username = State()
    waiting_for_full_name = State()
    waiting_for_quality_name = State()
    waiting_for_scenario_type = State()
    waiting_for_timezone = State()
    waiting_for_confirmation = State()

class AdminStates(StatesGroup):
    waiting_for_reply_text = State()
    waiting_for_client_id = State()
    waiting_for_edit_selection = State()
    waiting_for_edit_quality = State()
    waiting_for_edit_scenario = State()
    waiting_for_edit_scenario_confirm = State()
    waiting_for_edit_day = State()
    waiting_for_edit_day_confirm = State()

class ClientStates(StatesGroup):
    waiting_for_log = State()
    waiting_for_log_confirmation = State()

class ClientSettings(StatesGroup):
    waiting_for_edit_name = State()
    waiting_for_edit_timezone = State()

class SettingsState(StatesGroup):
    waiting_for_time = State()
    waiting_for_time_type = State()

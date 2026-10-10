import single_instance
from settings import SETTINGS_FILE

if __name__ == "__main__":
    # Vor dem Import von gui: der zieht faster-whisper samt nativen Bibliotheken
    # nach und braucht Sekunden - eine zweite Instanz soll sofort weiterreichen.
    lock_dir = SETTINGS_FILE.parent
    guard = single_instance.acquire(lock_dir)
    if guard is None:
        if single_instance.wake_running_instance(lock_dir):
            print("Das Diktiertool läuft bereits – das vorhandene Fenster wurde nach vorne geholt.")
        else:
            print("Das Diktiertool läuft bereits, das Fenster ließ sich aber nicht nach vorne holen.")
    else:
        from gui import main
        main(guard)

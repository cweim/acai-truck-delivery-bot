"""One-time cleanup: close delivery sessions past their cutoff time."""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.supabase_client import get_db


def main() -> None:
    db = get_db()
    closed_count = db.auto_close_cutoff_sessions()
    print(f"Auto-closed {closed_count} delivery session(s).")


if __name__ == "__main__":
    main()

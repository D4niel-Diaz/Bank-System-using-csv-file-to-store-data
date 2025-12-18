import csv
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

# file use to store the data(users.csv and transactions.csv)
BASE_DIR = Path(__file__).resolve().parent
USERS_FILE = BASE_DIR / "users.csv"
TRANSACTIONS_FILE = BASE_DIR / "transactions.csv"

# Initialize the files
def _ensure_headers(file_path: Path, headers: list[str]):
    """Make sure a CSV file exists and starts with the expected headers."""
    if not file_path.exists():
        with file_path.open(mode="w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(headers)
        return

    # If headers are missing or wrong, rewrite them and keep existing rows.
    with file_path.open(mode="r", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    if rows and rows[0] == headers:
        return

    with file_path.open(mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        # If the previous first row looked like headers, drop it; else keep all rows.
        start_idx = 1 if rows and set(rows[0]) == set(headers) else 0
        for row in rows[start_idx:]:
            if row:  # skip empty lines
                writer.writerow(row)


def initialize_files():
    "Create necessary CSV files with headers if they don't exist."
    _ensure_headers(USERS_FILE, ["username", "password", "balance"])
    _ensure_headers(TRANSACTIONS_FILE, ["username", "date", "type", "amount", "balance", "details"])

def _normalize_decimal(value: Decimal) -> Decimal:
    """Keep money values at 2 decimal places. Falls back to 0.00 on invalid."""
    try:
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return Decimal("0.00")


# User Creation and Login
def user_exists(username: str) -> bool:
    if not USERS_FILE.exists():
        return False
    with USERS_FILE.open(mode="r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return any(row["username"] == username for row in reader)

#User Registration
def register():
    print("\n=== Register ===")
    username = input("Choose a username: ").strip()
    if not username:
        print("Username cannot be empty.")
        return

    if user_exists(username):
        print("Username already exists. Please choose another.")
        return

    password = input("Choose a password: ").strip()
    if not password:
        print("Password cannot be empty.")
        return

    with USERS_FILE.open(mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([username, password, "0.00"])
    print(f"Account created for {username}. You can now log in.")

def login():
    print("\n=== Login ===")
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    with USERS_FILE.open(mode="r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["username"] == username and row["password"] == password:
                print(f"Welcome back, {username}!")
                return username
    print("Invalid credentials. Please try again.")
    return None

# Balance Check and Update
def get_balance(username: str) -> Decimal:
    with USERS_FILE.open(mode="r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["username"] == username:
                try:
                    return _normalize_decimal(Decimal(row["balance"]))
                except InvalidOperation:
                    return Decimal("0.00")
    return Decimal("0.00")

#Update balance
def update_balance(username: str, new_balance: Decimal):
    new_balance = _normalize_decimal(new_balance)
    rows = []
    with USERS_FILE.open(mode="r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    with USERS_FILE.open(mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["username", "password", "balance"])
        writer.writeheader()
        for row in rows:
            if row["username"] == username:
                row["balance"] = f"{new_balance:.2f}"
            writer.writerow(row)

#Trnscation and record
def add_transaction(username: str, tx_type: str, amount: Decimal, balance: Decimal, details: str = ""):
    amount = _normalize_decimal(amount)
    balance = _normalize_decimal(balance)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with TRANSACTIONS_FILE.open(mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([username, timestamp, tx_type, f"{amount:.2f}", f"{balance:.2f}", details])

#Input amount
MAX_AMOUNT = Decimal("100000.00")
def _input_amount(prompt: str) -> Decimal | None:
    raw = input(prompt).strip()
    try:
        amount = Decimal(raw)
    except InvalidOperation:
        print("Please enter a valid number.")
        return None

    if amount <= 0:
        print("Amount must be greater than zero.")
        return None
    if amount > MAX_AMOUNT:
        print(f"Amount must be less than {MAX_AMOUNT:.2f}.")
        return None
    try:
        return _normalize_decimal(amount)
    except InvalidOperation:
        print("Amount is too large or invalid.")
        return None


# User Interaction Menu
def _repeat_or_back(label: str, allow_repeat: bool = True) -> bool:
    """Ask the user if they want to repeat the same action or go back.
    Returns True if the user wants to repeat, False to go back."""
    while True:
        if allow_repeat:
            choice = input(f"Press Enter to {label} again or 'b' to go back: ").strip().lower()
            if choice == "":
                return True
            if choice == "b":
                return False
        else:
            choice = input("Press 'b' then Enter to go back: ").strip().lower()
            if choice == "b" or choice == "":
                return False
        print("Invalid option.")


#Banking operations and record
def deposit(current_user: str):
    while True:
        print("\n=== Deposit ===")
        amount = _input_amount("Enter amount to deposit: ")
        if amount is None:
            if not _repeat_or_back("deposit"):
                return
            continue

        balance = get_balance(current_user) + amount
        update_balance(current_user, balance)
        add_transaction(current_user, "DEPOSIT", amount, balance, "Cash deposit")
        print(f"Deposited {amount:.2f}. New balance: {balance:.2f}.")

        if not _repeat_or_back("deposit"):
            return


def withdraw(current_user: str):
    while True:
        print("\n=== Withdraw ===")
        amount = _input_amount("Enter amount to withdraw: ")
        if amount is None:
            if not _repeat_or_back("withdraw"):
                return
            continue

        balance = get_balance(current_user)
        if amount > balance:
            print("Insufficient balance.")
            if not _repeat_or_back("withdraw"):
                return
            continue

        balance -= amount
        update_balance(current_user, balance)
        add_transaction(current_user, "WITHDRAW", amount, balance, "Cash withdrawal")
        print(f"Withdrew {amount:.2f}. New balance: {balance:.2f}.")

        if not _repeat_or_back("withdraw"):
            return

#Transfer money
def transfer(current_user: str):
    while True:
        print("\n=== Transfer ===")
        recipient = input("Enter recipient username: ").strip()
        if recipient == current_user:
            print("You cannot transfer to yourself.")
            if not _repeat_or_back("transfer"):
                return
            continue
        if not user_exists(recipient):
            print("Recipient does not exist.")
            if not _repeat_or_back("transfer"):
                return
            continue

        amount = _input_amount("Enter amount to transfer: ")
        if amount is None:
            if not _repeat_or_back("transfer"):
                return
            continue

        sender_balance = get_balance(current_user)
        if amount > sender_balance:
            print("Insufficient balance.")
            if not _repeat_or_back("transfer"):
                return
            continue

        recipient_balance = get_balance(recipient)

        # Update balances
        update_balance(current_user, sender_balance - amount)
        update_balance(recipient, recipient_balance + amount)

        # Record transactions
        add_transaction(current_user, "TRANSFER OUT", amount, sender_balance - amount, f"To {recipient}")
        add_transaction(recipient, "TRANSFER IN", amount, recipient_balance + amount, f"From {current_user}")

        print(f"Transferred {amount:.2f} to {recipient}. Your new balance: {(sender_balance - amount):.2f}.")

        if not _repeat_or_back("transfer"):
            return

#Check balance
def check_balance(current_user: str):
    balance = get_balance(current_user)
    print(f"\nCurrent balance: {balance:.2f}")
    _repeat_or_back("check balance", allow_repeat=False)

#Transaction history
def transaction_history(current_user: str):
    print("\n=== Transaction History ===")
    if not TRANSACTIONS_FILE.exists():
        print("No transactions found.")
        return

    with TRANSACTIONS_FILE.open(mode="r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        records = [row for row in reader if row["username"] == current_user]

    if not records:
        print("No transactions found.")
        return

    print(f"{'Date':19} | {'Type':12} | {'Amount':10} | {'Balance':10} | Details")
    print("-" * 70)
    for row in records:
        print(f"{row['date']:19} | {row['type']:12} | {row['amount']:10} | {row['balance']:10} | {row['details']}")

    _repeat_or_back("view transactions", allow_repeat=False)


# Main Menu for user to choose the operation
def main_menu(mel_user: str):
    while True:
        print("\n=== Mel Banking System ====")
        print("1. Deposit")
        print("2. Withdraw")
        print("3. Transfer")
        print("4. Check Balance")
        print("5. Transaction History")
        print("6. Logout")

        choice = input("Choose an option (1-6): ").strip()

        if choice == "1":
            deposit(mel_user)
        elif choice == "2":
            withdraw(mel_user)
        elif choice == "3":
            transfer(mel_user)
        elif choice == "4":
            check_balance(mel_user)
        elif choice == "5":
            transaction_history(mel_user)
        elif choice == "6":
            print("Logging out...\n")
            break
        else:
            print("Invalid option. Please choose 1-6.")


def main():
    initialize_files()
    while True:
        print("\n=== Mel Banking System ===")
        print("1. Register")
        print("2. Login")
        print("3. Exit")
        choice = input("Choose an option (1-3): ").strip()

        if choice == "1":
            register()
        elif choice == "2":
            user = login()
            if user:
                main_menu(user)
        elif choice == "3":
            print("Goodbye!")
            break
        else:
            print("Invalid option. Please choose 1-3.")


if __name__ == "__main__":
    main()

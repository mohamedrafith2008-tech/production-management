import sqlite3
import sys
from werkzeug.security import generate_password_hash

def add_or_update_user(username, password, full_name, email, role):
    valid_roles = ['admin', 'prod_manager', 'shift_supervisor', 'quality_inspector', 'store_keeper']
    if role not in valid_roles:
        print(f"Error: Role must be one of {valid_roles}")
        return

    conn = sqlite3.connect('mpms.db')
    cursor = conn.cursor()
    
    password_hash = generate_password_hash(password)

    cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
    existing_user = cursor.fetchone()

    if existing_user:
        cursor.execute('''
            UPDATE users 
            SET password_hash = ?, full_name = ?, email = ?, role = ?
            WHERE username = ?
        ''', (password_hash, full_name, email, role, username))
        print(f"User '{username}' updated successfully.")
    else:
        cursor.execute('''
            INSERT INTO users (username, password_hash, full_name, email, role)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, password_hash, full_name, email, role))
        print(f"User '{username}' created successfully.")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    if len(sys.argv) < 6:
        print("Usage: python update_users.py <username> <password> <full_name> <email> <role>")
        print("Roles: admin | prod_manager | shift_supervisor | quality_inspector | store_keeper")
    else:
        add_or_update_user(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
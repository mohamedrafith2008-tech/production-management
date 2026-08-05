import sqlite3
from werkzeug.security import generate_password_hash

def init_db():
    conn = sqlite3.connect('mpms.db')
    cursor = conn.cursor()

    # Create Users table (Role-Based Access Control)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            role TEXT CHECK(role IN ('admin', 'prod_manager', 'shift_supervisor', 'quality_inspector', 'store_keeper')) NOT NULL
        )
    ''')

    # Create Machines table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS machines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            status TEXT CHECK(status IN ('Running', 'Idle', 'Downtime')) DEFAULT 'Idle',
            total_runtime_hrs REAL DEFAULT 0.0,
            downtime_hrs REAL DEFAULT 0.0
        )
    ''')

    # Create Raw Materials table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS raw_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE NOT NULL,
            material_name TEXT NOT NULL,
            quantity REAL NOT NULL DEFAULT 0.0,
            reorder_level REAL NOT NULL DEFAULT 100.0,
            unit TEXT NOT NULL DEFAULT 'kg'
        )
    ''')

    # Create Production Schedules table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS production_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_code TEXT UNIQUE NOT NULL,
            product_name TEXT NOT NULL,
            target_quantity INTEGER NOT NULL,
            machine_id INTEGER,
            assigned_by INTEGER NOT NULL,
            status TEXT CHECK(status IN ('Scheduled', 'In Production', 'Completed', 'Cancelled')) DEFAULT 'Scheduled',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (machine_id) REFERENCES machines(id),
            FOREIGN KEY (assigned_by) REFERENCES users(id)
        )
    ''')

    # Create Quality Inspections table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quality_inspections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_id INTEGER NOT NULL,
            inspector_id INTEGER NOT NULL,
            result TEXT CHECK(result IN ('Pass', 'Fail', 'Rework')) NOT NULL,
            defect_type TEXT DEFAULT 'None',
            notes TEXT,
            inspected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (schedule_id) REFERENCES production_schedules(id),
            FOREIGN KEY (inspector_id) REFERENCES users(id)
        )
    ''')

    # Seed Default Users for All Roles
    users_seed = [
        ('admin', generate_password_hash('admin123'), 'A. Mohamed Rafith (Admin)', 'admin@factory.com', 'admin'),
        ('pm_user', generate_password_hash('pm123'), 'Production Manager', 'pm@factory.com', 'prod_manager'),
        ('sup_user', generate_password_hash('sup123'), 'Shift Supervisor', 'supervisor@factory.com', 'shift_supervisor'),
        ('qi_user', generate_password_hash('qi123'), 'Quality Inspector', 'quality@factory.com', 'quality_inspector'),
        ('sk_user', generate_password_hash('sk123'), 'Store Keeper', 'inventory@factory.com', 'store_keeper')
    ]

    for user in users_seed:
        try:
            cursor.execute('''
                INSERT INTO users (username, password_hash, full_name, email, role)
                VALUES (?, ?, ?, ?, ?)
            ''', user)
        except sqlite3.IntegrityError:
            pass

    # Seed Initial Machines
    machines_seed = [
        ('MCH-101', 'CNC Milling Station A', 'Running', 120.5, 4.0),
        ('MCH-102', 'Automated Lathe B', 'Idle', 85.0, 12.5),
        ('MCH-103', 'Hydraulic Press C', 'Downtime', 45.0, 18.0)
    ]

    for mch in machines_seed:
        try:
            cursor.execute('''
                INSERT INTO machines (machine_code, name, status, total_runtime_hrs, downtime_hrs)
                VALUES (?, ?, ?, ?, ?)
            ''', mch)
        except sqlite3.IntegrityError:
            pass

    # Seed Initial Raw Materials
    materials_seed = [
        ('MAT-STEEL-01', 'Stainless Steel Sheets (3mm)', 450.0, 100.0, 'sheets'),
        ('MAT-ALUM-02', 'Aluminum Rods (10mm)', 80.0, 150.0, 'units'),  # Low stock trigger
        ('MAT-POLY-03', 'Industrial Polymer Resin', 1200.0, 300.0, 'kg')
    ]

    for mat in materials_seed:
        try:
            cursor.execute('''
                INSERT INTO raw_materials (sku, material_name, quantity, reorder_level, unit)
                VALUES (?, ?, ?, ?, ?)
            ''', mat)
        except sqlite3.IntegrityError:
            pass

    # Seed Initial Production Schedules
    schedules_seed = [
        ('SCH-9001', 'Gearbox Casing Type-A', 500, 1, 2, 'In Production'),
        ('SCH-9002', 'Engine Bracket Shaft', 250, 2, 2, 'Scheduled'),
        ('SCH-9003', 'Exhaust Flange Mount', 1000, 3, 2, 'Completed')
    ]

    for sch in schedules_seed:
        try:
            cursor.execute('''
                INSERT INTO production_schedules (schedule_code, product_name, target_quantity, machine_id, assigned_by, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', sch)
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()
    print("MPMS Database initialized successfully with role-based seed data.")

if __name__ == '__main__':
    init_db()
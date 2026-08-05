import sqlite3
import random
import string
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.secret_key = 'mpms_industrial_production_secret_key'

def get_db_connection():
    conn = sqlite3.connect('mpms.db')
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Session expired or login required.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def roles_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get('role') not in allowed_roles and session.get('role') != 'admin':
                flash('Unauthorized access for your assigned role.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def generate_schedule_code():
    digits = ''.join(random.choices(string.digits, k=4))
    return f"SCH-{digits}"

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            flash(f'Welcome back, {user["full_name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()

    total_schedules = conn.execute('SELECT COUNT(*) FROM production_schedules').fetchone()[0]
    active_schedules = conn.execute("SELECT COUNT(*) FROM production_schedules WHERE status = 'In Production'").fetchone()[0]
    total_machines = conn.execute('SELECT COUNT(*) FROM machines').fetchone()[0]
    running_machines = conn.execute("SELECT COUNT(*) FROM machines WHERE status = 'Running'").fetchone()[0]
    low_stock_alerts = conn.execute('SELECT COUNT(*) FROM raw_materials WHERE quantity <= reorder_level').fetchone()[0]

    recent_schedules = conn.execute('''
        SELECT ps.*, m.name as machine_name, u.full_name as manager_name
        FROM production_schedules ps
        LEFT JOIN machines m ON ps.machine_id = m.id
        LEFT JOIN users u ON ps.assigned_by = u.id
        ORDER BY ps.created_at DESC LIMIT 5
    ''').fetchall()

    conn.close()

    stats = {
        'total_schedules': total_schedules,
        'active_schedules': active_schedules,
        'total_machines': total_machines,
        'running_machines': running_machines,
        'low_stock_alerts': low_stock_alerts
    }

    return render_template('dashboard.html', stats=stats, schedules=recent_schedules)

@app.route('/schedules')
@login_required
def schedules():
    search_query = request.args.get('q', '').strip()
    conn = get_db_connection()

    if search_query:
        query = '''
            SELECT ps.*, m.name as machine_name, u.full_name as manager_name
            FROM production_schedules ps
            LEFT JOIN machines m ON ps.machine_id = m.id
            LEFT JOIN users u ON ps.assigned_by = u.id
            WHERE ps.schedule_code LIKE ? OR ps.product_name LIKE ? OR ps.status LIKE ?
            ORDER BY ps.created_at DESC
        '''
        term = f"%{search_query}%"
        schedules_list = conn.execute(query, (term, term, term)).fetchall()
    else:
        schedules_list = conn.execute('''
            SELECT ps.*, m.name as machine_name, u.full_name as manager_name
            FROM production_schedules ps
            LEFT JOIN machines m ON ps.machine_id = m.id
            LEFT JOIN users u ON ps.assigned_by = u.id
            ORDER BY ps.created_at DESC
        ''').fetchall()

    conn.close()
    return render_template('schedules.html', schedules=schedules_list, search_query=search_query)

@app.route('/schedule/new', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'prod_manager')
def create_schedule():
    conn = get_db_connection()
    machines = conn.execute("SELECT * FROM machines").fetchall()

    if request.method == 'POST':
        product_name = request.form['product_name']
        target_quantity = request.form['target_quantity']
        machine_id = request.form.get('machine_id') or None
        schedule_code = generate_schedule_code()

        conn.execute('''
            INSERT INTO production_schedules (schedule_code, product_name, target_quantity, machine_id, assigned_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (schedule_code, product_name, target_quantity, machine_id, session['user_id']))
        
        conn.commit()
        conn.close()
        flash(f'Production Schedule {schedule_code} generated successfully.', 'success')
        return redirect(url_for('schedules'))

    conn.close()
    return render_template('generic_form.html', form_type='create_schedule', machines=machines)

@app.route('/schedule/update_status/<int:schedule_id>', methods=['POST'])
@login_required
@roles_required('admin', 'prod_manager', 'shift_supervisor')
def update_schedule_status(schedule_id):
    new_status = request.form.get('status')
    conn = get_db_connection()
    conn.execute('UPDATE production_schedules SET status = ? WHERE id = ?', (new_status, schedule_id))
    conn.commit()
    conn.close()
    flash(f'Schedule status updated to {new_status}.', 'info')
    return redirect(request.referrer or url_for('schedules'))

@app.route('/machines')
@login_required
def machines():
    conn = get_db_connection()
    machines_list = conn.execute('SELECT * FROM machines').fetchall()
    conn.close()
    return render_template('machines.html', machines=machines_list)

@app.route('/machine/log_runtime/<int:machine_id>', methods=['POST'])
@login_required
@roles_required('admin', 'shift_supervisor')
def log_machine_runtime(machine_id):
    added_runtime = float(request.form.get('runtime_hrs', 0))
    added_downtime = float(request.form.get('downtime_hrs', 0))
    new_status = request.form.get('status')

    conn = get_db_connection()
    conn.execute('''
        UPDATE machines 
        SET total_runtime_hrs = total_runtime_hrs + ?, 
            downtime_hrs = downtime_hrs + ?, 
            status = ?
        WHERE id = ?
    ''', (added_runtime, added_downtime, new_status, machine_id))
    conn.commit()
    conn.close()
    flash('Machine operation log updated.', 'success')
    return redirect(url_for('machines'))

@app.route('/inspections')
@login_required
def inspections():
    conn = get_db_connection()
    inspections_list = conn.execute('''
        SELECT qi.*, ps.schedule_code, ps.product_name, u.full_name as inspector_name
        FROM quality_inspections qi
        JOIN production_schedules ps ON qi.schedule_id = ps.id
        JOIN users u ON qi.inspector_id = u.id
        ORDER BY qi.inspected_at DESC
    ''').fetchall()
    conn.close()
    return render_template('inspections.html', inspections=inspections_list)

@app.route('/inspection/new', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'quality_inspector')
def create_inspection():
    conn = get_db_connection()
    schedules = conn.execute("SELECT id, schedule_code, product_name FROM production_schedules").fetchall()

    if request.method == 'POST':
        schedule_id = request.form['schedule_id']
        result = request.form['result']
        defect_type = request.form.get('defect_type', 'None')
        notes = request.form.get('notes', '')

        conn.execute('''
            INSERT INTO quality_inspections (schedule_id, inspector_id, result, defect_type, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (schedule_id, session['user_id'], result, defect_type, notes))
        
        conn.commit()
        conn.close()
        flash('Quality inspection logged successfully.', 'success')
        return redirect(url_for('inspections'))

    conn.close()
    return render_template('generic_form.html', form_type='create_inspection', schedules=schedules)

@app.route('/inventory')
@login_required
def inventory():
    conn = get_db_connection()
    materials = conn.execute('SELECT * FROM raw_materials').fetchall()
    conn.close()
    return render_template('inventory.html', materials=materials)

@app.route('/inventory/update/<int:material_id>', methods=['POST'])
@login_required
@roles_required('admin', 'store_keeper')
def update_inventory(material_id):
    added_qty = float(request.form.get('quantity_change', 0))
    conn = get_db_connection()
    conn.execute('UPDATE raw_materials SET quantity = quantity + ? WHERE id = ?', (added_qty, material_id))
    conn.commit()
    conn.close()
    flash('Stock quantity updated successfully.', 'success')
    return redirect(url_for('inventory'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
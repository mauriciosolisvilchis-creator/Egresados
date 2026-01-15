from flask import Flask, render_template, request, redirect, url_for, session, flash
import config
from database.db import get_connection, get_db, init_db, close_db

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.teardown_appcontext(close_db)

# Inicializar esquema al arrancar (esto también hará que funcione al usar gunicorn en Render)
with app.app_context():
    init_db()

# Carreras precargadas
CAREER_OPTIONS = [
    "Ingeniería en Sistemas Computacionales",
    "Ingeniería en Innovación Agrícola Sustentable",
    "Licenciatura en Contaduría"
]

# -----------------
# Funciones de DB (compatibles con SQLite y Postgres)
# -----------------
import os
DATABASE_URL = os.environ.get('DATABASE_URL')


def db_execute(query, params=(), fetchone=False, fetchall=False, commit=False):
    """Ejecuta una consulta adaptando placeholders según el motor y devuelve resultados opcionales."""
    conn = get_db()
    c = conn.cursor()
    q = query
    if DATABASE_URL:
        # psycopg2 usa %s
        q = q.replace('?', '%s')
    c.execute(q, params)
    result = None
    if fetchone:
        result = c.fetchone()
    if fetchall:
        result = c.fetchall()
    if commit:
        conn.commit()
    return result


def add_egresado(matricula, nombre_completo, carrera=None, generacion=None,
                 estatus=None, domicilio=None, genero=None, telefono=None,
                 correo_electronico=None):
    db_execute(
        """
        INSERT INTO egresados (matricula, nombre_completo, carrera, generacion, estatus, domicilio, genero, telefono, correo_electronico)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (matricula, nombre_completo, carrera, generacion, estatus, domicilio, genero, telefono, correo_electronico),
        commit=True,
    )


def update_egresado(matricula, nombre_completo, carrera=None, generacion=None,
                    estatus=None, domicilio=None, genero=None, telefono=None,
                    correo_electronico=None):
    db_execute(
        """
        UPDATE egresados SET nombre_completo=?, carrera=?, generacion=?, estatus=?, domicilio=?, genero=?, telefono=?, correo_electronico=?
        WHERE matricula=?
        """,
        (nombre_completo, carrera, generacion, estatus, domicilio, genero, telefono, correo_electronico, matricula),
        commit=True,
    )


def get_egresado(matricula):
    row = db_execute("SELECT * FROM egresados WHERE matricula = ?", (matricula,), fetchone=True)
    return row


def delete_egresado(matricula):
    db_execute("DELETE FROM egresados WHERE matricula = ?", (matricula,), commit=True)


def list_egresados():
    rows = db_execute("SELECT * FROM egresados ORDER BY nombre_completo", fetchall=True)
    return rows

# -----------------
# Autenticación
# -----------------


def login_required(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('login', next=request.url))
        response = f(*args, **kwargs)
        # Agregar headers para prevenir caché y que no se pueda volver atrás
        if isinstance(response, str):
            from flask import make_response
            response = make_response(response)
        elif not hasattr(response, 'headers'):
            from flask import make_response
            response = make_response(response)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    return decorated


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == config.ADMIN_USER and password == config.ADMIN_PASS:
            session['admin'] = True
            flash('Bienvenido, administrador.', 'success')
            next_url = request.args.get('next') or url_for('dashboard')
            return redirect(next_url)
        else:
            flash('Credenciales inválidas', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('admin', None)
    flash('Sesión cerrada', 'info')
    return redirect(url_for('login'))


@app.route('/')
@login_required
def dashboard():
    # Obtener conteos por carrera (compatible con SQLite y Postgres)
    rows = db_execute("SELECT carrera, COUNT(*) as cnt FROM egresados GROUP BY carrera", fetchall=True)

    # db_execute devuelve filas como dict-like (RealDictCursor en Postgres o sqlite3.Row)
    counts_map = {}
    for r in rows:
        try:
            carrera = r['carrera'] or ''
            cnt = r['cnt']
        except Exception:
            # tuple fallback
            carrera = r[0] or ''
            cnt = r[1]
        counts_map[carrera] = cnt

    labels = CAREER_OPTIONS.copy()
    values = [counts_map.get(c, 0) for c in labels]

    # Sumar otros
    otros = sum(v for k, v in counts_map.items() if k not in labels)
    if otros:
        labels.append('Otros')
        values.append(otros)

    total = sum(values)
    return render_template('dashboard.html', total=total, labels=labels, values=values)


# -----------------
# Rutas CRUD
# -----------------


@app.route('/egresados')
@login_required
def egresados_list():
    q = request.args.get('q', '').strip()
    if q:
        like = f"%{q}%"
        rows = db_execute(
            "SELECT * FROM egresados WHERE matricula LIKE ? OR nombre_completo LIKE ? OR carrera LIKE ? OR correo_electronico LIKE ? ORDER BY nombre_completo",
            (like, like, like, like),
            fetchall=True,
        )
    else:
        rows = db_execute("SELECT * FROM egresados ORDER BY nombre_completo", fetchall=True)
    return render_template('egresados_list.html', egresados=rows, q=q)


@app.route('/egresados/new', methods=['GET', 'POST'])
@login_required
def egresado_new():
    if request.method == 'POST':
        data = {k: request.form.get(k) for k in ['matricula', 'nombre_completo', 'carrera', 'generacion', 'estatus', 'domicilio', 'genero', 'telefono', 'correo_electronico']}
        try:
            add_egresado(**data)
            flash('Egresado creado', 'success')
            return redirect(url_for('egresados_list'))
        except Exception as e:
            flash(f'Error: {e}', 'danger')
    return render_template('egresado_form.html', action='Crear', egresado=None, carreras=CAREER_OPTIONS)


@app.route('/egresados/edit/<matricula>', methods=['GET', 'POST'])
@login_required
def egresado_edit(matricula):
    eg = get_egresado(matricula)
    if not eg:
        flash('No encontrado', 'warning')
        return redirect(url_for('egresados_list'))
    if request.method == 'POST':
        data = {k: request.form.get(k) for k in ['nombre_completo', 'carrera', 'generacion', 'estatus', 'domicilio', 'genero', 'telefono', 'correo_electronico']}
        try:
            update_egresado(matricula, data['nombre_completo'], data['carrera'], data['generacion'], data['estatus'], data['domicilio'], data['genero'], data['telefono'], data['correo_electronico'])
            flash('Egresado actualizado', 'success')
            return redirect(url_for('egresados_list'))
        except Exception as e:
            flash(f'Error: {e}', 'danger')
    return render_template('egresado_form.html', action='Editar', egresado=eg, carreras=CAREER_OPTIONS)


@app.route('/egresados/delete/<matricula>', methods=['POST'])
@login_required
def egresado_delete(matricula):
    try:
        delete_egresado(matricula)
        flash('Egresado eliminado', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('egresados_list'))


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
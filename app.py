from flask import Flask, render_template, jsonify, request
from datetime import datetime
import pymysql
import pymysql.cursors

app = Flask(__name__)

DB_CONFIG = {
    'host': 'localhost',
    'user': 'iotuser',
    'password': 'iotpassword',
    'database': 'smarthome'
}

def get_db():
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)

# ─── ROUTES ───────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/latest')
def get_latest():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM sensor_data 
        ORDER BY timestamp DESC LIMIT 1
    """)
    data = cursor.fetchone()
    conn.close()
    if data:
        data['timestamp'] = str(data['timestamp'])
    return jsonify(data or {})

@app.route('/api/history')
def get_history():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM sensor_data 
        ORDER BY timestamp DESC LIMIT 20
    """)
    rows = cursor.fetchall()
    conn.close()
    for row in rows:
        row['timestamp'] = str(row['timestamp'])
    return jsonify(rows)

@app.route('/api/analytics')
def get_analytics():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT 
            ROUND(AVG(temperature), 2) as avg_temp,
            ROUND(MIN(temperature), 2) as min_temp,
            ROUND(MAX(temperature), 2) as max_temp,
            ROUND(AVG(humidity), 2) as avg_humidity,
            ROUND(MIN(humidity), 2) as min_humidity,
            ROUND(MAX(humidity), 2) as max_humidity,
            ROUND(AVG(light_level), 2) as avg_light,
            MIN(light_level) as min_light,
            MAX(light_level) as max_light,
            COUNT(*) as total_readings
        FROM sensor_data
    """)
    data = cursor.fetchone()
    conn.close()
    return jsonify(data or {})

@app.route('/api/rules', methods=['GET'])
def get_rules():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM rules ORDER BY id DESC LIMIT 1")
    rule = cursor.fetchone()
    conn.close()
    if rule:
        rule['updated_at'] = str(rule['updated_at'])
    return jsonify(rule or {})

@app.route('/api/rules', methods=['POST'])
def update_rules():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE rules SET 
            temp_threshold = %s,
            humidity_threshold = %s,
            light_threshold = %s,
            updated_at = NOW()
        WHERE id = (SELECT MAX(id) FROM (SELECT id FROM rules) as r)
    """, (data['temp_threshold'], data['humidity_threshold'], data['light_threshold']))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'message': 'Rules updated successfully!'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)

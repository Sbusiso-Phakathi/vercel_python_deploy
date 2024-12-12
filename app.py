import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import face_recognition
from PIL import Image
import numpy as np
import io
import psycopg2
from datetime import date, datetime
from dotenv import load_dotenv
import pickle

load_dotenv()
app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})

project_dir = os.path.dirname(os.path.abspath(__file__))  
images_dir = os.path.join(project_dir, "images")
known_faces = []

def get_db_connection():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        port=os.environ.get("DB_PORT"),
        password=os.environ.get("DB_PASSWORD")
    )

def load_known_faces():
    global known_faces
    try:
        for file_name in os.listdir(images_dir):
            file_path = os.path.join(images_dir, file_name)
            
            try:
                with Image.open(file_path).convert("RGB") as image:
                    image_np = np.array(image)
                    
                    unknown_encodings = face_recognition.face_encodings(image_np)
                    
                    if unknown_encodings:
                        known_faces.append({
                            "name": file_name[0:-4],
                            "encoding": unknown_encodings[0],
                            "image": "sbu",
                        })
                    else:
                        print(f"No faces found in {file_name}")
            except Exception as e:
                print(f"Error processing file {file_name}: {e}")

    except Exception as e:
        print(f"Error loading known faces: {e}")

@app.route('/recognize-face', methods=['POST'])
def recognize_face():
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400

    image_file = request.files['image']
    image = Image.open(image_file.stream).convert("RGB")
    image_np = np.array(image)

    unknown_encodings = face_recognition.face_encodings(image_np)
    
    faces_data = []

    if unknown_encodings:
        unknown_encoding = unknown_encodings[0]

        matched = False
        for known_face in known_faces:
            results = face_recognition.compare_faces([known_face["encoding"]], unknown_encoding, tolerance=0.39)
            if results[0]:
                matched = True
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    current_date = date.today()
                    current_datetime = datetime.now()
                    # print(known_face["name"])
                    cur.execute(
                        "SELECT attendance FROM learners WHERE email = %s",
                        (known_face['name'],)
                    )
                    result = list(cur.fetchone()[0])
                    print(known_face["name"])

                    marker = int(str(current_datetime)[11:13])
                    print("ssfd")

                    if marker >= 8 :
                        result[int(str(current_date)[8:10]) - 1] = "U"
                    else :
                        result[int(str(current_date)[8:10]) - 1] = "Y"

                    result  = "{" + ",".join(f"{item}" for item in result) + "}"

                    print(result)

                    # if result:
                    #     cur.execute(
                    #         '''UPDATE learners 
                    #            SET attendance = %s
                    #            WHERE email = %s''',
                    #         (result, known_face['name'],)
                    #     )
                    #     conn.commit()

                    faces_data.append({
                        "status": "ok",
                        "name": known_face["name"],
                        "time":  current_datetime
                    })
                except Exception as e:
                    return jsonify({"error": str(e)}), 500
                # finally:
                #     if conn:
                #         cur.close()
                #         conn.close()
                break

        if not matched:
            faces_data.append({
                "status": "bad",
                "name": "Unknown",
            })

    return jsonify({"faces": faces_data})

@app.route('/cohorts', methods=['POST'])
def cohorts():

    cohortname = request.form.get('cohortname')
    siteid = request.form.get('siteid')


    if not cohortname or not siteid:
        return jsonify({"error": "Name and ID are required"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            '''INSERT INTO cohorts ( cohortname, site_id)
               VALUES (%s, %s)''',
            (cohortname, int(siteid))
        )
        conn.commit()

        return jsonify({"message": "ok"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            cur.close()
            conn.close()


@app.route('/upload-image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image part in the request"}), 400

    image_file = request.files['image']
    image = Image.open(image_file.stream).convert("RGB")
    image_np = np.array(image)

    name = request.form.get('name')
    surname = request.form.get('surname')
    lid = request.form.get('learnernumber')
    cohort = request.form.get('cohort')
    email = request.form.get('email')

    unknown_encodings = face_recognition.face_encodings(image_np)
    array_data = pickle.dumps(unknown_encodings)

    if not os.path.exists(images_dir):
        os.makedirs(images_dir)

    file_name = email+".jpg"

    file_path = os.path.join(images_dir, file_name)

    image.save(file_path)  

    print(f"Image saved to {file_path}")

    if not name:
        return jsonify({"error": "Name and ID are required"}), 400

    try:
        image_data = image_file.read()
        conn = get_db_connection()
        cur = conn.cursor()
        print(image_file)

        # cur.execute(
        #     '''INSERT INTO learners ( name, surname, lid, cohort_id, email, image_data, attendance, jan, feb, mar, apr, may, jun, jul, aug, sep, oct, nov, dec)
        #        VALUES (%s, %s, %s, %s, %s, %s, %s,%s, %s, %s, %s, %s, %s,%s, %s, %s, %s, %s, %s)''',
        #     (name, surname, int(lid), int(cohort), email, array_data, 
        #      '{"", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "","", "", "", "", "", "", "", "", ""}',    
        #      '{"", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "","", "", "", "", "", "", "", "", ""}',
        #     '{"", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "","", "", "", "", "", "", "", "", ""}',
        #     '{"", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "","", "", "", "", "", "", "", "", ""}',
        #     '{"", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "","", "", "", "", "", "", "", "", ""}',
        #     '{"", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "","", "", "", "", "", "", "", "", ""}',
        #     '{"", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "","", "", "", "", "", "", "", "", ""}',
        #     '{"", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "","", "", "", "", "", "", "", "", ""}',
        #     '{"Y", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "","", "", "", "", "", "", "", "", ""}',
        #     '{"", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "","", "", "", "", "", "", "", "", ""}',
        #     '{"", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "","", "", "", "", "", "", "", "", ""}',
        #     '{"", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "","", "", "", "", "", "", "", "", ""}',
        #     '{"", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "","", "", "", "", "", "", "", "", ""}')
        # )
        # conn.commit()

        return jsonify({"name": name}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            cur.close()
            conn.close()

load_known_faces()

@app.route('/learners', methods=['GET'])
def get_data():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('''SELECT lr.learner_id, lr.name, lr.surname, st.sitename, ch.cohortname, lr.lid, lr.email, lr.aug FROM learners as lr
                        join cohorts as ch  using(cohort_id) 
                        join sites as st using(site_id) ''')
    rows = cursor.fetchall()

    cursor.execute('''SELECT cohortname from cohorts''')
    rows2 = cursor.fetchall()

    cursor.execute('''SELECT cohort_id from cohorts''')
    rows3 = cursor.fetchall()

    cursor.execute('''SELECT COUNT(*) AS learner_count
                    FROM learners AS lr
                    JOIN cohorts AS ch ON lr.cohort_id = ch.cohort_id
                    GROUP BY ch.cohort_id, ch.cohortname;''')
    rows4 = cursor.fetchall()


    all = [item[0] for item in rows2]
    allids = [item[0] for item in rows3]
    counts = [item[0] for item in rows4]

    data = [
        {
            "id" : row[0],
            "name": row[1],
            "surname": row[2],
            "site": row[3],
            "cohort": row[4],
            "lid": row[5],
            "email": row[6],
            "attendance": row[7],
            "all": all,
            "allids": allids,
            "counts": counts
        }
        for row in rows
    ]

    cursor.close()
    connection.close()

    return jsonify(data)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '')
    if not query:
        return jsonify({"error": "Search query is required"}), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute('''
        SELECT lr.learner_id, lr.name, lr.surname, st.sitename, ch.cohortname, lr.lid, lr.email, lr.attendance FROM learners as lr
                        join cohorts as ch  using(cohort_id) 
                        join sites as st using(site_id) 
        WHERE lr.name ILIKE %s OR lr.email ILIKE %s OR lr.surname ILIKE %s
    ''', (f'%{query}%',f'%{query}%',f'%{query}%'))

    rows = cursor.fetchall()
    data = [
        { "id" : row[0],
            "name": row[1],
            "surname": row[2],
            "site": row[3],
            "cohort": row[4],
            "lid": row[5],
            "email": row[6],
            "attendance": row[7]}
        for row in rows
    ]

    cursor.close()
    connection.close()

    return jsonify(data)

@app.route('/users', methods=['GET'])
def users():
    id = request.args.get('id')
    month = request.args.get('month')

    connection = get_db_connection()
    cursor = connection.cursor()
    if id != 5000:
        cursor.execute('''SELECT lr.learner_id, lr.name, lr.surname, st.sitename, ch.cohortname, lr.lid, lr.email, lr.aug   FROM learners as lr
                        join cohorts as ch  using(cohort_id) 
                    join sites as st using(site_id) where cohort_id=%s''',(id,))
    else:
        cursor.execute('''SELECT lr.learner_id, lr.name, lr.surname, st.sitename, ch.cohortname, lr.lid, lr.email, lr.aug  FROM learners as lr
                        join cohorts as ch  using(cohort_id) 
                    join sites as st using(site_id)''')
    rows = cursor.fetchall()

    data = [
        {
            "id" : row[0],
            "name": row[1],
            "surname": row[2],
            "site": row[3],
            "cohort": row[4],
            "lid": row[5],
            "email": row[6],
            "attendance": row[7],
        }
        for row in rows
    ]

    cursor.close()
    connection.close()

    return jsonify(data)

@app.route('/data', methods=['GET'])
def get_data_for_date():
    print('fvdf')
    date = request.args.get('date')  
    cohort = request.args.get('cohort')
    if not date:
        return jsonify({"error": "Date is required"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        print(date)

        cursor.execute("SELECT * FROM admin WHERE date = %s and cohort_id = %s", (date,cohort,))

        rows = cursor.fetchall()
        data = [
        {
            "id" : row[0],
            "name": row[1],
            "surname": row[2],
            "site": row[3],
            "cohort": row[4],
            "lid": row[4],
            "email": row[3],
        }
        for row in rows
    ]
        print(data)

        cursor.close()
        conn.close()

        return jsonify(data)

    except psycopg2.Error as e:
        return jsonify({"error": str(e)}), 500
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400

@app.route('/delet/<int:id>', methods=['DELETE'])
def delet(id):
    data = []
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM learners where learner_id = %s", (id,))
    data.append({
                        "status": "ok",
                    })

    connection.commit()

    cursor.close()
    connection.close()

    return jsonify(data)


@app.route('/attendance', methods=['GET'])
def attendance():
    conn = get_db_connection()
    cursor = conn.cursor()

    employee_metrics_query = """
    SELECT
        name,
        COUNT(DISTINCT day) AS days_present,
        SUM(CASE 
            WHEN hour = 8 AND minute <= 5 THEN 1
            ELSE 0
        END) AS on_time,
        SUM(CASE
            WHEN hour = 8 AND minute > 5 THEN 1
            WHEN hour = 9 THEN 1
            ELSE 0
        END) AS late,
        SUM(CASE
            WHEN hour > 9 THEN 1
            ELSE 0
        END) AS very_late,
        SUM(CASE
            WHEN hour > 8 THEN ((hour - 8) * 60) + minute
            WHEN hour = 8 AND minute > 5 THEN (minute - 5)
            ELSE 0
        END) AS cost_to_company_minutes
    FROM attendance
    GROUP BY name;
    """

    attendance_per_day_query = """
    SELECT 
        day,
        COUNT(DISTINCT name) AS employees_present
    FROM attendance
    GROUP BY day
    ORDER BY day;
    """

    daily_late_comers_query = """
    SELECT 
        day,
        COUNT(CASE
            WHEN hour > 8 OR (hour = 8 AND minute > 5) THEN 1
            ELSE NULL
        END) AS late_comers
    FROM attendance
    GROUP BY day
    ORDER BY day;
    """

    cursor.execute(employee_metrics_query)
    employee_metrics = cursor.fetchall()

    cursor.execute(attendance_per_day_query)
    attendance_per_day = cursor.fetchall()

    cursor.execute(daily_late_comers_query)
    daily_late_comers = cursor.fetchall()

    cursor.close()
    conn.close()

    data = {
        "employee_metrics": [
            {
                "name": row[0],
                "days_present": row[1],
                "on_time": row[2],
                "late": row[3],
                "very_late": row[4],
                "cost_to_company_minutes": row[5]
            }
            for row in employee_metrics
        ],
        "attendance_per_day": [
            {"day": row[0], "employees_present": row[1]}
            for row in attendance_per_day
        ],
        "daily_late_comers": [
            {"day": row[0], "late_comers": row[1]}
            for row in daily_late_comers
        ],
    }

    return jsonify(data)


if __name__ == '__main__':
    app.run(debug=False, port=5002)

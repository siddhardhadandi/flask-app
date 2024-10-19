from flask import Flask, render_template, request, redirect, url_for, send_file
import pandas as pd
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'

# Ensure the uploads and outputs folder exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

if not os.path.exists(app.config['OUTPUT_FOLDER']):
    os.makedirs(app.config['OUTPUT_FOLDER'])

allocated_data = []

# Function to load Excel data
def load_excel_data(file):
    data = pd.read_excel(file)
    return data.to_dict(orient='records')

# Allocate students and save to Excel file
def allocate_students_to_benches(students, classrooms, teachers):
    global allocated_data
    allocated_data = []  # Reset the allocated data
    student_count = 0
    current_classroom = 0

    students_sorted = sorted(students, key=lambda x: x['Subject'])

    while student_count < len(students_sorted) and current_classroom < len(classrooms):
        classroom = classrooms[current_classroom]
        teacher = teachers[current_classroom % len(teachers)]  # Assign teachers in a round-robin fashion
        benches_filled = 0
        total_benches = int(classroom['Total Benches'])  # Number of benches in the classroom
        bench_number = 1

        while benches_filled < total_benches and student_count < len(students_sorted):
            student1 = students_sorted[student_count]

            # Try to find a second student with a different subject
            second_student_found = False
            for i in range(student_count + 1, len(students_sorted)):
                student2 = students_sorted[i]
                if student1['Subject'] != student2['Subject']:
                    # Assign both students to the same bench
                    allocated_data.append({
                        'Classroom': classroom['Classroom ID'],
                        'Bench Number': bench_number,
                        'Reg No': student1['Reg No'],
                        'Student Name': student1['Name'],
                        'Subject': student1['Subject'],
                        'Year of Study': student1['Year of Study'],
                        'Teacher Name': teacher['Name']
                    })
                    allocated_data.append({
                        'Classroom': classroom['Classroom ID'],
                        'Bench Number': bench_number,
                        'Reg No': student2['Reg No'],
                        'Student Name': student2['Name'],
                        'Subject': student2['Subject'],
                        'Year of Study': student2['Year of Study'],
                        'Teacher Name': teacher['Name']
                    })
                    students_sorted.pop(i)
                    second_student_found = True
                    break

            if not second_student_found:
                allocated_data.append({
                    'Classroom': classroom['Classroom ID'],
                    'Bench Number': bench_number,
                    'Reg No': student1['Reg No'],
                    'Student Name': student1['Name'],
                    'Subject': student1['Subject'],
                    'Year of Study': student1['Year of Study'],
                    'Teacher Name': teacher['Name']
                })

            bench_number += 1
            benches_filled += 1
            student_count += 1

        current_classroom += 1

    return allocated_data

def save_allocation_to_excel(allocated_data, filename):
    df = pd.DataFrame(allocated_data)
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    df.to_excel(output_path, index=False)
    return output_path

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    classroom_file = request.files['classrooms']
    teacher_file = request.files['teachers']
    student_file = request.files['students']

    classroom_path = os.path.join(app.config['UPLOAD_FOLDER'], classroom_file.filename)
    teacher_path = os.path.join(app.config['UPLOAD_FOLDER'], teacher_file.filename)
    student_path = os.path.join(app.config['UPLOAD_FOLDER'], student_file.filename)

    classroom_file.save(classroom_path)
    teacher_file.save(teacher_path)
    student_file.save(student_path)

    classrooms = load_excel_data(classroom_path)
    teachers = load_excel_data(teacher_path)
    students = load_excel_data(student_path)

    allocated_data = allocate_students_to_benches(students, classrooms, teachers)

    output_filename = 'hall_allocation_with_benches.xlsx'
    output_path = save_allocation_to_excel(allocated_data, output_filename)

    return render_template('allocation.html', 
                           allocated_data=allocated_data, 
                           download_link=url_for('download_file', filename=output_filename))

# New route to serve the search page
@app.route('/open_search_page')
def open_search_page():
    return render_template('search.html')

# Route for searching student or teacher allocation
@app.route('/search_allocation', methods=['POST'])
def search_allocation():
    user_type = request.form.get('user_type')  # Get whether it's a student or teacher
    reg_no_or_id = request.form.get('reg_no_or_id')  # Get the entered reg number or teacher name/ID

    # Load the previously generated allocation Excel
    file_path = os.path.join(app.config['OUTPUT_FOLDER'], 'hall_allocation_with_benches.xlsx')
    data = pd.read_excel(file_path)

    # Logic for searching based on user type
    if user_type == 'student':
        result = data[data['Reg No'].astype(str) == reg_no_or_id]
    elif user_type == 'teacher':
        result = data[data['Teacher Name'].str.contains(reg_no_or_id, case=False, na=False)]

    # Check if the result is found and return the appropriate page
    if result is not None and not result.empty:
        return render_template('search_results.html', allocated_data=result.to_dict(orient='records'), message=None)
    else:
        return render_template('search_results.html', allocated_data=[], message="No allocation found for this ID.")

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)


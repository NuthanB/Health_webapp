import os
import openai
from sqlalchemy import and_
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session
from tempfile import mkdtemp
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, jsonify , send_file
from gtts import gTTS
from datetime import datetime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
import base64




app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.Integer, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gen = db.Column(db.String(1), nullable=False)
    dob = db.Column(db.DateTime, nullable=False)
    address = db.Column(db.Text, nullable=False)
    blood = db.Column(db.String(3), nullable=False)
    disease = db.Column(db.String(150))
    documents = db.relationship('Document', backref='patient', lazy=True)
    medicine_history = db.relationship('MedicineHistory', backref='patient', lazy=True)
    medicine_history = relationship('MedicineHistory', back_populates='patient')

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(255), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.Integer, nullable=False)
    speciality = db.Column(db.String(150))
    rating = db.Column(db.Integer, nullable=False)
    available = db.Column(db.String(150))
    cost = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<Doctor {self.name}>'

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, nullable=False)
    doctor_id = db.Column(db.Integer, nullable=False)
    appointment_date = db.Column(db.String(20), nullable=False)
    appointment_time = db.Column(db.String(10), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    doctor = db.relationship('Doctor', backref='appointments')
    def __repr__(self):
        return f'{self.id}'

class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text)
    side_effects = db.Column(db.Text)
    rating = db.Column(db.Integer)
    medicine_history = relationship('MedicineHistory', back_populates='medicine')

class MedicineHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, ForeignKey('patient.id'), nullable=False)
    medicine_id = db.Column(db.Integer, ForeignKey('medicine.id'), nullable=False)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)
    patient = relationship('Patient', back_populates='medicine_history')
    medicine = relationship('Medicine', back_populates='medicine_history')

class LabTest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    testname = db.Column(db.String(100), nullable=False)
    companyname = db.Column(db.String(100))
    availability = db.Column(db.String(50))
    ratings = db.Column(db.Integer)
    cost = db.Column(db.Integer, nullable=False)

class LabHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    labtest_id = db.Column(db.Integer, db.ForeignKey('lab_test.id'), nullable=False)
    booking_date =  db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(10), nullable=False)
    labtest = db.relationship('LabTest', backref='lab_history')

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

conversation = []
convers = []


app.config.from_pyfile('.env')

openai.api_key = os.getenv("OPENAI_API_KEY")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
   return render_template("index.html")  

@app.route('/profile')
def profile():
    user_id = session.get('user_id')
    if user_id is None:
        return redirect('/login')  # Redirect to login if user is not logged in

    user = Patient.query.get(user_id)
    if user is None:
        return "User not found"

    medicines = MedicineHistory.query.filter_by(patient_id=user_id).all()
    documents = Document.query.filter_by(patient_id=user_id).all()
    appointments = Appointment.query.filter_by(patient_id=user_id).all()
    lab_tests = LabHistory.query.filter_by(patient_id=user_id).all()

    return render_template('profile.html', user=user, medicines=medicines,
                           documents=documents, appointments=appointments, lab_tests=lab_tests)


@app.route('/awareness')
def awaren():
   return render_template('aware.html')

@app.route('/assitance')
@login_required
def assitance():
    welcome_message = "Welcome! Press 1 to book lab appoinments  , Press 2 to book  appoinments with doctors  . Press 3 to buy medicine "
    tts = gTTS(welcome_message)
    audio_file_path = 'static/welcome_message.mp3'
    tts.save(audio_file_path)
    return render_template('assitance.html', conversation=conversation,audio_url=audio_file_path)


@app.route('/clear')
def clear():
    conversation.clear()
    return redirect('/assitance')



@app.route('/submit', methods=['POST'])
def submit():
   user_input = request.form['user_input']
   conversation.append(('user', user_input))
   if  user_input in ['1' ,'2','3']:
       user_input = int(user_input)
       if user_input == 1:
         if len(conversation)>2:
            bot_response = "You have opted for Blood test , enter the date in DD-MM-YYYY format"
            conversation.append(('bot', bot_response)) 
         else:
            bot_response = "Welcome to book your lab test. The different types of tests we offer are: enter the number corresponding-"
            lab_tests = LabTest.query.with_entities(LabTest.testname).all()
            k=1
            tests=[]
            #lab_test_names = [k,test[0] for test in lab_tests]
            for test in lab_tests:
                tests.append([k,test[0]])
                k+=1
            print(tests)
            string=''
            for t in tests:
                string+=str(t[0])+". "+t[1]+"\n"
            lab_tests_list =string
            print(lab)
            bot_response += lab_tests_list
            print(conversation)
            conversation.append(('bot', bot_response))   
            print(conversation)
            
       if user_input == 2:
          bot_response = "Welcome to book your Appointment with the doctors . The different types of speclist we have are: endter the numbers-\n"
          unique_specialties = db.session.query(Doctor.speciality).distinct().all()
          specialties_list = [specialty[0] for specialty in unique_specialties]
          doctors_list = ", ".join(specialties_list)
          print(doctors_list)
          bot_response += doctors_list
          conversation.append(('bot', bot_response))
       if user_input == 3:
           bot_response = "Welcome to buy your medicine , Press 1 for Private Medincine , Press 2 for Government medication"
           conversation.append(('bot', bot_response))   
       if user_input==11:
           bot_response = "You have opted for Blood test , enter the date in DDMMYYYY format"
           conversation.append(('bot', bot_response))   
      

   else:
       if user_input=='21082023':
           bot_response = "booking date confirmed on 21-08-2023 , Please enter time in hours"
           conversation.append(('bot', bot_response))   
       elif user_input=='16 30':
          bot_response='booking confirmed for 16.30 hours'
          conversation.append(('bot',bot_response))
       else:
         bot_response = "please enter valid response" 
         conversation.append(('bot', bot_response)) 

   tts = gTTS(text=bot_response, lang='en')
   tts_path = 'static/response.mp3'
   tts.save(tts_path)  # Save the generated voice response to a file

    # Read audio file as binary and encode as Base64
   with open(tts_path, 'rb') as audio_file:
        audio_data = base64.b64encode(audio_file.read()).decode('utf-8')

   return jsonify(conversation=conversation, audio_data=audio_data)  #

@app.route('/knowaround')
def disease_analysis():
    # Query the database to get the count of each disease
    diseases = db.session.query(Patient.disease, db.func.count(Patient.disease)).group_by(Patient.disease).order_by(db.func.count(Patient.disease).desc()).all()

    # Convert the result into a list of dictionaries
    #diseases_data = [{'disease': row[0], 'count': row[1]} for row in diseases]
    dd={}
    for row in diseases:
        dd[row[0]]=row[1] 
    print(dd)
    dd.pop('None')
    dd.pop('none')
    diseases_data1 = [{'disease': key, 'count':dd[key] } for key in dd]
    return render_template('disease_analysis.html', diseases=diseases_data1)


@app.route('/login',  methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Check if the email exists in the database
        user = Patient.query.filter_by(email=email).first()
        if user and user.password == password:
            # Store the user's data in the session
            session['user_id'] = user.id
            return redirect("/")

        return "Invalid email or password"

    return render_template('login.html')

@app.route('/lab')
def lab():
    return render_template('lab.html')

@app.route('/labs', methods=['GET', 'POST'])
@login_required
def lab_tests():
    user_id = session.get('user_id')
    
    if request.method == 'GET':
        search_term = request.args.get('search', '')
        cost_filter = request.args.get('cost_filter', 'all')
        rating_filter = request.args.get('rating_filter', 'all')
        
        query = db.session.query(LabTest)
        
        if search_term:
            query = query.filter(LabTest.testname.ilike(f'%{search_term}%'))
        
        if cost_filter != 'all':
            min_cost, max_cost = map(int, cost_filter.split('-'))
            query = query.filter(and_(LabTest.cost >= min_cost, LabTest.cost <= max_cost))
        
        if rating_filter != 'all':
            query = query.filter(LabTest.ratings >= int(rating_filter))
        
        lab_tests = query.all()
        
        return render_template('labtest.html', lab_tests=lab_tests, search_term=search_term,
                               cost_filter=cost_filter, rating_filter=rating_filter)
    
    if request.method == 'POST':
        labtest_id = request.form['labtest']
        lab_date = request.form['date']
        lab_time = request.form['time']
        new_lab_history = LabHistory(patient_id=user_id, labtest_id=labtest_id, booking_date=lab_date, time=lab_time)
        print(new_lab_history)
        db.session.add(new_lab_history)
        db.session.commit()
        flash('Lab test booked successfully!', 'success')
        return redirect('/labconf')
    
@app.route('/labconf')
@login_required
def labconf():
        user_id = session.get('user_id')
        most_recent_lab_history = LabHistory.query.filter_by(patient_id=user_id).order_by(LabHistory.id.desc()).first()
        return render_template('labconf.html',most_recent_lab_history=most_recent_lab_history)


@app.route('/lab_history')
@login_required
def lab_history():
    user_id = session.get('user_id')
    patient = Patient.query.get(user_id)
    return render_template('lab_history.html', patient=patient)

@app.route('/medicine', methods=['GET', 'POST'])
@login_required
def medicine():
    user_id = session.get('user_id')
    search_term = request.args.get('search', '')
    cost_filter = request.args.get('cost_filter', '')
    type_filter = request.args.get('type_filter', '')

    query = Medicine.query

    if search_term:
        query = query.filter(Medicine.name.ilike(f'%{search_term}%'))

    if cost_filter == 'asc':
        query = query.order_by(Medicine.price.asc())
    elif cost_filter == 'desc':
        query = query.order_by(Medicine.price.desc())

    if type_filter:
        query = query.filter_by(type=type_filter)

    medicines = query.all()

    if request.method == 'POST':
        medicine_id = request.form['medicine_id']
        selected_medicine = Medicine.query.get(medicine_id)

        new_history = MedicineHistory(patient_id=user_id, medicine_id=medicine_id, purchase_date=datetime.now())
        db.session.add(new_history)
        db.session.commit()

        flash(f"You bought {selected_medicine.name} successfully!", 'success')
        return redirect('/mbill')

    return render_template('medicine.html', medicines=medicines, search_term=search_term)


@app.route('/mbill')
@login_required
def config():
    user_id = session.get('user_id')
    most_recent_medicine_history = MedicineHistory.query.filter_by(patient_id=user_id).order_by(MedicineHistory.id.desc()).first()
    return render_template('mbill.html', most_recent_medicine_history=most_recent_medicine_history)

@app.route('/appointment', methods=['GET', 'POST'])
@login_required
def book_appointment():
    user_id = session.get('user_id')
    unique_specialties = db.session.query(Doctor.speciality).distinct().all()

    if request.method == 'GET':
        search_term = request.args.get('search', '')
        selected_speciality = request.args.get('speciality', '')

        if selected_speciality:
            doctors = Doctor.query.filter_by(speciality=selected_speciality).all()
        elif search_term:
            doctors = Doctor.query.filter(Doctor.name.ilike(f'%{search_term}%')).all()
        else:
            doctors = Doctor.query.all()

        return render_template('appointment.html', doctors=doctors, unique_specialties=unique_specialties)

    if request.method == 'POST':
        doctor_id = request.form['doctor']
        appointment_date = request.form['date']
        appointment_time = request.form['time']

        # Check doctor availability and existing appointments
        doctor = Doctor.query.get(doctor_id)
        existing_appointment = Appointment.query.filter_by(doctor_id=doctor_id,
                                                           appointment_date=appointment_date,
                                                           appointment_time=appointment_time).first()

        if existing_appointment:
            flash('Doctor is not available at the selected time or already booked!', 'danger')
            return redirect('/appointment')

        new_appointment = Appointment(patient_id=user_id, doctor_id=doctor_id,
                                      appointment_date=appointment_date, appointment_time=appointment_time)
        db.session.add(new_appointment)
        db.session.commit()

        flash('Appointment booked successfully!', 'success')
        
        return redirect('/confirmed')  # Redirect to dashboard or any other page

@app.route('/confirmed', methods=['GET', 'POST'])
def confirmed():
    user_id = session.get('user_id')
    most_recent_appointment = Appointment.query.filter_by(patient_id=user_id).order_by(Appointment.id.desc()).first()
    return render_template('confirmed.html', most_recent_appointment=most_recent_appointment)

@app.route('/bmi_calculator', methods=['GET', 'POST'])
def bmi_calculator():
    bmi = None
    if request.method == 'POST':
        weight = float(request.form['weight'])
        height = float(request.form['height'])
        bmi = calculate_bmi(weight, height)
    return render_template('bmi_calculator.html', bmi=bmi)

def calculate_bmi(weight, height):
    return round(weight / (height ** 2), 2)

@app.route('/documents')
@login_required
def documents():
    user_id = session.get('user_id')
    if user_id is None:
        return redirect("/")

    user = Patient.query.get(user_id)
    return render_template('documnets.html', user=user)


@app.route('/upload_document', methods=['GET', 'POST'])
@login_required
def upload_document():
    if request.method == 'POST':
        user_id = session.get('user_id')
        if user_id is None:
            return redirect("/")

        user = Patient.query.get(user_id)

        title = request.form['title']
        description = request.form['description']
        file = request.files['file']

        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            new_document = Document(title=title, description=description, file_path=filepath, patient=user)
            db.session.add(new_document)
            db.session.commit()

            return redirect('/documents')

    return render_template('upload_document.html')



@app.route('/compaines')
def insurance():
   return render_template('insurance_companies.html')


@app.route('/kids')
def kids():
    return render_template('kids.html')

@app.route('/get_kids_story', methods=['POST'])
def get_kids_story():
    prompt = request.form['prompt']

    messages = [
        {"role": "system", "content": "You are a kids storyteller"}
    ]

    if prompt:
        messages.append(
            {"role": "user", "content": prompt}
        )
        chat = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages
        )

        assistant_message = chat.choices[0].message['content']
    else:
        assistant_message = "Please provide a prompt."
    
    my_text = assistant_message
    language = 'en'
    myobj = gTTS(text=my_text, lang=language, slow=False)
    myobj.save("./static/voice.mp3")
    response = {
        "assistant_message": assistant_message,
        "audio_url": "/get_kids_audio"
    }
    return jsonify(response)


@app.route('/get_kids_audio')
def get_kids_audio():
    audio_file_path = "./static/voice.mp3"
    return send_file(audio_file_path, mimetype="audio/mpeg")



@app.route('/adults')
def adults():
    return render_template('adults.html')


@app.route('/adults_kids_story', methods=['POST'])
def get_adults_story():
    prompt = request.form['prompt']

    messages = [
        {"role": "system", "content": "You are a adult storyteller"}
    ]

    if prompt:
        messages.append(
            {"role": "user", "content": prompt}
        )
        chat = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages
        )

        assistant_message = chat.choices[0].message['content']
    else:
        assistant_message = "Please provide a prompt."
    
    my_text = assistant_message
    language = 'en'
    myobj = gTTS(text=my_text, lang=language, slow=False)
    myobj.save("./static/voicead.mp3")
    response = {
        "assistant_message": assistant_message,
        "audio_url": "/get_adults_audio"
    }
    return jsonify(response)


@app.route('/get_adults_audio')
def get_adults_audio():
    audio_file_path = "./static/voicead.mp3"
    return send_file(audio_file_path, mimetype="audio/mpeg")


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        phone = request.form['phone']
        gen = request.form['gen']
        dob_str = request.form['dob']
        dob = datetime.strptime(dob_str, '%Y-%m-%d')
        current_date = datetime.now()
        age = current_date.year - dob.year - ((current_date.month, current_date.day) < (dob.month, dob.day))
        address = request.form['address']
        blood = request.form['blood']
        disease = request.form['disease']

        # Convert the dob string to a datetime object
        dob = datetime.strptime(dob_str, '%Y-%m-%d')

        # Check if the username already exists
        existing_patient = Patient.query.filter_by(username=username).first()
        if existing_patient:
            return "Username already exists. Please choose another."

        new_patient = Patient(username=username, password=password, email=email, phone=phone, age=age, gen=gen, dob=dob, address=address, blood=blood, disease=disease)
        db.session.add(new_patient)
        db.session.commit()

        return redirect("/")

    return render_template('register.html')


@app.route("/logout")
@login_required
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")



if __name__ == '__main__':
   app.run(debug=True)

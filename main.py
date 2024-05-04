import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, send_file
import time
import sys
import webbrowser
from modelHistory import ModelTuner, API_KEY
from datetime import datetime
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import ssl
import os

first_run=True
email_signup=False
email_provided = None
receiver=""
app = Flask('__main__')

print("APP STARTED")
@app.route('/', methods=['GET', 'POST'])
def index():
    global first_run, email_signup, email_provided,receiver, convo
    first_run=True
    email_signup=False
    email_provided = None
    receiver=""
    convo = model.start_chat(history=ModelTuner)
    if request.method == 'POST' and 'terminate_script' in request.form:
        sys.exit()  # Terminate the script
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    global first_run
    global email_provided
    global email_signup
    user_input = request.json.get('user_input')
    
    if first_run:
        if user_input.lower() == 'y':
          first_run=False
          email_provided=False
          return jsonify({'response': "<b>PoultaVet AI:</b> <br>Please enter your email address to receive poultry health alerts."})
          
        elif user_input.lower() == 'n':
          email_provided=True
          first_run=False
          return jsonify({'response': "<b>PoultaVet AI:</b> <br>How may I assist you today?"})
        
        else:
          return jsonify({'response': '<b>PoultaVet AI:</b> <br>Kindly indicate your preferred option by typing "Y" for yes or "N" for no.'})
    
    if not email_provided:
      if "@gmail.com" in user_input or "@outlook.com" in user_input or "@hotmail.com" in user_input or "@icloud.com" in user_input or "@yahoo.com" in user_input:
          global receiver 
          receiver= user_input
          email_provided=True
          email_signup=True
          return jsonify({'response': "<b>PoultaVet AI:</b> <br>Your email has been recorded for future alerts. How may I assist you today?"})

      else:
          return jsonify({'response': "<b>PoultaVet AI:</b> <br>Please enter a valid email to continue the conversation."})
    else:
        try:
            response = handle_user_input(user_input) if user_input else 'Invalid input'
        except Exception as e:
            print(e)
            try:
              time.sleep(15)
              response = handle_user_input(user_input) if user_input else 'Invalid input'
            except Exception as e:
              print(e)
              response = "Sorry, I didn't understand that. Try using different words."
        while "**" in response:
          response = response.replace('**', '<b>',1).replace('**', '</b>',2)
        while "*" in response:
          response = response.replace('*', '<b>',1).replace('*', '</b>',2)
          
        response="<b>PoultaVet AI:</b> <br>"+response
        return jsonify({'response': response})


@app.route('/restart', methods=['POST'])
def restart():
        return jsonify({'message': 'Flask application restarted'})


#Initializing AI model:
genai.configure(api_key=API_KEY)

generation_config = {
    "temperature": 0.9,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 2048,
}

safety_settings = [
  {
    "category": "HARM_CATEGORY_HARASSMENT",
    "threshold": "BLOCK_NONE"
  },
  {
    "category": "HARM_CATEGORY_HATE_SPEECH",
    "threshold": "BLOCK_NONE"
  },
  {
    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "threshold": "BLOCK_NONE"
  },
  {
    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
    "threshold": "BLOCK_NONE"
  },
]

model = genai.GenerativeModel(
    model_name="gemini-1.5-pro-latest",
    generation_config=generation_config,
    safety_settings=safety_settings,
)

convo = model.start_chat(history=ModelTuner)

def generate_pdf(response, save_path='static/Report.pdf'):
    text = response
    pdf_format = []

    def extract_info(text, keywords):
        lines = text.split(",")  # Split the text into lines using comma and space as separator
        for line in lines:
            for keyword in keywords:
                if keyword.lower() in line.lower():
                    pdf_format.append(line.strip())
                    break

    def create_pdf1(data, filename):
        c = canvas.Canvas(filename, pagesize=letter)

        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(300, 750, "PoultaVet AI: Boosting Chicken Health")

        # Logo (scaled down)
        logo_path = "static/oldLogo.png"
        c.drawImage(ImageReader(logo_path), 50, 730, width=60, height=40)

        y_position = 600
        # Content from pdf_format
        c.setFont("Helvetica", 12)
        for item in data:
            if item:  # Check if the item is not an empty string
                c.drawString(50, y_position, item)
                y_position -= 20  # Move to the next line

        c.drawString(100, y_position-30, "-" * 125)
        y_position -= 50

        # Professional Description
        c.setFont("Helvetica-Bold", 12)
        y_position -= 20
        c.drawString(50, y_position, "DISCLAIMER:")
        c.setFont("Helvetica", 12)
        y_position -= 20
        c.drawString(50, y_position, "This report is a prediction generated by PoultaVet AI. It is intended to provide an initial")
        y_position -= 20
        c.drawString(50, y_position, "assessment based on the data provided. However, please note that veterinary consultation")
        y_position -= 20
        c.drawString(50, y_position, "is essential for accurate diagnosis. Any decisions regarding poultry health should be made ")
        y_position -= 20
        c.drawString(50, y_position, "in consultation with a qualified veterinarian.")
        y_position -= 20

        # Footer
        c.setFont("Helvetica", 10)
        current_datetime = datetime.now()
        formatted_datetime = current_datetime.strftime("%A, %I:%M %p, %B %d, %Y")
        c.drawString(50,75, formatted_datetime)
        c.drawCentredString(300, 50, "© 2024 PoultaVet AI Powered by Google's GEMINI")

        c.save()

    # Extracting information using the extract_info function
    keywords = ["Disease:", "Cause:", "Treatment:", "Probability:", "Other possibilities:", "Warning:"]
    extract_info(text, keywords)
    create_pdf1(pdf_format, save_path)


def send_warning_email(receiver):
    # Your email sending logic
    context = ssl.create_default_context()
    message = MIMEMultipart()
    message['From'] = 'poultavetai@gmail.com'
    message['To'] = receiver
    message['Subject'] = 'Disease Outbreak Alert'

    # Email body
    body = """
    <b>
    <span style="color: red;">WARNING:</span><br>
    
    Based on the conversation, it has been identified that one of your chickens may be carrying a contagious disease. 
    It is crucial to isolate this chicken promptly to mitigate the risk of a disease outbreak within your flocks.
    <br><br><br><br><br>
    <div style="text-align: center;">
        <p>&copy; 2024 PoultaVet AI <span style="color: #800000;">Powered by Google's GEMINI</span></p>
    </div>
    </b>
    """
    message.attach(MIMEText(body, 'html'))

    # Attachment - PDF file named Report.pdf in the same directory
    attachment_path = os.path.join(os.getcwd(), 'static/Report.pdf')
    with open(attachment_path, 'rb') as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header(
        'Content-Disposition',
        f'attachment; filename=Report.pdf'
    )
    message.attach(part)

    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    sender_email = 'poultavetai@gmail.com'
    password = 'rpjhskofdpmeepib'
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls(context=context)
        server.login(sender_email, password)
        server.send_message(message)

def handle_user_input(user_input):
    convo.send_message(user_input)
    response = convo.last.text
    with open('responses.txt','a') as file:
      file.write(f"User: {user_input}\n")
      file.write(f"Chatbot: {response}\n")
      file.write(f"\n")
      file.close()
    if "warning:" in response.lower():
      generate_pdf(response)
      print(response)
      if email_signup:
        send_warning_email(receiver)
      indexing=response.lower().find("warning:")
      response=response[:indexing]+"<br><br>"+response[indexing:]
         
    if "disease:" in response.lower():
      indexing=response.lower().find("disease:")
      response=response[:indexing]+"<br>"+response[indexing:]
    
    if "cause:" in response.lower():
      indexing=response.lower().find("cause:")
      response=response[:indexing]+"<br><br>"+response[indexing:]
      
    if "treatment:" in response.lower():
      indexing=response.lower().find("treatment:")
      response=response[:indexing]+"<br><br>"+response[indexing:]
    
    if "probability:" in response.lower():
      indexing=response.lower().find("probability:")
      response=response[:indexing]+"<br><br>"+response[indexing:]
      
    if "other possibilities:" in response.lower():
      indexing=response.lower().find("other possibilities:")
      response=response[:indexing]+"<br><br>"+response[indexing:]
      
    return response

        


if __name__ == '__main__':
    webbrowser.open('http://127.0.0.1:5000')
    app.run(debug=False, port=5000)
    

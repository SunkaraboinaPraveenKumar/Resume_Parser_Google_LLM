from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
import os
import json
from PyPDF2 import PdfReader
from dotenv import load_dotenv  # Load dotenv to read .env file
import re

# Load environment variables from the .env file
load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

app = Flask(__name__)

model = genai.GenerativeModel("models/gemini-1.5-pro")



def clean_json(response):
    # Remove any extra non-JSON text or markdown-like markers
    response = response.replace("```json", "").replace("```", "").strip()

    # Remove any trailing content after the JSON closes
    last_brace_index = response.rfind("}")
    if last_brace_index != -1:
        response = response[:last_brace_index + 1]

    # Fix common JSON formatting issues (like missing commas between key-value pairs)
    response = re.sub(r'(?<=\})\s*(?=\{)', ',', response)  # Add missing commas between objects
    response = re.sub(r'(?<=\])\s*(?=\[)', ',', response)  # Add missing commas between arrays

    return response

def resume_details(resume):
    prompt = f"""
      You are resume parsing assistant. Given the following resume text, extract all the important details and return them in a well structured JSOn format.
      The resume text is as follows:
      {resume}
      Extract and include the following:
      - Full Name
      - Contact Number
      - Email Address
      - Location
      - Skills (Technical and Non-Technical, separately if possible)
      - Education
      - Work Experience(including company name, role and responsibilities)
      - Certifications
      - Languages spoken
      - Suggested Resume Category(based on the skills and experience)
      - Recommended Job Roles (based on the candidate's skills and experience)
    
      Return the response in JSON format.
      """
    # prompt with detailed request
    response = model.generate_content(prompt).text
    return response


# api end points
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload_resume",methods=["POST"])
def upload_resume():
    if 'resume' not in request.files:
        return jsonify({"error":"No file uploaded"})

    file = request.files['resume']

    if file.filename == '':
        return jsonify({"error": "No file Selected"})

    if file and file.filename.endswith('.pdf'):
        text = ""
        reader=PdfReader(file)

        for page in reader.pages:
            text += page.extract_text()
        response = resume_details(text)

    cleaned_response = clean_json(response)
    data = json.loads(cleaned_response)
    full_name = data.get("Full Name")
    contact_number = data.get("Contact Number")
    email = data.get("Email Address")
    location = data.get("Location")

    skills = data.get("Skills", {})
    technical_skills = skills.get("Technical Skills", [])
    non_technical_skills = skills.get("Non-Technical Skills", [])
    technical_skills_str = ", ".join(technical_skills)
    non_technical_skills_str = ", ".join(non_technical_skills)
    education_list = data.get("Education", [])
    work_experience_list = data.get("Work Experience", [])
    certifications_list = data.get("Certifications", [])
    languages_spoken_list = data.get("Languages spoken", [])
    education_str = " ".join([
        f"{edu.get('Degree', '')} in {edu.get('University', '')} (Graduated:{edu.get('Graduation Date', '')})" for edu
        in education_list
    ])
    work_experience_str = "\n".join([
        f"{job.get('Job Title', 'N/A')} at {job.get('Company Name', 'N/A')} ({job.get('Years of Experience', 'N/A')})\nResponsibilities:\n{job.get('Responsibilities', 'N/A')}"
        for job in work_experience_list
    ])
    suggested_resume_category=data.get("Suggested Resume Category")
    recommended_job_roles_str=", ".join(data.get("Recommended Job Roles",[]))

    return render_template("index.html",
                           full_name=full_name,
                           contact_number=contact_number,
                           email_address=email,
                           location=location,
                           technical_skills=technical_skills_str,
                           non_technical_skills=non_technical_skills_str,
                           education=education_str,
                           work_experience=work_experience_str,
                           certifications=certifications_list,
                           language=languages_spoken_list,
                           suggested_resume_category=suggested_resume_category,
                           recommended_job_roles=recommended_job_roles_str
                           )



if __name__ == "__main__":
    app.run(debug=True)

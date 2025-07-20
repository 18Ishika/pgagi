import streamlit as st
import google.generativeai as genai
import json
import re
from datetime import datetime

# Page config
st.set_page_config(
    page_title="TalentScout Hiring Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS
st.markdown("""
<style>
/* Your CSS remains unchanged, keep as is */
</style>
""", unsafe_allow_html=True)


class HiringAssistant:
    def __init__(self):
        self.candidate_info = {}
        self.conversation_stage = "greeting"
        self.required_fields = ["name", "email", "phone", "experience", "position", "tech_stack"]
        self.current_field = 0

    def get_candidate_name(self):
        name = self.candidate_info.get('name', '')
        if name:
            return name.split()[0]
        return ""

    def get_gemini_response(self, user_input, context=""):
        try:
            if not st.session_state.get('gemini_api_key'):
                return "Please enter your Google Gemini API key in the sidebar to continue."
            genai.configure(api_key=st.session_state.gemini_api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            candidate_name = self.get_candidate_name()
            name_context = f" The candidate's name is {candidate_name}." if candidate_name else ""

            if self.conversation_stage == "greeting":
                system_prompt = f"""You are a friendly hiring assistant for TalentScout recruitment agency. 
Hello, I am the TalentScout Hiring Assistant. I'll help you with your application today. 
I'll ask for some basic information and a few technical questions. 
Let's start by getting your full name. Keep it brief and professional."""
            elif self.conversation_stage == "collecting_info":
                field_prompts = {
                    "name": "Ask for their full name professionally",
                    "email": f"Thank {candidate_name if candidate_name else 'them'} and ask for their email address",
                    "phone": f"Great! Now ask {candidate_name if candidate_name else 'them'} for their phone number",
                    "experience": f"Perfect! Ask {candidate_name if candidate_name else 'them'} how many years of experience they have in technology",
                    "position": f"Excellent! Ask {candidate_name if candidate_name else 'them'} what position they're interested in applying for",
                    "tech_stack": f"Wonderful! Ask {candidate_name if candidate_name else 'them'} to list their technical skills"
                }
                current_field_name = self.required_fields[self.current_field]
                system_prompt = f"""You are collecting candidate information for a tech recruitment process. 
{field_prompts.get(current_field_name, 'Ask for the information')}. 
Be friendly but brief.{name_context}"""
            elif self.conversation_stage == "technical_questions":
                tech_stack = self.candidate_info.get('tech_stack', '')
                system_prompt = f"""Based on {candidate_name}'s tech stack: "{tech_stack}", generate 3-4 relevant technical questions. 
Make them practical interview questions. Format as a numbered list. Be encouraging.{name_context}"""
            else:
                system_prompt = f"""You are a helpful hiring assistant. Respond appropriately and professionally.{name_context}"""

            full_prompt = system_prompt
            if context:
                full_prompt += f"\nContext: {context}"
            full_prompt += f"\nCandidate message: {user_input}"

            response = model.generate_content(full_prompt)
            return response.text.strip()

        except Exception:
            return "Sorry, I'm having trouble connecting to the AI service. Please check your API key."

    def extract_info_from_response(self, user_input, field_type):
        user_input = user_input.strip()
        if field_type == "email":
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            match = re.search(email_pattern, user_input)
            return match.group() if match else user_input
        elif field_type == "phone":
            digits_only = re.sub(r'\D', '', user_input)
            return digits_only
        elif field_type == "experience":
            numbers = re.findall(r'\d+\.?\d*', user_input)
            return numbers[0] if numbers else user_input
        return user_input

    def process_message(self, user_input):
        if any(word in user_input.lower() for word in ['exit', 'quit', 'bye', 'goodbye', 'stop']):
            candidate_name = self.get_candidate_name()
            return f"Thank you{', ' + candidate_name if candidate_name else ''}! Our team will review your information and get back to you soon."

        if self.conversation_stage == "greeting":
            # Capture the candidate's name
            field_type = "name"
            extracted_info = self.extract_info_from_response(user_input, field_type)
            self.candidate_info[field_type] = extracted_info
            self.conversation_stage = "collecting_info"
            return self.get_gemini_response("Continue collecting information")

        elif self.conversation_stage == "collecting_info":
            if self.current_field < len(self.required_fields):
                field_name = self.required_fields[self.current_field]
                extracted_info = self.extract_info_from_response(user_input, field_name)
                self.candidate_info[field_name] = extracted_info
                self.current_field += 1
                if self.current_field >= len(self.required_fields):
                    self.conversation_stage = "technical_questions"
                    summary = self.create_summary()
                    tech_questions = self.get_gemini_response("Generate technical questions")
                    return f"{summary}\n**Technical Assessment:**\n{tech_questions}"
                return self.get_gemini_response("Continue collecting information")

        elif self.conversation_stage == "technical_questions":
            self.candidate_info['technical_answers'] = user_input
            self.conversation_stage = "completed"
            candidate_id = self.save_candidate_data()
            conclusion = self.get_gemini_response("Thank you for completing the assessment")
            return f"**Assessment Complete!**\n{conclusion}\n**Application ID:** {candidate_id}\n**Contact Email:** {self.candidate_info.get('email', 'N/A')}"

        else:
            return self.get_gemini_response(user_input)

    def create_summary(self):
        info = self.candidate_info
        candidate_name = self.get_candidate_name()
        return f"""**Information Summary for {candidate_name if candidate_name else 'Candidate'}:**
• Name: {info.get('name', 'N/A')}
• Email: {info.get('email', 'N/A')}
• Phone: {info.get('phone', 'N/A')}
• Experience: {info.get('experience', 'N/A')} years
• Position: {info.get('position', 'N/A')}
• Tech Stack: {info.get('tech_stack', 'N/A')}

Great! I have all your information."""

    def save_candidate_data(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        candidate_id = f"TS{timestamp[-6:]}"
        self.candidate_info['candidate_id'] = candidate_id
        self.candidate_info['timestamp'] = datetime.now().isoformat()

        # Store JSON in session_state only for download
        st.session_state['download_json'] = json.dumps(self.candidate_info, indent=2)

        return candidate_id


def main():
    st.title("TalentScout Hiring Assistant")
    if 'assistant' not in st.session_state:
        st.session_state.assistant = HiringAssistant()
        st.session_state.messages = []

    stage_progress = {
        "greeting": 20,
        "collecting_info": 40 + (st.session_state.assistant.current_field / 6) * 40,
        "technical_questions": 85,
        "completed": 100
    }
    progress = stage_progress.get(st.session_state.assistant.conversation_stage, 0)
    st.progress(progress / 100)

    with st.sidebar:
        st.markdown("### Configuration")
        api_key = st.text_input("Google Gemini API Key:", type="password")
        if api_key:
            st.session_state.gemini_api_key = api_key
            st.success("API Key configured!")
        else:
            st.warning("Enter your API key to start")
        st.markdown("### Progress")
        current_stage = st.session_state.assistant.conversation_stage.replace('_', ' ').title()
        st.write(f"**Stage:** {current_stage}")
        st.write(f"**Progress:** {progress:.0f}%")
        if st.session_state.assistant.candidate_info:
            st.markdown("### Candidate Info")
            info = st.session_state.assistant.candidate_info
            if info.get('name'):
                st.write(f"Name: {info['name']}")
            if info.get('position'):
                st.write(f"Position: {info['position']}")
        if st.button("Start New Interview"):
            for key in ['assistant', 'messages', 'download_json']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    for message in st.session_state.messages:
        if message['role'] == 'user':
            st.markdown(f"""
            <div class="chat-message user-message">
                <strong>You:</strong><br>{message["content"]}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="chat-message bot-message">
                <strong>TalentScout Assistant:</strong><br>{message["content"]}
            </div>
            """, unsafe_allow_html=True)

    user_input = st.chat_input("Type your message..." if st.session_state.get('gemini_api_key') else "Enter API key first")
    if user_input and st.session_state.get('gemini_api_key'):
        st.session_state.messages.append({"role": "user", "content": user_input})
        if len(st.session_state.messages) == 1:
            response = st.session_state.assistant.get_gemini_response("Hello")
        else:
            response = st.session_state.assistant.process_message(user_input)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

    if not st.session_state.messages:
        if st.session_state.get('gemini_api_key'):
            st.markdown("""
            <div class="chat-message bot-message">
                <strong>TalentScout Assistant:</strong><br>
                Hello! I'm ready to help with your job application.
                I'll collect some information about you and ask technical questions.
                <br><br>
                Type "Hi" to get started!
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="info-box">
                <strong>Welcome to TalentScout!</strong><br><br>
                To get started:<br>
                1. Get your free API key from Google AI Studio<br>
                2. Enter it in the sidebar<br>
                3. Start chatting!
            </div>
            """, unsafe_allow_html=True)

    if st.session_state.assistant.conversation_stage == "completed" and 'download_json' in st.session_state:
        st.download_button(
            label="📥 Download your application JSON",
            data=st.session_state['download_json'],
            file_name="application.json",
            mime="application/json",
        )


if __name__ == "__main__":
    main()

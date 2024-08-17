from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.core.text import LabelBase
from kivy.clock import mainthread
import pandas as pd
import os
import google.generativeai as genai

# Read the API key from file
with open('api.txt', 'r') as file:
    api_key = file.read().strip()

GOOGLE_API_KEY = api_key
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')


class FileChoosePopup(Popup):
    def __init__(self, callback, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback

    def on_select(self, filechooser):
        selected_file = filechooser.selection
        if selected_file:
            self.callback(selected_file[0])
            self.dismiss()


class MyWidget(Screen):
    def show_filechooser(self):
        popup = FileChoosePopup(self.on_file_selected)
        popup.open()

    def on_file_selected(self, file_path):
        self.ids.file_label.text = f'Selected File: {os.path.basename(file_path)}'
        self.selected_file_path = file_path

    def on_submit(self):
        # Check if input field is not empty
        input_text = self.ids.text_input.text.strip()
        if input_text:
            questions = [q.strip() for q in input_text.split('\n') if q.strip()]
        elif hasattr(self, 'selected_file_path'):
            try:
                if self.selected_file_path.endswith('.csv'):
                    df = pd.read_csv(self.selected_file_path)
                elif self.selected_file_path.endswith(('.xls', '.xlsx')):
                    df = pd.read_excel(self.selected_file_path)
                else:
                    print("Unsupported file format.")
                    return

                questions = df['Questions'].tolist()
            except Exception as e:
                print(f"Error reading file: {e}")
                return
        else:
            print('No input provided.')
            return

        self.total_questions = len(questions)
        self.ids.progress_bar.max = self.total_questions
        self.ids.progress_bar.value = 0
        self.ids.progress_label.text = 'Progress: 0%'
        
        self.manager.get_screen('result_screen').initialize_questions(questions)
        self.manager.current = 'result_screen'


class ResultScreen(Screen):
    def initialize_questions(self, questions):
        self.questions = questions
        self.current_question_index = 0
        self.process_next_question()

    @mainthread
    def process_next_question(self):
        if self.current_question_index < len(self.questions):
            question = self.questions[self.current_question_index]
            self.add_question_answer(self.current_question_index + 1, question)
            self.current_question_index += 1

            # Update progress bar
            main_screen = self.manager.get_screen('main_screen')
            progress = self.current_question_index
            total = len(self.questions)
            percentage = (progress / total) * 100
            main_screen.ids.progress_bar.value = progress
            main_screen.ids.progress_label.text = f'Progress: {progress}/{total} ({int(percentage)}%)'

            # Schedule the next question processing
            self.process_next_question()
        else:
            # Final update when all questions are processed
            main_screen = self.manager.get_screen('main_screen')
            total = len(self.questions)
            main_screen.ids.progress_bar.value = total
            main_screen.ids.progress_label.text = f'Processing Complete: {total}/{total} ({100}%)'

    @mainthread
    def add_question_answer(self, no, question):
        try:
            response = model.generate_content(f"{question}")
            answer_text = response.text

            label_question = Label(text=f"[b][color=00ff00]Q{no}:[/color] {question}[/b]", markup=True,
                                   size_hint_y=None, text_size=(self.width * 0.9, None))
            label_question.bind(width=lambda *x: label_question.setter('text_size')(label_question, (label_question.width * 0.9, None)))
            label_question.bind(texture_size=lambda *x: label_question.setter('height')(label_question, label_question.texture_size[1] + 10))

            label_answer = Label(text=f"[color=ffffff]{answer_text}[/color]", markup=True, size_hint_y=None, text_size=(self.width * 0.9, None))
            label_answer.bind(width=lambda *x: label_answer.setter('text_size')(label_answer, (label_answer.width * 0.9, None)))
            label_answer.bind(texture_size=lambda *x: label_answer.setter('height')(label_answer, label_answer.texture_size[1] + 10))

            layout = self.ids.question_layout
            layout.add_widget(label_question)
            layout.add_widget(label_answer)
        except Exception as e:
            print(f"Error generating answer: {e}")


class MyApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MyWidget(name='main_screen'))
        sm.add_widget(ResultScreen(name='result_screen'))
        return sm


if __name__ == '__main__':
    MyApp().run()

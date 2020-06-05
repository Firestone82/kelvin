import os
import glob
import datetime
import subprocess
import lxml.html as html
import re

from django.db import models

BASE = "exams"


class Exam:
    def __init__(self, exam_id):
        self.id = exam_id
        self.students = []
        self.begin = None
        self.dir = os.path.join(BASE, exam_id)
        self.subject = exam_id.split('/')[0]
        self.questions = None

        try:
            with open(os.path.join(self.dir, "description")) as f:
                lines = [i.strip() for i in f.read().splitlines()]
                self.begin = datetime.datetime.strptime(lines[0], "%d. %m. %Y %H:%M")
                self.students = lines[1:]
        except FileNotFoundError as e:
            pass

    def is_finished(self):
        return os.path.exists(os.path.join(self.dir, "finished"))

    def finish(self):
        with open(os.path.join(self.dir, "finished"), "w")as f:
            f.write("")

    def save_answer(self, student, question_num, answer):
        base = os.path.join(self.dir, student)
        try:
            os.mkdir(base)
        except FileExistsError:
            pass
        with open(os.path.join(base, str(question_num)), "w") as f:
            f.write(answer)

    def get_questions(self):
        if self.questions:
            return self.questions

        with open(os.path.join(BASE, self.id, "assignment.md")) as markdown:
            p = subprocess.Popen(["pandoc", "--self-contained"], stdout=subprocess.PIPE, stdin=subprocess.PIPE, cwd=self.dir)
            out = p.communicate(input=markdown.read().encode('utf-8'))
            out = out[0].decode('utf-8')
            root = html.fromstring(out)
            questions = root.cssselect('body > ol > li')

            def strip(s):
                s = re.sub(r'^<li>', '', s)
                s = re.sub(r'<li>$', '', s)
                return s

            questions = [strip(html.tostring(question, pretty_print=True).decode('utf-8')) for question in questions]

            self.questions = questions
            return questions

    def get_answers(self, student):
        base_dir = os.path.join(BASE, self.id, student)
        answers = []
        for i in range(1, len(self.get_questions()) + 1):
            answer = ""
            try:
                with open(os.path.join(base_dir, str(i))) as f:
                    answer = f.read()
            except FileNotFoundError:
                pass
            answers.append(answer)

        return answers


def all_exams():
    exams = []
    for d in glob.glob(BASE + "/**/description", recursive=True):
        d = d[len(BASE)+1:]
        exams.append(Exam(os.path.dirname(d)))
    return exams
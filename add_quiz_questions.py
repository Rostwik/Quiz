import os

from dotenv import load_dotenv


def add_quiz_questions():
    load_dotenv()
    dic_q = {}
    path = os.getenv('QUIZ_FILE_PATH')

    if not path:
        path = "files/quiz.txt"

    with open(path, "r", encoding="KOI8-R") as file:
        file_contents = file.read()

    separated_content = file_contents.split('\n\n\n')

    question, answer = '', ''

    for question in separated_content:
        question_components = question.split('\n\n')
        for item in question_components:
            if 'Вопрос' in item:
                symbol_position = item.find(':') + 1
                question = item[symbol_position:]
            if 'Ответ' in item:
                symbol_position = item.find(':') + 1
                answer = item[symbol_position:]
            if answer and question:
                dic_q[question] = answer

    return dic_q


if __name__ == '__main__':
    add_quiz_questions()

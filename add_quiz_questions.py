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

    sep_box = file_contents.split('\n\n\n')

    new_q, new_a = '', ''
    for box in sep_box:
        boxter = box.split('\n\n')
        for item in boxter:
            if 'Вопрос' in item:
                q = item.find(':') + 1
                new_q = item[q:]
            if 'Ответ' in item:
                a = item.find(':') + 1
                new_a = item[a:]
            if new_a and new_q:
                dic_q[new_q] = new_a

    return dic_q


if __name__ == '__main__':
    add_quiz_questions()

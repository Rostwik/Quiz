def get_quiz_questions(path='files/quiz.txt'):
    quiz = {}

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
                quiz[question] = answer

    return quiz


if __name__ == '__main__':
    get_quiz_questions()

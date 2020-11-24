import json
import re
import statistics

import nltk
import numpy as np
import pymorphy2
from nameko.rpc import RpcProxy, rpc
from nameko.web.handlers import http
from nltk.corpus import stopwords
from werkzeug.wrappers import Request

nltk.download("stopwords")

global_tags = [
    {
        "tag": "Web",
        "aliases": ["javascript", "разработка", "css", "react", "angular", "web", "php", "vue", "программирование", "typescript"]
    },
    {
        "tag": "Gamedev",
        "aliases": ["gamedev", "игры", "геймдев", "unity", "unity3d", "c#", "геймдизайн", "game"]
    },
    {
        "tag": "Mobile",
        "aliases": ["android", "ios", "swift", "мобильная", "разработка", "kotlin", "android", "мобильные", "ios", "flutter", "xamarin"]
    },
    {
        "tag": "Robot",
        "aliases": ["роботы", "робототехника", "искусственный", "интеллект", "дроны", "nasa", "марс", "будущее", "arduino", "ros", "квадрокоптер", ]
    },
    {
        "tag": "DevOps",
        "aliases": ["devops", "kubernetes", "docker", "ansible", "k8s", "gitlab", "слёрм", "open", "source", "ci", "cd", "linux"]
    },
    {
        "tag": "QA",
        "aliases": ["тестирование", "qa", "automation", "testing", "selenium", "heisenbug", "автоматизация", "тестирования"]
    },
    {
        "tag": "DataScience",
        "aliases": ["big", "data", "science", "machine", "learning", "машинное", "обучение", "mining", "анализ", "данных", "большие", "данные", "python", "hadoop", "bigdata"]
    },
    {
        "tag": "UI",
        "aliases": ["интерфейсы", "юзабилити", "дизайн", "ux", "ui", "интерфейс"]
    },
    {
        "tag": "Java",
        "aliases": ["java", "kotlin",  "android", "spring", "boot", "программирование", "jvm", "spring", "jpoint", "j2me", "mobile", "midlets", "nokia", "sun", "javafx", "cldc"]
    },
    {
        "tag": "PHP",
        "aliases": ["php", "laravel", "symfony", "yii", "web"]
    },
    {
        "tag": "Python",
        "aliases": ["python", "машинное", "обучение", "machine", "learning", "python3", "data", "science", "django", "tensorflow", "pandas", "flask"]
    },
    {
        "tag": "Csharp",
        "aliases": ["c#", "microsoft", "asp.net", "azure", ".net", "core", "unity3d", "unity", "wpf", "visual", "studio", "xamarin", "xamarin.forms", "android", "xamarincolumn", "ios", "xamarin.android"]
    },
    {
        "tag": "Cplus",
        "aliases": ["c++", "pvs-studio", "c", "программирование", "си++", "c++11", "qt", "qml", "qt5", "qt4"]
    },
    {
        "tag": "CSS",
        "aliases": ["css", "css3", "javascript", "html", "html5", "браузеры", "react", "angular", "es6"]
    },
    {
        "tag": "HTML",
        "aliases": ["javascript", "css", "html5", "html", "react", "браузеры", "angular", "фронтенд", "es6", "vue"]
    },
    {
        "tag": "JavaScript",
        "aliases": ["javascript", "разработка", "react", "angular", "vue", "css", "фронтенд", "typescript", "программирование", "es6"]
    },
    {
        "tag": "React",
        "aliases": ["react", "javascript", "react.js", "redux", "reactjs", "разработка", "frontend", "native", "typescript", "web"]
    },
    {
        "tag": "Angular",
        "aliases": ["angular", "angularjs", "javascript", "typescript", "angular2",  "react", "frontend", "rxjs", "node", "js"]
    },
    {
        "tag": "Kotlin",
        "aliases": ["kotlin", "java", "android", "jetbrains",  "котлин", "jvm", "coroutines"]
    }
]


class EventThemeAnalyzer:
    # Vars

    name = "event_theme_analyzer"
    tag_das = RpcProxy("tag_das")
    stop_words = stopwords.words("russian")
    logger_rpc = RpcProxy("logger")
    morph = pymorphy2.MorphAnalyzer()

    # array of arrays fro tags where each inner array is a subset of aliases for tag

    # Logic

    def _preprocess(self, text) -> dict:
        text = text.lower()
        text = re.sub(r"""[,.;@?!&$/]+ \ *""", " ", text, flags=re.VERBOSE)
        text = re.sub(r"^\s+|\n|\r|\t|\s+$", "", text)
        text = " ".join([word for word in text.split(
            " ") if (word not in self.stop_words)])
        text = " ".join([t for t in text.split(" ") if len(t) > 0])
        text = " ".join(
            [self.morph.parse(word)[0].normal_form for word in text.split(" ")])
        return text

    def _analyze(self, text):
        text = self._preprocess(text)

        print("TEXT:\n{}\n\n".format(text))

        words = text.split(" ")

        tags = {}

        for word in words:
            # TODO: replace this with call of tag_das
            selected_tags = []

            for tag in global_tags:
                if word in tag["aliases"]:
                    print("appending {}".format(tag["tag"]))
                    selected_tags.append(tag["tag"])

            # try:
            # selected_tags = self.tag_das.get_tags_by_alias(word)
            # except:
            # self.logger_rpc.log(
            # self.name, self._analyze.__name__, text, "Error", "Can't get tags from tag_das")
            # continue

            for tag in selected_tags:
                if tag in tags.keys():
                    tags[tag] += 1
                else:
                    tags[tag] = 1

        tag_num = np.sum([v for _, v in tags.items()])

        for key, value in tags.items():
            tags[key] = float(value / tag_num)

        print("Tags: {} ".format(tags))

        if len(tags) == 0:
            return []

        mean = statistics.mean([tags[key] for key in tags.keys()])

        print(mean)

        result = []

        for tag in tags.keys():
            if tags[tag] >= mean:
                result.append(tag)

        return result

    # API

    @http("GET", "/preprocess")
    def preprocess_handler(self, request: Request):
        return 200, self._preprocess(request.get_data(as_text=True))

    @http("POST", "/analyze")
    def analyze_handler(self, request: Request):
        description = request.get_data(as_text=True)

        return 200, json.dumps(self._analyze(description), ensure_ascii=False)

    @rpc
    def analyze_events(self, events):
        self.logger_rpc.log(self.name, self.analyze_events.__name__,
                            events, "Info", "Starting analizing")

        for event in events:
            event["tags"].extend(self._analyze(event["description"]))

        self.logger_rpc.log(
            self.name, self.analyze_events.__name__, events, "Info", "Analizing ended")
        return events

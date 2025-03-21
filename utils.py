import re

replace = {
    "hina": "heena",
    "vtuber": "v tuber",
    "vtubing": "v tubing",
    "anime": "Annie-May",
    "(^ai| ai)[ |,|.|!|]": " Aey I ",
    "(^vr| vr)[ |,|.|!|]": " v r ",
    "3d": "three dee",
    "(^loli| loli)[ |,|.|!|]": "lawly",
    "blockchain": "block chain",
    "cryptocurrenc": "crypto currenc",
    "dayo": "dyeo",
    "vshojo": "v sho joe",
    "(^cpu| cpu)[ |,|.|!|]": " c p u ",
    "(^gpu| gpu)[ |,|.|!|]": " g p u ",
    "(^irl| irl)[ |,|.|!|]": " i r l ",
    "(^url| url)[ |,|.|!|]": " u r l ",
    "(^tts| tts)[ |,|.|!|]": " t t s ",
    "zentreya": "zen treya",
    "slimenetwork": "slime network",
    "berch": "burch",
    "'": "",
}

replace_response = {
    "\n": ", "
}

def replace_all(text: str):
    text = text.lower()
    # rep = dict((re.escape(k), v) for k, v in replace.items())
    for k, v in replace.items():
        text = re.sub(k, v, text)
    return text
    # pattern = re.compile("|".join(rep.keys()))
    # return pattern.sub(lambda m: rep[re.escape(m.group(0))], text)

def replace_all_response(text: str):
    text = text.lower()
    rep = dict((re.escape(k), v) for k, v in replace_response.items()) 
    pattern = re.compile("|".join(rep.keys()))
    return pattern.sub(lambda m: rep[re.escape(m.group(0))], text)

# the main thing is ai is ai. ai is coolai 